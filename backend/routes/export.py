from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import csv
import io
from datetime import datetime
from ..services.metrics import EXPORT_TOTAL

router = APIRouter(tags=["export"])


class ExportCSVRequest(BaseModel):
    rows: List[Dict[str, Any]]


@router.post("/export/csv")
def export_csv(req: ExportCSVRequest):
    """
    Returns CSV text for provided rows. Keys are union of all row keys.
    """
    try:
        EXPORT_TOTAL.inc()
    except Exception:
        pass
    rows = req.rows or []
    # Collect header from union of keys
    header: List[str] = []
    seen = set()
    for r in rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                header.append(k)

    sio = io.StringIO()
    writer = csv.DictWriter(sio, fieldnames=header, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

    csv_bytes = sio.getvalue().encode("utf-8")
    filename = f"export_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


class ExportPDFRequest(BaseModel):
    """Minimal shape to render a concise brief. Accept same keys as summarize output."""
    overview: str | None = None
    overview_deterministic: str | None = None
    key_risks: List[Dict[str, Any]] | None = None
    recommendations: List[str] | None = None
    flags: Dict[str, Any] | None = None
    totals: Dict[str, Any] | None = None
    severity_matrix: Dict[str, int] | None = None


@router.post("/export/pdf")
def export_pdf(req: ExportPDFRequest):
    try:
        EXPORT_TOTAL.inc()
    except Exception:
        pass
    # Try reportlab; if unavailable, return a simple text file to avoid failing the request.
    try:
        import importlib
        _pagesizes = importlib.import_module('reportlab.lib.pagesizes')
        _pdfgen = importlib.import_module('reportlab.pdfgen.canvas')
        letter = getattr(_pagesizes, 'letter')
        canvas = getattr(_pdfgen, 'Canvas')
    except Exception:
        # Fallback: plain text
        txt = io.StringIO()
        txt.write("Executive Overview\n")
        txt.write((req.overview or req.overview_deterministic or "(none)") + "\n\n")
        if req.totals:
            txt.write(f"Totals: {req.totals}\n\n")
        if req.severity_matrix:
            txt.write(f"Severity: {req.severity_matrix}\n\n")
        if req.key_risks:
            txt.write("Top Risks:\n")
            for r in (req.key_risks or [])[:5]:
                ttl = str(r.get("title") or r.get("id") or "risk")
                sev = str(r.get("severity") or "-")
                txt.write(f" - [{sev}] {ttl}\n")
        if req.recommendations:
            txt.write("\nNext Actions:\n")
            for i, a in enumerate(req.recommendations[:5], 1):
                txt.write(f" {i}. {a}\n")
        buf = txt.getvalue().encode("utf-8")
        filename = f"brief_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.txt"
        return Response(content=buf, media_type="text/plain; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    # PDF happy path
    buffer = io.BytesIO()
    c = canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 72
    def line(text: str, dy: int = 14, bold: bool = False):
        nonlocal y
        if bold:
            c.setFont("Helvetica-Bold", 11)
        else:
            c.setFont("Helvetica", 10)
        for seg in wrap_text(text, 90):
            c.drawString(72, y, seg)
            y -= dy
        y -= 4

    def wrap_text(s: str, width_chars: int) -> List[str]:
        words = (s or "").split()
        lines: List[str] = []
        cur: List[str] = []
        cur_len = 0
        for w in words:
            if cur_len + len(w) + 1 > width_chars:
                lines.append(" ".join(cur))
                cur = [w]
                cur_len = len(w)
            else:
                cur.append(w)
                cur_len += len(w) + 1
        if cur:
            lines.append(" ".join(cur))
        return lines

    # Header
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, "Censys Executive Brief")
    y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(72, y, datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
    y -= 24

    # Overview
    line("Executive Overview", bold=True)
    line(req.overview or req.overview_deterministic or "(none)")

    if req.totals:
        line("Totals", bold=True)
        line(json_like(req.totals))
    if req.severity_matrix:
        line("Severity", bold=True)
        line(json_like(req.severity_matrix))

    if req.key_risks:
        line("Top Risks", bold=True)
        for r in (req.key_risks or [])[:5]:
            ttl = str(r.get("title") or r.get("id") or "risk")
            sev = str(r.get("severity") or "-")
            line(f"[{sev}] {ttl}")

    if req.recommendations:
        line("Next Actions", bold=True)
        for i, a in enumerate(req.recommendations[:5], 1):
            line(f"{i}. {a}")

    c.showPage()
    c.save()
    pdf = buffer.getvalue()
    filename = f"brief_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.pdf"
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def json_like(obj: Any) -> str:
    try:
        import json as _json
        return _json.dumps(obj, separators=(", ", ": "))
    except Exception:
        return str(obj)
