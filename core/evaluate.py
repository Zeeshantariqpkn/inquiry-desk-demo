"""Decision rules, calibration and honest accuracy measurement.

How a new question is placed:
 1. Library match: compare it with the library of known questions (many
    wordings per question, from past RFPs plus every staff correction).
    A confident match puts it in that question's group.
 2. Inbox match: otherwise compare it with questions already received.
 3. Anything in between goes to Needs review with a suggested group.
 4. Nothing close: a new question, also flagged for staff.

Thresholds are calibrated on one half of the labeled questions and the
accuracy is reported on the other half, which calibration never saw.
"""
import random
import numpy as np
from .data import LABELED
from .embed import encode, engine
from .text import clean_for_match


def _items():
    out = []
    for intent, (cat, ws) in LABELED.items():
        for i, w in enumerate(ws):
            out.append({"intent": intent, "cat": cat, "text": w, "half": "cal" if i % 2 == 0 else "test"})
    return out


def nearest(vec, mat, skip=None):
    if mat is None or len(mat) == 0:
        return -1, -1.0
    s = mat @ vec
    if skip is not None:
        s = s.copy(); s[skip] = -1
    j = int(np.argmax(s)); return j, float(s[j])


def lib_score(vec, lib_embs, lib_intents, skip=None):
    """Best intent by its two closest wordings (more stable than one)."""
    s = lib_embs @ vec
    if skip is not None:
        s = s.copy(); s[skip] = -1
    per = {}
    for v, it in zip(s, lib_intents):
        per.setdefault(it, []).append(float(v))
    scored = {it: (sorted(v)[-1] * 0.7 + (sorted(v)[-2] if len(v) > 1 else sorted(v)[-1]) * 0.3) for it, v in per.items()}
    best = max(scored, key=scored.get)
    second = max([v for k, v in scored.items() if k != best], default=0.0)
    return best, scored[best], scored[best] - second, int(np.argmax(s))


def decide(vec, th, lib_embs, lib_intents, inbox_embs, inbox_groups, intent_group):
    """Return (group_key or None, score, how, review_reason)."""
    # Exact repeats (same words) are always the same question.
    if inbox_embs is not None and len(inbox_embs):
        j0, s0 = nearest(vec, inbox_embs)
        if s0 >= 0.995:
            return ("group", inbox_groups[j0]), s0, "exact", ""
    if lib_embs is not None and len(lib_embs):
        j1, s1 = nearest(vec, lib_embs)
        if s1 >= 0.995:
            return ("intent", lib_intents[j1]), s1, "known", ""
    if lib_embs is not None and len(lib_embs):
        it, s, margin, _ = lib_score(vec, lib_embs, lib_intents)
        if s >= th["t_lib"] and margin >= th["m_lib"]:
            return ("intent", it), s, "library", ""
    else:
        it, s, margin = None, -1.0, 0.0
    j, sp = nearest(vec, inbox_embs)
    if sp >= th["t_merge"]:
        return ("group", inbox_groups[j]), sp, "inbox", ""
    best_s = max(s, sp)
    if best_s >= th["t_low"]:
        if s >= sp and it is not None:
            return ("intent", it), s, "suggested", "Probably the same question as a known one. Please confirm."
        return ("group", inbox_groups[j]), sp, "suggested", "Probably the same question as one already received. Please confirm."
    return None, best_s, "new", "New question, not like anything seen before."


def simulate(items, embs, lib_embs, lib_intents, th, seed=7):
    order = list(range(len(items))); random.Random(seed).shuffle(order)
    inbox_embs, inbox_groups, group_intent, intent_group = [], [], [], {}
    r = {"auto_ok": 0, "auto_wrong": 0, "review_ok": 0, "review_wrong": 0, "new_ok": 0, "new_missed": 0}
    for k in order:
        truth = items[k]["intent"]
        key, s, how, _ = decide(embs[k], th, lib_embs, lib_intents,
                                np.array(inbox_embs) if inbox_embs else None, inbox_groups, intent_group)
        if key is None:
            g = len(group_intent); group_intent.append(truth)
            r["new_missed" if truth in group_intent[:-1] else "new_ok"] += 1
        else:
            if key[0] == "intent":
                pred = key[1]
                g = intent_group.get(pred)
                if g is None:
                    g = len(group_intent); group_intent.append(pred); intent_group[pred] = g
            else:
                g = key[1]; pred = group_intent[g]
            ok = pred == truth
            if how == "suggested":
                r["review_ok" if ok else "review_wrong"] += 1
            else:
                r["auto_ok" if ok else "auto_wrong"] += 1
        inbox_embs.append(embs[k]); inbox_groups.append(g)
    return r


def calibrate():
    items = _items()
    embs = encode([clean_for_match(x["text"]) for x in items])
    cal = [i for i, x in enumerate(items) if x["half"] == "cal"]
    test = [i for i, x in enumerate(items) if x["half"] == "test"]
    cal_embs = embs[cal]; cal_int = [items[i]["intent"] for i in cal]
    grid = np.round(np.arange(0.05, 0.99, 0.01), 2)

    # 1) Library threshold, leave-one-out on the calibration library:
    #    the loosest threshold that keeps library matches at least 97% right.
    loo = []
    for n, i in enumerate(cal):
        it, s, m, _ = lib_score(embs[i], cal_embs, cal_int, skip=n)
        loo.append((s, m, it == items[i]["intent"]))
    t_lib, m_lib, best_cov = 0.99, 0.0, 0
    for m_req in (0.0, 0.02, 0.04, 0.06, 0.08, 0.10):
        cand = None
        for t in grid[::-1]:
            sel = [ok for s, m, ok in loo if s >= t and m >= m_req]
            if sel and sum(sel) / len(sel) < 0.97:
                break
            cand = float(t)
        if cand is None:
            continue
        cov = sum(1 for s, m, ok in loo if s >= cand and m >= m_req)
        if cov > best_cov:
            t_lib, m_lib, best_cov = cand, m_req, cov

    # 2) Inbox threshold: pairwise nearest-question precision >= 97%.
    nn = []
    for n, i in enumerate(cal):
        j, s = nearest(embs[i], cal_embs, skip=n)
        nn.append((s, cal_int[j] == items[i]["intent"]))
    t_merge = 0.98
    for t in grid[::-1]:
        sel = [ok for s, ok in nn if s >= t]
        if sel and sum(sel) / len(sel) < 0.97:
            break
        t_merge = float(t)

    # 3) Review band: suggestions must be right at least 60% of the time.
    band_src = [(s, ok) for s, m, ok in loo] + nn
    t_low = min(t_lib, t_merge)
    for t in grid[::-1]:
        if t >= min(t_lib, t_merge):
            continue
        band = [ok for s, ok in band_src if t <= s < min(t_lib, t_merge)]
        if band and sum(band) / len(band) < 0.6:
            break
        t_low = float(t)
    th = {"t_lib": t_lib, "m_lib": m_lib, "t_merge": t_merge, "t_low": t_low}

    # Held-out test: the test half arrives as an inbox; the library is the calibration half.
    test_items = [items[i] for i in test]; test_embs = embs[test]
    runs = [simulate(test_items, test_embs, cal_embs, cal_int, th, seed=s) for s in range(5)]
    g = {k: sum(r[k] for r in runs) / len(runs) for k in runs[0]}
    auto = g["auto_ok"] + g["auto_wrong"]; rev = g["review_ok"] + g["review_wrong"]
    cat_of = {k: v[0] for k, v in LABELED.items()}
    cat_ok = cat_auto = 0
    for i in test:
        it, s, m, _ = lib_score(embs[i], cal_embs, cal_int)
        if s >= t_low:
            cat_auto += 1; cat_ok += int(cat_of[it] == items[i]["cat"])
    report = {
        "engine": engine().name, "engine_kind": engine().kind,
        "n_cal": len(cal), "n_test": len(test), "n_intents": len(LABELED), **th,
        "auto": auto, "auto_precision": g["auto_ok"] / auto if auto else 1.0, "auto_wrong": g["auto_wrong"],
        "review": rev, "review_precision": g["review_ok"] / rev if rev else 1.0,
        "new_ok": g["new_ok"], "new_missed": g["new_missed"],
        "cat_auto": cat_auto, "cat_precision": cat_ok / cat_auto if cat_auto else 1.0,
    }
    return th, report
