from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import os
from datetime import datetime, UTC
from .services.metrics import REQUESTS_TOTAL, REQUEST_LATENCY, INFLIGHT, prometheus_asgi_app
from .core.observability import RequestIDMiddleware

app = FastAPI(title="Censys Summarization Agent")

# ---- Prometheus middleware ----
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    method = request.method
    INFLIGHT.inc()
    start = datetime.now().timestamp()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        INFLIGHT.dec()
        dur = datetime.now().timestamp() - start
        try:
            REQUEST_LATENCY.labels(path=path).observe(dur)
        except Exception:
            pass
        try:
            status = str(getattr(response, "status_code", 500))
        except Exception:
            status = "500"
        try:
            REQUESTS_TOTAL.labels(path=path, method=method, status=status).inc()
        except Exception:
            pass

# Attach Request ID middleware for correlation
try:
    app.add_middleware(RequestIDMiddleware)
except Exception:
    pass

# --- Include existing routers (optional / try-safe) ---
# Legacy summarize endpoint (keeps /summarize/legacy)
try:
    from .app_legacy import router as legacy_router
    app.include_router(legacy_router)  # no prefix to preserve path
except Exception as e:
    print("legacy router not loaded:", e)

# Enrichment endpoints under /api
try:
    from .routes.enrich import router as enrich_router
    app.include_router(enrich_router, prefix="/api")
except Exception as e:
    print("enrich router not loaded:", e)

# CSV export endpoints under /api
try:
    from .routes.export import router as export_router
    app.include_router(export_router, prefix="/api")
except Exception as e:
    print("export router not loaded:", e)

# Admin endpoints (hot-load KEV, etc.) under /api
try:
    from .routes.admin import router as admin_router
    app.include_router(admin_router, prefix="/api")
except Exception as e:
    print("admin router not loaded:", e)

# Summarize endpoints under /api
try:
    from .routes.summarize import router as summarize_router
    app.include_router(summarize_router, prefix="/api")
except Exception as e:
    print("summarize router not loaded:", e)

# Saved views and alerts
try:
    from .routes.views import router as views_router
    app.include_router(views_router, prefix="/api")
except Exception as e:
    print("views router not loaded:", e)

# Trends
try:
    from .routes.trends import router as trends_router
    app.include_router(trends_router, prefix="/api")
except Exception as e:
    print("trends router not loaded:", e)

# AI check endpoint
try:
    from .routes.ai_check import router as ai_router
    app.include_router(ai_router, prefix="/api")
except Exception as e:
    print("ai router not loaded:", e)

# Telemetry
try:
    from .routes.telemetry import router as telemetry_router
    app.include_router(telemetry_router, prefix="/api")
except Exception as e:
    print("telemetry router not loaded:", e)

# Screenshot
try:
    from .routes.screenshot import router as screenshot_router
    app.include_router(screenshot_router, prefix="/api")
except Exception as e:
    print("screenshot router not loaded:", e)

# Mutes
try:
    from .routes.mute import router as mute_router
    app.include_router(mute_router, prefix="/api")
except Exception as e:
    print("mute router not loaded:", e)

# Tickets
try:
    from .routes.tickets import router as tickets_router
    app.include_router(tickets_router, prefix="/api")
except Exception as e:
    print("tickets router not loaded:", e)

# Compatibility/root endpoints for tests and legacy clients
try:
    from .routes.compat import router as compat_router
    app.include_router(compat_router)
except Exception as e:
    print("compat router not loaded:", e)

# Health (with fingerprint so we always know which file is live)
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "0.2.0",
        "time": datetime.now(UTC).isoformat(),
        "file": __file__,
    }

# ---- /metrics endpoint ----
@app.get("/metrics")
def metrics():
    ctype, body = prometheus_asgi_app()
    return Response(content=body, media_type=ctype)

# Optional CORS (set ALLOW_ORIGINS env, comma-separated)
allow = os.environ.get("ALLOW_ORIGINS", "").strip()
if allow:
    origins = [x.strip() for x in allow.split(",") if x.strip()]
    try:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    except Exception as _e:
        # don't crash startup if misconfigured
        pass
