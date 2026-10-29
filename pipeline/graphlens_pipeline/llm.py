"""The only place that talks to OpenAI. Bounded: timeout, few retries, token limits, cost.

The API key is read from the OPENAI_API_KEY environment variable and is never printed,
logged or stored. Error messages carry only the error type.

If LLM_BASE_URL is set (for example http://ollama:11434/v1), the same client talks to that
OpenAI-compatible server instead, no key is needed and calls cost nothing. Unset it to use OpenAI.
"""

import os
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Protocol

# US dollars per 1 million tokens (input, output). Source: OpenAI pricing page, read on
# 2026-10-24 (standard tier). A model not listed here has an unknown cost and is refused
# when a cost cap is set.
PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4": (2.50, 15.00),
}
TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 2


# Where the text of the final answer goes while the model is still writing it (streaming). The
# search service sets it for the one main answer; the call sites read it with `delta_kwargs()`.
_delta_sink: ContextVar[Callable[[str], None] | None] = ContextVar("delta_sink", default=None)


def set_delta_sink(sink: Callable[[str], None] | None):
    """Returns a token for `reset_delta_sink`."""
    return _delta_sink.set(sink)


def reset_delta_sink(token) -> None:
    _delta_sink.reset(token)


def delta_kwargs() -> dict:
    """`{"on_delta": sink}` when a sink is set, else `{}` (fakes without the argument work)."""
    sink = _delta_sink.get()
    return {"on_delta": sink} if sink else {}


class LlmError(Exception):
    """The model call failed. The message never contains the key or the request text."""


@dataclass(frozen=True)
class LlmResult:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    finish_reason: str = ""  # "stop" is normal; "length" means the answer was cut off


class Llm(Protocol):
    model: str

    def complete(
        self,
        system: str,
        user: str,
        max_output_tokens: int,
        json_schema: dict | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> LlmResult: ...


def cost_usd(model: str, tokens_in: int, tokens_out: int) -> float | None:
    """Cost of one call in dollars, or None when the model has no known price."""
    if os.environ.get("LLM_BASE_URL"):
        return 0.0  # a local model on the owner's machine
    prices = PRICES_PER_MILLION.get(model.split("-20")[0])  # "gpt-4.1-mini-2025-04-14" too
    if prices is None:
        return None
    return (tokens_in * prices[0] + tokens_out * prices[1]) / 1_000_000


class OpenAiLlm:
    def __init__(
        self, model: str | None = None, timeout: float | None = None, max_retries: int | None = None
    ) -> None:
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "")
        base_url = os.environ.get("LLM_BASE_URL") or None
        self.model = model or os.environ.get("LLM_MODEL_MAIN", "")
        if base_url:
            api_key = "local"  # the local server ignores it
        elif not api_key or api_key.startswith("sk-placeholder"):
            raise LlmError("OPENAI_API_KEY is not set")
        if not self.model or self.model.startswith("to-be-chosen"):
            raise LlmError("LLM_MODEL_MAIN is not set")
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout or TIMEOUT_SECONDS * (4 if base_url else 1),
            max_retries=MAX_RETRIES if max_retries is None else max_retries,
        )

    def complete(
        self,
        system: str,
        user: str,
        max_output_tokens: int,
        json_schema: dict | None = None,
        on_delta: Callable[[str], None] | None = None,
    ) -> LlmResult:
        """One model call. With `json_schema`, the reply must follow that schema exactly.
        With `on_delta`, the text is streamed: the function gets each new piece while the model
        writes, and the result is the same as without streaming."""
        if on_delta is not None and json_schema is None:
            return self._complete_streaming(system, user, max_output_tokens, on_delta)
        options: dict = {}
        if json_schema is not None:
            options["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "extraction", "strict": True, "schema": json_schema},
            }
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_completion_tokens=max_output_tokens,
                temperature=0,
                **options,
            )
        except Exception as error:  # the SDK raises many types; report only the type
            raise LlmError(f"model call failed ({type(error).__name__})") from error
        usage = response.usage
        return LlmResult(
            text=response.choices[0].message.content or "",
            model=response.model,
            tokens_in=usage.prompt_tokens if usage else 0,
            tokens_out=usage.completion_tokens if usage else 0,
            finish_reason=response.choices[0].finish_reason or "",
        )

    def _complete_streaming(
        self, system: str, user: str, max_output_tokens: int, on_delta: Callable[[str], None]
    ) -> LlmResult:
        parts: list[str] = []
        tokens_in = tokens_out = 0
        finish, model = "", self.model
        try:
            stream = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_completion_tokens=max_output_tokens,
                temperature=0,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                model = chunk.model or model
                if chunk.usage:
                    tokens_in, tokens_out = chunk.usage.prompt_tokens, chunk.usage.completion_tokens
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                piece = choice.delta.content if choice.delta else None
                if piece:
                    parts.append(piece)
                    on_delta(piece)
                finish = choice.finish_reason or finish
        except Exception as error:  # the SDK raises many types; report only the type
            raise LlmError(f"model call failed ({type(error).__name__})") from error
        return LlmResult(
            text="".join(parts),
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            finish_reason=finish,
        )
