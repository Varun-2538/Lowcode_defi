"""Normalize a real Koan ``WorkflowDefinition`` into evaluator format.

Koan emits rich per-node objects with backend-specific config keys and
node-id-based edges. The evaluator works on *type-level* graphs plus a
flat execution config. This module performs a faithful, documented
translation:

- ``nodes``  : the ordered list of node *types*.
- ``edges``  : Koan's id-based edges re-expressed as type pairs.
- ``config`` : Koan's per-node configs merged, then a *fixed* set of
  Koan keys mapped to the evaluator's execution-config vocabulary. Only
  values Koan genuinely determines are surfaced; trade-specific values
  Koan does not parse (fromToken/toToken/amount/targetPrice/...) are left
  absent rather than fabricated.

The mapping is intentionally charitable: where Koan sets a concrete value
(even a wrong one, e.g. an identical destination chain), we surface it so
the safety layer, not this adapter, decides whether it is acceptable.
"""

from __future__ import annotations

from typing import Any


# inverse of WorkflowGenerator's chain_mapping
_CHAIN_ID_TO_NAME = {
    1: "ethereum",
    137: "polygon",
    42161: "arbitrum",
    10: "optimism",
    56: "bsc",
    43114: "avalanche",
}


def _chain_name(value: Any) -> Any:
    if isinstance(value, list) and value:
        value = value[0]
    if isinstance(value, int):
        return _CHAIN_ID_TO_NAME.get(value, value)
    return value


def normalize_workflow(raw: dict[str, Any]) -> dict[str, Any]:
    raw_nodes = raw.get("nodes", [])
    raw_edges = raw.get("edges", [])

    id_to_type: dict[str, str] = {}
    node_types: list[str] = []
    merged: dict[str, Any] = {}

    for node in raw_nodes:
        node_type = node.get("type")
        node_id = node.get("id", node_type)
        id_to_type[node_id] = node_type
        node_types.append(node_type)
        config = (node.get("data") or {}).get("config") or node.get("config") or {}
        for key, value in config.items():
            # first-writer wins is fine; keys are consistent across nodes
            merged.setdefault(key, value)
        # per-node keys that matter for chain resolution
        if node_type == "fusionPlus":
            if "supported_source_chains" in config:
                merged["__source_chain"] = config["supported_source_chains"]
            if "supported_destination_chains" in config:
                merged["__destination_chain"] = config["supported_destination_chains"]
        if node_type == "chainSelector" and "default_chain" in config:
            merged.setdefault("__source_chain", config["default_chain"])

    edges: list[list[str]] = []
    for edge in raw_edges:
        src = id_to_type.get(edge.get("source"))
        dst = id_to_type.get(edge.get("target"))
        if src and dst:
            edges.append([src, dst])

    # Translate Koan config -> evaluator execution config (documented subset)
    config: dict[str, Any] = {}
    if "default_slippage" in merged:
        config["slippage"] = merged["default_slippage"]
    elif "max_slippage" in merged:
        config["slippage"] = merged["max_slippage"]
    if "warning_threshold" in merged:
        config["warning_threshold"] = merged["warning_threshold"]
    if "max_impact_threshold" in merged:
        config["max_impact_threshold"] = merged["max_impact_threshold"]
    if "default_confirmations" in merged:
        config["default_confirmations"] = merged["default_confirmations"]
    if "min_confirmations" in merged:
        config["min_confirmations"] = merged["min_confirmations"]
    if "default_expiration_days" in merged:
        config["expiry"] = merged["default_expiration_days"]
    if "__source_chain" in merged:
        config["sourceChain"] = _chain_name(merged["__source_chain"])
    if "__destination_chain" in merged:
        config["destinationChain"] = _chain_name(merged["__destination_chain"])

    return {
        "nodes": node_types,
        "edges": edges,
        "config": config,
    }
