"""Shared helpers for LLM baselines.

Both LLM baselines are *real* but *optional*: if no API key is
configured they raise :class:`BaselineSkipped`, which the runner records
as a skipped run (never silently dropped, never fabricated). All model
metadata (provider, model, temperature) is returned with each run for
reproducibility.

Provider is selected via env:
- ``OPENROUTER_API_KEY`` -> OpenRouter (OpenAI-compatible) chat completions
  (``KOAN_LLM_MODEL`` or openai/gpt-4o-mini)
- ``ANTHROPIC_API_KEY`` -> Anthropic messages (``KOAN_LLM_MODEL`` or claude-3-5-sonnet-latest)
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))
from workflow_utils import derive_safety  # noqa: E402


NODE_VOCAB = [
    "walletConnector", "tokenSelector", "chainSelector", "oneInchQuote",
    "oneInchSwap", "priceImpactCalculator", "transactionMonitor",
    "limitOrder", "fusionPlus", "fusionSwap", "portfolioAPI", "defiDashboard",
]

CONFIG_VOCAB = [
    "fromToken", "toToken", "amount", "slippage", "targetPrice", "expiry",
    "sourceChain", "destinationChain", "destinationAddress",
    "warning_threshold", "default_confirmations",
]


class BaselineSkipped(RuntimeError):
    """Raised when an LLM baseline cannot run (e.g. no API key)."""


def _provider() -> tuple[str, str] | None:
    model = os.environ.get("KOAN_LLM_MODEL")
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter", model or "openai/gpt-4o-mini"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic", model or "claude-3-5-sonnet-latest"
    return None


# A single worked example used by the few-shot ablation. It is deliberately
# for a swap (the most common category) and demonstrates the exact output
# contract, including a populated config and a needs_clarification=false flag.
_FEWSHOT_EXAMPLE = (
    "Example request: Swap 1 ETH to USDC with at most 1% slippage and show "
    "the price impact.\n"
    "Example JSON: {\"nodes\": [\"walletConnector\", \"tokenSelector\", "
    "\"oneInchQuote\", \"priceImpactCalculator\", \"oneInchSwap\", "
    "\"transactionMonitor\"], \"edges\": [[\"walletConnector\", "
    "\"tokenSelector\"], [\"tokenSelector\", \"oneInchQuote\"], "
    "[\"oneInchQuote\", \"priceImpactCalculator\"], [\"priceImpactCalculator\", "
    "\"oneInchSwap\"], [\"oneInchSwap\", \"transactionMonitor\"]], \"config\": "
    "{\"fromToken\": \"ETH\", \"toToken\": \"USDC\", \"amount\": \"1\", "
    "\"slippage\": \"1%\", \"warning_threshold\": 3}, "
    "\"needs_clarification\": false}\n"
)

# The safety-instruction ablation: an explicit directive to make the workflow
# safe to execute. This tests whether simply *asking* for safety closes the
# structural-vs-safe gap.
_SAFETY_INSTRUCTION = (
    "Safety requirement: the workflow must be SAFE TO EXECUTE, not just "
    "structurally plausible. For any swap, set a concrete slippage bound AND "
    "include priceImpactCalculator with a concrete warning_threshold so a "
    "large-impact trade is gated (a slippage bound alone does not stop "
    "own-trade price impact). For any limit order, set a concrete targetPrice "
    "and expiry. For any bridge, set distinct sourceChain and destinationChain "
    "and a confirmation count. Always include transactionMonitor.\n"
)


def build_prompt(prompt: dict[str, Any], constrained: bool,
                 fewshot: bool = False, safety: bool = False) -> str:
    nodes = ", ".join(NODE_VOCAB)
    keys = ", ".join(CONFIG_VOCAB)
    base = (
        "You convert a DeFi request into a workflow graph.\n"
        f"Allowed node types: {nodes}.\n"
        f"Allowed config keys: {keys}.\n"
        "Return ONLY JSON: {\"nodes\": [types...], \"edges\": [[src,dst]...], "
        "\"config\": {key: value...}, \"needs_clarification\": bool}.\n"
        "Each edge is a pair of node TYPE strings from your nodes list "
        "(e.g. [\"tokenSelector\",\"oneInchSwap\"]), not indices.\n"
        "Only populate config values you can extract from the request; "
        "do not invent amounts, prices, or chains that are not stated.\n"
        "If the request is too vague to build a concrete workflow, set "
        "needs_clarification=true and return empty nodes.\n"
    )
    if constrained:
        base += (
            "Constraints: a swap must include priceImpactCalculator and "
            "transactionMonitor; a cross-chain bridge must include "
            "chainSelector and distinct sourceChain/destinationChain; a "
            "limit order must include a concrete targetPrice.\n"
        )
    if safety:
        base += _SAFETY_INSTRUCTION
    if fewshot:
        base += "\n" + _FEWSHOT_EXAMPLE
    return base + f"\nRequest: {prompt['prompt']}\n"


def _call_openrouter(model: str, content: str, temperature: float) -> str:
    # OpenRouter is OpenAI-compatible; point the OpenAI client at its base URL.
    from openai import OpenAI  # noqa: E402
    client = OpenAI(
        base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[{"role": "user", "content": content}],
    )
    return resp.choices[0].message.content or ""


def _call_anthropic(model: str, content: str, temperature: float) -> str:
    import anthropic  # noqa: E402
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=1024,
        temperature=temperature,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError(f"no JSON in model output: {text[:200]}")
    return json.loads(match.group(0))


def _normalize_edges(raw_edges: Any, raw_nodes: list[Any]) -> list[list[str]]:
    """Accept edges as node-type pairs or as integer index pairs.

    Some models emit ``[[0,1],...]`` (indices into the node list) instead of
    ``[["tokenSelector","oneInchSwap"],...]``. Both are resolved to
    node-type pairs, then filtered to endpoints in the allowed vocabulary.
    """
    out: list[list[str]] = []
    for edge in raw_edges or []:
        if not isinstance(edge, list) or len(edge) != 2:
            continue
        resolved: list[str] = []
        for endpoint in edge:
            if isinstance(endpoint, bool):
                break
            if isinstance(endpoint, int) and 0 <= endpoint < len(raw_nodes):
                resolved.append(str(raw_nodes[endpoint]))
            elif isinstance(endpoint, str):
                resolved.append(endpoint)
            else:
                break
        if len(resolved) == 2 and all(v in NODE_VOCAB for v in resolved):
            out.append(resolved)
    return out


def run_llm_baseline(prompt: dict[str, Any], name: str, constrained: bool,
                     fewshot: bool = False, safety: bool = False) -> dict[str, Any]:
    provider = _provider()
    if provider is None:
        raise BaselineSkipped("no OPENROUTER_API_KEY or ANTHROPIC_API_KEY set")
    provider_name, model = provider
    temperature = 0.0

    content = build_prompt(prompt, constrained, fewshot=fewshot, safety=safety)
    if provider_name == "openrouter":
        raw_text = _call_openrouter(model, content, temperature)
    else:
        raw_text = _call_anthropic(model, content, temperature)

    workflow, status = parse_model_output(raw_text)

    return {
        "id": prompt["id"],
        "baseline": name,
        "category": prompt["category"],
        "status": status,
        "error": None,
        "model": {"provider": provider_name, "model": model, "temperature": temperature},
        "raw_output": raw_text,
        "workflow": workflow,
    }


def parse_model_output(raw_text: str) -> tuple[dict[str, Any], str]:
    """Turn a model's JSON text into a normalized workflow + status.

    Deterministic and provider-agnostic: node/edge/config normalization and
    safety derivation live here so the same logic can (re)score a live call
    or a previously saved ``raw_output`` without new API calls.
    """
    data = _extract_json(raw_text)
    raw_nodes = list(data.get("nodes", []))
    nodes = [n for n in raw_nodes if n in NODE_VOCAB]
    edges = _normalize_edges(data.get("edges", []), raw_nodes)
    config = {k: v for k, v in (data.get("config", {}) or {}).items()}
    needs_clarification = bool(data.get("needs_clarification", False)) or not nodes
    status = "needs_clarification" if needs_clarification else "ok"
    safety = derive_safety(nodes, config)
    return {"nodes": nodes, "edges": edges, "config": config, "safety": safety}, status
