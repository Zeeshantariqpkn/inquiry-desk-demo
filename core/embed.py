"""Meaning vectors for questions.

Primary engine: BAAI/bge-small-en-v1.5 through fastembed (ONNX, no GPU, ~130 MB),
which places questions with the same meaning close together even when they
share no words. If the model cannot be downloaded, a lighter fallback engine
is used so the app still runs; the Accuracy page says which engine is active,
and thresholds are calibrated separately for whichever one runs.
"""
import re
import numpy as np

_ENGINE = None


class _BGE:
    name = "Meaning model (bge-small-en-v1.5)"
    kind = "semantic"

    def __init__(self):
        from fastembed import TextEmbedding
        self.m = TextEmbedding("BAAI/bge-small-en-v1.5")

    def encode(self, texts):
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        v = np.array(list(self.m.embed(list(texts))), dtype=np.float32)
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


# Fallback: hashed word and character n-grams, plus a small procurement
# thesaurus so common paraphrases meet. Weaker than the meaning model.
_SYN = [
    (r"\b(not[- ]to[- ]exceed|set aside|allocated|funding|ceiling|cap on|willing to spend|contract value|dollar amount|budget(ed)?)\b", " budgetterm "),
    (r"\b(offshore|overseas|outside the (united states|us|u\.s\.)|another country|india|pakistan|abroad|located overseas)\b", " offshoreterm "),
    (r"\b(cms|content management|sitefinity|wordpress|drupal|platform)\b", " cmsterm "),
    (r"\b(host(ing|ed)?|servers?|cloud)\b", " hostterm "),
    (r"\b(due date|deadline|due|submit by|extension|extended|more time)\b", " dueterm "),
    (r"\b(wcag|section 508|accessib\w*|ada)\b", " a11yterm "),
    (r"\b(hard copy|paper|printed|mail|pdf by email|delivered)\b", " submitterm "),
]


class _Fallback:
    name = "Fallback engine (word and character patterns)"
    kind = "fallback"

    def __init__(self):
        from sklearn.feature_extraction.text import HashingVectorizer
        self.w = HashingVectorizer(n_features=2**14, ngram_range=(1, 2), stop_words="english", alternate_sign=False, norm="l2")
        self.c = HashingVectorizer(n_features=2**14, analyzer="char_wb", ngram_range=(3, 5), alternate_sign=False, norm="l2")

    def _norm(self, t):
        t = t.lower()
        for p, r in _SYN:
            t = re.sub(p, r, t)
        return t

    def encode(self, texts):
        texts = [self._norm(t) for t in texts]
        a = self.w.transform(texts).toarray() * 0.75
        b = self.c.transform(texts).toarray() * 0.45
        v = np.hstack([a, b]).astype(np.float32)
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


class _WordLlama:
    """Small meaning model whose weights ship inside the pip package (no download)."""
    name = "Backup meaning model (WordLlama, bundled)"
    kind = "semantic-lite"

    def __init__(self):
        import pathlib, wordllama
        from wordllama import WordLlama
        self.m = WordLlama.load(cache_dir=pathlib.Path(wordllama.__file__).parent, disable_download=True)

    def encode(self, texts):
        if not texts:
            return np.zeros((0, 256), dtype=np.float32)
        v = np.asarray(self.m.embed(list(texts), norm=True), dtype=np.float32)
        return v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)


def engine():
    global _ENGINE
    if _ENGINE is None:
        for cls in (_BGE, _WordLlama, _Fallback):
            try:
                e = cls(); e.encode(["warm up"]); _ENGINE = e; break
            except Exception:
                continue
    return _ENGINE


def encode(texts):
    return engine().encode(list(texts))
