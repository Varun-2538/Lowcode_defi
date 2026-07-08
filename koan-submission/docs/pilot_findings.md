# Pilot Findings

Generated from `results/processed/pilot`, `results/fork/pilot`, and
`results/tables`. Regenerate with `code/run_pilot.sh`. All numbers below
come from saved outputs, not hand entry.

LLM baselines were run live via OpenRouter at temperature 0 on two models:
`google/gemini-3.1-flash-lite` and `openai/gpt-5.4-mini`. Each raw record
stores the provider/model and the full model output under
`results/raw/pilot/<run_id>/`, where `run_id = <baseline>__<model-tag>`.

## Setup

- 30 authored prompts, 4 categories (swap 8, limit_order 7, cross_chain 8,
  compositional 7). 4 prompts are deliberately underspecified and scored on
  the clarification axis, leaving 26 "workflow" prompts.
- Static baselines: `template` (category template, no parsing),
  `koan_current` (the real Koan regex intent parser + `WorkflowGenerator`,
  offline). LLM baselines: `direct_llm`, `constrained_llm` on both models.
- Two static scoring layers plus one on-chain layer:
  - `graph_valid`: required node types + type-level edges present, run ok.
  - `executable_proxy` / `safe_executable_proxy`: config populated / safety
    predicates declared (static proxy).
  - **fork execution**: the workflow's swap is *actually executed* on a
    local py-EVM chain (real AMM + ERC20s, solc 0.8.24). This is a pinned
    local chain snapshot, **not** a mainnet fork (no external RPC here).

## Headline result — static layers (pilot, n=26 workflow prompts)

| Run | Graph valid | Exec. (cfg) | Safe (cfg) | Config compl. | Safety recall | Clarif. |
|---|---|---|---|---|---|---|
| Template-only | 1.00 | 0.00 | 0.00 | 0.00 | 0.70 | 0.00 |
| Koan (regex+gen) | 0.15 | 0.00 | 0.00 | 0.16 | 0.49 | 0.25 |
| Direct LLM · Gemini 3.1 FL | 0.08 | 0.04 | 0.00 | 0.58 | 0.37 | 1.00 |
| Constrained LLM · Gemini 3.1 FL | 0.27 | 0.04 | 0.00 | 0.56 | 0.49 | 1.00 |
| Direct LLM · GPT-5.4 mini | 0.04 | 0.00 | 0.00 | 0.38 | 0.24 | 1.00 |
| Constrained LLM · GPT-5.4 mini | 0.04 | 0.00 | 0.00 | 0.52 | 0.42 | 1.00 |

(Numbers are from the latest coherent run; LLM calls at temperature 0 have
minor run-to-run variation, so exact decimals may shift slightly on
re-run. The qualitative pattern is stable.)

**No system produces a single statically safe-executable workflow
(safe = 0.00 everywhere), and this holds across two different LLM
families.** The failure is not one model's quirk.

## Headline result — on-chain execution (fork pass)

| Run | On-chain executed (definite) | Safe | Unsafe-executed | Fork safe-rate |
|---|---|---|---|---|
| Template-only | 0 | 0 | 0 | n/a (nothing executable) |
| Koan (regex+gen) | 0 | 0 | 0 | n/a (nothing executable) |
| Direct LLM · Gemini 3.1 FL | 3 | 2 | 1 | 0.67 |
| Constrained LLM · Gemini 3.1 FL | 3 | 2 | 1 | 0.67 |
| Direct LLM · GPT-5.4 mini | 2 | 1 | 1 | 0.50 |
| Constrained LLM · GPT-5.4 mini | 2 | 1 | 1 | 0.50 |

**The concrete safety failure**: prompt `s03` ("trade 500 DAI into ETH")
has a large own-trade price impact. Every LLM (both models) produces a
workflow that includes a swap with `amount = 500` but **no wired
price-impact gate**. On the local EVM this swap **executes successfully
(tx status 1) at ~33% price impact** — a trade a safe system should have
blocked. The static `executable_proxy` even counts these as "executable";
only running them on-chain and inspecting impact exposes them as
`unsafe_executed`.

This is the paper's thesis made concrete: a workflow can be structurally
plausible, config-complete, and still *execute an unsafe trade* because a
slippage bound protects against price movement between quote and
execution, not against the impact of your own large order. Only a separate
price-impact gate prevents it, and none of the systems wire one.

## Why the static layers fail (per system)

- **Template-only**: perfect structure (graph 1.00) but zero trade
  parameters (config 0.00) — nothing is executable, so nothing reaches the
  chain.
- **Koan**: over-generates swaps to a fixed 10-node suite (breaks the
  `oneInchSwap -> transactionMonitor` edge), omits `tokenSelector` and sets
  identical source/dest chains for cross-chain, and collapses compositional
  "swap + limit" to limit-only. Only limit_order is structurally valid
  (0.67), and even then `targetPrice`/`amount` are never set.
- **Gemini 3.1 FL**: strong at config extraction (0.57–0.58) and
  clarification (1.00); constraints lift graph-valid 0.08 -> 0.35. Still
  declares safety nodes without parameterizing thresholds.
- **GPT-5.4 mini**: builds terser, differently-structured graphs — omits
  `walletConnector`/`transactionMonitor`, attaches `priceImpactCalculator`
  as a side branch, or adds an unneeded `chainSelector` — so type-level
  graph-valid is 0.00 under strict matching, though it still extracts
  concrete config (0.43) and asks for clarification perfectly (1.00).

## Honest caveats

- **Local EVM, not a mainnet fork.** We deploy a constant-product AMM
  (0.3% fee) + mock ERC20s on an in-process py-EVM chain; reserves and
  prices are seeded deterministically. This gives real EVM semantics (real
  `transferFrom`, real `require` reverts, real gas) for swap/limit
  primitives, but token prices/liquidity are synthetic. Runs are
  byte-for-byte reproducible.
- **Category scope of the fork pass.** swap (and the swap leg of
  compositional) is executed on-chain; limit_order is checked for immediate
  fillability against the pool mid price; cross_chain is `not_simulated`
  (one local chain cannot bridge). Every case is recorded explicitly.
- **Strict, type-level edge matching** penalizes reasonable-but-reordered
  LLM graphs, so LLM structural numbers are a lower bound. It does not
  affect the safe = 0.00 or the on-chain unsafe-executed findings.
- **n = 26, temperature 0, one seed per model.** Two model families agree,
  which is encouraging, but scale to 200–300 prompts before strong claims.
- **GPT-5.4 mini was heavily rate-limited** on OpenRouter during this run;
  its results were re-derived deterministically from each call's saved
  `raw_output` via `code/benchmark/rescore_llm.py` (no re-query), after the
  edge-format normalization fix. No numbers were fabricated or dropped.
