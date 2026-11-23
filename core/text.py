"""Turn a raw email into its separate questions."""
import re

_SIGNOFF = re.compile(r"^\s*(thank(s| you)|best( regards)?|regards|sincerely|cheers|kind regards|respectfully)\b", re.I)
_GREETING = re.compile(r"^\s*(hello|hi|dear|good (morning|afternoon)|greetings)\b[^\n]*$", re.I)
_QUOTED = re.compile(r"^\s*(>|on .+ wrote:|-----original message-----|from: )", re.I)
_ASK = re.compile(r"^\s*(is|are|was|will|would|can|could|may|might|should|shall|do|does|did|has|have|what|when|where|which|who|whom|why|how)\b", re.I)
_REQUEST = re.compile(r"\b(please (confirm|clarify|advise|provide|share|let us know)|we would like to (know|confirm)|kindly (confirm|clarify))\b", re.I)
_LISTMARK = re.compile(r"^\s*(\(?\d{1,2}[.)]|[a-h][.)]|[-•*])\s+")
_JOINERS = re.compile(r"^(also|and|additionally|secondly|finally|lastly|in addition|further(more)?)[,:]?\s+", re.I)


def body_lines(body: str) -> list[str]:
    """Keep the message itself: drop quoted replies, greeting and signature."""
    out = []
    for line in body.replace("\r", "").split("\n"):
        if _QUOTED.match(line):
            break
        if _SIGNOFF.match(line):
            break
        out.append(line)
    while out and (not out[0].strip() or _GREETING.match(out[0])):
        out.pop(0)
    return out


def _sentences(block: str) -> list[str]:
    block = re.sub(r"\s+", " ", block).strip()
    if not block:
        return []
    parts = re.split(r"(?<=[?.!])\s+(?=[A-Z0-9(])", block)
    return [p.strip() for p in parts if p.strip()]


def _is_question(s: str) -> bool:
    core = _JOINERS.sub("", _LISTMARK.sub("", s)).strip()
    return s.rstrip().endswith("?") or bool(_REQUEST.search(s)) or (bool(_ASK.match(core)) and len(core.split()) >= 4)


def split_questions(body: str) -> list[str]:
    """Return each separate question, exactly as the vendor wrote it.

    Handles numbered or bulleted lists, several questions in one paragraph,
    and "Also, ..." follow-ups. If nothing looks like a question, the whole
    message is returned as one item so nothing is ever dropped.
    """
    lines = body_lines(body)
    blocks, cur = [], []
    for line in lines:
        if not line.strip():
            if cur:
                blocks.append(" ".join(cur)); cur = []
        elif _LISTMARK.match(line) and cur:
            blocks.append(" ".join(cur)); cur = [line.strip()]
        else:
            cur.append(line.strip())
    if cur:
        blocks.append(" ".join(cur))

    qs = []
    for b in blocks:
        for s in _sentences(b):
            if _is_question(s):
                qs.append(s)
    seen, out = set(), []
    for q in qs:
        k = q.lower()
        if k not in seen:
            seen.add(k); out.append(q)
    if not out:
        text = " ".join(" ".join(lines).split())
        return [text] if text else []
    return out


def clean_for_match(q: str) -> str:
    """Strip list numbers and joining words before comparing meaning."""
    q = _LISTMARK.sub("", q)
    q = _JOINERS.sub("", q)
    return q.strip()
