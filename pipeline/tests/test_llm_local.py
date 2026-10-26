import pytest

from graphlens_pipeline.llm import LlmError, OpenAiLlm, cost_usd


def test_local_server_needs_no_key_and_costs_nothing(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://ollama:11434/v1")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    llm = OpenAiLlm(model="qwen2.5:3b")
    assert llm.model == "qwen2.5:3b"
    assert cost_usd("qwen2.5:3b", 1000, 1000) == 0.0


def test_without_base_url_a_key_is_still_required(monkeypatch):
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(LlmError):
        OpenAiLlm(model="gpt-4.1-mini")
    assert cost_usd("unknown-model", 1, 1) is None
