from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from ..services.ai_check import ai_rewrite_check


router = APIRouter(tags=["ai"])


class AICheckRequest(BaseModel):
    records: List[Dict[str, Any]]
    model: Optional[str] = None
    min_similarity: float = 0.25
    min_number_matches: int = 2
    # bounds on len(LLM)/len(Deterministic)
    length_ratio_low: float = 0.4
    length_ratio_high: float = 2.5


@router.post("/ai/check")
def ai_check(req: AICheckRequest):
    result = ai_rewrite_check(
        req.records,
        model=req.model,
        min_similarity=req.min_similarity,
        min_number_matches=req.min_number_matches,
        length_ratio_bounds=(req.length_ratio_low, req.length_ratio_high),
    )
    return result
