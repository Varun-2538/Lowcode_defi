"""Shared helpers for baselines: config concreteness and safety derivation.

All baselines emit a normalized workflow::

    {"nodes": [...types...], "edges": [[a, b], ...], "config": {...}}

Safety predicates are *derived* from that normalized workflow with a
single uniform function so every system is judged by the same rule. A
predicate is only declared when the underlying evidence is concrete (a
node is present *and* the relevant config value is a real value, not a
template placeholder). This encodes the paper's distinction between
"a node exists" and "a safety constraint is actually parameterized".

Note: derivation captures *declared / statically-parameterized* safety.
Runtime enforcement (e.g. a price-impact abort actually gating a swap)
is out of scope for the pilot and belongs to the fork-simulation layer.
"""

from __future__ import annotations

from typing import Any


_PLACEHOLDERS = {"", None, "template", "template_creation_mode", "tbd", "todo", "any", "default"}


def is_concrete(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in _PLACEHOLDERS
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return value not in _PLACEHOLDERS


def concrete_config(config: dict[str, Any], key: str) -> bool:
    return key in config and is_concrete(config[key])


def derive_safety(nodes: list[str], config: dict[str, Any]) -> list[str]:
    """Derive the set of *declared* safety predicates from a workflow."""
    node_set = set(nodes)
    declared: list[str] = []

    # slippage bound: a concrete slippage tolerance is configured
    if concrete_config(config, "slippage") or concrete_config(config, "max_slippage") \
            or concrete_config(config, "default_slippage"):
        declared.append("slippage_bound")

    # price impact gate: calculator node present AND a threshold configured
    if "priceImpactCalculator" in node_set and (
        concrete_config(config, "warning_threshold")
        or concrete_config(config, "max_impact_threshold")
        or concrete_config(config, "price_impact_threshold")
    ):
        declared.append("price_impact_gate")

    # transaction monitoring: monitor node present
    if "transactionMonitor" in node_set:
        declared.append("transaction_monitoring")

    # price bound: limit order node present AND a concrete target price
    if "limitOrder" in node_set and concrete_config(config, "targetPrice"):
        declared.append("price_bound")

    # expiry set: a concrete expiry configured
    if concrete_config(config, "expiry") or concrete_config(config, "default_expiration_days"):
        declared.append("expiry_set")

    # destination chain check: bridge present AND source/dest concrete AND distinct
    if ("fusionPlus" in node_set or "chainSelector" in node_set):
        src = config.get("sourceChain")
        dst = config.get("destinationChain")
        if is_concrete(src) and is_concrete(dst) and str(src).lower() != str(dst).lower():
            declared.append("destination_chain_check")

    # bridge confirmation: cross-chain monitoring with confirmations configured
    if "fusionPlus" in node_set and "transactionMonitor" in node_set and (
        concrete_config(config, "default_confirmations")
        or concrete_config(config, "min_confirmations")
    ):
        declared.append("bridge_confirmation")

    return declared
