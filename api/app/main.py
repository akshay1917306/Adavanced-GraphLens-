"""GraphLens API entry point."""

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.ask import AskService, EngineUnavailable, get_ask_service
from app.config import get_settings
from app.health import run_checks
from app.schemas import AskRequest, AskResponse, ErrorResponse

log = logging.getLogger("graphlens.api")

app = FastAPI(title="GraphLens API", version="0.0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().web_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _error(code: str, message: str, http_status: int) -> JSONResponse:
    body = ErrorResponse(error={"code": code, "message": message})
    return JSONResponse(status_code=http_status, content=body.model_dump())


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, error: RequestValidationError) -> JSONResponse:
    # Never echo the input back: a question may carry a secret the user pasted by mistake.
    fields = sorted({str(e["loc"][-1]) for e in error.errors() if e.get("loc")})
    where = ", ".join(fields) or "the body"
    return _error("invalid_request", f"Invalid request: check {where}.", 422)


@app.exception_handler(EngineUnavailable)
async def engine_unavailable(request: Request, error: EngineUnavailable) -> JSONResponse:
    return _error("engine_unavailable", "The answer engine is not available right now.", 503)


@app.exception_handler(Exception)
async def internal_error(request: Request, error: Exception) -> JSONResponse:
    log.error("unhandled error: %s", type(error).__name__)  # type only: no text, no stack
    return _error("internal_error", "Something went wrong.", 500)


@app.get("/api/v1/health")
def health(response: Response) -> dict:
    """Report whether each backing service is reachable. Returns 503 if any is down."""
    result = run_checks(get_settings())
    if result["status"] != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@app.post("/api/v1/ask", response_model=AskResponse)
def ask(body: AskRequest, service: Annotated[AskService, Depends(get_ask_service)]) -> AskResponse:
    """Answer one question with its evidence. A refusal or a clarify request is a normal 200."""
    return service.ask(body.question, body.compare)
