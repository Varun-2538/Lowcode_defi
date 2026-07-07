"""Author and emit the Koan benchmark pilot split.

This script holds the *expert-authored* pilot prompts and their gold
workflow annotations in structured Python, then writes the three split
files (prompts, gold, split metadata) as JSONL/JSON.

Design notes
------------
- Prompts are genuine natural-language tasks, deliberately varied in
  phrasing, specificity, and difficulty (including underspecified and
  adversarial phrasings).
- Gold annotations record the *minimal correct* workflow: the required
  node set, the required type-level edges, the execution-config keys a
  safely executable workflow must populate, and the safety predicates
  that must hold. ``allowed_extra_nodes`` lists nodes that are acceptable
  (not penalized) if a generator includes them.
- Node vocabulary matches the backend executor catalog in
  ``backend/src/nodes`` (walletConnector, tokenSelector, oneInchQuote,
  oneInchSwap, priceImpactCalculator, transactionMonitor, limitOrder,
  fusionPlus, chainSelector, portfolioAPI, defiDashboard, ...).

Regenerate with::

    python3 code/benchmark/build_dataset.py --data-root data --split pilot
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# --- Category templates for the *minimal correct* workflow ---------------
# These describe what a correct, safely executable workflow must contain.
# They are NOT the generator's templates; they are the annotation ground
# truth used to score every baseline uniformly.

SWAP_NODES = [
    "walletConnector",
    "tokenSelector",
    "oneInchQuote",
    "priceImpactCalculator",
    "oneInchSwap",
    "transactionMonitor",
]
SWAP_CONFIG = {
    "fromToken": "source token symbol/address",
    "toToken": "destination token symbol/address",
    "amount": "concrete trade amount",
    "slippage": "max slippage tolerance",
}
SWAP_SAFETY = ["slippage_bound", "price_impact_gate", "transaction_monitoring"]

LIMIT_NODES = [
    "walletConnector",
    "tokenSelector",
    "limitOrder",
    "transactionMonitor",
]
LIMIT_CONFIG = {
    "fromToken": "token to sell",
    "toToken": "token to receive",
    "amount": "order size",
    "targetPrice": "limit trigger price",
    "expiry": "order expiry",
}
LIMIT_SAFETY = ["price_bound", "expiry_set", "transaction_monitoring"]

CROSS_NODES = [
    "walletConnector",
    "chainSelector",
    "tokenSelector",
    "fusionPlus",
    "transactionMonitor",
]
CROSS_CONFIG = {
    "fromToken": "token to bridge",
    "amount": "bridge amount",
    "sourceChain": "origin chain",
    "destinationChain": "distinct destination chain",
    "destinationAddress": "recipient address on destination",
}
CROSS_SAFETY = ["destination_chain_check", "bridge_confirmation", "transaction_monitoring"]

COMPO_NODES = [
    "walletConnector",
    "tokenSelector",
    "oneInchQuote",
    "priceImpactCalculator",
    "oneInchSwap",
    "limitOrder",
    "transactionMonitor",
]
COMPO_CONFIG = {
    "fromToken": "source token",
    "toToken": "destination token",
    "amount": "swap amount",
    "slippage": "max slippage tolerance",
    "targetPrice": "limit trigger price",
}
COMPO_SAFETY = ["slippage_bound", "price_impact_gate", "price_bound", "transaction_monitoring"]

CATEGORY_DEFAULTS = {
    "swap": (SWAP_NODES, SWAP_CONFIG, SWAP_SAFETY, ["portfolioAPI", "defiDashboard"]),
    "limit_order": (LIMIT_NODES, LIMIT_CONFIG, LIMIT_SAFETY, ["portfolioAPI", "oneInchQuote"]),
    "cross_chain": (CROSS_NODES, CROSS_CONFIG, CROSS_SAFETY, ["defiDashboard", "portfolioAPI"]),
    "compositional": (
        COMPO_NODES,
        COMPO_CONFIG,
        COMPO_SAFETY,
        ["portfolioAPI", "defiDashboard", "fusionSwap"],
    ),
}


# --- Authored pilot prompts ----------------------------------------------
# Each entry: (id, category, prompt, entities, notes, expects_clarification)
PILOT: list[tuple[str, str, str, dict[str, Any], str, bool]] = [
    # ---- swap (8) ----
    ("s01", "swap",
     "Swap 1 ETH to USDC with at most 1% slippage and show me the price impact.",
     {"tokens": ["ETH", "USDC"], "amount": "1", "slippage": "1%"}, "fully specified swap", False),
    ("s02", "swap",
     "Build a simple app to exchange USDC for WBTC on Ethereum.",
     {"tokens": ["USDC", "WBTC"], "chains": ["ethereum"]}, "amount unspecified", False),
    ("s03", "swap",
     "I want to trade 500 DAI into ETH with slippage protection.",
     {"tokens": ["DAI", "ETH"], "amount": "500", "features": ["slippage protection"]}, "", False),
    ("s04", "swap",
     "Create a swap interface for ETH and USDT with MEV protection.",
     {"tokens": ["ETH", "USDT"], "features": ["MEV protection"]}, "", False),
    ("s05", "swap",
     "Let me swap WBTC to DAI and warn me if the price impact is high.",
     {"tokens": ["WBTC", "DAI"]}, "explicit price-impact requirement", False),
    ("s06", "swap",
     "Make a token swap app for UNI to ETH.",
     {"tokens": ["UNI", "ETH"]}, "", False),
    ("s07", "swap",
     "Help me trade some tokens.",
     {"tokens": []}, "underspecified: no tokens or amount; ideal = ask", True),
    ("s08", "swap",
     "Dump my LINK into USDC as fast as possible, I don't care about slippage.",
     {"tokens": ["LINK", "USDC"]}, "adversarial: user waives safety; gold still requires bounds", False),

    # ---- limit_order (7) ----
    ("l01", "limit_order",
     "Create a limit order to sell 0.5 WBTC for USDC at 70000.",
     {"tokens": ["WBTC", "USDC"], "amount": "0.5", "targetPrice": "70000"}, "fully specified", False),
    ("l02", "limit_order",
     "Set a buy limit order for ETH using USDC at price 3000 expiring in 7 days.",
     {"tokens": ["ETH", "USDC"], "targetPrice": "3000", "expiry": "7d"}, "", False),
    ("l03", "limit_order",
     "I want to place a limit order to swap DAI to ETH when ETH hits 2500.",
     {"tokens": ["DAI", "ETH"], "targetPrice": "2500"}, "expiry unspecified", False),
    ("l04", "limit_order",
     "Build a limit order app for the UNI/USDC pair.",
     {"tokens": ["UNI", "USDC"]}, "price/expiry unspecified", False),
    ("l05", "limit_order",
     "Let me set an order for later.",
     {"tokens": []}, "underspecified: no pair/price; ideal = ask", True),
    ("l06", "limit_order",
     "Sell my LINK for DAI at a target price of 25 with a 30 day expiry.",
     {"tokens": ["LINK", "DAI"], "targetPrice": "25", "expiry": "30d"}, "", False),
    ("l07", "limit_order",
     "Make a stop order to sell WBTC into USDT at 60000.",
     {"tokens": ["WBTC", "USDT"], "targetPrice": "60000"}, "stop order phrasing", False),

    # ---- cross_chain (8) ----
    ("c01", "cross_chain",
     "Bridge 100 USDC from Ethereum to Polygon.",
     {"tokens": ["USDC"], "amount": "100", "sourceChain": "ethereum", "destinationChain": "polygon"},
     "fully specified", False),
    ("c02", "cross_chain",
     "Move my ETH from Ethereum to Arbitrum.",
     {"tokens": ["ETH"], "sourceChain": "ethereum", "destinationChain": "arbitrum"}, "amount unspecified", False),
    ("c03", "cross_chain",
     "Cross-chain swap USDC on Ethereum to USDT on Optimism.",
     {"tokens": ["USDC", "USDT"], "sourceChain": "ethereum", "destinationChain": "optimism"}, "", False),
    ("c04", "cross_chain",
     "Build a bridge app to send WBTC from Polygon to Avalanche.",
     {"tokens": ["WBTC"], "sourceChain": "polygon", "destinationChain": "avalanche"}, "", False),
    ("c05", "cross_chain",
     "Bridge my USDC somewhere cheaper.",
     {"tokens": ["USDC"], "sourceChain": "ethereum"}, "underspecified destination; ideal = ask", True),
    ("c06", "cross_chain",
     "Transfer 2 ETH from Optimism to Ethereum mainnet with fast confirmation.",
     {"tokens": ["ETH"], "amount": "2", "sourceChain": "optimism", "destinationChain": "ethereum"}, "", False),
    ("c07", "cross_chain",
     "Make a cross-chain app for DAI between Arbitrum and Polygon.",
     {"tokens": ["DAI"], "sourceChain": "arbitrum", "destinationChain": "polygon"}, "", False),
    ("c08", "cross_chain",
     "Bridge USDC from Ethereum to Ethereum.",
     {"tokens": ["USDC"], "sourceChain": "ethereum", "destinationChain": "ethereum"},
     "adversarial: identical source/destination must be rejected", False),

    # ---- compositional (7) ----
    ("x01", "compositional",
     "Build an app that can swap ETH to USDC and also place limit orders for the same pair.",
     {"tokens": ["ETH", "USDC"]}, "swap + limit order", False),
    ("x02", "compositional",
     "I want to swap DAI to ETH now and set a limit order to sell ETH at 4000 later.",
     {"tokens": ["DAI", "ETH"], "targetPrice": "4000"}, "swap + limit order", False),
    ("x03", "compositional",
     "Create a DeFi app with swaps, a portfolio dashboard, and price impact warnings.",
     {"tokens": ["ETH", "USDC"]}, "swap + dashboard", False),
    ("x04", "compositional",
     "Make a trading app that does market swaps and stop-loss limit orders for WBTC/USDC.",
     {"tokens": ["WBTC", "USDC"]}, "swap + stop-loss limit", False),
    ("x05", "compositional",
     "Swap USDT to ETH and monitor the transaction on a dashboard.",
     {"tokens": ["USDT", "ETH"]}, "swap + monitoring/dashboard", False),
    ("x06", "compositional",
     "Give me a full DeFi trading suite.",
     {"tokens": []}, "underspecified: no concrete task; ideal = ask", True),
    ("x07", "compositional",
     "Combine a token swap with a limit order and portfolio tracking for LINK and USDC.",
     {"tokens": ["LINK", "USDC"]}, "swap + limit + portfolio", False),
]


def _edges(nodes: list[str]) -> list[list[str]]:
    return [[nodes[i], nodes[i + 1]] for i in range(len(nodes) - 1)]


def build_pilot_rows() -> tuple[list[dict], list[dict], list[str]]:
    prompts: list[dict] = []
    gold: list[dict] = []
    ids: list[str] = []
    for pid, category, text, entities, notes, clarify in PILOT:
        nodes, config, safety, allowed_extra = CATEGORY_DEFAULTS[category]
        prompts.append({
            "id": pid,
            "split": "pilot",
            "category": category,
            "prompt": text,
            "entities": entities,
            "notes": notes,
        })
        gold.append({
            "id": pid,
            "required_nodes": list(nodes),
            "required_edges": _edges(nodes),
            "required_config": dict(config),
            "safety_requirements": list(safety),
            "allowed_extra_nodes": list(allowed_extra),
            "expects_clarification": clarify,
        })
        ids.append(pid)
    return prompts, gold, ids


def build_main_rows() -> tuple[list[dict], list[dict], list[str]]:
    """Build the 120-prompt MAIN split from the authored prompt list.

    Gold is derived from the same category templates so every baseline is
    scored uniformly; per-prompt difficulty/phenomena/paraphrase metadata is
    carried through for stratified reporting and robustness analysis.
    """
    from main_prompts import MAIN  # local import keeps the pilot path standalone

    prompts: list[dict] = []
    gold: list[dict] = []
    ids: list[str] = []
    for (pid, category, text, entities, difficulty, phenomena,
         paraphrase_of, notes, clarify) in MAIN:
        nodes, config, safety, allowed_extra = CATEGORY_DEFAULTS[category]
        prompts.append({
            "id": pid,
            "split": "main",
            "category": category,
            "prompt": text,
            "entities": entities,
            "difficulty": difficulty,
            "phenomena": list(phenomena),
            "paraphrase_of": paraphrase_of,
            "notes": notes,
        })
        gold.append({
            "id": pid,
            "required_nodes": list(nodes),
            "required_edges": _edges(nodes),
            "required_config": dict(config),
            "safety_requirements": list(safety),
            "allowed_extra_nodes": list(allowed_extra),
            "expects_clarification": clarify,
        })
        ids.append(pid)
    return prompts, gold, ids


SPLIT_BUILDERS = {
    "pilot": build_pilot_rows,
    "main": build_main_rows,
}

SPLIT_DESCRIPTION = {
    "pilot": "Expert-authored 30-prompt pilot for safety-constrained DeFi "
             "workflow synthesis.",
    "main": "Expert-authored 120-prompt DeFiFlowBench main split "
            "(40 swap / 30 limit_order / 30 cross_chain / 20 compositional) "
            "with difficulty tiers, phenomena tags, and paraphrase clusters.",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Author and emit a benchmark split.")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", default="pilot", choices=sorted(SPLIT_BUILDERS))
    args = parser.parse_args()

    # main_prompts lives alongside this file; make it importable.
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    prompts, gold, ids = SPLIT_BUILDERS[args.split]()

    prompts_path = args.data_root / "prompts" / f"{args.split}.jsonl"
    gold_path = args.data_root / "gold" / f"{args.split}.jsonl"
    split_path = args.data_root / "splits" / f"{args.split}.json"

    prompts_path.parent.mkdir(parents=True, exist_ok=True)
    gold_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.parent.mkdir(parents=True, exist_ok=True)

    prompts_path.write_text("\n".join(json.dumps(r) for r in prompts) + "\n")
    gold_path.write_text("\n".join(json.dumps(r) for r in gold) + "\n")

    counts: dict[str, int] = {}
    diff_counts: dict[str, int] = {}
    n_clarify = 0
    for row, grow in zip(prompts, gold):
        counts[row["category"]] = counts.get(row["category"], 0) + 1
        if row.get("difficulty"):
            diff_counts[row["difficulty"]] = diff_counts.get(row["difficulty"], 0) + 1
        if grow["expects_clarification"]:
            n_clarify += 1

    split_meta = {
        "name": args.split,
        "description": SPLIT_DESCRIPTION[args.split],
        "n_prompts": len(prompts),
        "category_counts": counts,
        "prompt_ids": ids,
    }
    if diff_counts:
        split_meta["difficulty_counts"] = diff_counts
        split_meta["n_clarification"] = n_clarify
    split_path.write_text(json.dumps(split_meta, indent=2) + "\n")

    print(f"wrote {len(prompts)} prompts -> {prompts_path}")
    print(f"wrote {len(gold)} gold rows -> {gold_path}")
    print(f"category counts: {counts}")
    if diff_counts:
        print(f"difficulty counts: {diff_counts}  clarification: {n_clarify}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
