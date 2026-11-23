"""Inquiry Desk by DataPoch — live demo.

Vendor questions on an RFP: logged, split, grouped by meaning, answered once,
approved by staff, published as an addendum, and replied to, with every step
traceable to the original email.
"""
import html
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from core import llm
from core import mail as mailer
from core.data import CATEGORIES, LABELED
from core.embed import encode, engine
from core.engine import Desk, load_seed, now_et
from core.evaluate import calibrate, lib_score, nearest
from core.text import clean_for_match

st.set_page_config(page_title="Inquiry Desk · DataPoch demo", page_icon="📨", layout="wide")

# ---------------- shared state (one store for every viewer) ----------------


def _secret(k, default=None):
    try:
        return st.secrets[k]
    except Exception:
        return default


@st.cache_resource(show_spinner="Loading the meaning model and calibrating…")
def get_desk():
    ai = _secret("ai", {}) or {}
    llm.configure(ai.get("base_url", ""), ai.get("api_key", ""), ai.get("model", ""))
    th, report = calibrate()
    desk = Desk("inquirydesk.db", th)
    desk.report = report
    desk.last_poll = 0.0
    if not desk.emails():
        load_seed(desk)
    return desk


desk = get_desk()
MAIL = dict(_secret("mail", {}) or {})
MAIL_ON = bool(MAIL.get("user") and MAIL.get("password"))
INBOX_ADDR = (MAIL.get("only_to") or MAIL.get("user") or "")
ROLES = {
    "Administrator": {"perms": ["view", "review", "edit", "approve", "publish", "send", "settings", "audit", "users"], "icon": "🛡️",
                      "desc": "Runs the system: users and roles, mailbox and settings, plus everything a manager can do."},
    "Contracts Manager": {"perms": ["view", "review", "edit", "approve", "publish", "send", "audit"], "icon": "✅",
                          "desc": "Approves answers, publishes addenda and releases replies to vendors."},
    "Contracts Staff": {"perms": ["view", "review", "edit"], "icon": "🗂️",
                        "desc": "Sorts questions, confirms or moves matches, merges groups and drafts answers. Cannot approve or send."},
    "Security Reviewer": {"perms": ["view", "audit", "settings_view"], "icon": "🔐",
                          "desc": "Reviews who has access, the audit log, data handling and accuracy. Read-only."},
    "Viewer": {"perms": ["view"], "icon": "👁️",
               "desc": "Read-only look at emails, questions, answers and replies."},
}
_ALIAS = {"Manager": "Contracts Manager", "Staff": "Contracts Staff", "Admin": "Administrator", "Security": "Security Reviewer"}
USERS = [dict(u) for u in (_secret("users", None) or [
    {"name": "Avery Collins", "role": "Administrator", "passcode": "admin-2026"},
    {"name": "Morgan Lee", "role": "Contracts Manager", "passcode": "manager-2026"},
    {"name": "Jordan Reyes", "role": "Contracts Staff", "passcode": "staff-2026"},
    {"name": "Sam Patel", "role": "Security Reviewer", "passcode": "security-2026"},
    {"name": "Riley Brooks", "role": "Viewer", "passcode": "viewer-2026"},
])]
for _u in USERS:
    _u["role"] = _ALIAS.get(_u.get("role"), _u.get("role"))
    if _u["role"] not in ROLES:
        _u["role"] = "Viewer"
# One-click demo sign-in for each role. Set demo_roles = false in secrets to require passcodes.
DEMO_ROLES = bool(_secret("demo_roles", True))
PERM_LABEL = {"view": "See emails, questions, answers and replies", "review": "Confirm or move questions in review",
              "edit": "Merge questions, change categories, draft answers", "approve": "Approve answers",
              "publish": "Publish addenda", "send": "Send replies to vendors", "audit": "See access and the audit log",
              "settings_view": "See settings (read-only)", "settings": "Change settings and reset the demo", "users": "Manage users and roles"}

st.markdown("""<style>
mark.q{background:#fff1b8;color:#2a2100;border-radius:4px;padding:1px 4px}
mark.q b{font-family:monospace;font-size:11px;background:#1a7f93;color:#fff;border-radius:3px;padding:0 4px;margin-right:5px}
.pill{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:999px;margin:0 4px 2px 0;white-space:nowrap}
.ok{background:#dff2e6;color:#1f7a45}.info{background:#dcf0f3;color:#14606f}.warn{background:#fcedd6;color:#8a5206}
.bad{background:#fadfdc;color:#b3261e}.mute{background:#eceff3;color:#4d5b68}.adv{background:#ece5f7;color:#5b3e96}
.mail{white-space:pre-wrap;background:#fafbfc;border:1px solid #e3e8ec;border-radius:8px;padding:12px 14px;line-height:1.6;color:#1f2a33}
.small{font-size:13px;color:#5b6b7a}
</style>""", unsafe_allow_html=True)


def pill(t, c="mute"):
    return f'<span class="pill {c}">{html.escape(str(t))}</span>'


STATUS = {"needs-answer": ("Needs answer", "warn"), "draft": ("Draft ready", "info"),
          "approved": ("Approved", "ok"), "published": ("Published", "ok")}
HOW = {"exact": ("Exact repeat", "ok"), "known": ("Word for word a known question", "ok"), "library": ("Same meaning as a known question", "info"),
       "inbox": ("Same meaning as an earlier email", "info"), "ai": ("Confirmed by AI check", "adv"),
       "suggested": ("Suggested, needs review", "warn"), "new": ("New question", "warn"), "staff": ("Set by staff", "ok")}


def gstatus(g):
    t, c = STATUS.get(g["status"], (g["status"], "mute"))
    if g["status"] == "published":
        t = f"Addendum No. {g['addendum']}, Q#{g['qno']}"
    return pill(t, c)


def how_pill(h):
    t, c = HOW.get(h, (h, "mute")); return pill(t, c)


def fmt(at):
    try:
        return datetime.strptime(at[:16], "%Y-%m-%dT%H:%M").strftime("%b %d, %I:%M %p")
    except Exception:
        return at


def highlight(body, parts, focus=None):
    b = html.escape(body)
    for i, p in enumerate(parts):
        t = html.escape(p["text"])
        if t and t in b:
            style = "" if focus is None or p.get("group_id") == focus else ' style="background:#eceff3"'
            b = b.replace(t, f'<mark class="q"{style}><b>Q{i + 1}</b>{t}</mark>', 1)
    return f'<div class="mail">{b}</div>'


# ---------------- sign in ----------------
user = st.session_state.get("user")

# Optional "Sign in with Google" (Streamlit's built-in login). Active only when [auth] is set in Secrets.
AUTH_ON = bool(_secret("auth", None)) and hasattr(st, "login")
GOOGLE_ROLES = {k.lower(): _ALIAS.get(v, v) for k, v in dict(_secret("google_roles", {}) or {}).items()}
GOOGLE_DEFAULT = _ALIAS.get(_secret("google_default_role", "Viewer"), _secret("google_default_role", "Viewer"))
if not user and AUTH_ON:
    try:
        if st.user.is_logged_in:
            email = (st.user.get("email") or "").lower()
            role = GOOGLE_ROLES.get(email, GOOGLE_DEFAULT)
            role = role if role in ROLES else "Viewer"
            user = {"name": st.user.get("name") or email, "role": role, "email": email, "via": "google"}
            st.session_state["user"] = user
            desk.log(user["name"], f"Signed in with Google as {role}")
    except Exception:
        pass


def can(p):
    return bool(user) and p in ROLES[user["role"]]["perms"]


def sign_in(u, how="passcode"):
    st.session_state["user"] = {"name": u["name"], "role": u["role"]}
    desk.log(u["name"], f"Signed in as {u['role']}" + (" (demo access)" if how == "demo" else ""))
    st.rerun()


def render_user_card():
    with st.sidebar:
        r = ROLES[user["role"]]
        st.markdown(f"### 📨 Inquiry Desk")
        st.caption(f"RFP No. {desk.s('rfp_no')} · {desk.s('rfp_title')}")
        with st.container(border=True):
            st.markdown(f"{r['icon']} **{user['name']}**  \n<span class='small'>{user['role']}</span>", unsafe_allow_html=True)
            st.caption(r["desc"])
            if st.button("Sign out", use_container_width=True):
                desk.log(user["name"], "Signed out"); st.session_state.pop("user")
                if user.get("via") == "google":
                    st.logout()
                st.rerun()
        st.caption(("🟢 Live inbox: " + INBOX_ADDR) if MAIL_ON else "⚪ Live inbox not connected")
        st.caption("🟢 AI check on" if llm.enabled() else "⚪ AI check off (meaning model only)")
        st.caption("Demo by DataPoch · test data only")


def who():
    return (user or {}).get("name", "Viewer")


# ---------------- live mail ----------------
def poll_mail(force=False):
    if not MAIL_ON:
        return 0
    with desk.lock:
        if not force and time.time() - desk.last_poll < 15:
            return 0
        desk.last_poll = time.time()
    try:
        msgs = mailer.fetch_unseen(MAIL)
    except Exception as ex:
        desk.log("System", f"Inbox check failed: {type(ex).__name__}")
        return 0
    n = 0
    for m in msgs:
        if not MAIL.get("only_to") and m["from_email"].lower() == MAIL["user"].lower():
            continue  # our own sent replies
        if desk.ingest(m["from_name"], m["from_email"], m["subject"] or "(no subject)", m["body"], None, "live", m["msgid"]):
            n += 1
    return n


# ================= guide =================
TIPS = {
    "dashboard": "Start here. The numbers show how many emails came in, how many questions were inside them, and how many unique questions are left after grouping repeats.",
    "vendor": "Act as a vendor. Write several questions in one message, word one question differently from the samples, or avoid obvious keywords. Keep the reference number.",
    "inbox": "Click any row to open the original email. Each question is highlighted (Q1, Q2…) and the right side shows which group it joined and why.",
    "review": "Only uncertain matches land here, so staff never read every email. Confirm, move, or make it its own question; the system learns from each decision.",
    "questions": "Each card is one unique question with every vendor who asked it. Open one to see the original wording from each email, merge two questions, or undo a merge.",
    "merge": "Pick a question to see every email merged into it, with each vendor's exact wording and reference ID. The least certain matches are listed first.",
    "answers": "Drafts come only from published RFP documents and show their source. A Contracts Manager approves each answer, then publishes the addendum.",
    "tracker": "Every email and the answers it maps to. A reply goes out only when all questions in that email are answered, so each vendor gets one complete reply.",
    "access": "Who can do what, by role, and an audit log of every sign-in, decision and reply.",
    "accuracy": "Accuracy measured on test questions the system never saw. Try your own question at the bottom to see how it would be matched.",
    "settings": "RFP details, inquiry deadline and demo reset.",
}
GUIDE = [("vendor", "1 · Ask as a vendor"), ("inbox", "2 · Open your email"), ("review", "3 · Review uncertain"),
         ("questions", "4 · See the originals"), ("merge", "5 · Merge report"), ("answers", "6 · Approve & publish"),
         ("tracker", "7 · Send replies"), ("vendor", "8 · Read your reply"), ("access", "9 · Check the audit log")]


def tip(key):
    if st.session_state.get("show_guide", True) and key in TIPS:
        st.info(f"**What to look for:** {TIPS[key]}", icon="💡")


# ================= pages =================
def page_dashboard():
    st.title("Dashboard")
    tip("dashboard")
    em, gs = desk.emails(), desk.groups()
    nq = sum(g["n"] for g in gs)
    states = [desk.email_state(e)[0] for e in em]
    c = st.columns(5)
    c[0].metric("Vendor emails", len(em))
    c[1].metric("Questions found", nq, help="An email can hold several questions")
    c[2].metric("Unique questions", len(gs), f"{round((1 - len(gs) / max(1, nq)) * 100)}% were repeats", delta_color="off")
    c[3].metric("Needs review", len(desk.review_queue()))
    c[4].metric("Replied", states.count("replied"), f"{states.count('ready')} ready to send", delta_color="off")
    st.markdown("#### How it works")
    f = st.columns(6)
    for col, (t, d) in zip(f, [("1 · Log", "Every email saved with an ID"), ("2 · Split", "Each question found separately"),
                               ("3 · Group", "Same meaning → one question"), ("4 · Review", "Uncertain items go to staff"),
                               ("5 · Approve & publish", "Staff approve; addendum issued"), ("6 · Reply", "One reply per email, every Q# listed")]):
        col.markdown(f"**{t}**  \n<span class='small'>{d}</span>", unsafe_allow_html=True)
    l, r = st.columns([3, 2])
    with l:
        st.markdown("#### Emails per day")
        if em:
            df = pd.DataFrame({"day": [e["received"][:10] for e in em], "late": ["Late" if e["late"] else "On time" for e in em]})
            st.bar_chart(df.groupby(["day", "late"]).size().unstack(fill_value=0), color=["#d9534f", "#1a7f93"] if df["late"].nunique() > 1 else None)
    with r:
        st.markdown("#### Most asked")
        for g in sorted(gs, key=lambda g: -g["n"])[:6]:
            st.markdown(f"**{g['n']}×** {html.escape(g['title'][:80])}  \n{pill(g['category'], 'info')}{gstatus(g)}", unsafe_allow_html=True)


def page_inbox():
    st.title("Inbox")
    tip("inbox")
    top = st.columns([3, 1, 1])
    top[0].caption(f"Every email is saved with an ID, split into its questions and matched. {'Live inbox: ' + INBOX_ADDR if MAIL_ON else 'Live inbox not connected: use “Send a test email”.'}")
    if MAIL_ON and top[1].button("Check inbox now"):
        n = poll_mail(force=True); st.toast(f"{n} new email{'s' if n != 1 else ''}")
    auto = top[2].toggle("Auto-check", value=MAIL_ON, disabled=not MAIL_ON, help="Checks the test inbox every 20 seconds while this page is open")

    @st.fragment(run_every=20 if (auto and MAIL_ON) else None)
    def live():
        n = poll_mail()
        if n:
            st.toast(f"📨 {n} new email{'s' if n != 1 else ''} received and sorted"); st.rerun()
    live()

    with st.expander("✉️ Send a test email (works without a mailbox)", expanded=not MAIL_ON and not desk.q("SELECT 1 FROM emails WHERE source!='seed'")):
        c1, c2 = st.columns(2)
        fn = c1.text_input("From name", "Test Vendor")
        fe = c2.text_input("From email", "vendor@example.com")
        sj = st.text_input("Subject", "Questions on RFP 19-2026")
        bd = st.text_area("Message", "Hello,\n\nHow much money has been set aside for this project? Also, will the Commission host the new website, or should we include hosting?\n\nThank you,\nTest Vendor", height=170)
        if st.button("Receive this email", type="primary"):
            with st.spinner("Splitting, matching and categorizing…"):
                r = desk.ingest(fn, fe, sj, bd, None, "sim")
            st.session_state["sel_email"] = r["id"]
            st.success(f"{r['id']} received: {len(r['parts'])} question(s) found.")

    em = desk.emails()
    rows = []
    for e in em:
        stt, ps = desk.email_state(e)
        rows.append({"ID": e["id"], "Received": fmt(e["received"]), "From": f"{e['from_name']} · {e['firm']}", "Subject": e["subject"],
                     "Questions": len(ps), "Timing": "Late" if e["late"] else "On time",
                     "Status": {"replied": "Replied", "ready": "Ready to reply", "review": "Needs review", "waiting": "Waiting for answer"}.get(stt, stt),
                     "Source": {"seed": "Sample", "live": "Live email", "sim": "Test form", "portal": "Vendor portal"}.get(e["source"], e["source"])})
    df = pd.DataFrame(rows)
    flt = st.segmented_control("Show", ["All", "Live and test", "Several questions", "Needs review", "Late"], default="All")
    if flt == "Live and test":
        df = df[df.Source != "Sample"]
    elif flt == "Several questions":
        df = df[df.Questions > 1]
    elif flt == "Needs review":
        df = df[df.Status == "Needs review"]
    elif flt == "Late":
        df = df[df.Timing == "Late"]
    ev = st.dataframe(df, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", height=300)
    if ev.selection.rows:
        st.session_state["sel_email"] = df.iloc[ev.selection.rows[0]]["ID"]
    show_email(st.session_state.get("sel_email"))


def show_email(eid, focus=None):
    if not eid:
        st.caption("Select an email to see its questions highlighted and how each was matched."); return
    e = next((x for x in desk.emails() if x["id"] == eid), None)
    if not e:
        return
    stt, ps = desk.email_state(e)
    st.markdown(f"### {html.escape(e['subject'])}")
    st.markdown(f"<span class='small'>{e['id']} · {html.escape(e['from_name'])} &lt;{html.escape(e['from_email'])}&gt; · {fmt(e['received'])}</span> "
                f"{pill('Late' if e['late'] else 'On time', 'bad' if e['late'] else 'ok')}{pill(f'{len(ps)} question' + ('s' if len(ps) != 1 else ''), 'adv' if len(ps) > 1 else 'mute')}",
                unsafe_allow_html=True)
    l, r = st.columns([1, 1])
    l.markdown("**Original email** (each question highlighted, exactly as written)")
    l.markdown(highlight(e["body"], ps, focus), unsafe_allow_html=True)
    with r:
        st.markdown("**How each question was handled**")
        for i, p in enumerate(ps):
            with st.container(border=True):
                st.markdown(f"**Q{i + 1}** “{html.escape(p['text'])}”", unsafe_allow_html=True)
                score_txt = "match %.2f" % p["score"]
                st.markdown(f"→ {html.escape(p['gtitle'] or '')}  \n{how_pill(p['how'])}{pill(p['category'] or '', 'info')}{pill(score_txt, 'mute')}"
                            + (gstatus({'status': p['gstatus'], 'addendum': p['addendum'], 'qno': p['qno']}) if p['gstatus'] else ""), unsafe_allow_html=True)
                if p["ai_reason"]:
                    st.caption(f"AI reason: {p['ai_reason']}")
                if p["review"]:
                    st.caption(f"⚠️ {p['review_reason']}")
        for rp in desk.replies(e["id"]):
            with st.expander(f"Reply {rp['mode']} · {fmt(rp['at'])} · by {rp['by']}"):
                st.text(rp["body"])


def page_questions():
    st.title("Questions")
    tip("questions")
    gs = desk.groups()
    st.caption(f"{sum(g['n'] for g in gs)} questions from vendor emails, grouped into {len(gs)} unique questions. "
               "Grouping is by meaning: questions that one answer would fully answer belong together.")
    c1, c2 = st.columns([3, 1])
    cats = sorted({g["category"] for g in gs})
    cat = c1.segmented_control("Category", ["All"] + cats, default="All")
    sort = c2.selectbox("Sort", ["Most asked", "Needs work first", "Category", "Newest"])
    if cat and cat != "All":
        gs = [g for g in gs if g["category"] == cat]
    key = {"Most asked": lambda g: -g["n"], "Category": lambda g: g["category"], "Newest": lambda g: -g["id"],
           "Needs work first": lambda g: ["needs-answer", "draft", "approved", "published"].index(g["status"])}[sort]
    others = {g["id"]: g["title"] for g in desk.groups()}
    for g in sorted(gs, key=key):
        head = f"**{g['n']}×** {g['title'][:110]}"
        with st.expander(head):
            st.markdown(f"{pill(g['category'], 'info')}{gstatus(g)}" + (pill(f"{g['late']} late", 'bad') if g['late'] else "") +
                        (pill(f"{g['rev']} to review", 'warn') if g['rev'] else "") +
                        f"<br><span class='small'>Category reason: {html.escape(g['cat_how'] or '')}</span>", unsafe_allow_html=True)
            if g["merged"]:
                st.markdown(f"<div class='pill adv'>Merged from {len(g['merged']) + 1} questions</div>", unsafe_allow_html=True)
                st.markdown(f"Kept: “{html.escape(g['title'])}”", unsafe_allow_html=True)
                for i, m in enumerate(g["merged"]):
                    a, b = st.columns([5, 1])
                    a.markdown(f"Merged in: “{html.escape(m['group']['title'])}” <span class='small'>({len(m['pids'])} emails · {m['by']}, {fmt(m['at'])})</span>", unsafe_allow_html=True)
                    if can("edit") and b.button("Undo merge", key=f"um{g['id']}{i}"):
                        desk.undo_merge(g["id"], i, who()); st.rerun()
            ps = desk.parts_of_group(g["id"])
            st.dataframe(pd.DataFrame([{"Email": p["id"], "Vendor": p["firm"], "Received": fmt(p["received"]), "Question as written": p["text"],
                                        "Match": round(p["score"], 2), "How": HOW.get(p["how"], (p["how"],))[0]} for p in ps]),
                         hide_index=True, use_container_width=True)
            if can("edit"):
                a, b, c = st.columns([2, 2, 1])
                tgt = a.selectbox("Merge another question into this one", ["—"] + [f"{k} · {v[:70]}" for k, v in others.items() if k != g["id"]], key=f"mg{g['id']}")
                if tgt != "—" and a.button("Merge", key=f"mgb{g['id']}"):
                    desk.merge(g["id"], int(tgt.split(" · ")[0]), who()); st.rerun()
                nc = b.selectbox("Category", CATEGORIES, index=CATEGORIES.index(g["category"]) if g["category"] in CATEGORIES else 0, key=f"ct{g['id']}")
                if nc != g["category"] and b.button("Change category", key=f"ctb{g['id']}"):
                    desk.set_category(g["id"], nc, who()); st.rerun()
                if c.button("Merge report", key=f"mr{g['id']}"):
                    st.session_state["mr"] = g["id"]; st.switch_page(P_MERGE)
            sel = st.selectbox("Open an original email", ["—"] + [p["id"] for p in ps], key=f"oe{g['id']}")
            if sel != "—":
                show_email(sel, focus=g["id"])


def page_merge():
    st.title("Merge report")
    tip("merge")
    st.caption("Every email merged into one question, with the vendor's exact wording and its reference email. Lowest match first, so staff check the least certain ones.")
    gs = sorted(desk.groups(), key=lambda g: -g["n"])
    if not gs:
        return
    ids = [g["id"] for g in gs]
    cur = st.session_state.get("mr", ids[0])
    gid = st.selectbox("Question", ids, index=ids.index(cur) if cur in ids else 0,
                       format_func=lambda i: next(f"{g['n']} emails · {g['title'][:100]}" for g in gs if g["id"] == i))
    g = desk.group(gid); ps = desk.parts_of_group(gid)
    st.info(f"**Merged into:** {g['title']}")
    words = {}
    for p in ps:
        words.setdefault(p["text"].strip(), []).append(p)
    c = st.columns(4)
    c[0].metric("Emails merged", len(ps)); c[1].metric("Different wordings", len(words))
    c[2].metric("Vendors", len({p["firm"] for p in ps})); c[3].metric("Staff review", "1 question", f"instead of {len(ps)} emails", delta_color="off")
    mode = st.segmented_control("View", ["Every email", "Grouped by wording"], default="Every email")
    if mode == "Grouped by wording":
        st.dataframe(pd.DataFrame([{"Wording": w, "Emails": len(v), "Reference emails": ", ".join(p["id"] for p in v)}
                                   for w, v in sorted(words.items(), key=lambda x: -len(x[1]))]), hide_index=True, use_container_width=True)
    else:
        df = pd.DataFrame([{"Reference email": p["id"], "Vendor": p["firm"], "Contact": p["from_name"], "Received": fmt(p["received"]),
                            "Question as written": p["text"], "Match": round(p["score"], 2), "How it matched": HOW.get(p["how"], (p["how"],))[0]}
                           for p in sorted(ps, key=lambda p: p["score"])])
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.download_button("Download as CSV", df.to_csv(index=False), f"merge-report-{gid}.csv", "text/csv")


def page_review():
    st.title("Needs review")
    tip("review")
    rq = desk.review_queue()
    st.caption("Only uncertain items come here. Staff never need to open every email. Every decision teaches the system, so similar questions follow it next time.")
    if not rq:
        st.success("Nothing to review."); return
    opts = {g["id"]: g["title"] for g in desk.groups()}
    for p in rq:
        with st.container(border=True):
            a, b = st.columns([3, 2])
            a.markdown(f"**“{html.escape(p['text'])}”**  \n<span class='small'>{p['eid']} · {html.escape(p['firm'])} · {fmt(p['received'])}</span>", unsafe_allow_html=True)
            a.markdown(f"{how_pill(p['how'])} {pill(p['category'], 'info')}<br><span class='small'>{html.escape(p['review_reason'] or '')}</span>"
                       + (f"<br><span class='small'>AI reason: {html.escape(p['ai_reason'])}</span>" if p['ai_reason'] else ""), unsafe_allow_html=True)
            b.markdown(f"Suggested: **{html.escape(p['gtitle'] or '')}** (match {p['score']:.2f})")
            if can("review"):
                x, y, z = b.columns(3)
                if x.button("✓ Confirm", key=f"c{p['pid']}"):
                    desk.confirm(p["pid"], who()); st.rerun()
                if z.button("Own question", key=f"n{p['pid']}"):
                    desk.split_out(p["pid"], who()); st.rerun()
                tgt = b.selectbox("Or move to", ["—"] + [f"{k} · {v[:60]}" for k, v in opts.items() if k != p["group_id"]], key=f"m{p['pid']}")
                if tgt != "—" and y.button("Move", key=f"mb{p['pid']}"):
                    desk.move(p["pid"], int(tgt.split(" · ")[0]), who()); st.rerun()


def page_answers():
    st.title("Answers & addendum")
    tip("answers")
    gs = desk.groups()
    st.caption("Drafts come only from published RFP documents and always show their source. Questions with no source are left for staff. Nothing goes out until a manager approves it.")
    c = st.columns(4)
    for col, s in zip(c, ["needs-answer", "draft", "approved", "published"]):
        col.metric(STATUS[s][0], sum(1 for g in gs if g["status"] == s))
    left, right = st.columns([2, 3])
    with left:
        # Stable order (by question number) so the selection never jumps after saving or approving.
        show = st.segmented_control("Show", ["All", "To do", "Approved", "Published"], default="All", key="ans_filter")
        want = {"All": None, "To do": ("needs-answer", "draft"), "Approved": ("approved",), "Published": ("published",)}[show or "All"]
        ids = [g["id"] for g in sorted(gs, key=lambda g: g["id"]) if not want or g["status"] in want]
        if not ids:
            st.info("Nothing here."); return
        cur = st.session_state.get("ans_sel")
        gid = st.radio("Question", ids, index=ids.index(cur) if cur in ids else 0, label_visibility="collapsed",
                       format_func=lambda i: next(f"[{STATUS[g['status']][0]}] {g['n']}× {g['title'][:70]}" for g in gs if g["id"] == i))
        st.session_state["ans_sel"] = gid
    with right:
        g = desk.group(gid)
        st.markdown(f"**{html.escape(g['title'])}**  \n{pill(g['category'], 'info')}{gstatus(g)}", unsafe_allow_html=True)
        locked = g["status"] in ("approved", "published") or not can("edit")
        ans = st.text_area("Answer (as it will appear in the addendum)", g["answer"] or "", height=160, disabled=locked,
                           placeholder="No published source answers this. Staff to write the answer.")
        cite = st.text_input("Source", g["cite"] or "", disabled=locked)
        if g["cite"]:
            st.caption(f"📎 Drafted from: {g['cite']}")
        b = st.columns(3)
        if not locked and b[0].button("Save"):
            desk.save_answer(gid, ans, cite, who()); st.rerun()
        if g["status"] == "draft" and b[1].button("Approve", type="primary", disabled=not can("approve"), help=None if can("approve") else "Managers approve answers"):
            desk.save_answer(gid, ans, cite, who()); desk.approve(gid, who()); st.rerun()
        if g["status"] == "approved" and b[2].button("Reopen", disabled=not can("approve")):
            desk.reopen(gid, who()); st.rerun()
    st.divider()
    appr = [g for g in gs if g["status"] == "approved"]
    no = desk.s("next_addendum")
    a, b = st.columns([3, 1])
    a.markdown(f"#### Addendum No. {no}: {len(appr)} approved answer{'s' if len(appr) != 1 else ''} ready")
    if b.button(f"Publish Addendum No. {no}", type="primary", disabled=not (appr and can("publish"))):
        desk.publish(who()); st.toast("Published. Replies are now ready in the Reply tracker."); st.rerun()
    pubs = sorted({g["addendum"] for g in gs if g["addendum"]})
    for n in pubs:
        rows = desk.addendum_groups(n)
        text = (f"{desk.s('org').upper()}\nADDENDUM NO. {n}\nto RFP NO. {desk.s('rfp_no')}\n{desk.s('rfp_title').upper()}\n\n"
                "ANSWERS TO QUESTIONS RECEIVED DURING THE INQUIRY PERIOD:\n\n" +
                "\n\n".join(f"Q#{g['qno']} {g['title']}\nA#{g['qno']} {g['answer']}" for g in rows) + f"\n\nEND OF ADDENDUM NO. {n}\n(DEMO)")
        with st.expander(f"Addendum No. {n} · {len(rows)} answers"):
            st.text(text)
            st.download_button("Download", text, f"addendum-{n}.txt", key=f"dl{n}")


def page_tracker():
    st.title("Reply tracker")
    tip("tracker")
    st.caption("Every email, each question inside it, the answer it maps to, and whether its reply has gone out. A reply is sent only when every question in that email has a published answer, so each vendor gets one reply covering all their questions.")
    em = desk.emails(); rows, ready = [], []
    for e in em:
        stt, ps = desk.email_state(e)
        if stt == "ready":
            ready.append((e, ps))
        rows.append({"Email": e["id"], "Vendor": e["firm"], "Received": fmt(e["received"]), "Questions": len(ps),
                     "Answers": ", ".join(f"Q#{p['qno']}" if p["qno"] else STATUS.get(p["gstatus"], ("—",))[0] for p in ps),
                     "Status": {"replied": "✅ Replied", "ready": "📤 Ready to send", "review": "⚠️ Needs review", "waiting": "⏳ Waiting for answer"}.get(stt, stt)})
    df = pd.DataFrame(rows)
    c = st.columns(4)
    c[0].metric("Emails", len(df)); c[1].metric("Replied", int((df.Status == "✅ Replied").sum()))
    c[2].metric("Ready to send", len(ready)); c[3].metric("Waiting or in review", int(df.Status.str.contains("Waiting|review").sum()))
    a, b = st.columns([3, 1])
    q = a.text_input("Search", placeholder="Email ID or vendor")
    if b.button(f"Send {len(ready)} ready replies", type="primary", disabled=not (ready and can("send")), help=None if can("send") else "Managers send replies"):
        prog = st.progress(0.0)
        for i, (e, ps) in enumerate(ready):
            subj, body = desk.compose(e, ps)
            mode = "shown in vendor portal" if e["source"] == "portal" else "simulated (test address)"
            if MAIL_ON and e["source"] == "live":
                try:
                    mailer.send(MAIL, e["from_email"], subj, body, e["msgid"]); mode = "sent"
                except Exception as ex:
                    mode = "failed"; desk.log("System", f"Send failed for {e['id']}: {type(ex).__name__}")
            desk.record_reply(e["id"], subj, body, who(), mode)
            prog.progress((i + 1) / len(ready))
        st.rerun()
    if q:
        df = df[df.Email.str.contains(q, case=False) | df.Vendor.str.contains(q, case=False)]
    st.dataframe(df, hide_index=True, use_container_width=True, height=420)
    if ready:
        with st.expander(f"Preview the reply for {ready[0][0]['id']}"):
            st.text(desk.compose(*ready[0])[1])


def page_access():
    st.title("Access & audit")
    tip("access")
    st.caption("Who can sign in, what each role can do, and every action taken. Separation of duties: the person who drafts an answer is not the person who approves and sends it.")
    t1, t2, t3 = st.tabs(["People and roles", "Permissions by role", "Audit log"])
    with t1:
        c = st.columns(len(ROLES))
        for col, (rn, r) in zip(c, ROLES.items()):
            col.metric(f"{r['icon']} {rn}", sum(1 for u in USERS if u["role"] == rn))
        st.dataframe(pd.DataFrame([{"Name": u["name"], "Role": u["role"], "What they can do": ROLES[u["role"]]["desc"],
                                    "Signed in now": "✓ (you)" if user and u["name"] == user["name"] else ""} for u in USERS]),
                     hide_index=True, use_container_width=True)
        last = [e for e in desk.events(400) if e["what"].startswith(("Signed in", "Signed out", "Failed sign-in"))][:10]
        st.markdown("**Recent sign-ins**")
        st.dataframe(pd.DataFrame([{"When (ET)": fmt(e["at"]), "Who": e["who"], "Event": e["what"]} for e in last]) if last else pd.DataFrame(),
                     hide_index=True, use_container_width=True)
        if can("users"):
            st.info("Administrator: in this demo, accounts and passcodes are set in the app's Secrets on Streamlit Cloud. In production, sign-in uses the agency's Microsoft accounts with multi-factor authentication, and access follows the agency directory.")
    with t2:
        st.dataframe(pd.DataFrame([{"Permission": PERM_LABEL[p], **{rn: "✓" if p in r["perms"] else "" for rn, r in ROLES.items()}} for p in PERM_LABEL]),
                     hide_index=True, use_container_width=True)
    with t3:
        st.dataframe(pd.DataFrame([{"When (ET)": fmt(e["at"]), "Who": e["who"], "Action": e["what"]} for e in desk.events(300)]), hide_index=True, use_container_width=True, height=420)


def page_accuracy():
    st.title("Accuracy")
    tip("accuracy")
    r = desk.report
    st.caption("Measured, not claimed. The thresholds were set on one half of the test questions; the numbers below come from the other half, which the calibration never saw. Many test questions avoid the obvious keyword on purpose.")
    st.markdown(f"**Engine:** {r['engine']} · **AI check:** {'on (' + llm.CFG['model'] + ')' if llm.enabled() else 'off'}")
    c = st.columns(4)
    c[0].metric("Test questions", r["n_test"], f"{r['n_intents']} different questions", delta_color="off")
    c[1].metric("Grouped automatically", f"{r['auto']:.0f}", f"{r['auto_precision'] * 100:.0f}% correct", delta_color="off")
    c[2].metric("Sent to staff review", f"{r['review'] + r['new_ok'] + r['new_missed']:.0f}", f"suggestion right {r['review_precision'] * 100:.0f}%", delta_color="off")
    c[3].metric("Wrong automatic merges", f"{r['auto_wrong']:.1f}", help="The error that matters most. Thresholds are set to keep it near zero.")
    st.caption("How to read this: anything the system is not sure about goes to staff instead of being guessed. A weaker engine sends more to review; it should not make more wrong merges.")
    if r["engine_kind"] != "semantic":
        st.warning("The main meaning model is not loaded, so a lighter backup engine is running and more questions go to review. On Streamlit Cloud the main model downloads automatically on first start.")

    if llm.enabled():
        st.markdown("#### AI check on the same test questions")
        if st.button("Run AI test (about 2 minutes)"):
            items = [(it, w) for it, (cat, ws) in LABELED.items() for i, w in enumerate(ws) if i % 2 == 1]
            lib = [(it, w) for it, (cat, ws) in LABELED.items() for i, w in enumerate(ws) if i % 2 == 0]
            le = encode([clean_for_match(w) for _, w in lib]); li = [it for it, _ in lib]
            ok = n = none = 0; prog = st.progress(0.0)
            for k, (truth, w) in enumerate(items):
                v = encode([clean_for_match(w)])[0]; s = le @ v; seen, cands = set(), []
                for j in s.argsort()[::-1]:
                    if li[j] not in seen:
                        seen.add(li[j]); cands.append((li[j], lib[j][1]))
                    if len(cands) == 5:
                        break
                res = llm.match(w, cands, CATEGORIES)
                if res and res["key"]:
                    n += 1; ok += int(res["key"] == truth)
                else:
                    none += 1
                prog.progress((k + 1) / len(items)); time.sleep(2.1)
            desk.set("ai_test", f"{ok}|{n}|{none}|{len(items)}")
        if desk.s("ai_test"):
            ok, n, none, tot = map(int, desk.s("ai_test").split("|"))
            st.metric("AI check: matched to the right question", f"{ok}/{n}", f"{none} of {tot} left for staff", delta_color="off")

    st.markdown("#### Try your own question")
    q = st.text_input("Type any vendor question", "Is there a ceiling on total project cost?")
    if q:
        v = encode([clean_for_match(q)])[0]
        it, s, m, j = lib_score(v, desk.lib_embs, desk.lib_intents)
        sims = desk.lib_embs @ v
        top = sims.argsort()[::-1][:5]
        st.markdown(f"Closest known question: **{html.escape(desk.lib_text[j])}** → category **{desk.lib_cat[it]}** (score {s:.2f}, margin {m:.2f})")
        th = desk.th
        verdict = "Automatic match" if (s >= th["t_lib"] and m >= th["m_lib"]) else ("Suggested, goes to review" if s >= th["t_low"] else "New question, goes to review")
        st.markdown(f"Decision: **{verdict}**")
        st.dataframe(pd.DataFrame([{"Known wording": desk.lib_text[k], "Category": desk.lib_cat[desk.lib_intents[k]], "Similarity": round(float(sims[k]), 3)} for k in top]),
                     hide_index=True, use_container_width=True)
        if llm.enabled() and st.button("Ask the AI check"):
            cands, seen = [], set()
            for k in sims.argsort()[::-1]:
                if desk.lib_intents[k] not in seen:
                    seen.add(desk.lib_intents[k]); cands.append((desk.lib_intents[k], desk.lib_text[k]))
                if len(cands) == 5:
                    break
            res = llm.match(q, cands, CATEGORIES)
            st.json(res or {"error": "AI check failed"})
    with st.expander("Thresholds in use"):
        st.json(desk.th)


def page_settings():
    st.title("Settings")
    tip("settings")
    if not can("settings"):
        st.info("Read-only. Only an Administrator can change settings.")
        st.dataframe(pd.DataFrame([{"Setting": k, "Value": desk.s(k)} for k in ("rfp_no", "rfp_title", "deadline", "due", "live_on_time", "next_addendum")]), hide_index=True, use_container_width=True)
        st.markdown("**Data handling in this demo**")
        st.markdown(f"- Test data only, no agency data\n- Live inbox: {'connected (' + INBOX_ADDR + ')' if MAIL_ON else 'not connected'}\n"
                    f"- AI check: {'on, ' + llm.CFG['model'] if llm.enabled() else 'off'} (used only to confirm uncertain matches; no data is used to train models under the provider's API terms; check the provider's current terms)\n"
                    "- Every action is written to the audit log")
        return
    c1, c2 = st.columns(2)
    for k, label, col in [("rfp_no", "RFP number", c1), ("rfp_title", "RFP title", c2), ("deadline", "Inquiry deadline (YYYY-MM-DDTHH:MM, Eastern)", c1),
                          ("due", "Proposal due date (as shown in replies)", c2), ("org", "Organization name in replies", c1)]:
        v = col.text_input(label, desk.s(k))
        if v != desk.s(k):
            desk.set(k, v); desk.log(who(), f"Setting changed: {label}")
    lo = st.toggle("Treat live and test emails as on time (for the live demo)", value=desk.s("live_on_time") == "1")
    if lo != (desk.s("live_on_time") == "1"):
        desk.set("live_on_time", "1" if lo else "0")
    st.divider()
    if st.button("Reset demo to sample data", type="secondary"):
        desk.reset(); load_seed(desk); desk.log(who(), "Reset the demo"); st.session_state.pop("sel_email", None); st.rerun()
    if st.button("Clear everything (start with an empty inbox)"):
        desk.reset(); desk.log(who(), "Cleared all data"); st.session_state.pop("sel_email", None); st.rerun()


import landing
import vendor


def _signin_with_code(u, code):
    if code and code == u.get("passcode"):
        sign_in(u)
    else:
        desk.log("System", f"Failed sign-in attempt for {u['name']}")
        st.error("That passcode is not right.")


def page_vendor():
    if user:
        tip("vendor")
    vendor.render(desk, landing.CSS, signed_in=bool(user))


def page_landing():
    em, gs = desk.emails(), desk.groups()
    landing.render((len(em), sum(g["n"] for g in gs), len(gs)), ROLES, USERS, DEMO_ROLES,
                   on_role=lambda u: sign_in(u, "demo"), on_signin=_signin_with_code, rfp=desk.s("rfp_no"),
                   on_google=(lambda: st.login("google") if "google" in dict(_secret("auth", {}) or {}) else st.login()) if AUTH_ON else None)


P_MERGE = st.Page(page_merge, title="Merge report", icon="🧾", url_path="merge")
if not user:
    st.navigation([st.Page(page_landing, title="Inquiry Desk", icon="📨", default=True),
                   st.Page(page_vendor, title="Vendor portal", icon="✉️", url_path="vendor")], position="hidden").run()
else:
    PAGES = [
        (st.Page(page_dashboard, title="Dashboard", icon="📊", default=True), "view"),
        (st.Page(page_inbox, title="Inbox", icon="📥", url_path="inbox"), "view"),
        (st.Page(page_vendor, title="Vendor portal", icon="✉️", url_path="vendor"), "view"),
        (st.Page(page_review, title=f"Needs review ({len(desk.review_queue())})", icon="⚠️", url_path="review"), "review"),
        (st.Page(page_questions, title="Questions", icon="❓", url_path="questions"), "view"),
        (P_MERGE, "view"),
        (st.Page(page_answers, title="Answers & addendum", icon="✍️", url_path="answers"), "view"),
        (st.Page(page_tracker, title="Reply tracker", icon="📤", url_path="tracker"), "view"),
        (st.Page(page_access, title="Access & audit", icon="🔐", url_path="access"), "audit"),
        (st.Page(page_accuracy, title="Accuracy", icon="🎯", url_path="accuracy"), "view"),
        (st.Page(page_settings, title="Settings", icon="⚙️", url_path="settings"), "settings_view"),
    ]
    allowed = [pg for pg, perm in PAGES if can(perm) or (perm == "settings_view" and can("settings"))]
    by_path = {pg.url_path or "dashboard": pg for pg in allowed}
    with st.sidebar:
        st.session_state["show_guide"] = st.toggle("Show guide", value=st.session_state.get("show_guide", True))
        if st.session_state["show_guide"]:
            steps = [(i, k, t) for i, (k, t) in enumerate(GUIDE) if k in by_path]
            done = sum(1 for i, _, _ in steps if st.session_state.get(f"g{i}"))
            with st.expander(f"🧭 Guided test · {done}/{len(steps)} done", expanded=done < len(steps)):
                if user["role"] not in ("Contracts Manager", "Administrator"):
                    st.caption("Tip: sign in as Contracts Manager to approve, publish and send.")
                for i, k, t in steps:
                    a, b = st.columns([1, 6], vertical_alignment="center")
                    a.checkbox("done", key=f"g{i}", label_visibility="collapsed")
                    b.page_link(by_path[k], label=t, icon=None)
    render_user_card()
    st.navigation(allowed).run()
