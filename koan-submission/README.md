# Koan Submission Workspace

This folder is the clean research workspace for the Koan benchmark paper.

Plan A is the ICDLT 2026 full paper. The fallback is an ICSTCEE 2026-compatible version if a defensible draft is ready before the August 5 deadline.

## What this workspace is for

- Build a reproducible benchmark for safety-constrained DeFi workflow synthesis.
- Treat Koan as one evaluated system/baseline, not as the entire scientific contribution.
- Keep old papers, review documents, and templates quarantined under `archive/`.
- Keep generated results separate from source data and paper text.

## Main folders

- `paper/`: ICDLT and ICSTCEE LaTeX entrypoints plus shared section files.
- `data/`: prompt/gold data, schemas, and split definitions.
- `code/`: benchmark runners, baselines, Koan adapters, safety checks, and analysis scripts.
- `results/`: raw outputs, processed metrics, generated tables, figures, and logs.
- `docs/`: experiment plan, reproducibility notes, decision log, and cleanup manifest.
- `archive/`: legacy material preserved for reference only.

## Current run commands

All Python runs through `uv`. The Koan baseline imports the real project
modules under `agents/src`, so it runs through the agents environment; every
other step runs with `uv run --no-project`.

Reproduce the whole **main** split (120 prompts) end-to-end, including the
floor/ceiling baselines, LLM ablations, fork pass, tables, analyses, and
figure:

```bash
koan-submission/code/run_benchmark.sh main    # or: ... pilot
```

Or step by step:

```bash
# build + validate
uv run --no-project python koan-submission/code/benchmark/build_dataset.py \
  --data-root koan-submission/data --split main
uv run --no-project python koan-submission/code/benchmark/validate_dataset.py \
  --data-root koan-submission/data --split main

# a reference/offline baseline
#   (oracle | null | random_nodes | template | koan_current)
uv run --no-project python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline oracle

# an LLM baseline / ablation, one run per model tag
#   (direct_llm | constrained_llm | fewshot_llm | safety_llm)
KOAN_LLM_MODEL="google/gemini-3.1-flash-lite" \
uv run --no-project --with "openai>=1.0" \
  python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline safety_llm --tag google_gemini-3.1-flash-lite

# tables, deeper analyses (CIs / construct validity / taxonomy / robustness), figure
uv run --no-project python koan-submission/code/analysis/make_tables.py \
  --results-root koan-submission/results --split main
uv run --no-project python koan-submission/code/analysis/analyze.py \
  --results-root koan-submission/results --data-root koan-submission/data --split main
uv run --no-project --with matplotlib python koan-submission/code/analysis/make_figures.py \
  --results-root koan-submission/results --split main
```

Rebuild the paper from saved results (no experiments re-run):
`koan-submission/paper/build_icdlt.sh main`.

See `docs/pilot_findings.md` for the current results, `docs/datasheet.md` for
dataset documentation, and `docs/reproducibility.md` for LLM-baseline setup.

## Evidence policy

The old `paper/dapps2026` material is archived as legacy reference only. Its prior reported benchmark numbers should not be reused as evidence in the ICDLT or ICSTCEE paper.
