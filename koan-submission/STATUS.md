# Koan Submission Status

Last updated: 2026-07-07

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

1. Scale to ~120 prompts (40 swap / 30 limit / 30 cross-chain / 20
   compositional, incl. underspecified + adversarial), then rerun the full
   pipeline. Gap already confirmed across two models and on-chain.
2. Decide on the ICSTCEE 2026 fallback by ~July 25 (only if defensible).
3. Optionally swap the synthetic AMM for a real mainnet-fork RPC
   (Anvil/Alchemy) to replace synthetic prices/liquidity with live state.
4. Broaden the on-chain harness to the limit and cross-chain legs.
