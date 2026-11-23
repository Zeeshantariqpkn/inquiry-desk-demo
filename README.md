# Inquiry Desk: live demo (DataPoch)

Vendor questions on an RFP are logged, split into separate questions, grouped by meaning, answered once, approved by staff, published as an addendum, and replied to. Every step traces back to the original email.

Test data only. No real agency data.

## Put it online (free, about 10 minutes)

1. **GitHub:** create a new repository (for example `inquiry-desk-demo`) and upload everything in this folder, keeping the folders as they are. Don't upload a `secrets.toml` file.
2. **Streamlit Cloud:** go to share.streamlit.io, sign in with GitHub, and click **Create app → Deploy a public app from GitHub**.
   - Repository: your new repo · Branch: `main` · Main file: `streamlit_app.py`
   - **Advanced settings → Python version: 3.12**
   - Pick a custom address, e.g. `datapoch-inquirydesk`, to get `https://datapoch-inquirydesk.streamlit.app`
3. **Secrets:** in **Advanced settings → Secrets** (or later under App → Settings → Secrets), paste the contents of `.streamlit/secrets.toml.example` with your own values. **Change the passcodes.**
4. Click **Deploy**. The first start takes a few minutes while the meaning model downloads.
5. Open the **Accuracy** page. It should say **Engine: Meaning model (bge-small-en-v1.5)**. If it says "Backup", the model didn't download; reboot the app from the menu.

## Optional: live inbox (Jake's team emails it during the call)

1. Create a free Gmail account, e.g. `datapoch.rfpdemo@gmail.com`.
2. Turn on 2-Step Verification, then create an **App password** (Google Account → Security → App passwords).
3. Put the address and app password in the `[mail]` secret. The sidebar then shows 🟢 Live inbox.
4. On the **Inbox** page, keep **Auto-check** on. New emails appear within about 20 seconds.
5. Before the call, set **Settings → Treat live and test emails as on time** to ON.

Replies are only emailed to messages that arrived through the live inbox. The sample data and "Send a test email" are marked as simulated.

## Optional: AI check (better accuracy, free)

Create a free key at console.groq.com (no card needed) and add it under `[ai]`. The AI double-checks questions the meaning model is unsure about, and explains each decision in one line. Run **Accuracy → Run AI test** to measure it.

## Run it on your computer

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Demo script (about 10 minutes)

1. **Dashboard:** emails in, questions found, unique questions, % repeats.
2. **Inbox:** open the "Three questions" email. Each question is highlighted (Q1, Q2, Q3) and matched separately.
3. **Live test:** Jake's team emails the test address (or you use "Send a test email"). Watch it split and match.
4. **Needs review:** only uncertain items. Confirm one, and the system learns from it.
5. **Questions → Merge report:** every email behind a question, with its exact wording and reference ID.
6. **Answers & addendum:** sign in as Manager, approve, then publish Addendum No. 3.
7. **Reply tracker:** send the ready replies. One reply per email, listing every Q#.
8. **Access & audit:** who can do what, and every action logged.
9. **Accuracy:** the measured numbers, plus "try your own question".

## Roles

The landing page lets visitors sign in with a passcode, or enter as any role in one click (`demo_roles = true`).

| Role | Can do |
|---|---|
| Administrator | Everything, including settings and reset |
| Contracts Manager | Approve answers, publish addenda, send replies |
| Contracts Staff | Sort, confirm or move questions, merge, draft answers. Cannot approve or send |
| Security Reviewer | Access and audit log, settings (read-only), accuracy. Read-only |
| Viewer | Read-only |

## Good to know

- Refreshing the browser signs you out. Use the sidebar links to move between pages.
- On the free plan the app sleeps after a while without visitors. Open it 10 minutes before the call.
- Data can reset when Streamlit restarts the app. That's fine for a demo; a pilot would use a real database.
- Anyone with the link can **view**. Only people with a passcode can change anything.
