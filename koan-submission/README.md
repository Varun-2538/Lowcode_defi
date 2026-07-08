# DeFiFlowBench: Benchmarking and Improving Safe Executability in Natural-Language DeFi Workflow Synthesis

This repository contains the benchmark, code, execution harness, and paper source accompanying the submission.

---

## Overview

Natural-language DeFi workflow generators are typically evaluated by whether the output graph is structurally valid. We argue this is the wrong bar: a workflow whose graph is correct can still execute at ruinous cost if it sets a slippage bound but omits a price-impact gate.

We introduce **DeFiFlowBench**, a benchmark of 207 expert-annotated prompts scored on a four-level *safety ladder*:

1. **Graph-valid** — required nodes and edges are present
2. **Executable** — all required configuration keys carry concrete values
3. **Statically safe** — required safety predicates (slippage bound, price-impact gate, bridge confirmations) are declared and parameterized
4. **Execution-safe** — when run on a local EVM, the workflow completes without violating those predicates

Existing evaluations stop at level 1. We measure all four, and show the gap is large: no baseline exceeds 0.33 safe-executability on the held-out split, and direct, constrained, and few-shot language models each mine 15–19 swaps at ~33% self-inflicted price impact.

We also introduce **Koan-Safe**, a generator-agnostic enforcement layer that repairs workflow structure and injects conservative safety policy without fabricating trade intent. On a held-out test split authored after the method was frozen, Koan-Safe doubles safe-executability (0.67 vs. 0.33) and eliminates on-chain unsafe execution across three generators and two model families. An ablation toggling only the enforcement layer isolates it as the cause.

---

## Repository structure

```
├── data/               Prompt corpus, gold annotations, and split definitions
├── code/
│   ├── benchmark/      Dataset builder, evaluator, and baseline runners
│   ├── baselines/      Template, Koan, LLM, and Koan-Safe implementations
│   ├── safety/         EVM execution harness and mainnet fidelity validation
│   └── analysis/       Table generation, figure scripts, and statistical tests
├── results/            Raw outputs, processed metrics, tables, and figures
├── paper/
│   ├── shared/         Section .tex files shared across venue submissions
│   └── icdlt2026/      Primary venue LaTeX entrypoint and compiled PDF
└── docs/               Datasheet, reproducibility notes, and decision log
```

---

## Reproducing results

All Python steps use `uv`. The Koan baseline imports project modules from `agents/src` and runs through the agents environment; all other steps use `uv run --no-project`.

### Full pipeline

```bash
koan-submission/code/run_benchmark.sh main       # development split (120 prompts)
koan-submission/code/run_benchmark.sh heldout    # held-out test split (87 prompts)
```

### Step by step

```bash
# Build and validate the dataset
uv run --no-project python koan-submission/code/benchmark/build_dataset.py \
  --data-root koan-submission/data --split main

uv run --no-project python koan-submission/code/benchmark/validate_dataset.py \
  --data-root koan-submission/data --split main

# Run a reference baseline  (oracle | null | random_nodes | template | koan_current)
uv run --no-project python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline oracle

# Run an LLM baseline  (direct_llm | constrained_llm | fewshot_llm | safety_llm)
KOAN_LLM_MODEL="google/gemini-3.1-flash-lite" \
uv run --no-project --with "openai>=1.0" \
  python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline direct_llm --tag google_gemini-3.1-flash-lite

# Run Koan-Safe  (koan_safe_rules | koan_safe_llm | koan_safe_hybrid)
uv run --no-project python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline koan_safe_hybrid --tag google_gemini-3.1-flash-lite

# Enforcement-off ablation
KOAN_SAFE_ENFORCE=0 \
uv run --no-project python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline koan_safe_hybrid --tag google_gemini-3.1-flash-lite

# Derive tables and figures from saved outputs
uv run --no-project python koan-submission/code/analysis/make_tables.py \
  --results-root koan-submission/results --split main

uv run --no-project --with matplotlib \
  python koan-submission/code/analysis/make_figures.py \
  --results-root koan-submission/results --split heldout
```

### Rebuild the paper PDF from saved results

```bash
koan-submission/paper/build_icdlt.sh main heldout
```

Regenerates tables and figures from saved outputs and compiles with `latexmk`. No experiments are re-run.

---

## Splits

| Split | Prompts | Workflow prompts | Description |
|---|---|---|---|
| Development (`main`) | 120 | 105 | Used to characterize the structural-to-safe gap and tune Koan-Safe |
| Held-out test (`heldout`) | 87 | 75 | Evaluated once after the method was frozen; includes novel workflow structures outside all system presets |
| Metamorphic (`metamorphic`) | 68 | 68 | 34 base/variant pairs for label-free safety robustness testing |

---

## Key results (held-out test split, $n=75$)

| System | Graph-valid | Statically safe | On-chain unsafe |
|---|---|---|---|
| Oracle (ceiling) | 1.00 | 1.00 | 0 |
| Template-only | 0.52 | 0.00 | 0 |
| Direct LLM (Gemini 3.1 FL) | 0.09 | 0.03 | 19 |
| Safety-instruct LLM (Gemini 3.1 FL) | 0.33 | 0.33 | 0 |
| **Koan-Safe hybrid (Gemini 3.1 FL)** | 0.73 | **0.67** | **0** |

All rates carry 95% Wilson confidence intervals. The full table appears in the paper.

---

## Released artifacts

- Prompt corpus and gold annotations (`data/`)
- All baseline and Koan-Safe implementations (`code/baselines/`)
- EVM execution harness with mainnet fidelity validation (`code/safety/`)
- Raw model outputs and fork execution results (`results/`)
- Analysis and figure generation scripts (`code/analysis/`)
- Paper source and compiled PDF (`paper/`)

Dataset documentation is in `docs/datasheet.md`. LLM setup and reproducibility notes are in `docs/reproducibility.md`.
