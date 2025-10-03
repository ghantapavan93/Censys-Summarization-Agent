from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..services.views import list_views, save_view, list_alerts, save_alert

router = APIRouter(tags=["views"])


class SaveViewBody(BaseModel):
    name: str
    dsl: str


@router.get("/views")
def get_views():
    return {"views": list_views()}


@router.post("/views")
def post_view(body: SaveViewBody):
    return save_view(body.name, body.dsl)


class SaveAlertBody(BaseModel):
    name: str
    dsl: str
    webhook: Optional[str] = None
    email: Optional[str] = None


@router.get("/alerts")
def get_alerts():
    return {"alerts": list_alerts()}


@router.post("/alerts")
def post_alert(body: SaveAlertBody):
    return save_alert(body.name, body.dsl, body.webhook, body.email)
