from fastapi import APIRouter, HTTPException, Request
import os
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from ..services.summarizer_llm import summarize
from ..core.logging import log_json

router = APIRouter(tags=["summarize"])


class SummarizeRequest(BaseModel):
    records: List[Dict[str, Any]]
    rewrite_with_ai: bool = False
    llm_preference: Optional[str] = None  # e.g., "qwen2.5:7b"
    style: Optional[str] = None  # executive | bulleted | ticket
    language: Optional[str] = None  # e.g., "en"


@router.post("/summarize")
def do_summarize(req: SummarizeRequest, request: Request):
    try:
        # Enforce policy if requested via header; default from env if provided
        default_policy = os.environ.get("DEFAULT_VALIDATION_POLICY", "lenient").lower()
        policy = str(request.headers.get("X-Validation-Policy", default_policy)).lower()
        effective_policy = policy if policy in ("off", "lenient", "strict") else default_policy
        errors: List[str] = []
        warnings: List[str] = []
        # Minimal server-side validations to prevent obviously bad shapes
        if not isinstance(req.records, list):
            errors.append("records must be a list")
        else:
            for i, r in enumerate(req.records):
                if not isinstance(r, dict):
                    errors.append(f"record {i} must be an object")
                    continue
                services = r.get("services") or []
                if services and isinstance(services, list):
                    for si, s in enumerate(services):
                        p = (s or {}).get("port")
                        if p is None:
                            errors.append(f"records[{i}].services[{si}].port missing")
                        elif isinstance(p, int) and (p < 1 or p > 65535):
                            errors.append(f"records[{i}].services[{si}].port {p} out of range 1..65535")
                # Warn on unknown keys (lightweight)
                for k in r.keys():
                    if k not in ("ip","location","autonomous_system","labels","services","other","kev_present"):
                        warnings.append(f"unknown key at record {i}: {k}")

        blocked = effective_policy == "strict" and bool(errors)
        if blocked:
            detail = {
                "policy": "strict",
                "errors": [{"path": "records", "message": e} for e in errors],
                "warnings": [{"path": "records", "message": w} for w in warnings],
                "request_id": getattr(getattr(request, "state", None), "request_id", None),
                "effective_policy": effective_policy,
            }
            log_json("summarize.validation_failed", policy=effective_policy, errors_count=len(errors), warnings_count=len(warnings), blocked=True, request_id=detail["request_id"])
            raise HTTPException(status_code=422, detail=detail)

        log_json("summarize.validation", policy=effective_policy, error_count=len(errors), warning_count=len(warnings), blocked=False, request_id=getattr(getattr(request, "state", None), "request_id", None))
        result = summarize(req.records, req.rewrite_with_ai, req.llm_preference, style=req.style, language=req.language)
        # include effective policy for visibility
        if isinstance(result, dict):
            meta = result.get("meta") or {}
            meta["effective_policy"] = effective_policy
            result["meta"] = meta
            # emit telemetry for AI rewrite if available
            try:
                ai_meta = (result.get("ai_overview") or {})
                log_json(
                    "summarize.ai_overview",
                    model=ai_meta.get("model"),
                    latency_ms=ai_meta.get("latency_ms"),
                    guard_pass=ai_meta.get("guard_pass"),
                    guard_reason=ai_meta.get("guard_reason"),
                    used_ai=ai_meta.get("used_ai"),
                    request_id=getattr(getattr(request, "state", None), "request_id", None),
                )
            except Exception:
                pass
        return result
    except (FileNotFoundError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
