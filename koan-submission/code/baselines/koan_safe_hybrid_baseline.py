"""Koan-Safe (hybrid): LLM generation backstopped by the rules parser,
both under the enforcement layer.

The "together" arm of the generator ablation. It combines the LLM's broad
structural coverage with the rules parser's reliable, prompt-grounded intent
extraction, then hardens the result with the enforcement layer:

1. Parse the raw prompt with the deterministic parser (clarification gate +
   trade-intent fields read straight from the text).
2. Ask the LLM for a candidate workflow (structural breadth).
3. Backstop the candidate with the rules generator: if the LLM emits no
   usable nodes, fall back to the rules structure; and backfill only the
   *trade-intent* config fields the rules parser read from the text but the
   LLM dropped (never fabricating intent neither source produced).
4. Apply the enforcement layer (structural repair + safety-policy injection).

Requires an API key; without one it raises :class:`BaselineSkipped`.
``KOAN_SAFE_ENFORCE=0`` disables enforcement for the ablation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from koan_safe_core import (  # noqa: E402
    build_result, parse_intent, synthesize_rules, intent_config,
)
from koan_safe_llm_baseline import _llm_candidate  # noqa: E402

# trade-intent config keys (safe to backfill from the rules parser because the
# parser read them from the same prompt; policy keys are handled by enforce()).
_INTENT_KEYS = ("fromToken", "toToken", "amount", "slippage", "targetPrice",
                "expiry", "sourceChain", "destinationChain")


def _merge(llm_wf: dict[str, Any], intent) -> dict[str, Any]:
    rules_wf = synthesize_rules(intent)
    llm_nodes = [n for n in (llm_wf.get("nodes") or [])]
    # If the LLM produced nothing usable, take the rules structure wholesale.
    nodes = llm_nodes or list(rules_wf["nodes"])
    edges = (llm_wf.get("edges") or []) if llm_nodes else rules_wf["edges"]

    config = dict(llm_wf.get("config") or {})
    parsed = intent_config(intent)
    for key in _INTENT_KEYS:
        if key not in config and key in parsed:
            config[key] = parsed[key]           # prompt-grounded backfill only
    return {"nodes": list(nodes), "edges": [list(e) for e in edges], "config": config}


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    intent = parse_intent(prompt["prompt"])
    if intent.decision == "clarify":
        return build_result(prompt, "koan_safe_hybrid", {}, intent,
                            extra={"generator": "hybrid", "model": None})
    llm_wf, meta = _llm_candidate(prompt)
    candidate = _merge(llm_wf, intent)
    return build_result(prompt, "koan_safe_hybrid", candidate, intent,
                        extra={"generator": "hybrid", "model": meta})
