import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQ_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get(REQ_ID_HEADER, str(uuid.uuid4()))
        request.state.request_id = req_id
        resp = await call_next(request)
        resp.headers[REQ_ID_HEADER] = req_id
        return resp
