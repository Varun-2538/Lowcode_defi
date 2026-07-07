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

