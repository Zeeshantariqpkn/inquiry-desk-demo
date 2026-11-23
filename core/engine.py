"""Inquiry Desk engine: every email, question, group, answer and reply, with an audit log.

One shared store for all viewers of the app (SQLite + a lock). The rules that
make the guarantees hold live here:
  * every email is stored before anything else happens
  * every question keeps a link to its email and its exact wording
  * a merge keeps a snapshot and can be undone
  * nothing is sent unless every question in that email has a published answer
  * every action is written to the audit log
"""
import json
import sqlite3
import threading
from datetime import datetime, timezone, timedelta

import numpy as np

from . import llm
from .data import CATEGORIES, KB, LABELED
from .embed import encode
from .evaluate import decide, lib_score
from .text import clean_for_match, split_questions

ET = timezone(timedelta(hours=-5))
SCHEMA = """
CREATE TABLE IF NOT EXISTS emails(id TEXT PRIMARY KEY, msgid TEXT, from_name TEXT, from_email TEXT, firm TEXT,
  subject TEXT, body TEXT, received TEXT, late INT, source TEXT, status TEXT DEFAULT 'open');
CREATE TABLE IF NOT EXISTS parts(id INTEGER PRIMARY KEY AUTOINCREMENT, email_id TEXT, idx INT, text TEXT,
  group_id INT, score REAL, how TEXT, review INT, review_reason TEXT, ai_reason TEXT, emb BLOB);
CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, cat_how TEXT,
  intent TEXT, answer TEXT, cite TEXT, status TEXT, addendum INT, qno INT, merged TEXT DEFAULT '[]', created TEXT);
CREATE TABLE IF NOT EXISTS replies(id INTEGER PRIMARY KEY AUTOINCREMENT, email_id TEXT, at TEXT, subject TEXT,
  body TEXT, by TEXT, mode TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, who TEXT, what TEXT);
CREATE TABLE IF NOT EXISTS lib(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, intent TEXT, category TEXT, source TEXT, emb BLOB);
CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
"""
DEFAULTS = {"rfp_no": "19-2026", "rfp_title": "Website and Intranet Redesign and Deployment",
            "deadline": "2026-10-27T17:00", "due": "December 11, 2026, 5:00 P.M. Eastern",
            "live_on_time": "1", "next_addendum": "3", "org": "Ohio Turnpike and Infrastructure Commission (demo)"}


def now_et():
    return datetime.now(ET).strftime("%Y-%m-%dT%H:%M")


def _blob(v):
    return np.asarray(v, dtype=np.float32).tobytes()


def _vec(b):
    return np.frombuffer(b, dtype=np.float32)


class Desk:
    def __init__(self, path, thresholds):
        self.th = thresholds
        self.lock = threading.RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        for k, v in DEFAULTS.items():
            self.db.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (k, v))
        if not self.db.execute("SELECT 1 FROM lib LIMIT 1").fetchone():
            rows = [(w, it, cat) for it, (cat, ws) in LABELED.items() for w in ws]
            embs = encode([clean_for_match(r[0]) for r in rows])
            self.db.executemany("INSERT INTO lib(text,intent,category,source,emb) VALUES(?,?,?,?,?)",
                                [(t, it, c, "Past RFP questions", _blob(e)) for (t, it, c), e in zip(rows, embs)])
        self.db.commit()
        self._load_lib()

    # ---------- helpers ----------
    def q(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def x(self, sql, args=()):
        with self.lock:
            cur = self.db.execute(sql, args); self.db.commit(); return cur.lastrowid

    def s(self, k):
        r = self.q("SELECT v FROM settings WHERE k=?", (k,))
        return r[0]["v"] if r else DEFAULTS.get(k, "")

    def set(self, k, v):
        self.x("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, str(v)))

    def log(self, who, what):
        self.x("INSERT INTO events(at,who,what) VALUES(?,?,?)", (now_et(), who, what))

    def _load_lib(self):
        rows = self.q("SELECT text,intent,category,emb FROM lib")
        self.lib_intents = [r["intent"] for r in rows]
        self.lib_cat = {r["intent"]: r["category"] for r in rows}
        self.lib_text = [r["text"] for r in rows]
        self.lib_embs = np.vstack([_vec(r["emb"]) for r in rows]) if rows else None

    def learn(self, text, intent, category, who):
        """A staff decision becomes a new library example, so similar questions follow it next time."""
        e = encode([clean_for_match(text)])[0]
        self.x("INSERT INTO lib(text,intent,category,source,emb) VALUES(?,?,?,?,?)", (text, intent, category, f"Staff correction ({who})", _blob(e)))
        self._load_lib()

    # ---------- ingest ----------
    def next_email_id(self):
        r = self.q("SELECT id FROM emails")
        n = max([int(x["id"].split("-")[1]) for x in r] or [1000])
        return f"Q-{n + 1}"

    def ingest(self, from_name, from_email, subject, body, received=None, source="live", msgid="", firm=""):
        with self.lock:
            if msgid and self.q("SELECT 1 FROM emails WHERE msgid=?", (msgid,)):
                return None
            eid = self.next_email_id()
            received = received or now_et()
            late = int(received > self.s("deadline") and not (source != "seed" and self.s("live_on_time") == "1"))
            self.x("INSERT INTO emails VALUES(?,?,?,?,?,?,?,?,?,?,'open')",
                   (eid, msgid, from_name, from_email, firm or (from_email.split("@")[-1] if "@" in from_email else ""),
                    subject, body, received, late, source))
            qs = (llm.split(body) if source != "seed" else None) or split_questions(body)
            placed = []
            for i, qt in enumerate(qs):
                placed.append(self._place(eid, i, qt))
            self.log("System", f"Received {eid} from {from_name or from_email}: {len(qs)} question{'s' if len(qs) != 1 else ''}" +
                     (", late" if late else ""))
            return {"id": eid, "late": late, "parts": placed}

    def _group_for_intent(self, intent):
        r = self.q("SELECT id FROM groups WHERE intent=?", (intent,))
        if r:
            return r[0]["id"]
        for g in self.q("SELECT id, merged FROM groups WHERE merged != '[]'"):  # merged-away questions point to the keeper
            if any(m["group"].get("intent") == intent for m in json.loads(g["merged"])):
                return g["id"]
        return None

    def _key(self, gid):
        """Give a staff-made group a stable key so library examples can point to it."""
        g = self.group(gid)
        if not g["intent"]:
            self.x("UPDATE groups SET intent=? WHERE id=?", (f"G{gid}", gid)); return f"G{gid}"
        return g["intent"]

    def _new_group(self, title, category, cat_how, intent=None):
        ans, cite, status = "", "", "needs-answer"
        if intent:
            for k in KB:
                if intent in k["answers"]:
                    ans, cite, status = k["text"], k["cite"], "draft"; break
        return self.x("INSERT INTO groups(title,category,cat_how,intent,answer,cite,status,created) VALUES(?,?,?,?,?,?,?,?)",
                      (title, category, cat_how, intent, ans, cite, status, now_et()))

    def _place(self, eid, idx, text):
        clean = clean_for_match(text)
        vec = encode([clean])[0]
        inbox = self.q("SELECT id,group_id,emb FROM parts WHERE group_id IS NOT NULL")
        inbox_embs = np.vstack([_vec(p["emb"]) for p in inbox]) if inbox else None
        inbox_groups = [p["group_id"] for p in inbox]
        key, score, how, reason = decide(vec, self.th, self.lib_embs, self.lib_intents, inbox_embs, inbox_groups, {})
        ai_reason = ""

        # Optional AI check on anything that is not a confident library or inbox match.
        if llm.enabled() and how in ("suggested", "new", "inbox"):
            cands = self._candidates(vec)
            res = llm.match(clean, [(c["key"], c["text"]) for c in cands], CATEGORIES)
            if res:
                ai_reason = res["reason"]
                if res["key"] is not None and res["confidence"] >= 0.8:
                    key, how, reason = res["key"], "ai", ""
                elif res["key"] is not None:
                    key, how, reason = res["key"], "suggested", "The AI thinks this is probably the same question. Please confirm."
                else:
                    key, how, reason = None, "new", "New question. The AI found no earlier question it matches."
                self._ai_cat = res["category"]
        gid = None
        if key is not None:
            if key[0] == "intent":
                gid = self._group_for_intent(key[1]) or self._new_group(clean, self.lib_cat.get(key[1], "Other"), "From the matched known question", key[1])
            else:
                gid = key[1]
        else:
            cat, cat_how = self._category(vec)
            if getattr(self, "_ai_cat", None):
                cat, cat_how = self._ai_cat, "Chosen by the AI check"
            gid = self._new_group(clean, cat, cat_how)
        self._ai_cat = None
        review = int(how in ("suggested", "new"))
        self.x("INSERT INTO parts(email_id,idx,text,group_id,score,how,review,review_reason,ai_reason,emb) VALUES(?,?,?,?,?,?,?,?,?,?)",
               (eid, idx, text, gid, float(score), how, review, reason, ai_reason, _blob(vec)))
        return {"text": text, "group": gid, "how": how, "score": score, "review": review}

    def _candidates(self, vec, k=5):
        """Closest existing groups and known questions, for the AI to choose from."""
        out, seen = [], set()
        if self.lib_embs is not None:
            s = self.lib_embs @ vec
            for j in np.argsort(-s)[:12]:
                it = self.lib_intents[j]
                if it in seen:
                    continue
                seen.add(it); out.append({"key": ("intent", it), "text": self.lib_text[j], "s": float(s[j])})
        for p in self.q("SELECT p.group_id, p.emb, g.title, g.intent FROM parts p JOIN groups g ON g.id=p.group_id"):
            if p["intent"] in seen:
                continue
            sv = float(_vec(p["emb"]) @ vec)
            out.append({"key": ("group", p["group_id"]), "text": p["title"], "s": sv})
        best = {}
        for c in sorted(out, key=lambda c: -c["s"]):
            best.setdefault(c["key"], c)
        return list(best.values())[:k]

    def _category(self, vec):
        if self.lib_embs is None:
            return "Other", "No library yet"
        it, s, m, j = lib_score(vec, self.lib_embs, self.lib_intents)
        return self.lib_cat[it], f"Closest known question: “{self.lib_text[j]}” ({s:.2f})"

    # ---------- reads ----------
    def groups(self):
        gs = self.q("SELECT * FROM groups ORDER BY id")
        stats = {r["group_id"]: r for r in self.q(
            "SELECT p.group_id, COUNT(*) n, SUM(e.late) late, SUM(p.review) rev FROM parts p JOIN emails e ON e.id=p.email_id GROUP BY p.group_id")}
        for g in gs:
            st = stats.get(g["id"], {})
            g["n"] = st.get("n", 0); g["late"] = st.get("late", 0) or 0; g["rev"] = st.get("rev", 0) or 0
            g["merged"] = json.loads(g["merged"] or "[]")
        return [g for g in gs if g["n"] > 0 or g["merged"]]

    def group(self, gid):
        r = self.q("SELECT * FROM groups WHERE id=?", (gid,))
        if r:
            r[0]["merged"] = json.loads(r[0]["merged"] or "[]")
        return r[0] if r else None

    def parts_of_group(self, gid):
        return self.q("SELECT p.id pid, p.text, p.score, p.how, p.review, p.review_reason, p.ai_reason, e.* FROM parts p "
                      "JOIN emails e ON e.id=p.email_id WHERE p.group_id=? ORDER BY e.received", (gid,))

    def parts_of_email(self, eid):
        return self.q("SELECT p.*, g.title gtitle, g.category, g.status gstatus, g.addendum, g.qno FROM parts p "
                      "LEFT JOIN groups g ON g.id=p.group_id WHERE p.email_id=? ORDER BY p.idx", (eid,))

    def emails(self):
        return self.q("SELECT * FROM emails ORDER BY received DESC")

    def review_queue(self):
        return self.q("SELECT p.id pid, p.text, p.score, p.how, p.review_reason, p.ai_reason, p.group_id, g.title gtitle, g.category, "
                      "e.id eid, e.from_name, e.firm, e.received FROM parts p JOIN emails e ON e.id=p.email_id "
                      "LEFT JOIN groups g ON g.id=p.group_id WHERE p.review=1 ORDER BY e.received DESC")

    def events(self, n=200):
        return self.q("SELECT * FROM events ORDER BY id DESC LIMIT ?", (n,))

    def replies(self, eid):
        return self.q("SELECT * FROM replies WHERE email_id=? ORDER BY id", (eid,))

    # ---------- staff actions ----------
    def confirm(self, pid, who):
        p = self.q("SELECT p.*, g.intent, g.category, g.title FROM parts p JOIN groups g ON g.id=p.group_id WHERE p.id=?", (pid,))[0]
        self.x("UPDATE parts SET review=0, how='staff' WHERE id=?", (pid,))
        self.learn(p["text"], self._key(p["group_id"]), p["category"], who)
        self.log(who, f"Confirmed {p['email_id']} question {p['idx']+1} belongs to “{p['title'][:60]}”")

    def move(self, pid, gid, who):
        p = self.q("SELECT * FROM parts WHERE id=?", (pid,))[0]
        g = self.group(gid)
        self.x("UPDATE parts SET group_id=?, review=0, how='staff' WHERE id=?", (gid, pid))
        self.learn(p["text"], self._key(gid), g["category"], who)
        self.log(who, f"Moved {p['email_id']} question {p['idx']+1} to “{g['title'][:60]}”")

    def split_out(self, pid, who):
        p = self.q("SELECT * FROM parts WHERE id=?", (pid,))[0]
        cat, how = self._category(_vec(p["emb"]))
        gid = self._new_group(clean_for_match(p["text"]), cat, how)
        self.x("UPDATE parts SET group_id=?, review=0, how='staff' WHERE id=?", (gid, pid))
        self.log(who, f"Made {p['email_id']} question {p['idx']+1} its own question")
        return gid

    def set_category(self, gid, cat, who):
        g = self.group(gid)
        self.x("UPDATE groups SET category=?, cat_how=? WHERE id=?", (cat, f"Set by {who}", gid))
        for p in self.parts_of_group(gid)[:3]:
            self.learn(p["text"], self._key(gid), cat, who)
        self.log(who, f"Changed category of “{g['title'][:50]}” from {g['category']} to {cat}")

    def edit_title(self, gid, title, who):
        self.x("UPDATE groups SET title=? WHERE id=?", (title, gid)); self.log(who, f"Edited question wording: “{title[:60]}”")

    def merge(self, keep, other, who):
        a, b = self.group(keep), self.group(other)
        pids = [p["pid"] for p in self.parts_of_group(other)]
        snap = {k: b[k] for k in ("id", "title", "category", "cat_how", "intent", "answer", "cite", "status")}
        merged = a["merged"] + [{"group": snap, "pids": pids, "at": now_et(), "by": who}]
        self.x("UPDATE parts SET group_id=? WHERE group_id=?", (keep, other))
        self.x("UPDATE groups SET merged=? WHERE id=?", (json.dumps(merged), keep))
        self.x("DELETE FROM groups WHERE id=?", (other,))
        self.log(who, f"Merged “{b['title'][:50]}” ({len(pids)} emails) into “{a['title'][:50]}”. Can be undone.")

    def undo_merge(self, keep, i, who):
        a = self.group(keep); m = a["merged"].pop(i); g = m["group"]
        self.x("INSERT INTO groups(id,title,category,cat_how,intent,answer,cite,status,created,merged) VALUES(?,?,?,?,?,?,?,?,?,'[]')",
               (g["id"], g["title"], g["category"], g["cat_how"], g["intent"], g["answer"], g["cite"], g["status"], now_et()))
        for pid in m["pids"]:
            self.x("UPDATE parts SET group_id=? WHERE id=? AND group_id=?", (g["id"], pid, keep))
        self.x("UPDATE groups SET merged=? WHERE id=?", (json.dumps(a["merged"]), keep))
        self.log(who, f"Undid merge: “{g['title'][:50]}” split back out with its {len(m['pids'])} emails")

    def save_answer(self, gid, text, cite, who):
        g = self.group(gid)
        self.x("UPDATE groups SET answer=?, cite=?, status=? WHERE id=?", (text, cite, "draft" if text.strip() else "needs-answer", gid))
        self.log(who, f"Saved answer for “{g['title'][:50]}”")

    def approve(self, gid, who):
        g = self.group(gid)
        self.x("UPDATE groups SET status='approved' WHERE id=?", (gid,))
        self.log(who, f"Approved answer for “{g['title'][:50]}”")

    def reopen(self, gid, who):
        self.x("UPDATE groups SET status='draft' WHERE id=?", (gid,)); self.log(who, f"Reopened answer #{gid}")

    def publish(self, who):
        ready = self.q("SELECT id FROM groups WHERE status='approved' ORDER BY category, id")
        if not ready:
            return None
        no = int(self.s("next_addendum"))
        for n, g in enumerate(ready, 1):
            self.x("UPDATE groups SET status='published', addendum=?, qno=? WHERE id=?", (no, n, g["id"]))
        self.set("next_addendum", no + 1)
        self.log(who, f"Published Addendum No. {no} with {len(ready)} answers")
        return no

    def addendum_groups(self, no):
        return self.q("SELECT * FROM groups WHERE addendum=? ORDER BY qno", (no,))

    # ---------- replies ----------
    def email_state(self, e):
        ps = self.parts_of_email(e["id"])
        if e["status"] == "replied":
            return "replied", ps
        if not ps:
            return "no-question", ps
        if any(p["review"] for p in ps):
            return "review", ps
        if all(p["gstatus"] == "published" for p in ps):
            return "ready", ps
        return "waiting", ps

    def compose(self, e, ps):
        lines = [f"Dear {(e['from_name'] or 'vendor').split()[0]},", "",
                 f"Thank you for your question{'s' if len(ps) > 1 else ''} regarding RFP No. {self.s('rfp_no')}, {self.s('rfp_title')}.", ""]
        if e["late"]:
            lines += ["Your email arrived after the inquiry period closed. Your question has already been answered in a published addendum:", ""]
        else:
            lines += [f"{'Each of your questions has' if len(ps) > 1 else 'Your question has'} been answered in a published addendum:", ""]
        for p in ps:
            g = self.group(p["group_id"])
            lines += [f"Your question: {p['text']}", f"Answered in Addendum No. {g['addendum']}, Q#{g['qno']}: {g['answer']}", ""]
        lines += [f"The proposal due date is {self.s('due')}.", "", "Contracts Administration", self.s("org")]
        return f"RE: {e['subject']}", "\n".join(lines)

    def record_reply(self, eid, subject, body, who, mode):
        self.x("INSERT INTO replies(email_id,at,subject,body,by,mode) VALUES(?,?,?,?,?,?)", (eid, now_et(), subject, body, who, mode))
        if mode != "failed":
            self.x("UPDATE emails SET status='replied' WHERE id=?", (eid,))
        self.log(who, f"Reply to {eid}: {mode}")

    # ---------- demo data ----------
    def reset(self):
        with self.lock:
            for t in ("emails", "parts", "groups", "replies", "events"):
                self.db.execute(f"DELETE FROM {t}")
            self.db.execute("DELETE FROM lib WHERE source != 'Past RFP questions'")
            self.db.execute("UPDATE settings SET v='3' WHERE k='next_addendum'")
            self.db.commit()
        self._load_lib()


def load_seed(desk):
    from .data import SEED, FIRMS
    base = datetime(2026, 10, 13)
    for day, hour, fi, subj, qs in SEED:
        firm, name = FIRMS[fi % len(FIRMS)]
        dom = "".join(c for c in firm.lower() if c.isalnum())[:18] + ".example"
        multi = len(qs) > 1
        body = ("Hello Contracts Administration,\n\n" +
                (f"We have {'two' if len(qs) == 2 else 'a few'} questions on RFP No. 19-2026.\n\n" if multi else "We are preparing a response to RFP No. 19-2026 and have a question.\n\n") +
                "\n".join(qs) + f"\n\nThank you,\n{name}\n{firm}")
        at = (base + timedelta(days=day)).replace(hour=hour, minute=(day * 7 + hour * 3) % 60).strftime("%Y-%m-%dT%H:%M")
        desk.ingest(name, f"{name.split()[0].lower()}.{name.split()[1].lower()}@{dom}", f"{subj} – RFP 19-2026", body, at, "seed", firm=firm)
    desk.log("System", f"Loaded {len(SEED)} sample emails")
