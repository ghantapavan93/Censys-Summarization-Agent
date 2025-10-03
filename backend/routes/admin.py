from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from ..services.kev_loader import kev_store
from ..services.epss_loader import warm_reload as epss_reload, get_epss

router = APIRouter(tags=["admin"])


class KevUpdate(BaseModel):
    cves: List[str]


@router.post("/admin/kev")
def admin_set_kev(body: KevUpdate):
    kev_store.set_ids(body.cves or [])
    # optional: persist a cache for next boot (best-effort)
    try:
        kev_store.save_cache()
    except Exception:
        pass
    return {"ok": True, "count": len(kev_store.kev_ids)}


@router.get("/admin/kev/stats")
def admin_kev_stats():
    return {"count": len(kev_store.kev_ids)}


class EPSSReloadReq(BaseModel):
    path: str | None = None  # optional explicit path; defaults to env/ data/epss.json or data/epss.csv


@router.post("/admin/epss/reload")
def admin_epss_reload(body: EPSSReloadReq):
    n = epss_reload(body.path)
    return {"ok": True, "count": n}


@router.get("/admin/epss/sample")
def admin_epss_sample(limit: int = 5):
    m = get_epss()
    items = sorted(m.items())[:max(0, min(limit, 20))]
    return {"count": len(m), "sample": items}
