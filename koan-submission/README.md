# DeFiFlowBench

**Benchmarking and Improving Safe Executability in Natural-Language DeFi Workflow Synthesis**

This workspace contains the benchmark, code, results, and paper source for the ICDLT 2026 submission (fallback: ICSTCEE 2026).

---

## Overview

Natural-language DeFi workflow generators are typically evaluated by whether the output graph is structurally valid. We show this bar is dangerously low. A workflow whose graph is correct can still mine a trade at severe self-inflicted price impact if it sets a slippage bound but omits a price-impact gate.

We introduce **DeFiFlowBench**: 207 expert-annotated prompts spanning swaps, limit orders, cross-chain transfers, and compositional tasks, scored on a four-level *safety ladder* (graph-valid → executable → statically safe → execution-safe). The top level is measured by executing each generated swap on a local EVM with deployed AMM and ERC20 contracts.

We evaluate eight baseline families and propose **Koan-Safe**, a generator-agnostic enforcement layer that repairs workflow structure and injects conservative safety policy. On the held-out test split authored after the method was frozen, Koan-Safe doubles safe-executability (0.67 vs. 0.33) and eliminates on-chain unsafe execution across three generators and two model families.

---

## Repository layout

```
koan-submission/
├── data/               Prompt corpus, gold annotations, split definitions
├── code/
│   ├── benchmark/      Dataset builder, evaluator, baseline runners
│   ├── baselines/      Template, Koan, LLM, and Koan-Safe implementations
│   ├── safety/         EVM harness, fork fidelity validation
│   └── analysis/       Table generation, figure scripts, statistical tests
├── results/            Raw outputs, processed metrics, tables, figures
├── paper/
│   ├── shared/         Section .tex files (shared across venues)
│   ├── icdlt2026/      ICDLT 2026 entrypoint (main venue)
│   └── icstcee2026/    ICSTCEE 2026 fallback entrypoint
└── docs/               Datasheet, reproducibility notes, decision log
```

---

## Reproducing results

All Python steps use `uv`. The Koan baseline imports real project modules from `agents/src` and runs through the agents environment; everything else runs with `uv run --no-project`.

### Full pipeline (both splits)

```bash
koan-submission/code/run_benchmark.sh main       # development split (120 prompts)
koan-submission/code/run_benchmark.sh heldout    # held-out test split (87 prompts)
```

### Step by step

```bash
# 1. Build and validate the dataset
uv run --no-project python koan-submission/code/benchmark/build_dataset.py \
  --data-root koan-submission/data --split main

uv run --no-project python koan-submission/code/benchmark/validate_dataset.py \
  --data-root koan-submission/data --split main

# 2. Run a reference baseline (oracle | null | random_nodes | template | koan_current)
uv run --no-project python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline oracle

# 3. Run an LLM baseline (direct_llm | constrained_llm | fewshot_llm | safety_llm)
KOAN_LLM_MODEL="google/gemini-3.1-flash-lite" \
uv run --no-project --with "openai>=1.0" \
  python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline direct_llm --tag google_gemini-3.1-flash-lite

# 4. Run Koan-Safe (rules | llm | hybrid) with and without enforcement
uv run --no-project python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline koan_safe_hybrid --tag google_gemini-3.1-flash-lite

KOAN_SAFE_ENFORCE=0 \
uv run --no-project python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline koan_safe_hybrid --tag google_gemini-3.1-flash-lite

# 5. Derive tables, figures, and analyses from saved outputs
uv run --no-project python koan-submission/code/analysis/make_tables.py \
  --results-root koan-submission/results --split main

uv run --no-project python koan-submission/code/analysis/analyze.py \
  --results-root koan-submission/results --data-root koan-submission/data --split main

uv run --no-project --with matplotlib \
  python koan-submission/code/analysis/make_figures.py \
  --results-root koan-submission/results --split heldout
```

### Rebuild the paper PDF (no experiments re-run)

```bash
koan-submission/paper/build_icdlt.sh main heldout
```

Regenerates tables and figures from saved results, copies assets into `paper/icdlt2026/`, and compiles with `latexmk`. The held-out split is used for the primary results.

---

## Splits

| Split | Prompts | Workflow prompts | Purpose |
|---|---|---|---|
| `main` (development) | 120 | 105 | Characterizes the structural-to-safe gap; Koan-Safe was tuned here |
| `heldout` (test) | 87 | 75 | Frozen evaluation; includes novel workflow structures outside all presets |
| `metamorphic` | 68 | 68 | Label-free robustness suite; 34 base/variant pairs |

---

## Key results (held-out test split)

| System | Graph-valid | Statically safe | On-chain unsafe |
|---|---|---|---|
| Oracle (ceiling) | 1.00 | 1.00 | 0 |
| Direct LLM (Gemini 3.1 FL) | 0.09 | 0.03 | 19 |
| Safety-instruct LLM (Gemini 3.1 FL) | 0.33 | 0.33 | 0 |
| Koan-Safe (hybrid, Gemini 3.1 FL) | 0.73 | **0.67** | **0** |

All rates carry 95% Wilson confidence intervals; see Table I in the paper for the full table.

---

## Artifact contents

Released with the paper:
- Prompt corpus and gold annotations (`data/`)
- All baseline implementations (`code/baselines/`)
- EVM execution harness (`code/safety/`)
- Raw model outputs and saved fork results (`results/`)
- Analysis and figure generation scripts (`code/analysis/`)
- Paper source (`paper/`)

See `docs/datasheet.md` for dataset documentation and `docs/reproducibility.md` for LLM-baseline setup (API keys, model tags, reproducibility notes).

---

## Evidence policy

Legacy material under `archive/` is preserved for reference only. Prior benchmark numbers from earlier drafts should not be reused as evidence in the ICDLT or ICSTCEE submission.
