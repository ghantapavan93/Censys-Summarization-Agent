from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

MAX_JSON_BYTES = 5 * 1024 * 1024  # 5MB limit


class SizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cl = request.headers.get("content-length")
        try:
            if cl is not None and int(cl) > MAX_JSON_BYTES:
                return JSONResponse(status_code=413, content={
                    "error": "payload_too_large",
                    "detail": f"Payload too large (>{MAX_JSON_BYTES // (1024*1024)}MB). Try chunked upload."
                })
        except ValueError:
            pass
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        return resp
