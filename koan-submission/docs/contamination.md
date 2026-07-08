# Contamination & Gameability Note

Benchmark-quality guidelines (NeurIPS D&B; ABC; BetterBench) ask authors to
address data contamination and gameability. This note states what applies to
DeFiFlowBench.

## Contamination

- **Novel, authored prompts.** The main split is written by the project team
  for this benchmark; it is not scraped from the web and was not published
  before the paper's release. The prompts exercise a specific node/config/
  safety vocabulary tied to the Koan backend.
- **Held-out authoring source.** The single source of truth for the prompts
  and gold is `code/benchmark/main_prompts.py`; the split is regenerated
  deterministically. When citing results, report the release tag so the exact
  prompt set is identifiable.
- **No training on the benchmark.** The systems under test (a rule-based
  pipeline and off-the-shelf LLMs via API) are not trained or fine-tuned on
  this data. There is no train split to leak.
- **Determinism.** LLM calls run at temperature 0 and every raw output is
  saved (`results/raw/...`), so scores are re-derivable without new queries
  (`rescore_llm.py`). Minor provider-side run-to-run variation at temperature 0
  is documented in `docs/pilot_findings.md`.

## Gameability

- **Uniform, non-self-reported safety.** Safety predicates are *derived* from
  each system's normalized workflow by a single function
  (`code/benchmark/workflow_utils.py`), so a system cannot inflate its safety
  score by simply asserting predicates.
- **Nested, non-trivial metric.** The headline metric requires structural
  validity *and* concrete execution config *and* declared safety
  simultaneously; returning an empty or padded graph fails. The **null** and
  **random-node** baselines are reported precisely to show the metric cannot be
  gamed by degenerate outputs (both score 0 on every layer).
- **Oracle ceiling.** The **oracle** baseline (reconstructed from gold) scores
  1.0 on all three layers and is safe on-chain, proving the tasks are solvable
  and the scorer rewards a genuinely correct solution — a guard against
  impossible-task false negatives.
- **On-chain cross-check.** The static safe-executable proxy is validated
  against actual local-EVM execution (`results/analysis/main/construct_validity.json`):
  on this split the proxy never certifies a workflow that executes unsafely
  on-chain (zero false positives), so a system cannot pass the safety layer
  while shipping an on-chain-unsafe trade.

## Known limitations that bound interpretation

- The on-chain layer is a **local snapshot** with synthetic prices/liquidity,
  not a mainnet fork; absolute fork rates are harness properties, not market
  claims.
- Cross-chain legs are not executed on-chain (a single local chain cannot
  bridge); those are scored statically only.
- Static safety captures *declared/parameterized* safety, not runtime
  enforcement in a production engine.
