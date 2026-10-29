"""Request ids, security headers, a body-size limit and structured logs (D54, D55).

Logs carry the request id, method, route template, status and timing. They never carry the
question, an answer, a token, a key or the query string: nothing a person typed is written down.
"""

import json
import logging
import re
import time
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse

log = logging.getLogger("graphlens.request")

# the id of the request being handled, so calls to other services can carry it
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

REQUEST_ID_OK = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
MAX_BODY_BYTES = 32_768  # the largest legitimate body is a 4,000-character question
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")  # Swagger loads scripts, so no strict CSP there

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Resource-Policy": "same-origin",
}
API_CSP = "default-src 'none'; frame-ancestors 'none'"


def _refuse(status: int, code: str, message: str) -> Response:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "unmatched")


async def hardening(request: Request, call_next):
    started = time.perf_counter()
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if REQUEST_ID_OK.match(supplied) else uuid4().hex
    request.state.request_id = request_id
    request_id_var.set(request_id)

    response: Response | None = None
    if request.method in ("POST", "PUT"):
        length = request.headers.get("content-length")
        if length is None:
            response = _refuse(411, "length_required", "A Content-Length header is required.")
        elif not length.isdigit() or int(length) > MAX_BODY_BYTES:
            response = _refuse(413, "too_large", "The request is too large.")
    if response is None:
        response = await call_next(request)

    response.headers["X-Request-Id"] = request_id
    for name, value in SECURITY_HEADERS.items():
        response.headers[name] = value
    if request.url.path not in DOCS_PATHS:
        response.headers["Content-Security-Policy"] = API_CSP

    log.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "route": _route_template(request),
                "status": response.status_code,
                "ms": round((time.perf_counter() - started) * 1000),
            }
        )
    )
    return response


def configure_logging() -> None:
    """One JSON object per line on stdout; nothing else decorates the message."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", force=True)
