"""Read the test inbox (IMAP) and send replies (SMTP). Works with Gmail app passwords."""
import email
import imaplib
import smtplib
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.utils import parseaddr, parsedate_to_datetime, make_msgid


def _dec(v):
    try:
        return str(make_header(decode_header(v or "")))
    except Exception:
        return v or ""


def _text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                import re
                html = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", "replace")
                return re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>|</p>", "\n", html, flags=2))
        return ""
    return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", "replace")


def fetch_unseen(cfg, limit=25):
    """Return new messages and mark them read. cfg: imap_host, user, password."""
    box = imaplib.IMAP4_SSL(cfg.get("imap_host", "imap.gmail.com"))
    box.login(cfg["user"], cfg["password"])
    box.select("INBOX")
    _, data = box.search(None, "UNSEEN")
    out = []
    for num in data[0].split()[-limit:]:
        _, msgdata = box.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(msgdata[0][1])
        name, addr = parseaddr(_dec(msg.get("From")))
        try:
            when = parsedate_to_datetime(msg.get("Date"))
        except Exception:
            when = None
        out.append({"from_name": name or addr.split("@")[0], "from_email": addr, "subject": _dec(msg.get("Subject")),
                    "body": _text(msg), "msgid": msg.get("Message-ID", ""), "date": when})
        box.store(num, "+FLAGS", "\\Seen")
    box.logout()
    return out


def send(cfg, to, subject, body, in_reply_to=""):
    m = EmailMessage()
    m["From"] = cfg.get("from_name", "Contracts Administration (demo)") + f" <{cfg['user']}>"
    m["To"] = to
    m["Subject"] = subject
    m["Message-ID"] = make_msgid()
    if in_reply_to:
        m["In-Reply-To"] = in_reply_to; m["References"] = in_reply_to
    m.set_content(body)
    with smtplib.SMTP_SSL(cfg.get("smtp_host", "smtp.gmail.com"), int(cfg.get("smtp_port", 465))) as s:
        s.login(cfg["user"], cfg["password"])
        s.send_message(m)
