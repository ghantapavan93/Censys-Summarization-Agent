from fastapi import APIRouter, Body, HTTPException
from typing import Any, Dict, Optional
from ..settings import settings
from ..services.input_normalizer import normalize_input
from ..services.ingest import canonicalize_records
from ..agent.graph import run_pipeline


router = APIRouter(tags=["compat"])


@router.get("/health")
def health_root():
    return {"version": settings.version}


@router.get("/healthz")
def healthz():
    return {"ok": True}


@router.get("/config")
def get_config():
    return {
        "model_backend": settings.model_backend,
        "model_name": settings.model_name,
        "retrieval_k": settings.retrieval_k,
        "language": settings.language,
        "enable_validation": settings.enable_validation,
    }


def _pipeline_from_payload(payload: Dict[str, Any], topk: Optional[int] = None):
    try:
        norm = normalize_input(payload)
        recs = canonicalize_records(norm.get("raw_records") or [], field_map=None)
        return run_pipeline(
            records=recs,
            nl=norm.get("nl") or "",
            event_id=norm.get("event_id") or "evt-api",
            now_utc=None,
            request_topk=topk,
            use_llm=False,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"pipeline_error: {e}")


@router.post("/summarize")
def summarize_root(body: Dict[str, Any] = Body(...)):
    topk = None
    if isinstance(body, dict):
        t = body.get("topk")
        if isinstance(t, int) and t > 0:
            topk = t
    return _pipeline_from_payload(body, topk)


@router.post("/query-assistant")
def query_assistant(body: Dict[str, Any] = Body(...)):
    topk = None
    if isinstance(body, dict):
        t = body.get("topk")
        if isinstance(t, int) and t > 0:
            topk = t
    return _pipeline_from_payload(body, topk)
