# Koan Submission Status

Last updated: 2026-07-08

## Koan-Safe method + held-out test split (proposed system)

The paper now has a dual contribution: the benchmark **and** a proposed
safety-enforcement system, **Koan-Safe**, evaluated on a fresh held-out split.

- **Koan-Safe** (`code/baselines/koan_safe_*`): a prompt-only intent parser, a
  replaceable candidate generator (`rules` / `llm` / `hybrid`), and a
  generator-agnostic **safety-enforcement layer** that repairs structure and
  injects conservative safety *policy* (slippage bound, price-impact gate +
  threshold, bridge confirmations, expiry) but **never fabricates trade
  intent** (tokens/amount/price/chain). Missing intent -> clarify. Toggle the
  layer with `KOAN_SAFE_ENFORCE=0` for the ablation.
- **Integrity protocol**: the method was built/tuned on `main` (now the *dev*
  split), then **frozen** (commit `e98b0bb`), then evaluated **once** on a
  newly authored `heldout` test split with **new structural variants**
  (gasless swap, quote-first limit, dashboard bridge, cross-chain swap) whose
  gold structures lie outside Koan-Safe's presets. No tuning against heldout.

### Held-out results (n=75 workflow prompts; all real, saved)
| System | Graph | Safe [95% CI] | Fork unsafe |
|---|---|---|---|
| Best baseline (safety-instruct Gemini) | 0.33 | 0.33 [.24,.45] | 0 |
| Direct/Constr/Fewshot LLMs | 0.01-0.31 | 0.00-0.13 | **15-19** |
| **Koan-Safe (hybrid, Gemini)** | 0.73 | **0.67 [.55,.76]** | **0** |
| Koan-Safe (LLM, Gemini) | 0.71 | 0.64 | 0 |
| Koan-Safe (rules) | 0.52 | 0.43 | 0 |

- **Koan-Safe doubles safe-executability over the best baseline (0.67 vs 0.33)
  and drives on-chain unsafe executions to ZERO across all 3 generators x 2
  models**, vs 15-19 for plain LLMs.
- **Enforcement on/off ablation** (only the layer changes): safe 0.43->0.12
  (rules), 0.64->0.00 (LLM), 0.67->0.01 (hybrid); fork-unsafe 0->16/17. The
  layer, not the generator, is the cause.
- **Honest generalization gap**: the frozen rules presets don't cover the new
  structural variants (graph 1.00 dev -> 0.52 heldout); the LLM/hybrid
  generators recover most of it (graph 0.71-0.73). Reported as-is.
- **Construct validity holds on heldout**: proxy declared 282 safe, all 282
  safe on-chain (precision 1.00, 0 false positives; n=891).
- 3 held-out clarification misses (terse "I want a limit order") left
  unpatched per the freeze rule.

Paper reframed and rebuilt: title now "Benchmarking **and Improving** Safe
Executability..."; new method section, dev+heldout experiments, generator x
enforcement ablation (Table II), per-category (Table V). PDF: 9 pages,
clean build.

## Metamorphic safety suite + cost/latency (reviewer-hardening)

Added a label-free **metamorphic** split (`data/*/metamorphic.*`; 34
base/variant prompt pairs = 68 prompts) that tests output *relations* instead
of per-prompt gold: **amount** monotonicity (100x larger trade), **threshold**
tightening (5%->1%), **waiver** resistance ("ignore price impact"),
**paraphrase** invariance, **dropfield** non-fabrication. Analyzer:
`code/analysis/metamorphic.py` (invariant checkers over saved outputs + fork),
writes `results/analysis/metamorphic/metamorphic.json` + Table III.

### Metamorphic results (violated pairs, lower is better; denom = applicable pairs)
| System | Amt | Thr | Waiv | Para | Drop | All |
|---|---|---|---|---|---|---|
| Direct LLM (Gemini) | 8 | 0 | 6 | 0 | 0 | 14/32 |
| Direct LLM (GPT) | 7 | 0 | 7 | 2 | 0 | 16/33 |
| Safety-instruct (Gemini) | 0 | 0 | 1 | 2 | 0 | 3/30 |
| Safety-instruct (GPT) | 0 | 1 | 0 | 1 | 0 | 2/28 |
| **Koan-Safe (rules)** | 0 | 0 | 0 | 0 | 0 | **0/34** |
| **Koan-Safe (LLM, both)** | 0 | 0 | 0 | 0 | 0 | **0/34** |
| **Koan-Safe (hybrid, GPT)** | 0 | 0 | 0 | 0 | 0 | **0/34** |
| Koan-Safe (hybrid, Gemini) | 0 | 0 | 0 | 1 | 0 | 1/34 |

- **Direct LLMs fail every amount-monotonicity pair** (larger trade newly
  mines unsafe) and **most waiver pairs** (drop slippage/expiry/monitoring).
  Enforcement-OFF rules ablation: 15/34 (amount 8/8, waiver 7/8).
- **Every Koan-Safe config satisfies all amount/threshold/waiver/dropfield**;
  only residual = 1 hybrid-Gemini paraphrase (cross-chain class flip),
  reported not patched.

### Cost/latency (`code/analysis/cost.py`; Table IV)
- Rules generator: **0 LLM calls, fully offline**. LLM/hybrid: 0.99 calls/wf
  (clarification gate skips the call), vs 1.00 for plain baselines.
- Latency ~1.7-2.0 s/wf for all LLM systems (provider round-trip dominated,
  indistinguishable Koan-Safe vs baselines).
- **Enforcement-layer overhead measured in isolation: 0.07 ms/wf.** Est. spend
  < $0.005 / 100 wf at $0.30/1M output tokens.
- Runner now writes `results/processed/<split>/<run>_timing.json` (per-prompt
  seconds + llm_called).

## Main split (120 prompts) — benchmark-grade upgrade (now the DEV split)

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
