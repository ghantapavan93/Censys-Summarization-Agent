from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, ConfigDict
from .agent.graph import run_pipeline
from .services.ingest import canonicalize_records
from .services.input_normalizer import normalize_input


class LegacyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    count: int
    insights: dict
    summaries: list[str]


router = APIRouter()


@router.post("/summarize/legacy", response_model=LegacyResponse)
def summarize_legacy(body: dict = Body(...)) -> LegacyResponse:
    try:
        norm = normalize_input(body)
        recs = canonicalize_records(norm.get("raw_records") or [], field_map=None)
        if not recs:
            data = run_pipeline(records=[], nl=norm.get("nl") or "", event_id=norm.get("event_id") or "evt-legacy", now_utc=None, request_topk=None, use_llm=False)
        else:
            data = run_pipeline(records=recs, nl=norm.get("nl") or "", event_id=norm.get("event_id") or "evt-legacy", now_utc=None, request_topk=None, use_llm=False)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"pipeline_error: {e}")

    return LegacyResponse(
        count=int(data.meta.get("record_count", 0)),
        insights=(data.viz_payload.histograms or {}),
        summaries=[data.summary or (data.overview_deterministic or "")],
    )
