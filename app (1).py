"""AI Quest: interactive quiz game for AI Units I and II (DSC401-6).
Student: Joel | Reg. No. 2441323
Run with:  streamlit run app.py
"""
import random
import time

import streamlit as st

from questions import QUESTIONS, TOPICS

NAME, REG = "Joel", "2441323"
BASE = {"easy": 10, "medium": 15, "hard": 20}
TL = {"easy": 30, "medium": 45, "hard": 60}
TREE = "      A\n     / \\\n    B   C\n   / \\ / \\\n  D  E F  G"
BADGES = {
    "first": ("🥇 First Blood", "Got your first answer right"),
    "streak": ("🔥 On Fire", "3 correct answers in a row"),
    "quick": ("⚡ Quick Thinker", "Answered correctly with 70% of the time left"),
    "hard": ("🧗 Hard Mode Hero", "Solved a hard question"),
    "pure": ("🧠 Pure Logic", "Finished a round without any lifeline"),
    "master": ("🌳 Search Master", "Scored 90% or more in a round"),
}

st.set_page_config(page_title="AI Quest", page_icon="🌳", layout="wide")
s = st.session_state


@st.cache_resource
def leaderboard():
    return []  # shared by every visitor while the app is running


def extra(q):
    if "pairs" in q:
        return 30
    if "accept" in q or q["fmt"] in ("Problem-solving", "Scenario"):
        return 15
    return 0


def norm(t):
    return "".join(c for c in str(t).lower() if c.isalnum())


def init():
    s.setdefault("screen", "setup")
    s.setdefault("badges", set())
    s.setdefault("score", 0)
    s.setdefault("max_xp", 1)


def start(name, count, diff, timer):
    pool = [q for q in QUESTIONS if diff == "mixed" or q["diff"] == diff]
    n = len(pool) if count == "all" else min(int(count), len(pool))
    qs = random.sample(pool, n)
    s.update(screen="play", name=name or NAME, qs=qs, i=0, score=0, streak=0, best=0, correct=0,
             res=[], life=dict(fifty=2, hint=3, time=2, skip=1), used_life=False, timer=timer,
             badges=set(), saved=False, diff_label=diff, max_xp=sum(BASE[q["diff"]] * 1.5 for q in qs))
    new_cur()


def new_cur():
    q = s.qs[s.i]
    limit = TL[q["diff"]] + extra(q)
    order = list(range(len(q["opts"]))) if "opts" in q else []
    if order and not q.get("keep"):
        random.shuffle(order)
    rorder = random.sample(range(len(q["pairs"])), len(q["pairs"])) if "pairs" in q else []
    s.cur = dict(limit=limit, deadline=time.time() + limit, hint=False, fifty=False, removed=[],
                 locked=False, res=None, t0=time.time(), order=order, rorder=rorder)


def resolve(kind, payload=None):
    c = s.cur
    if c["locked"]:
        return
    c["locked"] = True
    q = s.qs[s.i]
    ratio = 0.0
    if kind == "choice":
        ratio = 1.0 if payload == q["ans"] else 0.0
    elif kind == "fill":
        ratio = 1.0 if any(norm(a) == norm(payload) for a in q["accept"]) else 0.0
    elif kind == "match":
        ratio = sum(1 for k, v in enumerate(payload) if v == q["pairs"][k][1]) / len(q["pairs"])
    left = max(0.0, c["deadline"] - time.time())
    if kind != "skip":
        if ratio == 1:
            s.streak += 1
            s.correct += 1
            s.best = max(s.best, s.streak)
        else:
            s.streak = 0
    base = BASE[q["diff"]]
    pen = (0.25 if c["hint"] else 0) + (0.25 if c["fifty"] else 0)
    pts = round(base * ratio * (1 - pen))
    bonus = sbonus = 0
    if ratio == 1:
        if s.timer:
            bonus = round(base * 0.5 * left / c["limit"] * (1 - pen))
        sbonus = min(max(s.streak - 1, 0), 5) * 2
        s.badges.add("first")
        if s.streak >= 3:
            s.badges.add("streak")
        if q["diff"] == "hard":
            s.badges.add("hard")
        if s.timer and left / c["limit"] >= 0.7:
            s.badges.add("quick")
    total = pts + bonus + sbonus
    s.score += total
    c["res"] = dict(kind=kind, ratio=ratio, given=payload, pts=pts, bonus=bonus, sb=sbonus, total=total, pen=pen)
    s.res.append(dict(q=q, kind=kind, ratio=ratio, total=total))


def use_life(k):
    c = s.cur
    q = s.qs[s.i]
    if c["locked"] or s.life[k] <= 0:
        return
    if k == "fifty":
        if "opts" not in q or len(q["opts"]) < 3 or c["fifty"]:
            return
        wrong = [d for d, o in enumerate(c["order"]) if o != q["ans"]]
        c["removed"] = random.sample(wrong, 2)
        c["fifty"] = True
    elif k == "hint":
        if c["hint"]:
            return
        c["hint"] = True
    elif k == "time":
        if not s.timer:
            return
        c["limit"] += 15
        c["deadline"] += 15
    s.life[k] -= 1
    s.used_life = True
    if k == "skip":
        resolve("skip")


def go_next():
    if s.i + 1 >= len(s.qs):
        s.screen = "result"
    else:
        s.i += 1
        new_cur()


@st.fragment(run_every=1)
def timer_box():
    c = s.get("cur")
    if not c or not s.get("timer") or c["locked"] or s.screen != "play":
        return
    left = c["deadline"] - time.time()
    if left <= 0:
        resolve("timeout")
        st.rerun(scope="app")
    st.progress(max(0.0, min(1.0, left / c["limit"])), text=f"⏱ {int(left) + 1} s left")


# ---------------------------------------------------------------- sidebar
def sidebar():
    with st.sidebar:
        st.markdown("### 🎮 Player profile")
        st.caption(f"{s.get('name', NAME)}  |  Reg. No. {REG}")
        st.metric("XP / Score", s.score)
        st.progress(min(1.0, s.score / s.max_xp) if s.max_xp else 0.0)
        st.markdown("### 🏅 Badges")
        if s.badges:
            for b in BADGES:
                if b in s.badges:
                    st.write(f"**{BADGES[b][0]}**  \n{BADGES[b][1]}")
        else:
            st.caption("Complete challenges to unlock badges!")
        st.divider()
        st.markdown("### 🎯 Mission")
        st.write("Your mission is to master **agents, search and constraint solving**: "
                 "understand *why* an AI picks each action, not just the answer.")
        st.info("💡 Think before you click. Use lifelines wisely: 50:50 and Hint cost 25% of the points.")


# ---------------------------------------------------------------- screens
def setup_screen():
    st.title("🌳 AI Quest")
    st.caption("DSC401-6 Artificial Intelligence, Units I and II")
    left, right = st.columns([3, 2])
    with left:
        with st.container(border=True):
            st.subheader("Climb the search tree")
            st.write(f"{len(QUESTIONS)} questions on agents, search and constraint solving.")
            name = st.text_input("Your name", value=NAME, max_chars=24)
            count = st.radio("Round length", ["10", "25", "all"], horizontal=True,
                             format_func=lambda x: {"10": "Viva round (10)", "25": "Standard (25)", "all": f"Full bank ({len(QUESTIONS)})"}[x])
            diff = st.radio("Difficulty", ["mixed", "easy", "medium", "hard"], horizontal=True,
                            format_func=str.capitalize)
            timer = st.toggle("Timed mode (speed bonus)", value=True)
            if st.button("Start round", type="primary"):
                start(name, count, diff, timer)
                st.rerun()
    with right:
        with st.container(border=True):
            st.subheader("🏆 Leaderboard")
            show_board()


def show_board():
    rows = sorted(leaderboard(), key=lambda r: -r["Score"])[:10]
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.caption("No scores yet. Finish a round to be the first on the board.")


def play_screen():
    q = s.qs[s.i]
    c = s.cur
    done = c["locked"]
    top = st.columns([1, 1, 1, 3])
    top[0].metric("Question", f"{s.i + 1} / {len(s.qs)}")
    top[1].metric("Score", s.score)
    top[2].metric("Streak", s.streak)
    with top[3]:
        if s.timer:
            timer_box()
        else:
            st.caption("Practice mode: no timer")
    marks = ""
    done_ids = {id(r["q"]): r for r in s.res}
    for k, qq in enumerate(s.qs):
        r = done_ids.get(id(qq))
        marks += "⬜" if k > s.i and not r else ("🔵" if k == s.i and not r else ("⚪" if r["kind"] == "skip" else "🟢" if r["ratio"] == 1 else "🔴"))
    st.write(marks)

    with st.container(border=True):
        st.caption(f"{q['fmt']}  |  {q['topic']}  |  {q['diff']} ({BASE[q['diff']]} pts)"
                   + ("  |  real-world" if q["real"] else "") + ("  |  search problem" if q["search"] else ""))
        st.markdown(f"#### {q['q']}")
        if q["tree"]:
            st.code(TREE, language=None)
        res = c["res"]
        if "opts" in q:
            shown = [d for d in range(len(c["order"])) if d not in c["removed"]]
            fmt = lambda d: f"{'ABCD'[d]}. {q['opts'][c['order'][d]]}"
            if not done:
                sel = st.radio("Choose one", shown, index=None, format_func=fmt, key=f"ans_{s.i}")
                if st.button("Submit answer", type="primary"):
                    if sel is None:
                        st.warning("Pick an option first.")
                    else:
                        resolve("choice", c["order"][sel])
                        st.rerun()
            else:
                for d in range(len(c["order"])):
                    o = c["order"][d]
                    mark = "✅" if o == q["ans"] else ("❌" if res["given"] == o else "▫️")
                    st.markdown(f"{mark} {fmt(d)}")
        elif "accept" in q:
            txt = st.text_input("Type your answer", key=f"fill_{s.i}", disabled=done)
            if not done and st.button("Submit answer", type="primary"):
                if txt.strip():
                    resolve("fill", txt.strip())
                    st.rerun()
                else:
                    st.warning("Type an answer first.")
        else:
            rights = [p[1] for p in q["pairs"]]
            picks = []
            for k, p in enumerate(q["pairs"]):
                a, b = st.columns(2)
                a.markdown(f"**{p[0]}**")
                picks.append(b.selectbox(f"Match {k}", [rights[j] for j in c["rorder"]], index=None,
                                         key=f"m_{s.i}_{k}", disabled=done, label_visibility="collapsed",
                                         placeholder="Choose..."))
            if not done and st.button("Check matches", type="primary"):
                if None in picks:
                    st.warning("Choose a match for every item.")
                else:
                    resolve("match", picks)
                    st.rerun()
        if c["hint"] and not done:
            st.warning(f"**Hint:** {q['hint']}")
        if done:
            res = c["res"]
            good = res["kind"] != "skip" and res["ratio"] == 1
            head = {"timeout": "Time's up", "skip": "Skipped"}.get(res["kind"], "Correct!" if good else "Not quite")
            if "opts" in q:
                ans = f"**Answer:** {q['opts'][q['ans']]}"
            elif "accept" in q:
                ans = f"**Answer:** {q['accept'][0]}"
            else:
                ans = "**Correct pairs:** " + "; ".join(f"{a} = {b}" for a, b in q["pairs"])
            parts = [f"{res['pts']} for the answer"]
            if res["bonus"]:
                parts.append(f"+{res['bonus']} speed")
            if res["sb"]:
                parts.append(f"+{res['sb']} streak")
            if res["pen"]:
                parts.append(f"lifeline penalty -{int(res['pen'] * 100)}%")
            box = st.success if good else st.error
            box(f"**{head}**  \n{ans}  \n{q['exp']}  \n*+{res['total']} points ({', '.join(parts)})*")
            st.button("See result" if s.i + 1 >= len(s.qs) else "Next question", type="primary",
                      on_click=go_next)

    if not done:
        L = s.life
        cols = st.columns(4)
        specs = [("fifty", "50:50", "opts" not in q or len(q.get("opts", [])) < 3 or c["fifty"]),
                 ("hint", "Hint", c["hint"]), ("time", "+15 seconds", not s.timer), ("skip", "Skip", False)]
        for col, (k, label, off) in zip(cols, specs):
            col.button(f"{label} ({L[k]})", key=f"life_{k}_{s.i}", disabled=off or L[k] <= 0,
                       on_click=use_life, args=(k,))


def result_screen():
    n = len(s.qs)
    pct = round(100 * s.correct / n)
    if not s.used_life:
        s.badges.add("pure")
    if pct >= 90:
        s.badges.add("master")
    rank = "Search Master" if pct >= 90 else "Heuristic Hero" if pct >= 75 else "Rational Agent" if pct >= 50 else "Hill Climber" if pct >= 25 else "Random Walker"
    if not s.saved:
        s.saved = True
        mode = ("Full bank" if n == len(QUESTIONS) else f"{n} Q") + f", {s.diff_label}" + ("" if s.timer else ", practice")
        leaderboard().append({"Name": s.name, "Score": s.score, "Correct": f"{s.correct}/{n}", "Mode": mode})
        leaderboard().sort(key=lambda r: -r["Score"])
    st.balloons() if pct >= 75 else None
    st.title(f"{s.name}, you finished as a {rank}")
    a, b, c = st.columns(3)
    a.metric("Score", s.score)
    b.metric("Correct", f"{s.correct} / {n} ({pct}%)")
    c.metric("Best streak", s.best)
    topic = {}
    for r in s.res:
        t = topic.setdefault(r["q"]["topic"], [0, 0])
        t[1] += 1
        t[0] += r["ratio"] == 1
    st.subheader("By topic")
    st.dataframe([{"Topic": k, "Correct": f"{v[0]}/{v[1]}"} for k, v in topic.items()], hide_index=True)
    if st.button("Play again", type="primary"):
        start(s.name, "all" if n == len(QUESTIONS) else str(n), s.diff_label, s.timer)
        st.rerun()
    if st.button("Back to start"):
        s.screen = "setup"
        st.rerun()
    st.subheader("🏆 Leaderboard")
    show_board()
    miss = [r for r in s.res if r["ratio"] < 1]
    st.subheader("Review your misses" if miss else "Perfect round, nothing to review")
    for r in miss:
        q = r["q"]
        with st.expander(f"Q{q['id']} {q['topic']}"):
            st.markdown(q["q"])
            if "opts" in q:
                st.markdown(f"**Answer:** {q['opts'][q['ans']]}")
            elif "accept" in q:
                st.markdown(f"**Answer:** {q['accept'][0]}")
            else:
                st.markdown("**Pairs:** " + "; ".join(f"{a} = {b}" for a, b in q["pairs"]))
            st.caption(q["exp"])


def bank_screen():
    st.subheader("Question bank with correct answers")
    st.caption(f"{len(QUESTIONS)} questions: {sum(q['real'] for q in QUESTIONS)} real-world, "
               f"{sum(q['search'] for q in QUESTIONS)} search/state-space.")
    f1, f2 = st.columns(2)
    fmt = f1.selectbox("Format", ["All"] + sorted({q["fmt"] for q in QUESTIONS}))
    top = f2.selectbox("Topic", ["All"] + TOPICS)
    for q in QUESTIONS:
        if (fmt != "All" and q["fmt"] != fmt) or (top != "All" and q["topic"] != top):
            continue
        with st.expander(f"Q{q['id']}  [{q['fmt']} | {q['topic']} | {q['diff']}]"):
            st.markdown(q["q"])
            if q["tree"]:
                st.code(TREE, language=None)
            if "opts" in q:
                for k, o in enumerate(q["opts"]):
                    st.markdown(f"{'✅' if k == q['ans'] else '▫️'} {'ABCD'[k]}. {o}")
            elif "accept" in q:
                st.markdown(f"**Answer:** {q['accept'][0]}")
            else:
                for a, b in q["pairs"]:
                    st.markdown(f"- {a} = **{b}**")
            st.caption(q["exp"])


def report_screen():
    st.subheader("Project report")
    st.markdown(f"""
**Name:** {NAME}  |  **Register number:** {REG}  |  **Course:** DSC401-6 Artificial Intelligence

**Aim.** Test Units I and II of AI through an interactive quiz game.

**Tool.** Python with Streamlit. Questions live in `questions.py`; the game logic is in `app.py`.

**Features.** Timer (30/45/60 s by difficulty), score with speed and streak bonus, immediate feedback with explanations,
lifelines (50:50, Hint, +15 seconds, Skip), easy/medium/hard/mixed levels, random questions, progress path,
XP bar with badges, leaderboard and a final result with topic breakdown.

**Source.** Written in my own words, following *Artificial Intelligence: A Modern Approach* (3rd ed.), Chapters 1, 2, 3,
Section 4.1 and Chapter 6; production systems, problem characteristics, search design issues and means-end analysis
follow Rich and Knight.
""")


init()
sidebar()
tab_play, tab_bank, tab_report = st.tabs(["Play", "Question bank", "Report"])
with tab_play:
    {"setup": setup_screen, "play": play_screen, "result": result_screen}[s.screen]()
with tab_bank:
    bank_screen()
with tab_report:
    report_screen()
