"""Koan-Safe (LLM): an LLM generator wrapped by the enforcement layer.

The LLM proposes a candidate workflow from the raw prompt (same call path as
the ``direct_llm`` baseline); Koan-Safe's deterministic clarification gate and
safety-enforcement layer then repair and harden it. This isolates the
enforcement layer's contribution on top of a strong neural generator.

Requires an API key (``OPENROUTER_API_KEY`` / ``ANTHROPIC_API_KEY``); without
one it raises :class:`BaselineSkipped` and the runner records a skipped run.
``KOAN_SAFE_ENFORCE=0`` disables enforcement for the ablation (then this is
just the LLM generator behind Koan-Safe's parser/clarification gate).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from koan_safe_core import build_result, parse_intent  # noqa: E402
from llm_common import (  # noqa: E402
    BaselineSkipped, _provider, build_prompt, _call_openrouter,
    _call_anthropic, parse_model_output,
)


def _llm_candidate(prompt: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Call the model once and return (candidate_workflow, model_meta)."""
    provider = _provider()
    if provider is None:
        raise BaselineSkipped("no OPENROUTER_API_KEY or ANTHROPIC_API_KEY set")
    provider_name, model = provider
    temperature = 0.0
    content = build_prompt(prompt, constrained=False)
    raw_text = (_call_openrouter(model, content, temperature)
                if provider_name == "openrouter"
                else _call_anthropic(model, content, temperature))
    workflow, _status = parse_model_output(raw_text)
    meta = {"provider": provider_name, "model": model, "temperature": temperature,
            "raw_output": raw_text}
    return workflow, meta


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    intent = parse_intent(prompt["prompt"])
    # Koan-Safe's clarification gate fires before generation, so skip the LLM
    # call entirely when the parse decides to ask for clarification.
    if intent.decision == "clarify":
        return build_result(prompt, "koan_safe_llm", {}, intent,
                            extra={"generator": "llm", "model": None})
    candidate, meta = _llm_candidate(prompt)
    return build_result(prompt, "koan_safe_llm", candidate, intent,
                        extra={"generator": "llm", "model": meta})
