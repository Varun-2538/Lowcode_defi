# Decision Log

## 2026-07-07

- Target ICDLT 2026 as Plan A.
- Prepare ICSTCEE 2026 only as a fallback if ready before August 5.
- Use quarantine-first cleanup.
- Preserve source directories untouched.
- Treat old `paper/dapps2026` results as legacy reference only.

## 2026-07-07 (pilot build)

- Authored a real 30-prompt pilot with gold graphs, required execution
  config, and safety predicates (`code/benchmark/build_dataset.py`). No
  reuse of prior unsupported numbers.
- Adopted three-layer scoring (structural / executable / safe-executable)
  plus a separate clarification axis, because the paper's whole claim is
  that these layers diverge.
- `koan_current` baseline drives the **real** Koan modules
  (`agents/src/.../architecture_mapper.py` + `workflow/generator.py`) via
  the deterministic regex fallback so it needs no API key and is fully
  reproducible. Ran everything through `uv run --project agents`.
- Safety predicates are *derived uniformly* for all baselines from the
  normalized workflow (`code/benchmark/workflow_utils.py`) so no system is
  advantaged by self-reporting.
- LLM baselines are implemented for real but skip (recorded, not dropped)
  when no API key is present. Did not fabricate LLM numbers.
- Decision: keep the static executable/safety proxy for the pilot and
  gate any "on-chain safety" claim on implementing fork simulation first.

## 2026-07-07 (fork execution + second model)

- Implemented `code/safety/fork_simulation.py`: a local py-EVM chain
  (`eth-tester`) with a real constant-product AMM + mock ERC20s (solc
  0.8.24). It **executes each generated swap on-chain** and records the
  receipt/revert. Explicitly labeled a pinned local snapshot, NOT a mainnet
  fork (no external RPC available in this environment).
- The harness distinguishes `reverted_slippage` (movement protection) from
  `unsafe_executed` (large own-trade impact went through with no
  price-impact gate), which is the concrete on-chain evidence for the
  thesis. Verified byte-for-byte determinism across re-runs.
- Added a second model, `openai/gpt-5.4-mini`, alongside
  `google/gemini-3.1-flash-lite`. Added a `--tag` to `run_evaluation.py`
  so each (baseline, model) run gets a distinct `run_id`
  (`<baseline>__<model-tag>`); tables/figures now key on `run_id`.
- Fixed an unfair edge-format artifact: GPT emitted integer index edges
  (`[[0,1]]`) vs Gemini's node-name edges. Clarified the prompt AND made
  `_normalize_edges` accept both. Re-derived GPT metrics from each call's
  saved `raw_output` via `rescore_llm.py` (no re-query) because OpenRouter
  was rate-limiting GPT-5.4-mini heavily.
- Result: safe = 0.00 across BOTH model families statically; on-chain, both
  models produce an `unsafe_executed` swap on prompt `s03` (~33% impact, no
  gate). The finding is not model-specific. Decision: proceed to the
  200–300 prompt final split.

## 2026-07-07 (paper package)

- Directive from user: stop adding machinery; freeze the pilot and turn it
  into a paper package. Scaling target revised down to ~120 prompts (not
  300) for the final split.
- Detected and fixed a data-contamination issue: a previously killed GPT
  background job had left `direct_llm__openai_gpt-5.4-mini` holding a MIXED
  set of prompt versions (2 new, 28 old). Re-ran all four LLM baselines
  fresh and coherently so every record is one prompt version. No numbers
  were carried over from the mixed run.
- Wrote the ICDLT 2026 draft under `paper/` (shared sections + IEEEtran
  `main.tex`). All tables/figure are generated from saved results only;
  `references.bib` contains only verified citations. PDF builds clean
  (5 pages, no undefined refs/citations).
- Fixed a LaTeX caption bug in `make_tables.py` (`>5%` → `$>$5\%`) and added
  `paper/build_icdlt.sh` to regenerate tables/figure from saved results and
  compile — it does NOT re-run experiments.
- Added `docs/annotation_guide.md` (field-by-field gold annotation rules
  matching `metrics.py` / `workflow_utils.py`) and `docs/worked_examples.md`
  (three verbatim prompt → gold → output comparisons: s03, c01, x01).
- Next: scale to ~120 prompts, then rerun the full pipeline; decide on the
  ICSTCEE fallback by ~July 25.

## 2026-07-08 (benchmark-grade main split)

- Directive from user: a benchmark paper needs more rigor (more ablations,
  more analyses). Researched best practice (Agentic Benchmark Checklist / ABC,
  NeurIPS 2025; BetterBench, Stanford; NeurIPS D&B CFP) and adopted the
  applicable items.
- User scope decisions: keep 2 models (cost); include all ablations (few-shot
  + safety-instruction); draft a 2nd-annotator IAA guide+subset for a human to
  fill; target ICDLT-depth packaging (datasheet-lite, license, reproducible
  scripts), not full NeurIPS-D&B Croissant/hosting.
- Built the 120-prompt `main` split (`code/benchmark/main_prompts.py`):
  balanced 40/30/30/20, difficulty tiers, phenomena tags, paraphrase clusters,
  15 clarification/rejection prompts. Schema extended with
  difficulty/phenomena/paraphrase_of. Gold still derived from the same
  category templates so scoring stays uniform.
- Added floor/ceiling baselines: `oracle` (reconstructs gold; scores
  1.00/1.00/1.00 and is on-chain safe — proves solvability + scorer soundness,
  ABC T.9/R.13), `null` and `random_nodes` (floor, ABC R.14). Runner passes
  gold to baselines that declare a 2nd param (oracle only).
- Added LLM ablations `fewshot_llm` and `safety_llm` sharing `llm_common`
  (one worked example / explicit safety directive). Ran both models x four
  LLM variants (~960 calls, ~$0.26). Fork pass rerun on main.
- Added rigor: `code/analysis/stats.py` (Wilson + bootstrap + two-proportion
  z, stdlib only); `code/analysis/analyze.py` (construct-validity confusion
  vs on-chain, quantified failure taxonomy, paraphrase/difficulty robustness).
  Tables now carry 95% Wilson CI on the Safe column and split-specific output
  dirs; per-category table pivoted to fit; figure omits reference baselines.
- Key finding update: the pilot's "safe=0.00 for everyone" is superseded by a
  nuanced result — best safe-executability 0.29 (safety-instructed Gemini);
  direct/constrained/few-shot each execute 10-13 on-chain unsafe swaps;
  safety instruction alone drives on-chain unsafe to 0 but leaves structure
  incomplete. Construct validity: static safe-proxy has ZERO false positives
  vs on-chain (sound, conservative).
- Docs: `datasheet.md`, `contamination.md`, `licensing.md` (flagged the
  proprietary-parent-repo conflict rather than asserting an open license),
  `second_annotator_guide.md` + `make_iaa_subset.py` + `compute_iaa.py`.
  New `code/run_benchmark.sh`; `paper/build_icdlt.sh` now split-aware.
- Paper rewritten on main-split numbers (abstract, intro, benchmark,
  experiments, new analysis section, discussion, limitations). Builds clean,
  6 pages, verified citations only. IAA number intentionally withheld until a
  human second pass exists (integrity: no fabricated annotator).

## 2026-07-08 (Koan-Safe method + held-out test split)

- Directive from user: make Koan the best performer, but by *improving Koan to
  the benchmark's failure taxonomy*, never by bending the benchmark to Koan.
  Reframe the paper from benchmark-only to "benchmark + proposed method".
- Design decisions (user-approved): build the safety layer over BOTH a rules
  generator and an LLM generator, plus a hybrid, so we can ablate
  rules/LLM/together (x/y/z). Held-out split = ~90 prompts including NEW
  structural variants (novel gold templates), not just harder parsing.
  Reporting stance: iterate on dev only, then FREEZE once and report held-out
  as-is even if Koan-Safe loses.
- Built `code/baselines/koan_safe_core.py` (parser + generator-agnostic
  enforcement layer) and three baselines (`koan_safe_rules/llm/hybrid`), all
  prompt-only. Hard integrity rules enforced in code: no gold/category/entities
  access; the layer injects safety *policy* but never fabricates trade intent;
  missing intent -> clarify; safety waivers overridden. `KOAN_SAFE_ENFORCE=0`
  toggles the layer for the causal ablation.
- Iterated the rules parser on dev (`main`) until graph=1.00, safe=0.56, 0
  category mislabels, 0 clarification mismatches, 0 on-chain unsafe. Verified
  every remaining executable miss is an honest prompt omission (no fabricated
  amount/price), not a scorer artifact.
- FROZE the method at commit `e98b0bb`. Then authored `heldout` (87 prompts,
  `code/benchmark/heldout_prompts.py` + `VARIANT_TEMPLATES` in
  `build_dataset.py`): canonical prompts with fresh/out-of-vocab tokens plus 5
  new structural variants. Ran ALL systems once (offline + 2 LLM families +
  Koan-Safe + ablations, ~1000 calls), fork pass, tables/analysis/figure.
- Result: Koan-Safe (hybrid, Gemini) safe=0.67 [.55,.76] on held-out, DOUBLE
  the best baseline (0.33), with 0 on-chain unsafe across all 3 generators x 2
  models (vs 15-19 for plain LLMs). Enforcement on/off is the sole cause
  (safe collapses to 0.00-0.12, unsafe returns to 16/17). Construct validity
  holds (precision 1.00, n=891). Honest generalization gap reported: frozen
  rules presets miss the new structural variants (graph 0.52), LLM/hybrid
  recover (0.71-0.73). 3 held-out clarification misses left unpatched by the
  freeze rule.
- Reframed the whole paper: title "Benchmarking and Improving..."; new
  `\section{Koan-Safe}` in method.tex; experiments now dev+heldout with the
  Koan-Safe results, generator ablation (Table II), and per-category (Table
  III); abstract/intro/benchmark/analysis/discussion/limitations updated.
  `build_icdlt.sh` regenerates both splits and copies held-out as primary.
  PDF rebuilt: 8 pages, clean, all 3 tables render as full-width floats.

## 2026-07-08 (metamorphic safety suite + cost/latency)

- Reviewer-hardening sprint. Of the user's five asks, three were unblocked and
  done this turn; two remain blocked on external inputs (see below).
- **Metamorphic safety suite** (new, highest-novelty): authored 34 base/variant
  prompt PAIRS across five metamorphic relations
  (`code/benchmark/metamorphic_prompts.py`): amount monotonicity (100x larger
  trade), threshold tightening (5%->1%), waiver resistance ("ignore price
  impact"), paraphrase invariance, drop-field non-fabrication. Built as split
  `metamorphic` (68 prompts) via `build_dataset.py` (pairs manifest saved in
  the split json). The waiver adversarial suite (user ask #4) is folded in as
  the `waiver` relation rather than a separate anecdotal test.
- Rationale: absolute scores compare to a fixed target and cannot show whether
  declared/executed safety is *robust* to risk-relevant rewrites. Metamorphic
  testing checks output RELATIONS, so it needs no per-prompt gold label. The
  invariant checkers (`code/analysis/metamorphic.py`) are a-priori and
  interpretable: superset-of-safety, no-new-unsafe-on-chain, gate-preservation,
  numeric-threshold monotonicity, class/policy invariance, no-fabrication. A
  pair whose base fails to build is N/A (excluded from the denominator), so
  denominators legitimately vary across systems.
- Ran koan_safe_rules(+noenforce) offline, then the LLM-dependent systems
  (direct_llm, safety_llm, koan_safe_llm/hybrid) on both model families, plus a
  fork pass, then the analyzer. Result: **every Koan-Safe config satisfies all
  amount/threshold/waiver/dropfield relations** (0/34, except 1 hybrid-Gemini
  paraphrase class-flip, reported not patched); **direct LLMs fail every
  amount-monotonicity pair and most waiver pairs** (14-16/32); the rules
  enforcement-OFF ablation shows 15/34 (amount 8/8, waiver 7/8), proving the
  enforcement layer is what restores safety monotonicity and waiver resistance.
- **Cost/latency** (user ask #5): instrumented `run_evaluation.py` with
  per-prompt wall-clock + LLM-call detection -> `<run>_timing.json`; added
  `code/analysis/cost.py`. Grounded on the two measurable drivers (LLM
  calls/wf, latency) + a token estimate at a STATED price (no fabricated
  per-model prices). Rules = 0 calls/offline; LLM/hybrid 0.99 calls/wf
  (clarification gate skips the call); enforcement-layer overhead measured in
  isolation = 0.07 ms/wf; est. < $0.005/100 wf.
- Paper: added Experiments subsections "Metamorphic safety" (Table III) and
  "Cost and latency" (Table IV) + a benchmark paragraph + abstract/intro/
  contributions updates. `build_icdlt.sh` + `run_benchmark.sh` wired for the
  metamorphic split. PDF rebuilt: 9 pages, clean, no undefined refs.
- **Still blocked, reported to user (NOT fabricated):** (a) mainnet-fork
  validation (user ask #2) — this environment has no external RPC; needs an
  RPC key. (b) human inter-annotator agreement kappa (user ask #3) — the
  subset + `compute_iaa.py` + guides exist, but a real independent annotator
  must do the pass; will not invent a second annotator.

