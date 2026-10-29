"""The router: which mode should answer this question?

Four modes: local (specific, multi-hop), global (corpus-wide), relate (how are two things
connected) and baseline (a simple lookup). Rules decide first because they are free and easy to
explain. Only when the rules are unsure (confidence under 0.7) is a small model asked, for a few
hundredths of a cent. Under 0.6 overall the question runs as local and the answer says so.
The user can always force a mode.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from graphlens_pipeline.linking import EntityIndex, name_matches, sanitise
from graphlens_pipeline.llm import Llm, LlmError

MODES = ("local", "global", "relate", "baseline")
RULES_CONFIDENT = 0.7  # below this the model is asked
FALLBACK_BELOW = 0.6  # below this the question runs as local, with a note
SPECIFIC_WEIGHT = 0.5

RELATE_CUE = re.compile(
    # "link" alone is not a cue: "link prediction" is a task name, not a question about a relation
    r"\b(relat(?:ed|ion|ionship|es)\b|connect(?:ed|ion|s)\b|links? (?:between|to|with)\b"
    r"|linked (?:to|with)\b|path(?:s)? between"
    r"|what (?:links|connects)|how does .{1,60} (?:relate|connect)|in common)",
    re.IGNORECASE,
)
GLOBAL_CUE = re.compile(
    r"\b(main (?:themes?|directions?|topics?)|overall|in general|across (?:the )?(?:corpus|papers|"
    r"collection)|trends?|research directions?|which papers|what papers|how do(?:es)? the papers"
    r"|the papers in (?:this|the) (?:corpus|collection)|in (?:this|the) (?:corpus|collection)"
    r"|all (?:the )?papers|landscape|big picture|summari[sz]e)",
    re.IGNORECASE,
)
SIMPLE_CUE = re.compile(
    r"^\s*(?:what is|what are|what's|define|who (?:is|are|wrote|proposed)|when|where)\b",
    re.IGNORECASE,
)
MULTI_CUE = re.compile(
    r"\b(improve[sd]? on|compared? (?:to|with)|better than|evaluated on|which (?:methods?|models?|"
    r"datasets?)|and which|and on which|both|outperform)",
    re.IGNORECASE,
)

CLASSIFY_SYSTEM = """You route a question about a collection of research papers to one mode:
- local: a specific question about named methods, datasets or results, often needing several facts
- global: a question about the whole collection (themes, trends, which papers do X)
- relate: asks how two named things are connected
- baseline: a simple lookup of one fact or definition
Answer with JSON: {"mode": one of the four, "confidence": a number from 0 to 1}."""
CLASSIFY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["mode", "confidence"],
    "properties": {
        "mode": {"type": "string", "enum": list(MODES)},
        "confidence": {"type": "number"},
    },
}


@dataclass
class Route:
    mode: str
    confidence: float
    source: str  # rules, model, fallback or forced
    reason: str
    ran_as_fallback: bool = False  # confidence was too low, so it runs as local
    asked_model: bool = False
    cost_usd: float = 0.0


def route_by_rules(question: str, index: EntityIndex | None) -> Route:
    """(mode, confidence) from the question's words and the entities it names."""
    text = sanitise(question).text
    groups = name_matches(text, index) if index else []
    specific = [g for g in groups if max(m.weight for m in g) >= SPECIFIC_WEIGHT]
    words = len(text.split())
    relate, glob = bool(RELATE_CUE.search(text)), bool(GLOBAL_CUE.search(text))
    if relate and len(groups) >= 2:
        return Route("relate", 0.9, "rules", "asks how two named things are connected")
    if glob and len(specific) <= 1:
        return Route("global", 0.85, "rules", "asks about the whole collection")
    if glob and len(specific) >= 2:
        return Route("global", 0.55, "rules", "corpus-wide wording but several named things")
    if relate and len(groups) < 2:
        return Route("relate", 0.5, "rules", "relate wording but fewer than two named things")
    if specific and (MULTI_CUE.search(text) or len(specific) >= 2 or words > 12):
        return Route("local", 0.85, "rules", "names specific things and asks for several facts")
    if specific and SIMPLE_CUE.search(text) and words <= 12:
        return Route("baseline", 0.7, "rules", "a short definition or fact about one named thing")
    if specific:
        return Route("local", 0.75, "rules", "names a specific thing")
    if SIMPLE_CUE.search(text) and words <= 10:
        return Route("baseline", 0.55, "rules", "a short question that names nothing specific")
    return Route("local", 0.4, "rules", "no clear signal")


def classify_with_model(llm: Llm, question: str) -> tuple[str, float, float]:
    """(mode, confidence, cost). Raises LlmError when the answer is unusable."""
    from graphlens_pipeline.llm import cost_usd

    reply = llm.complete(
        CLASSIFY_SYSTEM,
        f"Question: {sanitise(question).text[:600]}",
        80,
        json_schema=CLASSIFY_SCHEMA,
    )
    cost = cost_usd(reply.model, reply.tokens_in, reply.tokens_out) or 0.0
    try:
        data = json.loads(reply.text)
        mode, confidence = data["mode"], float(data["confidence"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise LlmError("the router model gave no usable answer") from error
    if mode not in MODES or not 0 <= confidence <= 1:
        raise LlmError("the router model gave a mode or confidence out of range")
    return mode, confidence, cost


def route_question(
    question: str, index: EntityIndex | None, llm: Llm | None = None, force: str | None = None
) -> Route:
    """The final route. `force` is the user's manual override."""
    if force:
        if force not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        return Route(force, 1.0, "forced", "chosen by the user")
    route = route_by_rules(question, index)
    if route.confidence >= RULES_CONFIDENT or llm is None:
        return _finish(route)
    try:
        mode, confidence, cost = classify_with_model(llm, question)
    except LlmError:
        route.reason += " (the router model was not available)"
        return _finish(route)
    if confidence >= route.confidence:
        reason = f"the rules were unsure ({route.reason})"
        return _finish(Route(mode, confidence, "model", reason, asked_model=True, cost_usd=cost))
    route.asked_model, route.cost_usd = True, cost
    return _finish(route)


def _finish(route: Route) -> Route:
    """Below the fallback bar the question runs as local, and the answer says so."""
    if route.confidence < FALLBACK_BELOW and route.mode != "local" and route.source != "forced":
        route.reason += f" (confidence {route.confidence:.2f}, so it runs as local)"
        route.mode, route.ran_as_fallback = "local", True
    return route
