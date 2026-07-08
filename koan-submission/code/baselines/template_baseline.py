"""Template baseline: fixed per-category workflow, no prompt parsing.

This baseline represents the "template-only" approach. Given the prompt
category, it emits the canonical structure for that category with static
safety-threshold defaults, but it does *not* parse the natural-language
prompt and therefore cannot populate trade-specific execution parameters
(amount, target price, destination chain, ...). It also never asks a
clarifying question.

This is deliberately honest: a category template is structurally strong
but executably empty, which is exactly the gap the benchmark measures.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))
from workflow_utils import derive_safety  # noqa: E402


TEMPLATES: dict[str, dict[str, Any]] = {
    "swap": {
        "nodes": ["walletConnector", "tokenSelector", "oneInchQuote",
                  "priceImpactCalculator", "oneInchSwap", "transactionMonitor"],
        # static, non-trade-specific defaults only
        "config": {"mode": "template", "warning_threshold": 3.0, "default_slippage": 1.0,
                   "default_confirmations": 1},
    },
    "limit_order": {
        "nodes": ["walletConnector", "tokenSelector", "limitOrder", "transactionMonitor"],
        "config": {"mode": "template", "default_confirmations": 1},
    },
    "cross_chain": {
        "nodes": ["walletConnector", "chainSelector", "tokenSelector",
                  "fusionPlus", "transactionMonitor"],
        "config": {"mode": "template", "default_confirmations": 3, "min_confirmations": 3},
    },
    "compositional": {
        "nodes": ["walletConnector", "tokenSelector", "oneInchQuote",
                  "priceImpactCalculator", "oneInchSwap", "limitOrder", "transactionMonitor"],
        "config": {"mode": "template", "warning_threshold": 3.0, "default_slippage": 1.0,
                   "default_confirmations": 1},
    },
}


def _edges(nodes: list[str]) -> list[list[str]]:
    return [[nodes[i], nodes[i + 1]] for i in range(len(nodes) - 1)]


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    template = TEMPLATES[prompt["category"]]
    nodes = list(template["nodes"])
    config = dict(template["config"])
    safety = derive_safety(nodes, config)
    return {
        "id": prompt["id"],
        "baseline": "template",
        "category": prompt["category"],
        "status": "ok",
        "error": None,
        "workflow": {
            "nodes": nodes,
            "edges": _edges(nodes),
            "config": config,
            "safety": safety,
        },
    }
