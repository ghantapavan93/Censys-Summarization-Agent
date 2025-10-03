from fastapi import APIRouter
from ..services.rollups import get_trends

router = APIRouter(tags=["trends"])


@router.get("/trends")
def trends():
    return get_trends()
