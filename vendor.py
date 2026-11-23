"""Vendor portal: submit questions without signing in, then track them and read the reply.

Works with no email setup. Questions enter the same pipeline as live email
(split, grouped by meaning, reviewed, approved, published), and the reply a
vendor would receive by email is shown here once its answers are published.
"""
import html

import streamlit as st

STATE_TEXT = {
    "needs-answer": ("Being answered by staff", "#8a5206", "#fcedd6"),
    "draft": ("Answer drafted, waiting for approval", "#14606f", "#dcf0f3"),
    "approved": ("Approved, will be published in the next addendum", "#1f7a45", "#dff2e6"),
    "published": ("Answered", "#1f7a45", "#dff2e6"),
}

CSS = """<style>
.vp,.vp *{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif}
.vp-top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:18px 0}
.vp-top a{color:#0f3d4a!important;text-decoration:none!important;font-weight:600}
.vp-head{background:linear-gradient(135deg,#0c3540,#0f3d4a 45%,#14606f);border-radius:18px;padding:clamp(22px,4vw,40px);color:#d9eef1;margin-bottom:18px}
.vp-head h1{color:#fff!important;font-size:clamp(26px,3.4vw,38px);font-weight:800;letter-spacing:-.02em;margin:6px 0 10px;padding:0!important}
.vp-head h1 span{color:#fff!important}
.vp-head p{margin:0;max-width:720px;line-height:1.55;font-size:16px}
.vp-k{font-size:12.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#8fe3ef}
.vp-q{border:1px solid #e1e7ec;border-radius:12px;padding:12px 14px;margin:8px 0;background:#fff}
.vp-q b{color:#14212b}.vp-s{display:inline-block;font-size:12px;font-weight:600;padding:2px 9px;border-radius:999px;margin-top:6px}
.vp-ref{font-family:monospace;font-size:22px;font-weight:700;color:#0f3d4a}
.vp-reply{white-space:pre-wrap;background:#fff;border:1px solid #e1e7ec;border-left:4px solid #1a7f93;border-radius:10px;padding:14px 16px;line-height:1.6;color:#1f2a33}
.st-key-vp_form [data-testid="stForm"],.st-key-vp_track [data-testid="stForm"]{background:#fff;border-radius:14px}
</style>"""

EXAMPLE = ("Hello,\n\nWe are preparing a proposal for RFP No. 19-2026 and have a few questions.\n\n"
           "1. How much has the Commission set aside for this project?\n"
           "2. Will the Commission host the new website, or should we include hosting?\n"
           "3. Is WCAG 2.1 AA required for the intranet as well?\n\nThank you")


def _status_card(desk, p):
    if p["review"]:
        t, fg, bg = "Received, staff are checking it", "#8a5206", "#fcedd6"
    else:
        t, fg, bg = STATE_TEXT.get(p["gstatus"], ("Received", "#4d5b68", "#eceff3"))
    extra = ""
    if p["gstatus"] == "published":
        g = desk.group(p["group_id"])
        t = f"Answered in Addendum No. {g['addendum']}, Q#{g['qno']}"
        extra = f"<div style='margin-top:8px;color:#3d4c58'><b>Answer:</b> {html.escape(g['answer'])}</div>"
    return (f"<div class='vp-q'><b>{html.escape(p['text'])}</b><br>"
            f"<span class='vp-s' style='color:{fg};background:{bg}'>{t}</span>{extra}</div>")


def render(desk, base_css, signed_in=False):
    if not signed_in:
        st.markdown(base_css, unsafe_allow_html=True)
    st.markdown(CSS, unsafe_allow_html=True)
    if not signed_in:
        st.markdown('<div class="vp vp-top"><a href="/" target="_self">← Inquiry Desk</a><span style="color:#6a7884;font-size:13px">Vendor portal · demo</span></div>', unsafe_allow_html=True)
    st.markdown(f"""<div class="vp vp-head"><div class="vp-k">Vendor portal · RFP No. {html.escape(desk.s('rfp_no'))}</div>
<h1>Ask a question about this RFP</h1>
<p>Write your questions the way you would in an email. Each question is found and logged separately, and you get a reference number to check its status. No sign-in needed. This is a demo: please don't enter real procurement or personal information.</p></div>""", unsafe_allow_html=True)

    tab_ask, tab_track = st.tabs(["Submit questions", "Check status and read the reply"])
    with tab_ask, st.container(key="vp_form"):
        with st.form("vp_submit", clear_on_submit=False):
            c1, c2 = st.columns(2)
            name = c1.text_input("Your name", placeholder="Jane Smith")
            firm = c2.text_input("Company", placeholder="Example Web Partners")
            email = c1.text_input("Your email", placeholder="you@company.com", help="Used only to look up your reply in this portal.")
            subject = c2.text_input("Subject", value=f"Questions on RFP {desk.s('rfp_no')}")
            body = st.text_area("Your message", value=EXAMPLE, height=220)
            sent = st.form_submit_button("Submit questions", type="primary", use_container_width=True)
        if sent:
            if not (name.strip() and email.strip() and "@" in email and body.strip()):
                st.error("Please add your name, a valid email and your message.")
            else:
                with st.spinner("Finding each question and matching it…"):
                    r = desk.ingest(name.strip(), email.strip(), subject.strip() or "Question", body, None, "portal", firm=firm.strip())
                st.session_state["vp_ref"] = (r["id"], email.strip().lower())
                st.success("Received. Keep your reference number to check the status.")
                st.markdown(f"Reference: <span class='vp-ref'>{r['id']}</span>", unsafe_allow_html=True)
                ps = desk.parts_of_email(r["id"])
                st.markdown(f"**We found {len(ps)} separate question{'s' if len(ps) != 1 else ''} in your message:**")
                st.markdown("".join(_status_card(desk, p) for p in ps), unsafe_allow_html=True)
                st.caption("Answers are published to all vendors at the same time in an addendum. You'll see each answer here once it is published.")

    with tab_track, st.container(key="vp_track"):
        last = st.session_state.get("vp_ref", ("", ""))
        with st.form("vp_lookup"):
            c1, c2 = st.columns(2)
            ref = c1.text_input("Reference number", value=last[0], placeholder="Q-1030")
            em = c2.text_input("Your email", value=last[1], placeholder="you@company.com")
            go = st.form_submit_button("Check status", use_container_width=True)
        if go or last[0]:
            ref_u, em_l = (ref or "").strip().upper(), (em or "").strip().lower()
            e = next((x for x in desk.emails() if x["id"].upper() == ref_u and x["from_email"].lower() == em_l), None)
            if not e:
                if go:
                    st.warning("No submission matches that reference number and email.")
            else:
                ps = desk.parts_of_email(e["id"])
                done = sum(1 for p in ps if p["gstatus"] == "published")
                st.markdown(f"**{e['id']}** · {html.escape(e['subject'])} · {done} of {len(ps)} answered")
                st.markdown("".join(_status_card(desk, p) for p in ps), unsafe_allow_html=True)
                reps = desk.replies(e["id"])
                if reps:
                    st.markdown("**The reply you received**")
                    st.markdown(f"<div class='vp-reply'>{html.escape(reps[-1]['body'])}</div>", unsafe_allow_html=True)
                    st.caption(f"Sent {reps[-1]['at'].replace('T', ' ')} ET. With email connected, this reply is also emailed to you.")
                elif done == len(ps) and ps:
                    st.info("All your questions are answered. Your reply is being prepared by Contracts Administration.")
