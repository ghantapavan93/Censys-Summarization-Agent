from __future__ import annotations
from typing import List, Dict, Any, Tuple
import re
import numpy as np
from backend.models import Record

# --- tiny, unicode-friendly tokenizer ---
TOKEN_RX = re.compile(r"[A-Za-z0-9._-]+", re.UNICODE)
STOP = {
    "the","a","an","and","or","to","of","for","on","in","by","with","at","is","are","be","this","that","it"
}


def tokenize(text: str) -> List[str]:
    toks = [t.lower() for t in TOKEN_RX.findall(text or "")]
    return [t for t in toks if t not in STOP and len(t) > 1]


def _record_text(r: Record) -> str:
    parts = [r.ip, str(r.port or ""), r.product or "", r.version or "", r.hardware or "", r.country or ""]
    if r.cve:
        parts.extend([c.get("id", "") for c in r.cve if c.get("id")])
    if r.other:
        parts.extend([f"{k}:{v}" for k, v in r.other.items() if isinstance(v, (str, int, float))])
    return " ".join([p for p in parts if p])


def build_corpus(records: List[Record]) -> Dict[str, Any]:
    # tokenize docs
    docs_tokens: List[List[str]] = [tokenize(_record_text(r)) for r in records]

    # vocab (deterministic order)
    vocab: Dict[str, int] = {}
    for toks in docs_tokens:
        for t in toks:
            if t not in vocab:
                vocab[t] = len(vocab)

    V = len(vocab)
    N = len(records)
    if N == 0 or V == 0:
        return {"records": records, "X": np.zeros((0, 0), dtype=np.float32), "vocab": vocab, "idf": np.zeros((0,), dtype=np.float32)}

    # term frequencies per doc and document frequency per term
    df = np.zeros(V, dtype=np.int32)
    rows = []
    for toks in docs_tokens:
        tf: Dict[int, int] = {}
        for t in toks:
            j = vocab[t]
            tf[j] = tf.get(j, 0) + 1
        rows.append(tf)
        for j in tf.keys():
            df[j] += 1

    # smooth idf
    idf = np.log((N + 1) / (df + 1)) + 1.0  # shape (V,)

    # build dense TF-IDF matrix (N x V) — OK for small/medium corpora
    X = np.zeros((N, V), dtype=np.float32)
    for i, tf in enumerate(rows):
        for j, f in tf.items():
            X[i, j] = float(f) * idf[j]
        norm = np.linalg.norm(X[i])
        if norm > 0:
            X[i] /= norm

    return {"records": records, "X": X, "vocab": vocab, "idf": idf}


def _filter_mask(records: List[Record], filters: Dict[str, str]) -> np.ndarray:
    if not filters:
        return np.ones(len(records), dtype=bool)
    prod = (filters.get("product") or "").lower() or None
    ver = filters.get("version") or None
    hw = (filters.get("hardware") or "").lower() or None
    ctry = (filters.get("country") or "").upper() or None
    mask = np.ones(len(records), dtype=bool)
    for i, r in enumerate(records):
        if prod and (r.product or "").lower() != prod:
            mask[i] = False
            continue
        if ver and (r.version or "") != ver:
            mask[i] = False
            continue
        if hw and (r.hardware or "").lower() != hw:
            mask[i] = False
            continue
        if ctry and (r.country or "").upper() != ctry:
            mask[i] = False
            continue
    return mask


def _query_vector(query_text: str, vocab: Dict[str, int], idf: np.ndarray) -> np.ndarray:
    if not query_text or not query_text.strip() or len(vocab) == 0:
        # neutral query → near-uniform small weights
        if len(vocab) == 0:
            return np.zeros((0,), dtype=np.float32)
        q = np.ones(len(vocab), dtype=np.float32)
        q /= np.linalg.norm(q)
        return q
    q_tf: Dict[int, int] = {}
    for t in tokenize(query_text):
        j = vocab.get(t)
        if j is not None:
            q_tf[j] = q_tf.get(j, 0) + 1
    if not q_tf:
        q = np.ones(len(vocab), dtype=np.float32)
        q /= np.linalg.norm(q)
        return q
    q = np.zeros(len(vocab), dtype=np.float32)
    for j, f in q_tf.items():
        q[j] = float(f) * idf[j]
    norm = np.linalg.norm(q)
    if norm > 0:
        q /= norm
    return q


def _topk(sim: np.ndarray, k: int) -> List[int]:
    k = min(k, sim.size)
    if k <= 0:
        return []
    idx = np.argpartition(-sim, k - 1)[:k]
    idx = idx[np.argsort(-sim[idx])]
    return idx.tolist()


# ----- Compatibility wrappers with existing pipeline -----
def ensure_index(records: List[Record], prev: Dict[str, Any] | None) -> Dict[str, Any]:
    # We don't attempt to incrementally update; always rebuild for determinism
    return build_corpus(records)


def retrieve(corpus: Dict[str, Any], query_text: str, k: int = 20) -> List[Tuple[Record, float]]:
    recs: List[Record] = corpus["records"]
    X: np.ndarray = corpus["X"]
    vocab: Dict[str, int] = corpus["vocab"]
    idf: np.ndarray = corpus["idf"]

    if X.size == 0 or len(recs) == 0:
        return []

    mask = np.ones(len(recs), dtype=bool)
    qv = _query_vector(query_text, vocab, idf)
    if qv.size == 0:
        return []
    sims = X.dot(qv)
    sims[~mask] = -1.0
    top = _topk(sims, k)
    return [(recs[i], float(sims[i])) for i in top if sims[i] > 0]


# Optional extended API (not used by current pipeline)
def retrieve_with_filters(corpus: Dict[str, Any], filters: Dict[str, str], query_text: str, k: int = 20) -> Dict[str, Any]:
    recs: List[Record] = corpus["records"]
    X: np.ndarray = corpus["X"]
    vocab: Dict[str, int] = corpus["vocab"]
    idf: np.ndarray = corpus["idf"]
    if X.size == 0 or len(recs) == 0:
        return {"records": [], "scores": []}
    mask = _filter_mask(recs, filters)
    if not np.any(mask):
        return {"records": [], "scores": []}
    qv = _query_vector(query_text, vocab, idf)
    if qv.size == 0:
        return {"records": [], "scores": []}
    sims = X.dot(qv)
    sims[~mask] = -1.0
    top = _topk(sims, k)
    return {"records": [recs[i] for i in top if sims[i] > 0], "scores": [float(sims[i]) for i in top]}
