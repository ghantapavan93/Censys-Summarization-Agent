from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from ..services.mutes import list_mutes, add_mute

router = APIRouter(tags=["mute"])


@router.get("/mutes")
def get_mutes():
    return {"mutes": list_mutes()}


class MuteBody(BaseModel):
    id: str
    days: int
    reason: str


@router.post("/mutes")
def post_mute(body: MuteBody):
    return add_mute(body.id, body.days, body.reason)
