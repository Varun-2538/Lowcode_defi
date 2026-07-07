# Benchmark Code

Small, deterministic, and reproducible. All Python runs through `uv`.
Baselines write raw outputs to `results/raw/`; analysis derives every
table and figure from saved metrics.

## Layout

- `benchmark/build_dataset.py`  — authors and emits the pilot split.
- `benchmark/validate_dataset.py` — schema/consistency checks.
- `benchmark/run_evaluation.py` — runs one baseline (optionally `--tag`
  per model), saves raw + metrics under a `run_id`.
- `benchmark/rescore_llm.py` — re-derive LLM metrics from saved
  `raw_output`, no API calls (use after parsing changes).
- `benchmark/metrics.py` — three-layer scoring (structural/executable/safe).
- `benchmark/workflow_utils.py` — uniform config-concreteness + safety derivation.
- `baselines/template_baseline.py` — category template, no parsing.
- `baselines/koan_current.py` — drives the **real** Koan pipeline offline.
- `baselines/direct_llm.py`, `baselines/constrained_llm.py` — real, optional
  (skipped without an API key); share `baselines/llm_common.py` (which also
  exposes `parse_model_output` for re-scoring).
- `koan_adapter/normalize_workflow.py` — Koan `WorkflowDefinition` -> evaluator format.
- `safety/executable_checks.py` — static config checks.
- `safety/fork_simulation.py` — **executes swaps on a local py-EVM chain**
  (real AMM + ERC20s); labels `unsafe_executed` etc. Not a mainnet fork.
- `analysis/make_tables.py`, `analysis/make_figures.py` — outputs from
  processed metrics + fork results.
- `run_pilot.sh` — end-to-end reproduction (two models + fork pass).

## Quick start

```bash
koan-submission/code/run_pilot.sh
```

## Notes

- The Koan baseline evaluates Koan's deterministic **regex fallback** intent
  path plus the real `WorkflowGenerator`, so it is fully reproducible with no
  API key. The LLM-backed Koan path is out of scope for the offline pilot.
- Safety predicates are derived identically for every baseline so no system
  can advantage itself by self-reporting safety.
