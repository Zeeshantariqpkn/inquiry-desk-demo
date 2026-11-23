"""Public landing page: what Inquiry Desk does, and how to get in.

Pure presentation. Sign-in actions are passed in from the app so this file
holds no account logic. Layout is fluid: 4 → 2 → 1 columns as the screen narrows.
"""
import html

import streamlit as st

CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],header[data-testid="stHeader"],
[data-testid="stToolbar"],footer{display:none!important}
.stApp{background:#f5f7f9}
.block-container{padding:0 clamp(16px,4vw,40px) 40px!important;max-width:1200px!important}
.lp,.lp *{font-family:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;box-sizing:border-box}
.lp{color:#14212b}
/* top bar */
.lp-nav{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:18px 0;flex-wrap:wrap}
.lp-brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:17px;color:#0f3d4a;text-decoration:none}
.lp-mark{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#1a7f93,#0f3d4a);display:grid;place-items:center}
.lp-brand small{display:block;font-weight:500;font-size:12px;color:#6a7884;margin-top:-2px}
.lp-links{display:flex;gap:22px;align-items:center;flex-wrap:wrap}
.lp-links a{color:#3d4c58;text-decoration:none;font-size:14px;font-weight:500}
.lp-links a:hover{color:#0f3d4a}
.lp-links a.cta{background:#0f3d4a;color:#fff;padding:9px 16px;border-radius:9px}
/* hero */
.lp-hero{display:grid;grid-template-columns:1.05fr .95fr;gap:clamp(24px,4vw,56px);align-items:center;
 background:radial-gradient(1200px 400px at 0% 0%,#1a7f93 0%,transparent 60%),linear-gradient(135deg,#0c3540,#0f3d4a 45%,#14606f);
 border-radius:22px;padding:clamp(28px,5vw,60px);color:#e9f5f7;overflow:hidden}
.lp-eyebrow{display:inline-flex;align-items:center;gap:8px;font-size:12.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
 background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.16);padding:6px 12px;border-radius:999px;color:#cfeef3}
.lp-eyebrow i{width:7px;height:7px;border-radius:50%;background:#5ee0a0;display:inline-block}
.lp-hero h1{font-size:clamp(30px,4.4vw,52px);line-height:1.06;letter-spacing:-.025em;font-weight:800;color:#fff;margin:18px 0 16px}
.lp-hero h1 span{color:#8fe3ef}
.lp-lead{font-size:clamp(16px,1.5vw,19px);line-height:1.55;color:#cfe4e8;max-width:560px;margin:0 0 26px}
.lp-ctas{display:flex;gap:12px;flex-wrap:wrap}
.lp-btn{display:inline-block;padding:13px 20px;border-radius:11px;font-weight:600;font-size:15px;text-decoration:none!important}
.lp-btn.p{background:#fff;color:#0f3d4a!important}.lp-btn.s{border:1px solid rgba(255,255,255,.35);color:#fff!important}
.lp-note{font-size:13px;color:#a9cdd4;margin-top:14px}
/* product preview */
.lp-win{background:#fff;border-radius:14px;box-shadow:0 30px 60px rgba(0,0,0,.28);overflow:hidden;color:#1f2a33}
.lp-bar{display:flex;gap:6px;padding:10px 12px;background:#eef2f5;border-bottom:1px solid #e1e7ec}
.lp-bar i{width:9px;height:9px;border-radius:50%;background:#cfd8df;display:inline-block}
.lp-win-b{padding:16px}
.lp-mail{font-size:13px;line-height:1.6;background:#fafbfc;border:1px solid #e6ebef;border-radius:10px;padding:12px}
.lp-mail .m{color:#6a7884;font-size:12px;margin-bottom:6px}
.lp-q{background:#fff1b8;border-radius:4px;padding:1px 4px}
.lp-q b{font-size:10px;background:#1a7f93;color:#fff;border-radius:3px;padding:0 4px;margin-right:4px}
.lp-arrow{text-align:center;color:#9aa7b1;font-size:12px;margin:10px 0}
.lp-match{display:flex;justify-content:space-between;align-items:center;gap:10px;border:1px solid #e1e7ec;border-radius:10px;padding:10px 12px;margin-bottom:8px;font-size:13px}
.lp-match b{font-weight:600}.lp-match .c{font-size:11.5px;color:#6a7884}
.lp-pill{font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px;white-space:nowrap}
.g{background:#dff2e6;color:#1f7a45}.b{background:#dcf0f3;color:#14606f}
/* stats */
.lp-stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0 8px}
.lp-stat{background:#fff;border:1px solid #e1e7ec;border-radius:14px;padding:18px 20px}
.lp-stat b{display:block;font-size:clamp(24px,2.6vw,32px);font-weight:800;letter-spacing:-.02em;color:#0f3d4a}
.lp-stat span{font-size:13.5px;color:#5b6b7a}
/* sections */
.lp-sec{padding:clamp(36px,6vw,64px) 0 0}
.lp-kick{font-size:12.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#1a7f93;margin-bottom:8px}
.lp-h2{font-size:clamp(24px,3vw,34px);line-height:1.15;letter-spacing:-.02em;font-weight:800;color:#14212b;margin:0 0 10px}
.lp-sub{font-size:16px;line-height:1.55;color:#5b6b7a;max-width:680px;margin:0 0 24px}
.lp-ba{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.lp-col{border-radius:16px;padding:22px;border:1px solid #e1e7ec;background:#fff}
.lp-col.after{border-color:#bfe0e6;background:#f2fafb}
.lp-col h4{margin:0 0 12px;font-size:15px;font-weight:700}
.lp-col ul{margin:0;padding:0;list-style:none}
.lp-col li{padding:9px 0;border-top:1px solid #eef2f5;font-size:14.5px;color:#3d4c58;display:flex;gap:10px}
.lp-col li:first-child{border-top:0}
.lp-col li i{font-style:normal;font-weight:700;width:18px;flex:none}
.before li i{color:#b3261e}.after li i{color:#1f7a45}
.lp-steps{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;counter-reset:s}
.lp-step{background:#fff;border:1px solid #e1e7ec;border-radius:14px;padding:16px;position:relative}
.lp-step .n{font-size:12px;font-weight:700;color:#1a7f93;background:#e3f3f5;border-radius:6px;padding:2px 7px}
.lp-step b{display:block;margin:10px 0 4px;font-size:15px}
.lp-step span{font-size:13.5px;line-height:1.5;color:#5b6b7a}
.lp-feats{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
.lp-feat{background:#fff;border:1px solid #e1e7ec;border-radius:16px;padding:22px}
.lp-ic{width:38px;height:38px;border-radius:10px;background:#e3f3f5;display:grid;place-items:center;margin-bottom:12px;font-size:18px}
.lp-feat h4{margin:0 0 6px;font-size:16px;font-weight:700}
.lp-feat p{margin:0;font-size:14.5px;line-height:1.55;color:#5b6b7a}
.lp-trust{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.lp-tr{background:#0f3d4a;color:#d6ecef;border-radius:16px;padding:20px}
.lp-tr b{display:block;color:#fff;font-size:15px;margin-bottom:6px}
.lp-tr span{font-size:14px;line-height:1.5}
.lp-foot{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;border-top:1px solid #e1e7ec;margin-top:48px;padding:22px 0;font-size:13px;color:#6a7884}
/* Streamlit widgets inside the landing page */
.st-key-lp_roles [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:14px}
.st-key-lp_roles [data-testid="stColumn"]{flex:1 1 200px!important;min-width:200px!important;width:auto!important}
.st-key-lp_roles [data-testid="stVerticalBlockBorderWrapper"],.st-key-lp_signin [data-testid="stVerticalBlockBorderWrapper"]{background:#fff;border-radius:16px}
.st-key-lp_roles h4{font-size:16px!important;margin:0!important;padding:0!important}
.st-key-lp_roles .stButton button,.st-key-lp_signin .stButton button{border-radius:10px;font-weight:600}
.st-key-lp_faq [data-testid="stExpander"]{background:#fff;border-radius:12px}
/* overrides for Streamlit's own link and heading styles */
.lp a.lp-brand,.lp a.lp-brand:hover{color:#0f3d4a!important;text-decoration:none!important}
.lp a.lp-brand small{color:#6a7884!important}
.lp-links a{text-decoration:none!important}.lp-links a.cta{color:#fff!important}
.lp .lp-hero h1,.lp .lp-hero h1 span{color:#ffffff!important;padding:0!important}.lp .lp-hero h1 span.hl{color:#8fe3ef!important}
.lp h1 a,.lp h2 a,.lp h4 a,[data-testid="stHeaderActionElements"]{display:none!important}
/* equal-height role cards with the button at the bottom */
.st-key-lp_roles [data-testid="stHorizontalBlock"]{align-items:stretch}
.st-key-lp_roles [data-testid="stColumn"]>[data-testid="stVerticalBlock"],
.st-key-lp_roles [data-testid="stColumn"] [data-testid="stLayoutWrapper"],
.st-key-lp_roles [data-testid="stColumn"] [data-testid="stLayoutWrapper"]>[data-testid="stVerticalBlock"]{height:100%}
.st-key-lp_roles [data-testid="stColumn"] [data-testid="stLayoutWrapper"]>[data-testid="stVerticalBlock"]{background:#fff;border-radius:16px}
.st-key-lp_roles [class*="st-key-demo_"]{margin-top:auto}
.st-key-lp_signin{margin-top:8px}
/* responsive */
@media (max-width:1100px){.lp-steps{grid-template-columns:repeat(3,1fr)}}
@media (max-width:900px){.lp-hero{grid-template-columns:1fr}.lp-stats,.lp-trust{grid-template-columns:repeat(2,1fr)}.lp-feats{grid-template-columns:repeat(2,1fr)}.lp-links a:not(.cta){display:none}}
@media (max-width:640px){.lp-ba,.lp-feats,.lp-trust{grid-template-columns:1fr}.lp-steps{grid-template-columns:repeat(2,1fr)}
 .lp-stats{grid-template-columns:1fr 1fr;gap:10px}.lp-stat{padding:14px}.lp-hero{border-radius:16px}.lp-btn{flex:1 1 100%;text-align:center}}
@media (max-width:380px){.lp-steps{grid-template-columns:1fr}}
</style>"""

MARK = '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h10M4 17h13" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/><circle cx="19" cy="17" r="2.6" fill="#8fe3ef"/></svg>'


def _md(x, **_):
    """Markdown treats blank lines as the end of an HTML block, so send the HTML as one line."""
    st.markdown(" ".join(x.split("\n")), unsafe_allow_html=True)


def render(stats, roles, users, demo_roles, on_role, on_signin, rfp, on_google=None):
    e = html.escape
    st.markdown(CSS, unsafe_allow_html=True)
    em, nq, ng = stats
    rep = round((1 - ng / max(1, nq)) * 100)

    _md(f"""<div class="lp">
<div class="lp-nav"><a class="lp-brand" href="#top"><span class="lp-mark">{MARK}</span><span>Inquiry Desk<small>by DataPoch</small></span></a>
<div class="lp-links"><a href="#how">How it works</a><a href="#features">Features</a><a href="#security">Security</a><a href="#faq">FAQ</a><a class="cta" href="#start">Open the demo</a></div></div>

<div class="lp-hero" id="top"><div>
<span class="lp-eyebrow"><i></i>RFP vendor questions, handled</span>
<h1>Every vendor question answered <span class="hl">once, on time,</span> and on the record.</h1>
<p class="lp-lead">Inquiry Desk reads the procurement mailbox, finds every question in every email, groups repeats by meaning, and helps your team publish one addendum and reply to every vendor. Staff approve every answer.</p>
<div class="lp-ctas"><a class="lp-btn p" href="#start">Try the live demo</a><a class="lp-btn s" href="#how">See how it works</a></div>
<div class="lp-note">Demo with sample data based on public RFP No. {e(rfp)} documents. No agency data.</div></div>

<div class="lp-win" aria-label="Product preview"><div class="lp-bar"><i></i><i></i><i></i></div><div class="lp-win-b">
<div class="lp-mail"><div class="m">Q-1005 · Pinecrest Consulting · 3 questions found</div>
<span class="lp-q"><b>Q1</b>Is there a cap on the total contract value?</span><br>
<span class="lp-q"><b>Q2</b>Must the new website stay on the current Sitefinity platform?</span><br>
<span class="lp-q"><b>Q3</b>Is WCAG 2.1 AA conformance required?</span></div>
<div class="lp-arrow">▼ matched by meaning</div>
<div class="lp-match"><div><b>Budget &amp; pricing</b><div class="c">7 vendors asked this</div></div><span class="lp-pill g">Addendum Q#2</span></div>
<div class="lp-match"><div><b>Platform &amp; CMS</b><div class="c">3 vendors asked this</div></div><span class="lp-pill b">Draft ready</span></div>
<div class="lp-match" style="margin:0"><div><b>Accessibility</b><div class="c">2 vendors asked this</div></div><span class="lp-pill b">Draft ready</span></div>
</div></div></div>

<div class="lp-stats"><div class="lp-stat"><b>{em}</b><span>vendor emails in this demo</span></div>
<div class="lp-stat"><b>{nq}</b><span>questions found inside them</span></div>
<div class="lp-stat"><b>{ng}</b><span>unique questions to answer</span></div>
<div class="lp-stat"><b>{rep}%</b><span>repeats staff never re-read</span></div></div>

<div class="lp-sec"><div class="lp-kick">The problem</div><div class="lp-h2">Hundreds of emails, mostly the same questions</div>
<p class="lp-sub">When an RFP draws heavy interest, contracts staff read every email, spot the repeats, write answers, compile an addendum and reply to each vendor by hand. Inquiry Desk takes the reading, sorting and copying, and leaves every decision with staff.</p>
<div class="lp-ba"><div class="lp-col before"><h4>Today, by hand</h4><ul>
<li><i>✕</i>Read every email to find the questions</li><li><i>✕</i>Spot repeats from memory</li>
<li><i>✕</i>Late questions pile up and are held</li><li><i>✕</i>Deadlines move while answers are prepared</li>
<li><i>✕</i>Reply to each vendor one by one</li></ul></div>
<div class="lp-col after"><h4>With Inquiry Desk</h4><ul>
<li><i>✓</i>Every question found and logged automatically</li><li><i>✓</i>Repeats grouped by meaning, originals kept</li>
<li><i>✓</i>Late repeats pointed to the published answer</li><li><i>✓</i>Staff review one list of unique questions</li>
<li><i>✓</i>One reply per email, every answer listed</li></ul></div></div></div>

<div class="lp-sec" id="how"><div class="lp-kick">How it works</div><div class="lp-h2">From inbox to addendum in six steps</div>
<div class="lp-steps">
<div class="lp-step"><span class="n">01</span><b>Log</b><span>Every email saved with an ID; late ones flagged.</span></div>
<div class="lp-step"><span class="n">02</span><b>Split</b><span>Each question in an email found separately.</span></div>
<div class="lp-step"><span class="n">03</span><b>Group</b><span>Same meaning becomes one question.</span></div>
<div class="lp-step"><span class="n">04</span><b>Review</b><span>Only uncertain matches go to staff.</span></div>
<div class="lp-step"><span class="n">05</span><b>Approve</b><span>A manager approves; the addendum is issued.</span></div>
<div class="lp-step"><span class="n">06</span><b>Reply</b><span>One reply per email, every Q# listed.</span></div></div></div>

<div class="lp-sec" id="features"><div class="lp-kick">What your team gets</div><div class="lp-h2">Built around the questions procurement teams ask</div>
<div class="lp-feats">
<div class="lp-feat"><div class="lp-ic">📄</div><h4>Every original, one click away</h4><p>Each grouped question links to the vendor's email, with their exact sentence highlighted.</p></div>
<div class="lp-feat"><div class="lp-ic">✂️</div><h4>Several questions in one email</h4><p>Each question is matched on its own, so one email can map to several answers.</p></div>
<div class="lp-feat"><div class="lp-ic">🧭</div><h4>Grouped by meaning</h4><p>“How much has the Commission set aside?” joins the budget question, even without the word budget.</p></div>
<div class="lp-feat"><div class="lp-ic">↩️</div><h4>Merge and undo</h4><p>When questions are merged, both originals stay visible and the merge can be reversed.</p></div>
<div class="lp-feat"><div class="lp-ic">📬</div><h4>A reply for every email</h4><p>The Reply tracker shows each email, its questions, their answer numbers and whether the reply went out.</p></div>
<div class="lp-feat"><div class="lp-ic">🎯</div><h4>Measured accuracy</h4><p>Tested on questions the system never saw. Anything uncertain goes to staff, never guessed.</p></div></div></div>

<div class="lp-sec" id="security"><div class="lp-kick">Control and security</div><div class="lp-h2">Your staff stay in charge</div>
<div class="lp-trust">
<div class="lp-tr"><b>Human approval</b><span>No answer or email reaches a vendor without a named approver.</span></div>
<div class="lp-tr"><b>Separation of duties</b><span>Staff draft. Managers approve and send. Security reviews.</span></div>
<div class="lp-tr"><b>Full audit trail</b><span>Every sign-in, decision and email is logged with who and when.</span></div>
<div class="lp-tr"><b>Your environment</b><span>In production: hosted in the United States or inside your own Microsoft tenant.</span></div></div></div>

<div class="lp-sec" id="start"><div class="lp-kick">Get started</div><div class="lp-h2">Open the demo as any role</div>
<p class="lp-sub">Each role sees only what that person would see. Try Contracts Staff, then Contracts Manager, to see separation of duties in action.</p></div>
</div>""", unsafe_allow_html=True)

    if demo_roles:
        with st.container(key="lp_roles"):
            cols = st.columns(len(roles))
            for col, (rn, r) in zip(cols, roles.items()):
                u = next((x for x in users if x["role"] == rn), None)
                with col.container(border=True):
                    st.markdown(f"#### {r['icon']} {rn}")
                    st.caption(r["desc"])
                    if u:
                        st.caption(f"Signs in as {u['name']}")
                        if st.button("Enter", key=f"demo_{rn}", use_container_width=True, type="primary" if rn == "Contracts Manager" else "secondary"):
                            on_role(u)
                    else:
                        st.caption("No account set for this role.")

    with st.container(key="lp_signin"):
        a, b = st.columns([1, 1], gap="large")
        with a:
            st.markdown('<div class="lp"><div class="lp-kick" style="margin-top:28px">Staff sign in</div>'
                        '<div class="lp-h2" style="font-size:22px">Sign in with your account</div>'
                        '<p class="lp-sub" style="font-size:15px">Accounts follow separation of duties. In production, sign-in uses the agency\'s Microsoft accounts with multi-factor authentication.</p></div>',
                        unsafe_allow_html=True)
        with b, st.container(border=True):
            if on_google:
                if st.button("Sign in with Google", use_container_width=True, icon=":material/login:"):
                    on_google()
                st.caption("Your role is set by the administrator for your Google account.")
                st.divider()
            labels = [f"{u['name']} · {u['role']}" for u in users]
            pick = st.selectbox("Account", labels)
            code = st.text_input("Passcode", type="password", placeholder="Passcode")
            if st.button("Sign in", type="primary", use_container_width=True):
                on_signin(users[labels.index(pick)], code)

    st.markdown('<div class="lp" id="faq"><div class="lp-sec" style="padding-top:40px"><div class="lp-kick">FAQ</div><div class="lp-h2">Questions agencies ask</div></div></div>', unsafe_allow_html=True)
    with st.container(key="lp_faq"):
        for q, a_ in [
            ("Does the AI send anything to vendors by itself?", "No. It sorts and drafts. Every answer is approved by a named manager, and replies go out only after the answer is published in an addendum."),
            ("What if it groups a question wrongly?", "Every match has a score. Uncertain ones go to a review queue instead of being guessed, staff can move or split any question, and merges can be undone. Each correction is used for similar questions later."),
            ("Do staff have to open every email to check it?", "No. They review only the uncertain matches and, if they wish, a small random sample. The original email is always one click away when needed."),
            ("Where is the data stored?", "This demo uses test data only. In production, the system runs in the United States or inside the agency's own Microsoft environment, and agency data is not used to train AI models."),
            ("How accurate is it?", "The Accuracy page shows measured results on test questions the system never saw. Accuracy is reported, not claimed."),
        ]:
            with st.expander(q):
                st.write(a_)

    st.markdown('<div class="lp"><div class="lp-foot"><span>Inquiry Desk · a DataPoch demo</span><span>Sample data based on public RFP documents · no agency data is used</span></div></div>', unsafe_allow_html=True)
