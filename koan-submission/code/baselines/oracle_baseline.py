"""Oracle baseline: emits a correct workflow reconstructed from the gold.

This is the benchmark *ceiling* (ABC guideline T.9 / R.13): a reference
"solver" whose output should score 1.0 on every layer for every workflow
prompt, and correctly ask for clarification on every clarification prompt.
Its purpose is not to be a competitor but to **prove the tasks are solvable**
and that the scoring pipeline actually rewards a fully correct solution --
without an oracle at 1.0, a low score for real systems could be an artifact
of an impossible task or a broken scorer.

The oracle reads the gold record (required nodes/edges, required config
keys, required safety predicates) and synthesizes a concrete workflow:

- nodes/edges: exactly the required set;
- config: a concrete, non-placeholder value for every required key, plus the
  threshold/parameter values that ``derive_safety`` needs to *declare* each
  required safety predicate;
- safety: derived by the same uniform ``derive_safety`` used for all
  baselines (never self-reported), so the oracle is judged by the identical
  rule.

For clarification prompts the oracle returns ``needs_clarification`` with no
workflow, which is the correct behavior on that axis.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))
from workflow_utils import derive_safety  # noqa: E402


# Concrete filler values for required config keys. These are deliberately
# generic but non-placeholder so ``_config_satisfied`` counts them.
_CONFIG_FILL: dict[str, Any] = {
    "fromToken": "USDC",
    "toToken": "ETH",
    "amount": "100",
    "slippage": "1%",
    "targetPrice": "3000",
    "expiry": "7d",
    "sourceChain": "ethereum",
    "destinationChain": "polygon",
    "destinationAddress": "0x1111111111111111111111111111111111111111",
}

# Extra config a correct system sets so that ``derive_safety`` *declares*
# each safety predicate. Keyed by predicate name.
_SAFETY_CONFIG: dict[str, dict[str, Any]] = {
    "slippage_bound": {"slippage": "1%"},
    "price_impact_gate": {"warning_threshold": 3.0},
    "price_bound": {"targetPrice": "3000"},
    "expiry_set": {"expiry": "7d"},
    "destination_chain_check": {"sourceChain": "ethereum", "destinationChain": "polygon"},
    "bridge_confirmation": {"default_confirmations": 3},
    "transaction_monitoring": {},  # satisfied by the transactionMonitor node
}


def _edges_from_required(required_edges: list[list[str]]) -> list[list[str]]:
    return [list(e) for e in required_edges]


def generate(prompt: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    base = {
        "id": prompt["id"],
        "baseline": "oracle",
        "category": prompt["category"],
        "error": None,
    }

    if gold.get("expects_clarification"):
        return {
            **base,
            "status": "needs_clarification",
            "workflow": {"nodes": [], "edges": [], "config": {}, "safety": []},
        }

    nodes = list(gold["required_nodes"])
    edges = _edges_from_required(gold["required_edges"])

    config: dict[str, Any] = {}
    for key in gold.get("required_config", {}):
        config[key] = _CONFIG_FILL.get(key, "concrete_value")
    for predicate in gold.get("safety_requirements", []):
        config.update(_SAFETY_CONFIG.get(predicate, {}))

    # Ensure identical-chain gold (none in the workflow set) never sneaks in.
    if config.get("sourceChain") == config.get("destinationChain"):
        config["destinationChain"] = "polygon" if config.get("sourceChain") != "polygon" else "arbitrum"

    safety = derive_safety(nodes, config)
    return {
        **base,
        "status": "ok",
        "workflow": {"nodes": nodes, "edges": edges, "config": config, "safety": safety},
    }
