from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
from ..core.logging import log_json

router = APIRouter(tags=["telemetry"])


class ClientTelemetry(BaseModel):
    policy: str
    errors_count: int
    warnings_count: int
    fixed_fields: Dict[str, int] | None = None
    blocked: bool
    request_id: Optional[str] = None


@router.post("/telemetry")
def post_telemetry(body: ClientTelemetry, request: Request):
    rid = body.request_id or getattr(getattr(request, "state", None), "request_id", None)
    log_json(
        "frontend.validation.telemetry",
        policy=body.policy,
        errors_count=body.errors_count,
        warnings_count=body.warnings_count,
        fixed_fields=body.fixed_fields or {},
        blocked=body.blocked,
        request_id=rid,
    )
    return {"ok": True}
