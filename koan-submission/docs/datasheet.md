# Datasheet — DeFiFlowBench

Following *Datasheets for Datasets* (Gebru et al., 2021). This documents the
120-prompt **main** split and the 30-prompt **pilot** split.

## Motivation

- **Purpose.** Measure whether natural-language DeFi requests are compiled into
  workflows that are not merely *structurally valid* but *executable* and
  *safe to execute*. The benchmark operationalizes the thesis that structural
  validity does not imply safe executability.
- **Who created it.** The Koan project team (School of Computing, SRMIST), as
  part of a research submission. No external funding specific to this dataset.
- **Gap addressed.** Prior DeFi/agent workflow work reports structural or
  intent-accuracy metrics; none separate structural validity from on-chain
  safe executability with a uniform, reproducible scorer and an on-chain check.

## Composition

- **Instances.** Each instance is a natural-language prompt paired with a gold
  workflow annotation (required nodes, required type-level edges, required
  execution-config keys, required safety predicates, allowed extra nodes,
  and an `expects_clarification` flag).
- **Counts.** Main (development) split: 120 prompts — swap 40, limit_order 30,
  cross_chain 30, compositional 20. Difficulty: 38 easy / 62 medium / 20 hard.
  15 prompts are clarification/rejection cases. Held-out (test) split: 87
  prompts — swap 31, limit_order 20, cross_chain 18, compositional 18; 16 easy
  / 47 medium / 24 hard; 12 clarification cases. Metamorphic split: 68 prompts
  = 34 base/variant PAIRS (swap 46, compositional 8, limit_order 6,
  cross_chain 8) across five metamorphic relations (amount 8, threshold 6,
  waiver 8, paraphrase 6, dropfield 6). Pilot split: 30 prompts (frozen).
- **Metadata per prompt.** `category`, `entities`, `difficulty`
  (easy/medium/hard), `phenomena` (challenge tags, e.g. `underspecified`,
  `adversarial_waiver`, `adversarial_reject`, `identical_chain`,
  `typo_noise`, `paraphrase`, `multi_intent`), and `paraphrase_of` linking
  surface-form variants of the same task.
- **Sampling / representativeness.** Prompts are expert-authored, not sampled
  from logs, to control category balance, difficulty, and the specific
  phenomena under test. They cover the token/chain/protocol vocabulary the
  real Koan backend supports; they are not a random sample of all possible
  DeFi requests and are not claimed to be.
- **Labels.** Gold annotations are derived from category-level *minimal
  correct* templates (see `code/benchmark/build_dataset.py`) plus per-prompt
  clarification flags. The node/config/safety vocabulary matches the backend
  executor catalog.
- **Splits.** `pilot` (early development, frozen), `main` (development /
  evaluation split used to characterize the gap and tune the Koan-Safe
  method), and `heldout` (test split, authored *after* Koan-Safe was frozen
  and evaluated once). The held-out split adds new gold structural variants
  (gasless swap, quote-first limit, dashboard bridge, cross-chain swap; see
  `VARIANT_TEMPLATES` in `code/benchmark/build_dataset.py`) plus
  out-of-vocabulary token symbols, so it tests generalization rather than
  in-distribution fit. `metamorphic` is a label-free robustness split of
  base/variant prompt pairs scored by output *relations* (see
  `code/analysis/metamorphic.py`), not per-prompt gold; its pairing manifest
  and relation are stored in `data/splits/metamorphic.json`. No train split:
  the benchmark evaluates externally-built systems, not a model trained on it.
- **Errors / noise.** Some prompts intentionally contain typos or vague
  phrasing (tagged `typo_noise` / `underspecified`); these are features, not
  defects.
- **External dependencies.** None at evaluation time. Static scoring is pure
  Python; the on-chain layer deploys a local py-EVM chain (no external RPC).
- **Sensitive data.** None. No personal data, no real user data, no real
  private keys or addresses (the one address in the oracle is a dummy
  `0x1111...`).

## Collection process

- **How collected.** Authored by the project team using the real backend node
  vocabulary and the categories the system supports. Gold annotations were
  written against a documented rubric (`docs/annotation_guide.md`).
- **Validation.** Every record is checked by `code/benchmark/validate_dataset.py`
  and `data/schemas/*.schema.json` (IDs unique, edges reference declared nodes,
  required config/safety non-empty, split metadata consistent). The oracle
  baseline scores 1.0 on all three layers, demonstrating tasks are solvable and
  the scorer rewards a correct solution.
- **Timeframe.** Authored 2026-07.

## Preprocessing / labeling

- Gold graphs are the minimal correct workflow; `allowed_extra_nodes` prevents
  penalizing reasonable additions. Safety predicates are *derived uniformly*
  from each system's normalized workflow (`code/benchmark/workflow_utils.py`),
  never self-reported, so every baseline is judged by the same rule.
- Raw model outputs (`raw_output`) are saved for every LLM call so metrics can
  be re-derived deterministically without re-querying (`rescore_llm.py`).

## Uses

- **Intended.** Evaluating NL→DeFi-workflow systems on structural validity,
  executable-config completeness, declared-safety completeness, on-chain
  safety, and clarification behavior; ablation studies on prompt design.
- **Out of scope / cautions.** The on-chain layer is a *local snapshot* with
  synthetic prices/liquidity, not a mainnet fork; absolute fork rates are
  properties of the harness, not of live markets. Cross-chain legs are not
  executed on-chain (a single local chain cannot bridge). The static safety
  layer captures *declared/parameterized* safety, not runtime enforcement.
- **Should not be used** to certify any workflow as safe for real funds.

## Distribution & maintenance

- **License.** To be finalized by the authors before release. The parent Koan
  repository is currently "All Rights Reserved"; publishing a benchmark
  requires an explicit open license. Recommended: **CC BY 4.0** for the
  dataset (`data/`) and **MIT** (or Apache-2.0) for the code (`code/`). See
  `docs/licensing.md` for the pending decision; do not treat the dataset as
  openly licensed until that is resolved.
- **Hosting.** Released with the paper's code repository; the dataset is small
  (<1 MB) and fully contained in `data/`.
- **Contamination.** See `docs/contamination.md`. The main split is authored
  and released with the paper; report the release tag when citing.
- **Maintenance.** Versioned in-repo; faulty prompts are fixed via a new
  patch version and noted in `docs/decision_log.md`. The `main_prompts.py`
  authoring source is the single point of truth.
