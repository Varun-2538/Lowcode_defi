"""Koan-Safe: intent parser + generator-agnostic safety-enforcement layer.

This module is the paper's *proposed method*. It is built to the benchmark's
failure taxonomy, not to the gold labels. Two hard integrity rules are
enforced in code and stated as threats-to-validity in the paper:

1. **Prompt-only input.** Every public entry point receives only
   ``prompt["prompt"]`` (raw text). The gold record, the ``category`` label,
   and the pre-parsed ``entities`` are never read. Koan-Safe therefore has
   exactly the same information as the LLM baselines.

2. **No fabricated trade intent.** The enforcement layer may inject *safety
   policy* (a default slippage bound, a price-impact gate + threshold, a
   bridge confirmation count, a default order expiry, a self-recipient for a
   bridge) because those are conservative defaults a safety-aware system is
   entitled to ship. It never invents *trade intent* it cannot read from the
   text -- tokens, amounts, target prices, or chains. When intent is missing
   the workflow is left structurally valid but not executable (honest), or,
   when the request is too vague to act on at all, Koan-Safe asks for
   clarification instead of guessing.

The design separates three concerns so they can be ablated independently:

* ``parse_intent``  -- text -> a typed :class:`Intent` (the parser).
* ``synthesize_rules`` / an LLM / hybrid -- intent (or text) -> a candidate
  workflow (the *generator*, swappable).
* ``enforce``       -- candidate workflow + intent -> repaired, safety-hardened
  workflow (the *enforcement layer*, the core contribution).

The enforcement layer is what closes the structural-vs-safe gap, and the
on/off ablation (``KOAN_SAFE_ENFORCE=0``) is how we show that.
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))
from workflow_utils import derive_safety  # noqa: E402


# --- domain vocabulary ---------------------------------------------------
# Token symbols and chain names Koan-Safe recognises. This is engineered
# domain knowledge (a token dictionary), not gold access.
TOKENS = {
    "ETH", "WETH", "USDC", "USDT", "DAI", "WBTC", "LINK", "UNI", "MATIC",
    "CRV", "AAVE", "COMP", "SNX", "LDO", "ARB", "OP",
}
CHAINS = {
    "ethereum", "polygon", "arbitrum", "optimism", "avalanche", "bsc",
    "base", "zksync",
}
# Unambiguous chain names/aliases (no token collision). Every canonical chain
# name maps to itself so a literal "to Polygon" resolves.
CHAIN_ALIASES = {name: name for name in CHAINS}
CHAIN_ALIASES.update({
    "mainnet": "ethereum", "poly": "polygon", "avax": "avalanche",
    "binance": "bsc",
})
# Aliases that collide with a token symbol (ETH/MATIC/ARB/OP). These are only
# treated as chains inside an explicit cross-chain context, so "swap SNX into
# ETH" stays a swap while "bridge USDC eth to polygon" resolves the source.
AMBIGUOUS_CHAIN_ALIASES = {
    "eth": "ethereum", "matic": "polygon", "arb": "arbitrum", "op": "optimism",
}

# Spelled-out token names -> symbol (a token dictionary, not gold access).
TOKEN_ALIASES = {
    "ether": "ETH", "wrapped ether": "WETH", "wrapped bitcoin": "WBTC",
    "usd coin": "USDC", "tether": "USDT",
}
# Number words for amounts written in prose (e.g. "one hundred USDC").
NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "ten": "10", "fifty": "50", "hundred": "100", "thousand": "1000",
    "one hundred": "100", "two hundred": "200", "five hundred": "500",
}

# Safety-policy defaults injected by the enforcement layer (never intent).
DEFAULT_SLIPPAGE = "1%"
DEFAULT_IMPACT_THRESHOLD = 3          # percent; feeds priceImpactCalculator
DEFAULT_CONFIRMATIONS = 12
DEFAULT_EXPIRY = "7d"
SELF_RECIPIENT = "self"               # bridge recipient = sender's own address


# --- category structural presets (engineered, generator-side) ------------
# These mirror the node types a correct workflow needs. They are the *rules
# generator's* knowledge; they are deliberately NOT imported from the gold
# templates so the two can diverge (and so held-out structural variants can
# stress them).
SWAP_NODES = ["walletConnector", "tokenSelector", "oneInchQuote",
              "priceImpactCalculator", "oneInchSwap", "transactionMonitor"]
LIMIT_NODES = ["walletConnector", "tokenSelector", "limitOrder",
               "transactionMonitor"]
CROSS_NODES = ["walletConnector", "chainSelector", "tokenSelector",
               "fusionPlus", "transactionMonitor"]
COMPO_NODES = ["walletConnector", "tokenSelector", "oneInchQuote",
               "priceImpactCalculator", "oneInchSwap", "limitOrder",
               "transactionMonitor"]
CATEGORY_NODES = {
    "swap": SWAP_NODES, "limit_order": LIMIT_NODES,
    "cross_chain": CROSS_NODES, "compositional": COMPO_NODES,
}


@dataclass
class Intent:
    """Structured, text-derived request. Missing fields stay ``None``."""

    category: str
    from_token: str | None = None
    to_token: str | None = None
    amount: str | None = None
    slippage: str | None = None
    target_price: str | None = None
    expiry: str | None = None
    source_chain: str | None = None
    dest_chain: str | None = None
    tokens: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)   # e.g. portfolio, dashboard, gasless
    waiver: bool = False                                 # user tried to waive safety
    decision: str = "build"                              # build | clarify
    reason: str = ""


# --- parsing helpers -----------------------------------------------------

def _token_hits(text: str) -> list[str]:
    """All recognised token symbols in order of appearance (with repeats).

    Matches symbols (ETH, USDC, ...) and spelled-out names (ether, usd coin).
    """
    hits: list[tuple[int, str]] = []
    for m in re.finditer(r"[A-Za-z]{2,6}", text):
        sym = m.group(0).upper()
        if sym in TOKENS:
            hits.append((m.start(), sym))
    low = text.lower()
    for name, sym in TOKEN_ALIASES.items():
        start = low.find(name)
        if start >= 0:
            hits.append((start, sym))
    hits.sort()
    return [s for _, s in hits]


def _find_tokens(text: str) -> list[str]:
    """Return recognised token symbols in order of appearance (deduped)."""
    seen: list[str] = []
    for sym in _token_hits(text):
        if sym not in seen:
            seen.append(sym)
    return seen


def _find_amount(text: str) -> str | None:
    """First bare quantity (not a percent, not a price after 'at/@')."""
    # strip slippage/percent and price clauses so we don't grab those numbers
    cleaned = re.sub(r"\d+(?:\.\d+)?\s*%", " ", text)
    cleaned = re.sub(r"(?:at|@|hits?|climbs?|reaches?|price)\s*\$?\d[\d,]*(?:\.\d+)?",
                     " ", cleaned, flags=re.I)
    m = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\d%])", cleaned)
    if m:
        return m.group(1)
    # spelled-out amounts ("one hundred USDC", "two ETH")
    low = cleaned.lower()
    for phrase in sorted(NUMBER_WORDS, key=len, reverse=True):
        if re.search(rf"\b{phrase}\b", low):
            return NUMBER_WORDS[phrase]
    return None


def _find_slippage(text: str) -> str | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if m and re.search(r"slip|slippage|slipage", text, re.I):
        return f"{m.group(1)}%"
    # "1% slippage cap" / "at most 1%" without the literal word nearby
    m2 = re.search(r"(?:at most|max|within|under|cap(?:ped)? at)\s*(\d+(?:\.\d+)?)\s*%",
                   text, re.I)
    return f"{m2.group(1)}%" if m2 else None


def _is_waiver(text: str) -> bool:
    return bool(re.search(
        r"don'?t care about slippage|slippage doesn'?t matter|as fast as possible|"
        r"ignore slippage|no slippage|whatever the (?:price|cost)", text, re.I))


def _find_price(text: str) -> str | None:
    """A concrete execution/trigger price: a number after at/@/trigger/target
    that is NOT a percentage (so '1% slippage' is not read as a price)."""
    for m in re.finditer(
            r"(?:at|@|hits?|climbs? to|reaches?|drops? to|"
            r"trigger price(?:\s*of)?|target price(?:\s*of)?|price(?:\s*of)?)\s*"
            r"\$?(\d[\d,]*(?:\.\d+)?)", text, re.I):
        tail = text[m.end():m.end() + 1]
        if tail == "%":
            continue                        # a slippage/percent, not a price
        return m.group(1).replace(",", "")
    return None


def _find_expiry(text: str, is_limit: bool = False) -> str | None:
    """Parse an order expiry. In limit-order context a bare 'N days' is the
    expiry; otherwise an expiry keyword must be nearby."""
    # keyword-anchored: "expiring in 3 days", "30 day expiry", "good for 7 days"
    m = re.search(r"(?:expir\w*|exp\b|open|valid|good\s+for|good\s+til\w*)\D{0,12}?"
                  r"(\d+)\s*(day|days|d|week|weeks|w)\b", text, re.I)
    if not m:
        m = re.search(r"(\d+)\s*[- ]?(day|days|week|weeks)\s*(?:expir\w*|exp\b)", text, re.I)
    if not m and is_limit:
        # inside a limit order, a duration is the expiry
        m = re.search(r"(\d+)\s*(day|days|week|weeks)\b", text, re.I)
    if m:
        n = int(m.group(1))
        if m.group(2).lower().startswith("w"):
            n *= 7
        return f"{n}d"
    if re.search(r"two weeks", text, re.I):
        return "14d"
    if re.search(r"\ba week\b", text, re.I):
        return "7d"
    return None


def _chain_vocab(allow_ambiguous: bool) -> dict[str, str]:
    vocab = dict(CHAIN_ALIASES)
    if allow_ambiguous:
        vocab.update(AMBIGUOUS_CHAIN_ALIASES)
    return vocab


def _chain_mentions(text: str, allow_ambiguous: bool = False) -> list[tuple[int, str]]:
    """All chain-name mentions as (position, canonical) in text order."""
    low = text.lower()
    vocab = _chain_vocab(allow_ambiguous)
    hits: list[tuple[int, str]] = []
    for alias, canon in vocab.items():
        for m in re.finditer(rf"\b{re.escape(alias)}\b", low):
            hits.append((m.start(), canon))
    hits.sort()
    return hits


def _find_chains(text: str, allow_ambiguous: bool = False) -> tuple[str | None, str | None]:
    """Resolve (source, destination) chains from the request text.

    Destination is the chain named after the last 'to'; source is a chain
    named before it (or after 'from'/'on'). Only recognised chain names are
    used, so nothing is invented. Token-colliding aliases (ETH/MATIC/...) are
    considered only when ``allow_ambiguous`` is set (an explicit bridge).
    """
    low = text.lower()
    vocab = _chain_vocab(allow_ambiguous)
    mentions = _chain_mentions(text, allow_ambiguous)
    dst = None
    dst_pos = -1
    # destination = chain named after the last 'to'/'over to'/'onto'
    for m in re.finditer(r"\b(?:to|onto|into)\s+(?:the\s+)?([a-z]+)", low):
        canon = vocab.get(m.group(1))
        if canon:
            dst, dst_pos = canon, m.start()
    # "between X and Y" phrasing: X=source, Y=destination
    mb = re.search(r"between\s+([a-z]+)\s+and\s+([a-z]+)", low)
    if mb:
        s2, d2 = vocab.get(mb.group(1)), vocab.get(mb.group(2))
        if s2 and d2:
            return s2, d2
    # Fallback: no explicit 'to <chain>', but >=2 chain mentions -> first is
    # source, last is destination (covers "... on Optimism", "X ... Y").
    if dst is None and len(mentions) >= 2:
        dst, dst_pos = mentions[-1][1], mentions[-1][0]
    src = None
    if dst is not None:
        for pos, canon in mentions:
            if pos < dst_pos:
                src = canon                  # last chain before the destination
    if src is None:
        m3 = re.search(r"\b(?:from|on)\s+(?:the\s+)?([a-z]+)", low)
        if m3:
            src = vocab.get(m3.group(1))
    # identical source/destination is surfaced (not silently fixed) so the
    # decision layer can reject it.
    return src, dst


def _detect_features(text: str) -> list[str]:
    feats: list[str] = []
    if re.search(r"portfolio", text, re.I):
        feats.append("portfolio")
    if re.search(r"dashboard", text, re.I):
        feats.append("dashboard")
    if re.search(r"gasless|fusion|mev", text, re.I):
        feats.append("gasless")
    return feats


def _detect_category(text: str) -> str:
    low = text.lower()
    has_limit = bool(re.search(r"limit\s*(?:ord|sell|buy)|limt\s*ordr|stop[- ]?loss|"
                               r"stop\s*order|\blimit\b|when .* (?:hits?|climbs?|reaches?|"
                               r"drops?)|target price|trigger price", low))
    # A concrete execution price plus an order verb (and no market-swap word)
    # signals a limit order even without the literal "limit" keyword.
    if not has_limit and _find_price(text) is not None \
            and re.search(r"\b(order|sell|buy|dump)\b", low):
        has_limit = True
    # A bridge needs explicit cross-chain language or a resolved chain pair,
    # NOT merely a "from X to Y" token phrasing (which is a swap).
    has_bridge = bool(re.search(r"bridg|brige|cross[- ]?chain|another chain|across chains",
                                low))
    if not has_bridge and re.search(r"\b(move|transfer|send|get)\b", low):
        # a move/transfer is a bridge only if it names an *unambiguous* chain as
        # destination ("to Arbitrum"), not a token-colliding word ("into ETH").
        _, dst = _find_chains(text, allow_ambiguous=False)
        if dst is not None:
            has_bridge = True
    # market-swap signal: the literal verb "swap" or a general trade verb.
    explicit_swap = bool(re.search(r"\bswaps?\b|\bswp\b|market swap", low))
    swap_signal = explicit_swap or bool(re.search(
        r"\b(exchange|convert|trade)\b|dump|get rid of|sell .* for", low))
    has_dashboard = bool(re.search(r"dashboard|portfolio", low))
    # a coordinating conjunction signals two distinct capabilities in one app.
    conjunction = bool(re.search(r"\b(and|plus|also|then|combine|both)\b", low))

    # compositional = two capabilities combined (swap+limit or swap+dashboard),
    # or an explicit multi-tool "suite" request.
    if re.search(r"\bsuite\b|everything defi|all[- ]in[- ]one|full defi|"
                 r"everything in one|everything defi in one", low):
        return "compositional"
    # swap+limit compositional requires the literal market-swap verb, so a
    # limit order that merely says "sell X for Y" is not misread.
    if explicit_swap and has_limit and conjunction:
        return "compositional"
    if swap_signal and has_dashboard and conjunction and not has_bridge:
        return "compositional"
    if has_bridge:
        return "cross_chain"
    if has_limit:
        return "limit_order"
    return "swap"


def _order_pair(text: str, tokens: list[str]) -> tuple[str | None, str | None]:
    """Pick (from, to) using appearance order (``tokens`` is already ordered)."""
    if not tokens:
        return None, None
    if len(tokens) == 1:
        return tokens[0], None
    return tokens[0], tokens[1]


# --- the parser ----------------------------------------------------------

VAGUE = re.compile(
    r"help me (?:trade|swap)|trade some tokens|get rid of my tokens|"
    r"some tokens|full defi|everything defi|trading suite|order for later|"
    r"set up an order|certain price|move funds across chains|"
    r"tokens to another chain|another chain", re.I)


def parse_intent(text: str) -> Intent:
    """Parse raw request text into a typed :class:`Intent` (prompt-only)."""
    category = _detect_category(text)
    tokens = _find_tokens(text)
    raw_hits = _token_hits(text)  # keeps repeats: catches "ETH for ETH"
    intent = Intent(category=category, tokens=tokens)
    intent._raw_token_hits = raw_hits  # type: ignore[attr-defined]
    intent.features = _detect_features(text)
    intent.waiver = _is_waiver(text)

    if category in ("swap", "compositional"):
        intent.from_token, intent.to_token = _order_pair(text, tokens)
        intent.amount = _find_amount(text)
        intent.slippage = _find_slippage(text)
        if category == "compositional":
            intent.target_price = _find_price(text)
    elif category == "limit_order":
        intent.from_token, intent.to_token = _order_pair(text, tokens)
        intent.amount = _find_amount(text)
        intent.target_price = _find_price(text)
        intent.expiry = _find_expiry(text, is_limit=True)
    else:  # cross_chain
        intent.from_token = tokens[0] if tokens else None
        intent.amount = _find_amount(text)
        intent.source_chain, intent.dest_chain = _find_chains(text, allow_ambiguous=True)

    _decide(intent, text)
    return intent


def _decide(intent: Intent, text: str) -> None:
    """Set intent.decision to 'build' or 'clarify' with an honest reason.

    Clarify only when the request cannot be acted on without guessing trade
    intent: no recognisable token, an identical source/destination (a no-op
    the user surely did not mean), or a bridge with no destination. Everything
    else is built (possibly incompletely, which the executable layer catches).
    """
    raw_hits = getattr(intent, "_raw_token_hits", intent.tokens)
    # identical source/destination token (e.g. "swap ETH for ETH") -> reject
    if intent.category in ("swap", "compositional", "limit_order"):
        if len(raw_hits) >= 2 and len(set(raw_hits)) == 1 and \
                re.search(r"\b(for|to|into)\b", text, re.I):
            intent.decision, intent.reason = "clarify", "identical source/destination token"
            return
    # a request with a clear action verb but no concrete token is still
    # buildable structure if it names a category task (e.g. "a DeFi app with
    # swaps and a dashboard"); it is only a clarify when there is nothing to
    # act on at all.
    if not intent.tokens:
        actionable = re.search(r"swap|exchange|convert|trade|limit|bridge|"
                               r"dashboard|portfolio", text, re.I)
        if not actionable or VAGUE.search(text):
            intent.decision, intent.reason = "clarify", "no concrete task to act on"
            return
    if VAGUE.search(text) and (intent.amount is None and intent.target_price is None):
        intent.decision, intent.reason = "clarify", "request too vague to act on"
        return
    if intent.category == "cross_chain":
        if intent.dest_chain is None:
            intent.decision, intent.reason = "clarify", "bridge destination chain missing"
            return
        if intent.source_chain and intent.dest_chain and \
                intent.source_chain == intent.dest_chain:
            intent.decision, intent.reason = "clarify", "identical source/destination chain"
            return
    intent.decision = "build"


# --- intent -> execution config (intent-only, no safety policy here) ------

def intent_config(intent: Intent) -> dict[str, Any]:
    """Config values *read from the request* (never invented)."""
    cfg: dict[str, Any] = {}
    if intent.from_token:
        cfg["fromToken"] = intent.from_token
    if intent.to_token:
        cfg["toToken"] = intent.to_token
    if intent.amount:
        cfg["amount"] = intent.amount
    if intent.slippage:
        cfg["slippage"] = intent.slippage
    if intent.target_price:
        cfg["targetPrice"] = intent.target_price
    if intent.expiry:
        cfg["expiry"] = intent.expiry
    if intent.source_chain:
        cfg["sourceChain"] = intent.source_chain
    if intent.dest_chain:
        cfg["destinationChain"] = intent.dest_chain
    return cfg


# --- rules generator -----------------------------------------------------

def _edges(nodes: list[str]) -> list[list[str]]:
    return [[nodes[i], nodes[i + 1]] for i in range(len(nodes) - 1)]


def synthesize_rules(intent: Intent) -> dict[str, Any]:
    """Deterministic rule-based generator: intent -> candidate workflow."""
    nodes = list(CATEGORY_NODES[intent.category])
    # modest, honest feature adaptation (real NLU, not gold lookup)
    if "portfolio" in intent.features and "portfolioAPI" not in nodes:
        nodes.append("portfolioAPI")
    if "dashboard" in intent.features and "defiDashboard" not in nodes:
        nodes.append("defiDashboard")
    if "gasless" in intent.features and intent.category == "swap" \
            and "fusionSwap" not in nodes:
        nodes.append("fusionSwap")
    return {
        "nodes": nodes,
        "edges": _edges(CATEGORY_NODES[intent.category]),
        "config": intent_config(intent),
    }


# --- the enforcement layer (core contribution) ---------------------------

def enforce(workflow: dict[str, Any], intent: Intent) -> dict[str, Any]:
    """Repair structure and inject safety *policy* (never trade intent).

    Given any candidate workflow (from rules, an LLM, or a hybrid), this:

    * ensures the category's required safety nodes are present (structural
      repair -- e.g. a swap without a price-impact calculator gets one);
    * injects conservative safety-policy config the request did not pin down
      (a default slippage bound, a concrete price-impact threshold so the
      gate actually fires, a bridge confirmation count, a default order
      expiry, a self recipient for a bridge);
    * leaves every trade-intent field exactly as parsed -- it never adds a
      token, amount, target price, or chain that was not in the request.

    A safety *waiver* in the request is deliberately overridden: the whole
    point is that a safe system refuses to ship an unsafe trade even when
    asked to.
    """
    nodes = list(dict.fromkeys(workflow.get("nodes") or []))
    edges = [list(e) for e in (workflow.get("edges") or [])]
    config = dict(workflow.get("config") or {})

    required = CATEGORY_NODES[intent.category]
    # structural repair: add any missing required node, then repair the spine
    for node in required:
        if node not in nodes:
            nodes.append(node)
    have = set(nodes)
    existing = {(a, b) for a, b in edges}
    for a, b in _edges(required):
        if a in have and b in have and (a, b) not in existing:
            edges.append([a, b])
            existing.add((a, b))

    # safety-policy injection (config keys that are policy, not intent)
    if intent.category in ("swap", "compositional"):
        config.setdefault("slippage", DEFAULT_SLIPPAGE)
        config.setdefault("warning_threshold", DEFAULT_IMPACT_THRESHOLD)
    if intent.category == "limit_order":
        config.setdefault("expiry", DEFAULT_EXPIRY)
    if intent.category == "cross_chain":
        config.setdefault("default_confirmations", DEFAULT_CONFIRMATIONS)
        config.setdefault("destinationAddress", SELF_RECIPIENT)

    return {"nodes": nodes, "edges": edges, "config": config}


# --- assembly ------------------------------------------------------------

def _enforcement_enabled() -> bool:
    return os.environ.get("KOAN_SAFE_ENFORCE", "1") != "0"


def build_result(prompt: dict[str, Any], baseline: str, candidate: dict[str, Any],
                 intent: Intent, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply the enforcement layer (if enabled) and finalise a run record."""
    if intent.decision == "clarify":
        return {
            "id": prompt["id"], "baseline": baseline, "category": intent.category,
            "status": "needs_clarification", "error": None,
            "koan_safe": {"decision": "clarify", "reason": intent.reason,
                          "enforced": False, **(extra or {})},
            "workflow": {"nodes": [], "edges": [], "config": {}, "safety": []},
        }

    enforced = _enforcement_enabled()
    workflow = enforce(candidate, intent) if enforced else {
        "nodes": list(candidate.get("nodes") or []),
        "edges": [list(e) for e in (candidate.get("edges") or [])],
        "config": dict(candidate.get("config") or {}),
    }
    workflow["safety"] = derive_safety(workflow["nodes"], workflow["config"])
    return {
        "id": prompt["id"], "baseline": baseline, "category": intent.category,
        "status": "ok", "error": None,
        "koan_safe": {"decision": "build", "reason": intent.reason,
                      "enforced": enforced, **(extra or {})},
        "workflow": workflow,
    }
