# Experiment Plan

## Research question

Do DeFi workflow generators that produce structurally valid graphs also
produce workflows that are safely executable under protocol,
configuration, and state constraints?

## Measurement layers

Every generated workflow is scored on three strictly-nested layers:

1. **Structural** (`graph_valid`): required node types and type-level
   edges are all present (recall = 1.0) and the run did not error.
   Deliberately lenient — this is the weak "valid" notion the paper
   critiques. Extra nodes are counted but do not fail this layer unless
   they break a required edge.
2. **Executable** (`executable_proxy`): structural AND every required
   execution-config key is populated with a concrete (non-placeholder)
   value.
3. **Safe-executable** (`safe_executable_proxy`): executable AND every
   required safety predicate is declared/parameterized.

A separate **clarification** axis scores underspecified prompts: the ideal
response is to ask for missing information, not to emit a workflow.

On top of the static layers, an **on-chain fork pass** actually executes
each generated swap on a local py-EVM chain (real AMM + ERC20s) and labels
the outcome (`executed_safe`, `reverted_slippage`, `aborted_price_impact`,
`unsafe_executed`, `pending_not_filled`, `not_executable`,
`not_simulated`). `unsafe_executed` = the trade mined at large own-trade
price impact with no price-impact gate. This is a pinned local snapshot,
not a mainnet fork.

## Pilot (done)

- 30 prompts; categories: swap (8), limit_order (7), cross_chain (8),
  compositional (7); 4 underspecified prompts across categories.
- Baselines: `template`, `koan_current`, `direct_llm`, `constrained_llm`;
  LLMs run on **two models** (Gemini 3.1 Flash Lite, GPT-5.4 mini) via
  OpenRouter at temperature 0.
- Static outcome: **safe = 0.00 for every system on both models.** On-chain:
  both models execute an unsafe swap (~33% impact, no gate) on prompt `s03`.
  See `docs/pilot_findings.md`.

## Final (in progress)

The pilot confirms the gap across two models and on-chain, so proceed to
200–300 prompts. Remaining additions for the final split:

- Scale the authored dataset to 200–300 prompts with the same annotation
  scheme.
- Optionally replace the synthetic AMM with a real mainnet-fork RPC
  (Anvil/Alchemy) so on-chain prices/liquidity are live, and extend the
  harness to the limit and cross-chain legs.
- Add an explicit adversarial split (state change between quote and
  execution) beyond the two adversarial pilot prompts (`s08`, `c08`).

## Non-goals (for now)

No user study, no production mainnet deployment, no formal verification,
no eight-way tool comparison. Keep the scope to one strong, reproducible
finding.
