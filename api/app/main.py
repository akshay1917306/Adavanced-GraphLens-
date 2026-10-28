"""GraphLens API entry point."""

import hmac
import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Header, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeout

from app.ask import AskService, EngineUnavailable, get_ask_service, set_ask_service
from app.config import get_settings
from app.hardening import configure_logging, hardening
from app.health import run_checks
from app.ratelimit import (
    DailyCapReached,
    Limiter,
    LimiterUnavailable,
    RateLimited,
    admin_limit,
    ask_limits,
    current_visitor,
    get_limiter,
    visitor_creation_limit,
)
from app.replay import ReplayService
from app.schemas import (
    AskRequest,
    AskResponse,
    ConversationDetail,
    DeletedCounts,
    ErrorResponse,
    FeedbackRequest,
    FeedbackResponse,
    HistoryList,
    Preferences,
    SavedList,
    SaveRequest,
)
from app.store import Store, get_store
from app.visitor import (
    VisitorNotConfigured,
    VisitorRequired,
    issue_token,
    signing_secret,
    verify_token,
)

configure_logging()
log = logging.getLogger("graphlens.api")

if get_settings().answer_mode == "replay":
    set_ask_service(ReplayService())

app = FastAPI(title="GraphLens API", version="0.0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[get_settings().web_origin],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)


app.middleware("http")(hardening)  # added after CORS, so it wraps it


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


@app.exception_handler(VisitorRequired)
async def visitor_required(request: Request, error: VisitorRequired) -> JSONResponse:
    return _error("visitor_required", "A valid visitor token is required.", 401)


@app.exception_handler(VisitorNotConfigured)
async def visitor_not_configured(request: Request, error: VisitorNotConfigured) -> JSONResponse:
    return _error("visitor_not_configured", "Visitor tokens are not set up.", 503)


@app.exception_handler(RateLimited)
async def rate_limited(request: Request, error: RateLimited) -> JSONResponse:
    message = f"Too many requests. Please try again in {error.retry_after} seconds."
    response = _error("rate_limited", message, 429)
    response.headers["Retry-After"] = str(error.retry_after)
    return response


@app.exception_handler(DailyCapReached)
async def daily_cap(request: Request, error: DailyCapReached) -> JSONResponse:
    return _error("daily_limit", "The daily limit for answers has been reached. Try tomorrow.", 429)


@app.exception_handler(LimiterUnavailable)
async def limiter_unavailable(request: Request, error: LimiterUnavailable) -> JSONResponse:
    return _error("limiter_unavailable", "The service is busy. Please try again shortly.", 503)


@app.exception_handler(OperationalError)
@app.exception_handler(InterfaceError)
@app.exception_handler(PoolTimeout)
async def storage_unavailable(request: Request, error: Exception) -> JSONResponse:
    """The database cannot be reached or is out of connections: tell the caller to try again.
    Other database errors (a bad query, a broken constraint) are our bugs and stay a plain 500."""
    request_id = getattr(request.state, "request_id", "-")
    log.error("storage unavailable %s request_id=%s", type(error).__name__, request_id)
    response = _error(
        "storage_unavailable", "Storage is busy. Please try again in a few seconds.", 503
    )
    response.headers["Retry-After"] = "5"
    return response


@app.exception_handler(Exception)
async def internal_error(request: Request, error: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    log.error(
        "unhandled error %s request_id=%s", type(error).__name__, request_id
    )  # no text, no stack
    return _error("internal_error", "Something went wrong.", 500)


@app.get("/api/v1/health")
def health(response: Response) -> dict:
    """Report whether each backing service is reachable. Returns 503 if any is down."""
    result = run_checks(get_settings())
    if result["status"] != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


class VisitorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str | None = Field(default=None, max_length=200)


class VisitorResponse(BaseModel):
    token: str
    max_age_seconds: int


@app.post(
    "/api/v1/visitor",
    response_model=VisitorResponse,
    dependencies=[Depends(visitor_creation_limit)],
)
def visitor(body: VisitorRequest, store: Annotated[Store, Depends(get_store)]) -> VisitorResponse:
    """Give the browser a signed token: renewed for a known visitor, else for a new visitor."""
    secret = signing_secret()
    ttl = get_settings().visitor_token_ttl_days * 86400
    known = verify_token(body.token or "", secret)
    if known is None or not store.visitor_exists(known):
        known = store.create_visitor()
    return VisitorResponse(token=issue_token(known, secret, ttl), max_age_seconds=ttl)


@app.post(
    "/api/v1/ask",
    response_model=AskResponse,
    dependencies=[Depends(ask_limits)],
)
def ask(
    body: AskRequest,
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    service: Annotated[AskService, Depends(get_ask_service)],
    store: Annotated[Store, Depends(get_store)],
    limiter: Annotated[Limiter, Depends(get_limiter)],
) -> AskResponse:
    """Answer one question with its evidence. A refusal or a clarify request is a normal 200."""
    response = service.ask(body.question, body.compare)
    spent = response.answer.cost_usd + (response.baseline.cost_usd if response.baseline else 0.0)
    limiter.record_cost(spent)  # counts toward today's cap, even if saving fails below
    try:
        answer_id = store.save_answer(
            visitor_id, body.question, response.answer, get_settings().index_version
        )
    except Exception as error:  # the answer is still useful without the record
        log.error("could not save the answer: %s", type(error).__name__)
        return response.model_copy(update={"saved": False})
    return response.model_copy(update={"answer_id": answer_id, "saved": True})


@app.post("/api/v1/feedback", response_model=None)
def feedback(
    body: FeedbackRequest,
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
) -> FeedbackResponse | JSONResponse:
    saved = store.save_feedback(visitor_id, body.answer_id, body.rating, body.reason, body.comment)
    if not saved:
        return _error("unknown_answer", "No such answer.", 404)
    return FeedbackResponse(saved=True)


@app.get("/api/v1/history", response_model=HistoryList)
def history(
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> HistoryList:
    return HistoryList(items=store.list_history(visitor_id, limit))


@app.get("/api/v1/history/{conversation_id}", response_model=None)
def history_item(
    conversation_id: UUID,
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
) -> ConversationDetail | JSONResponse:
    found = store.get_conversation(visitor_id, conversation_id)
    if found is None:
        return _error("not_found", "No such conversation.", 404)
    return ConversationDetail(**found)


@app.delete("/api/v1/history/{conversation_id}", response_model=None)
def delete_history_item(
    conversation_id: UUID,
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
) -> dict | JSONResponse:
    if not store.delete_conversation(visitor_id, conversation_id):
        return _error("not_found", "No such conversation.", 404)
    return {"deleted": True}


@app.delete("/api/v1/me", response_model=DeletedCounts)
def delete_my_data(
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
) -> DeletedCounts:
    """Delete this visitor and everything stored for them. The token stops working."""
    return DeletedCounts(**store.delete_visitor_data(visitor_id))


@app.get("/api/v1/saved", response_model=SavedList)
def saved(
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
) -> SavedList:
    return SavedList(items=store.list_saved(visitor_id))


@app.post("/api/v1/saved", response_model=None)
def save_answer(
    body: SaveRequest,
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
) -> dict | JSONResponse:
    if not store.save_for_later(visitor_id, body.answer_id, body.note):
        return _error("unknown_answer", "No such answer.", 404)
    return {"saved": True}


@app.delete("/api/v1/saved/{answer_id}", response_model=None)
def unsave_answer(
    answer_id: UUID,
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
) -> dict | JSONResponse:
    if not store.delete_saved(visitor_id, answer_id):
        return _error("not_found", "Not saved.", 404)
    return {"deleted": True}


@app.get("/api/v1/preferences", response_model=Preferences)
def get_preferences(
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
) -> Preferences:
    return Preferences(**store.get_preferences(visitor_id))


@app.put("/api/v1/preferences", response_model=Preferences)
def put_preferences(
    body: Preferences,
    visitor_id: Annotated[UUID, Depends(current_visitor)],
    store: Annotated[Store, Depends(get_store)],
) -> Preferences:
    store.set_preferences(visitor_id, body.theme, body.default_mode, body.evidence_panel_open)
    return body


@app.get("/api/v1/status", response_model=None, dependencies=[Depends(admin_limit)])
def run_status(
    store: Annotated[Store, Depends(get_store)],
    x_admin_key: Annotated[str | None, Header()] = None,
) -> dict | JSONResponse:
    """Read-only run and quality summary. Needs the admin key; off when no key is configured."""
    key = get_settings().admin_api_key.get_secret_value()
    if not key:
        return _error("admin_disabled", "The status page is switched off.", 403)
    if x_admin_key is None or not hmac.compare_digest(x_admin_key, key):
        store.audit("status_denied")
        return _error("unauthorized", "Missing or wrong admin key.", 401)
    store.audit("status_view")
    return store.status()


@app.get("/api/v1/examples")
def examples(service: Annotated[AskService, Depends(get_ask_service)]) -> dict:
    """Questions the current engine can answer in full (replay mode), for the example chips."""
    listing = getattr(service, "examples", None)
    return {"questions": listing() if listing else []}
