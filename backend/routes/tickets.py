from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from ..services.tickets import create_ticket, list_tickets

router = APIRouter(tags=["tickets"])


class TicketRequest(BaseModel):
    type: str  # 'jira' or 'servicenow'
    risk_id: str
    title: str
    description: Optional[str] = None


@router.post("/tickets")
def post_ticket(body: TicketRequest):
    return create_ticket(body.type, body.risk_id, body.title, body.description)


@router.get("/tickets")
def get_tickets():
    return {"tickets": list_tickets()}