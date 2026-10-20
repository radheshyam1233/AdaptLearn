# tests/test_ai.py
# We never call the real OpenAI API in tests (slow, costs money, flaky).
# Instead we swap in a fake client with monkeypatch.

import json
import types

from app.models import Question
from app.services import ai

Q = Question(id=1, text="Capital of India?", option_a="Mumbai", option_b="New Delhi",
             option_c="Kolkata", option_d="Chennai", answer="B", concept="GK")


def fake_client(reply=None, error=None):
    """Builds an object shaped like OpenAI(): client.chat.completions.create(...)"""
    def create(**kwargs):
        if error:
            raise error
        message = types.SimpleNamespace(content=json.dumps({"hint": reply}))
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])
    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))


def test_uses_ai_hint_when_safe(monkeypatch):
    monkeypatch.setattr(ai, "_client", fake_client("Think about where Parliament meets."))
    assert ai.generate_hint(Q, "A") == ("Think about where Parliament meets.", "ai")


def test_falls_back_when_ai_leaks_answer(monkeypatch):
    monkeypatch.setattr(ai, "_client", fake_client("It's New Delhi."))
    assert ai.generate_hint(Q, "A")[1] == "fallback"


def test_falls_back_when_ai_fails(monkeypatch):
    monkeypatch.setattr(ai, "_client", fake_client(error=TimeoutError("too slow")))
    hint, source = ai.generate_hint(Q, "A")
    assert source == "fallback" and "Mumbai" in hint


def test_guardrail_blocks_leaked_answer():
    assert ai.is_safe("Think about where Parliament sits.", Q)
    assert not ai.is_safe("It is New Delhi, the capital.", Q)
    assert not ai.is_safe("The correct answer is B.", Q)
    assert not ai.is_safe("", Q)
