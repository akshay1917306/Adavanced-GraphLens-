"""The internal search service (CR-0004).

One route, `POST /search`, answers one question and returns the same `Answer` shape that the public
API sends to the screen. It is reachable only from the API container, and every call must carry the
shared key. The public API keeps visitor tokens, rate limits, the cost cap and history.

The file has three layers: pure builders that turn the result of one search mode into the reply
shape (tested without any database), `SearchService` that routes a question and runs the mode
(tested with fake backends), and `create_app` that wraps the service in HTTP.
"""

import hmac
import logging
import re
import time
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated
from uuid import uuid4

from fastapi import FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from graphlens_pipeline.replayexport import KIND_OF_LABEL, _title, pick_graph

log = logging.getLogger("graphlens.search")

MAX_QUESTION_CHARS = 4000
NUMBERED = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")


# ------------------------------------------------------------------ reply builders


def _answer(mode: str, status: str, **fields) -> dict:
    """Every reply has exactly the fields of the API's `Answer` model."""
    reply = {
        "mode": mode,
        "status": status,
        "text": "",
        "message": None,
        "citations": [],
        "nodes": [],
        "links": [],
        "check_status": "not_checked",
        "model": "",
        "cost_usd": 0.0,
        "latency_ms": 0,
    }
    reply.update(fields)
    return reply


def _message(reason: str, suggestion: str = "", options: list[str] | None = None) -> str:
    parts = [reason.strip(), suggestion.strip()]
    if options:
        parts.append("Options: " + "; ".join(options) + ".")
    return " ".join(p for p in parts if p)


def _context_citations(labels: list[str], context, unit_rows) -> list[dict]:
    """The items the answer cited, each with its passage or description (text only)."""
    shown = context.by_label()
    found = [label for label in labels if label in shown]
    unit_ids = [shown[label].ref for label in found if label[0] == "T"]
    rows = unit_rows(unit_ids) if unit_ids else {}
    citations = []
    for label in found:
        item = shown[label]
        row = rows.get(item.ref, {}) if label[0] == "T" else {}
        citations.append(
            {
                "label": label,
                "kind": KIND_OF_LABEL[label[0]],
                "title": row.get("title") or _title(item.text),
                "text": item.text,
                "source": row.get("section") or None,
                "ref_id": item.ref,
            }
        )
    return citations


def build_local(answer, context, unit_rows) -> dict:
    """A finished local search: `answer` is a LocalAnswer, `context` its LocalContext (or None)."""
    if answer.status != "answered":
        return _answer(
            "local",
            answer.status,
            message=_message(answer.reason, answer.suggestion, answer.options),
            cost_usd=answer.cost_usd,
        )
    cited = list(dict.fromkeys(answer.check.cited))
    citations = _context_citations(cited, context, unit_rows) if context else []
    entity_ids = [c["ref_id"] for c in citations if c["kind"] == "entity"]
    graph = getattr(context, "graph", None)
    nodes, links = pick_graph(graph, entity_ids) if graph else ([], [])
    return _answer(
        "local",
        "answered",
        text=answer.text,
        citations=citations,
        nodes=nodes,
        links=links,
        check_status=answer.check.status,
        cost_usd=answer.cost_usd,
    )


def build_relate(answer, unit_rows) -> dict:
    """A finished relate search: `answer` is a RelateAnswer."""
    if answer.status == "clarify":
        return _answer(
            "relate", "clarify", message=_message(answer.reason, answer.suggestion, answer.options)
        )
    if answer.status == "no_path":
        titles = [c.get("title", "") for c in answer.shared_communities if c.get("title")]
        extra = f" Nearest shared topics: {'; '.join(titles[:3])}." if titles else ""
        return _answer("relate", "refused", message=(answer.reason + extra).strip())
    if answer.status != "answered":
        return _answer(
            "relate",
            "refused",
            message=_message(answer.reason, answer.suggestion),
            cost_usd=answer.cost_usd,
        )
    context = getattr(answer, "context", None)
    cited = list(dict.fromkeys(answer.check.cited))
    citations = _context_citations(cited, context, unit_rows) if context else []
    best = answer.paths[0] if answer.paths else None
    nodes = (
        [
            {"id": n["id"], "label": n["name"], "type": n["type"], "confidence": None}
            for n in best.nodes
        ]
        if best
        else []
    )
    links = (
        [
            {"source": h.source, "target": h.target, "predicate": h.predicate, "confidence": None}
            for h in best.hops
        ]
        if best
        else []
    )
    return _answer(
        "relate",
        "answered",
        text=answer.text,
        citations=citations,
        nodes=nodes,
        links=links,
        check_status=answer.check.status,
        cost_usd=answer.cost_usd,
    )


def build_global(answer) -> dict:
    """A finished global search: `answer` is a GlobalAnswer."""
    if not answer.text.strip():
        return _answer("global", "refused", message="No community report matched the question.")
    citations = [
        {
            "label": item.label,
            "kind": "community",
            "title": item.title,
            "text": item.summary + ("\n" + "\n".join(item.findings[:3]) if item.findings else ""),
            "source": None,
            "ref_id": item.id,
        }
        for item in answer.used
        if item.label
    ]
    return _answer(
        "global", "answered", text=answer.text, citations=citations, cost_usd=answer.cost_usd
    )


def build_baseline(result) -> dict:
    """A finished plain-RAG answer: `result` is an AnswerResult with numbered passages."""
    if result.refused:
        return _answer("baseline", "refused", message=result.answer, model=result.model or "")
    text = NUMBERED.sub(
        lambda m: "".join(f"[T{n.strip()}]" for n in m.group(1).split(",")), result.answer
    )
    cited = set(result.cited)
    citations = [
        {
            "label": f"T{p.number}",
            "kind": "text_unit",
            "title": p.title,
            "text": p.text,
            "source": p.section or None,
            "ref_id": p.unit_id,
        }
        for p in result.passages
        if p.number in cited
    ]
    if not cited:
        check = "not_checked"
    else:
        check = "verified" if result.citations_valid else "warning"
    return _answer(
        "baseline",
        "answered",
        text=text,
        citations=citations,
        check_status=check,
        model=result.model or "",
        cost_usd=result.cost_usd or 0.0,
    )


# ------------------------------------------------------------------ the service


@dataclass
class Backends:
    """The four search modes and the router, as functions, so tests can replace the databases."""

    route: Callable  # (question) -> Route
    local: Callable  # (question) -> reply dict
    relate: Callable
    global_: Callable
    baseline: Callable


class SearchService:
    def __init__(self, backends: Backends, model: str = "") -> None:
        self._b = backends
        self._model = model

    def ask(self, question: str, compare: bool) -> dict:
        started = time.perf_counter()
        route = self._b.route(question)
        runners = {
            "local": self._b.local,
            "relate": self._b.relate,
            "global": self._b.global_,
            "baseline": self._b.baseline,
        }
        answer = runners[route.mode](question)
        answer["cost_usd"] = round(answer["cost_usd"] + (route.cost_usd or 0.0), 6)
        answer["latency_ms"] = round((time.perf_counter() - started) * 1000)
        answer["model"] = answer["model"] or self._model
        baseline = None
        if compare and route.mode != "baseline":
            started = time.perf_counter()
            baseline = self._b.baseline(question)
            baseline["latency_ms"] = round((time.perf_counter() - started) * 1000)
            baseline["model"] = baseline["model"] or self._model
        return {
            "answer": answer,
            "baseline": baseline,
            "route": {
                "mode": route.mode,
                "source": route.source,
                "confidence": round(route.confidence, 3),
                "fallback": route.ran_as_fallback,
            },
        }


# ------------------------------------------------------------------ the HTTP wrapper


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    compare: bool = False


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(service_factory: Callable[[], SearchService], key: str) -> FastAPI:
    """`service_factory` runs once at start-up (it loads the models and opens the databases)."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = service_factory()
        yield

    app = FastAPI(
        title="GraphLens search service",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.service = None

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, error: RequestValidationError) -> JSONResponse:
        return _error("invalid_request", "Invalid request.", 422)  # never echoes the question

    @app.exception_handler(Exception)
    async def failed(request: Request, error: Exception) -> JSONResponse:
        log.error(
            "search failed %s request_id=%s",
            type(error).__name__,
            getattr(request.state, "request_id", "-"),
        )
        return _error("search_failed", "The search failed.", 500)

    @app.get("/healthz")
    def healthz():
        if app.state.service is None:
            return _error("not_ready", "The search service is still starting.", 503)
        return {"status": "ok"}

    @app.post("/search", response_model=None)
    def search(
        body: SearchRequest,
        request: Request,
        x_search_key: Annotated[str | None, Header()] = None,
        x_request_id: Annotated[str | None, Header()] = None,
    ):
        request.state.request_id = (x_request_id or uuid4().hex)[:64]
        if not key or x_search_key is None or not hmac.compare_digest(x_search_key, key):
            return _error("unauthorized", "Missing or wrong key.", 401)
        if app.state.service is None:
            return _error("not_ready", "The search service is still starting.", 503)
        reply = app.state.service.ask(body.question.strip(), body.compare)
        log.info(
            "search request_id=%s mode=%s status=%s ms=%s",
            request.state.request_id,
            reply["answer"]["mode"],
            reply["answer"]["status"],
            reply["answer"]["latency_ms"],
        )
        return reply

    return app


# ------------------------------------------------------------------ the real backends


def real_backends(deps, llm, driver, engine, qdrant, embedder, predicates, index_version, encoder):
    """The four modes wired to the real databases, the local embedding model and the model client.
    Everything heavy is imported here so the builders above stay light to test."""
    from graphlens_pipeline.answer import AnswerError, answer_question
    from graphlens_pipeline.globalsearch import answer_from_selection, select_communities
    from graphlens_pipeline.localanswer import answer_local
    from graphlens_pipeline.localcontext import postgres_unit_rows
    from graphlens_pipeline.relate import answer_relate
    from graphlens_pipeline.router import route_question

    def unit_rows(ids):
        return postgres_unit_rows(engine, ids)

    def count(text):
        return len(encoder.encode(text))

    def route(question):
        return route_question(question, deps.index, llm)

    def local(question):
        answer, context = answer_local(deps, llm, question)
        return build_local(answer, context, unit_rows)

    def relate(question):
        answer = answer_relate(
            driver, llm, deps.index, question, predicates, index_version, unit_rows, count
        )
        return build_relate(answer, unit_rows)

    def global_(question):
        selected = select_communities(driver, embedder.dense_query, question, index_version)
        if not selected:
            return _answer("global", "refused", message="No community report matched the question.")
        return build_global(answer_from_selection(llm, question, selected, count))

    def baseline(question):
        try:
            return build_baseline(answer_question(question, qdrant, engine, embedder, llm, k=6))
        except AnswerError as error:
            return _answer(
                "baseline", "refused", message=f"The answer could not be written ({error})."
            )

    return Backends(route, local, relate, global_, baseline)
