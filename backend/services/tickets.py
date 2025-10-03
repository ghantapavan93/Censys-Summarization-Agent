from __future__ import annotations

import json, os, time, uuid
from typing import Dict, Any, List, Optional

DATA_DIR = os.environ.get("DATA_DIR", "data")
TICKETS_PATH = os.path.join(DATA_DIR, "tickets.json")


def _load() -> List[Dict[str, Any]]:
    try:
        with open(TICKETS_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, list) else []
    except Exception:
        return []


def _save(rows: List[Dict[str, Any]]):
    os.makedirs(os.path.dirname(TICKETS_PATH), exist_ok=True)
    with open(TICKETS_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f)


def list_tickets() -> List[Dict[str, Any]]:
    return _load()


def create_ticket(ticket_type: str, risk_id: str, title: str, description: Optional[str] = None) -> Dict[str, Any]:
    """Create a ticket and return the ticket ID and URL for external integration"""
    ticket_id = str(uuid.uuid4())
    created_at = int(time.time())
    
    # Generate realistic demo ticket IDs and provide clear messaging about demo mode
    if ticket_type.lower() == 'jira':
        external_id = f"RISK-{ticket_id[:8].upper()}"
        # Professional demo message explaining what would happen in production
        demo_message = f"✅ Demo: JIRA ticket {external_id} created! In production, this would integrate with your organization's JIRA instance."
        external_url = None  # Don't provide a broken URL
    elif ticket_type.lower() == 'servicenow':
        external_id = f"INC{str(created_at)[-6:]}"
        demo_message = f"✅ Demo: ServiceNow incident {external_id} created! In production, this would integrate with your organization's ServiceNow instance."
        external_url = None  # Don't provide a broken URL
    else:
        external_id = ticket_id
        demo_message = f"✅ Demo: Ticket {external_id} created successfully!"
        external_url = None
    
    ticket = {
        "id": ticket_id,
        "external_id": external_id,
        "type": ticket_type.lower(),
        "risk_id": risk_id,
        "title": title,
        "description": description,
        "url": external_url,
        "demo_message": demo_message,
        "status": "created",
        "created_at": created_at
    }
    
    rows = _load()
    rows.append(ticket)
    _save(rows)
    
    return {
        "id": external_id,
        "ticket_id": ticket_id,
        "url": external_url,
        "demo_message": demo_message,
        "status": "created"
    }