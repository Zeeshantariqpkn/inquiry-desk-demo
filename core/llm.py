"""Optional AI check through any OpenAI-compatible API (Groq free tier by default).

Used only to confirm decisions the meaning model is unsure about, and to
explain them in one line. If no key is set or a call fails, the app falls
back to the calibrated rules, so it never stops working.
"""
import json
import re
import requests

CFG = {"base_url": "", "api_key": "", "model": ""}


def configure(base_url="", api_key="", model=""):
    CFG.update(base_url=(base_url or "https://api.groq.com/openai/v1").rstrip("/"),
               api_key=api_key or "", model=model or "llama-3.1-8b-instant")


def enabled():
    return bool(CFG.get("api_key"))


def _chat(system, user, max_tokens=400):
    r = requests.post(f"{CFG['base_url']}/chat/completions", timeout=20,
                      headers={"Authorization": f"Bearer {CFG['api_key']}"},
                      json={"model": CFG["model"], "temperature": 0, "max_tokens": max_tokens,
                            "response_format": {"type": "json_object"},
                            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})
    r.raise_for_status()
    txt = r.json()["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    return json.loads(m.group(0) if m else txt)


def match(question, candidates, categories):
    """candidates: list of (key, text). Returns dict or None on failure."""
    if not enabled():
        return None
    lines = "\n".join(f"{i+1}. {t}" for i, (_, t) in enumerate(candidates)) or "(none)"
    system = ("You sort vendor questions sent to a government procurement office about one RFP. "
              "Two questions are the SAME only if one answer would fully answer both. "
              "Questions that share a word but ask different things are NOT the same. Reply in JSON.")
    user = (f"New question:\n\"{question}\"\n\nExisting questions:\n{lines}\n\n"
            f"Categories: {', '.join(categories)}\n\n"
            'Return JSON: {"same_as": <number of the existing question it is the same as, or 0 if none>, '
            '"category": "<one category from the list>", "confidence": <0 to 1>, '
            '"reason": "<one short sentence quoting the words that decided it>"}')
    try:
        out = _chat(system, user)
        n = int(out.get("same_as") or 0)
        cat = out.get("category") if out.get("category") in categories else None
        return {"key": candidates[n - 1][0] if 0 < n <= len(candidates) else None,
                "category": cat, "confidence": float(out.get("confidence") or 0),
                "reason": str(out.get("reason") or "")[:240]}
    except Exception:
        return None


def split(body):
    """Ask the model to list each question. Returns None on failure."""
    if not enabled():
        return None
    system = ("Extract every separate question or request for information from a vendor email. "
              "Copy each one exactly as written, word for word. Ignore greetings, signatures and quoted replies. Reply in JSON.")
    try:
        out = _chat(system, f"Email:\n\"\"\"\n{body[:4000]}\n\"\"\"\n\nReturn JSON: {{\"questions\": [\"...\"]}}", 700)
        qs = [str(q).strip() for q in out.get("questions", []) if str(q).strip()]
        low = body.lower()
        # Keep only questions that really appear in the email (no invented text).
        keep = [q for q in qs if sum(w in low for w in q.lower().split()) >= 0.8 * max(1, len(q.split()))]
        return keep or None
    except Exception:
        return None
