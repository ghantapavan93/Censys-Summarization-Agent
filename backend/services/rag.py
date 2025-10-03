import os, json, hashlib
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

# Try FAISS; fall back gracefully
try:
    import faiss  # type: ignore
except Exception:
    faiss = None

# Lazy import sentence-transformers
def _try_get_st():
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        return SentenceTransformer
    except Exception:
        return None

RAG_DIR = Path(".rag"); RAG_DIR.mkdir(exist_ok=True)
INDEX_PATH = RAG_DIR / "faiss.index"
META_PATH = RAG_DIR / "meta.json"
MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEFAULT_DIM = 384

_model = None
_index = None
_meta: List[Dict] = []

def _get_model():
    global _model
    if _model is None:
        ST = _try_get_st()
        if ST is None:
            return None
        try:
            _model = ST(MODEL_NAME)
        except Exception:
            _model = None
    return _model

def _normalize(v: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12
    return v / norms

def _emb(texts: List[str]) -> np.ndarray:
    m = _get_model()
    if m is None:
        # operate in "no-embed" mode
        return np.zeros((len(texts), DEFAULT_DIM), dtype="float32")
    vecs = m.encode(texts, batch_size=64, convert_to_numpy=True, normalize_embeddings=True)
    return _normalize(vecs.astype("float32"))

def build_index(records: List[Dict]) -> None:
    global _index, _meta
    texts, meta = [], []
    for i, r in enumerate(records):
        t = (r.get("text") or "").strip()
        if not t: continue
        texts.append(t)
        meta.append({"i": i, "id": r.get("id", str(i)), "text": t})

    _meta = meta
    if not texts or faiss is None:
        _index = None  # no FAISS available
        return

    try:
        vecs = _emb(texts)
        d = vecs.shape[1]
        _index = faiss.IndexFlatIP(d)
        if len(texts): _index.add(vecs)
        faiss.write_index(_index, str(INDEX_PATH))
        with open(META_PATH, "w", encoding="utf-8") as f:
            json.dump(_meta, f, ensure_ascii=False)
    except Exception:
        _index = None  # fail safe

def load_index_if_exists() -> bool:
    global _index, _meta
    if faiss is None or not INDEX_PATH.exists() or not META_PATH.exists():
        return False
    try:
        _index = faiss.read_index(str(INDEX_PATH))
        with open(META_PATH, "r", encoding="utf-8") as f:
            _meta = json.load(f)
        return True
    except Exception:
        _index = None; _meta = []; return False

def ensure_index(records: List[Dict]) -> None:
    payload = [{"id": r.get("id"), "text": r.get("text", "")} for r in records]
    key = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    stamp_path = RAG_DIR / "content.sha256"
    if faiss is None:
        # no-op index; just keep meta for potential snippets
        _meta[:] = [{"i": i, "id": p["id"], "text": p["text"]} for i, p in enumerate(payload) if p["text"]]
        return
    if INDEX_PATH.exists() and META_PATH.exists() and stamp_path.exists():
        if stamp_path.read_text() == key and load_index_if_exists(): return
    build_index(records)
    stamp_path.write_text(key)

def retrieve(query: str, k: int = 8) -> List[Dict]:
    if _index is None or not _meta:
        return []
    qv = _emb([query])
    scores, idxs = _index.search(qv, min(k, len(_meta)))
    out = []
    for rank, (j, s) in enumerate(zip(idxs[0], scores[0])):
        if j < 0 or j >= len(_meta): continue
        m = dict(_meta[j]); m["score"] = float(s)
        t = m.get("text", "")
        m["snippet"] = (t[:220] + "…") if len(t) > 220 else t
        m.pop("text", None); m["rank"] = rank + 1
        out.append(m)
    return out

def auto_query_from_records(records: List[Dict]) -> str:
    seeds = []
    for r in records[:50]:
        t = (r.get("text") or "").lower()
        for kw in ["ssh","brute","failed","rce","cve","outdated","vuln","port","asn","exploit","suspicious","malware"]:
            if kw in t:
                seeds.append(kw)
    if not seeds:
        return "security incidents and anomalies in the dataset"
    uniq = list(dict.fromkeys(seeds))[:12]
    return " ".join(uniq)
