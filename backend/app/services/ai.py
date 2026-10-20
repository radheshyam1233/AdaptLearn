# app/services/ai.py
# Generates a hint for a wrong answer.
# Design rule: the AI must NEVER break answer submission.
# No API key, a timeout, an API error or a bad reply -> a safe fallback hint.

import json
import logging

from openai import OpenAI

from ..config import settings
from ..models import Question

log = logging.getLogger(__name__)

# One client for the whole app (it reuses connections). None if no key is set.
_client = (
    OpenAI(api_key=settings.openai_api_key, timeout=15.0, max_retries=1)
    if settings.openai_api_key else None
)

SYSTEM_PROMPT = (
    "You are a patient tutor. A student answered a multiple-choice question wrongly. "
    "Explain the likely misconception behind their choice and give ONE hint that "
    "guides them toward the right idea. Do NOT reveal the correct option or its text. "
    "Keep it under 60 words. Reply as JSON: {\"hint\": \"...\"}"
)


def fallback_hint(q: Question, selected: str) -> str:
    return (f"Not quite. You chose {selected}: \"{q.option_text(selected)}\". "
            f"Revisit the core idea of {q.concept} and check each option against it.")


def is_safe(hint: str, q: Question) -> bool:
    """Guardrail: AI output is not always right, so we check it before showing it.
    Reject a hint that is empty, too long, or gives the answer away."""
    h = hint.strip().lower()
    if not 0 < len(h) <= 600:
        return False
    if "correct answer" in h or f"option {q.answer.lower()}" in h:
        return False
    correct_text = q.option_text(q.answer).strip().lower()
    # Only check texts of 3+ characters: an answer like "1" appears in many harmless hints
    return not (len(correct_text) >= 3 and correct_text in h)


def generate_hint(q: Question, selected: str) -> tuple[str, str]:
    """Returns (hint, source) where source is "ai" or "fallback"."""
    if _client is None:
        return fallback_hint(q, selected), "fallback"

    user_msg = (
        f"Concept: {q.concept}\nQuestion: {q.text}\n"
        f"A) {q.option_a}\nB) {q.option_b}\nC) {q.option_c}\nD) {q.option_d}\n"
        f"Correct option: {q.answer}\nStudent chose: {selected}"
    )
    extra = {}
    if settings.openai_reasoning_effort:
        extra["reasoning_effort"] = settings.openai_reasoning_effort
    try:
        resp = _client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT},
                      {"role": "user", "content": user_msg}],
            response_format={"type": "json_object"},   # forces valid JSON
            max_completion_tokens=1000,                 # upper limit on cost per call
            **extra,
        )
        hint = json.loads(resp.choices[0].message.content)["hint"]
        if is_safe(hint, q):
            return hint, "ai"
        log.warning("AI hint rejected by guardrail for question %s", q.id)
    except Exception as exc:  # timeout, network, bad JSON, missing key...
        log.warning("AI hint failed: %s", exc)
    return fallback_hint(q, selected), "fallback"
