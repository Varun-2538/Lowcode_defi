# Koan Submission Status

Last updated: 2026-07-08

## Main split (120 prompts) — benchmark-grade upgrade

Scaled the pilot into **DeFiFlowBench** (120 prompts) following the Agentic
Benchmark Checklist (ABC), BetterBench, and NeurIPS D&B guidance:

- Balanced 40/30/30/20 across categories; difficulty tiers (38 easy / 62
  medium / 20 hard); phenomena tags; paraphrase clusters; 15 clarification/
  rejection prompts.
- Floor/ceiling baselines: **oracle** scores 1.00/1.00/1.00 and is on-chain
  safe (tasks solvable, scorer sound); **null** + **random_nodes** floor at
  0.00 (metric not gameable).
- Ablations: **few-shot** and **safety-instruction** LLM variants on both
  models. Safety instruction is the only intervention that removes on-chain
  unsafe execution (fork safe-rate -> 1.00) but still leaves most workflows
  structurally incomplete.
- Rigor: Wilson + bootstrap CIs; construct-validity check (static safe-proxy
  has zero false positives vs on-chain); quantified failure taxonomy;
  paraphrase/difficulty robustness.
- Docs: datasheet, contamination note, licensing note (parent repo is
  proprietary — open license pending author decision), second-annotator IAA
  guide + reproducible subset + `compute_iaa.py`.
- Paper rebuilt on the main split (6 pages, clean, CIs + ablations +
  analysis section). Build: `paper/build_icdlt.sh main`.

Headline (main, n=105 workflow prompts): best structural 0.44 (constrained
Gemini); best safe-executability 0.29 (safety-instructed Gemini, 95% CI
[0.21,0.38]); direct/constrained/few-shot each execute 10-13 on-chain unsafe
swaps at ~33% impact.

## Pilot (30 prompts) — retained for reference

## Venue plan

- Plan A: ICDLT 2026 full paper.
- Fallback: ICSTCEE 2026 paper only if the draft is defensible by August 5, 2026.

## Current state

- Clean submission workspace created; legacy material quarantined under `archive/`.
- **Pilot benchmark is live and reproducible** via `code/run_pilot.sh`:
  - 30 authored prompts + gold annotations (4 categories), schema-validated.
  - Static scoring (structural / executable / safe) **plus a real on-chain
    fork pass** that executes each swap on a local py-EVM chain.
  - Baselines: `template`, `koan_current` (real Koan pipeline offline),
    `direct_llm`, `constrained_llm` — the LLM baselines run against **two
    models** (Gemini 3.1 Flash Lite and GPT-5.4 mini) via OpenRouter.
  - Tables + figure generated only from saved metrics + fork results.
- **Full two-model pilot + fork pass complete.** Findings:
  - **No system is statically safe-executable (safe = 0.00) across both LLM
    families** — not a single-model quirk.
  - **On-chain proof**: for prompt `s03`, every LLM emits a swap with a
    concrete large amount but no price-impact gate; it **executes on the
    local EVM at ~33% price impact (tx status 1)** — an unsafe trade a safe
    system should block. See `docs/pilot_findings.md`.

## Paper package (ICDLT 2026 draft)

- Draft lives in `paper/` (shared sections + IEEEtran `main.tex`); build
  with `paper/build_icdlt.sh` (regenerates tables/figure from saved results,
  then `latexmk` — does not re-run experiments). Current PDF: 5 pages, clean
  build, verified citations only.
- Annotation guide: `docs/annotation_guide.md`. Worked examples (s03/c01/x01,
  verbatim from saved artifacts): `docs/worked_examples.md`.

## Next milestones

1. Complete an independent second-annotation pass on the IAA subset
   (`data/iaa/`) and report Cohen's kappa via `code/benchmark/compute_iaa.py`.
2. Resolve the open license question (`docs/licensing.md`) before any public
   release; parent repo is currently proprietary.
3. Rotate the OpenRouter API key (shared in chat earlier).
4. Decide on the ICSTCEE 2026 fallback by ~July 25 (only if defensible).
5. Optionally swap the synthetic AMM for a real mainnet-fork RPC
   (Anvil/Alchemy) to replace synthetic prices/liquidity with live state, and
   broaden the on-chain harness to the limit and cross-chain legs.
