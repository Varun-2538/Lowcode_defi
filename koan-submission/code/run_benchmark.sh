#!/usr/bin/env bash
# Reproduce a full DeFiFlowBench split end-to-end from a clean checkout.
#
# Usage:
#   koan-submission/code/run_benchmark.sh [split]      # split defaults to "main"
#
# Requirements: uv (https://docs.astral.sh/uv/). The Koan baseline imports the
# real project modules under agents/src, so those steps run inside the agents
# uv environment via `uv run --project agents`.
#
# Baselines:
#   Reference (offline, free):  oracle (ceiling), null + random_nodes (floor),
#                               template, koan_current (real Koan, offline).
#   LLM (need OPENROUTER_API_KEY / ANTHROPIC_API_KEY), one run per model:
#     direct_llm, constrained_llm, fewshot_llm (few-shot ablation),
#     safety_llm (safety-instruction ablation).
#   Without a key the LLM runs are recorded as skipped, not dropped.
#
# The fork pass executes every generated workflow on a local py-EVM chain
# (real AMM + ERC20s); it is NOT a mainnet fork (no external RPC here).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUB_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$SUB_ROOT")"
cd "$REPO_ROOT"

if [ -f "$SUB_ROOT/.env" ]; then
  set -a; . "$SUB_ROOT/.env"; set +a
  echo "loaded $SUB_ROOT/.env"
fi

DATA="koan-submission/data"
RESULTS="koan-submission/results"
CODE="koan-submission/code"
SPLIT="${1:-main}"

LLM_MODELS=("google/gemini-3.1-flash-lite" "openai/gpt-5.4-mini")
LLM_BASELINES=(direct_llm constrained_llm fewshot_llm safety_llm)
FORK_DEPS=(--with "web3>=6" --with "eth-tester[py-evm]>=0.9.0b1" --with "py-solc-x")

RUN_AGENTS() { echo "+ (agents) $*"; uv run --project agents "$@"; }
RUN_PLAIN()  { echo "+ $*"; uv run --no-project "$@"; }
RUN_LLM()    { echo "+ (llm) $*"; uv run --no-project --with "openai>=1.0" "$@"; }
tag_of() { echo "$1" | tr '/:' '__'; }

echo "== 1. (re)build dataset ($SPLIT) =="
RUN_PLAIN python "$CODE/benchmark/build_dataset.py" --data-root "$DATA" --split "$SPLIT"

echo "== 2. validate dataset =="
RUN_PLAIN python "$CODE/benchmark/validate_dataset.py" --data-root "$DATA" --split "$SPLIT"

echo "== 3a. reference baselines (offline) =="
for baseline in oracle null random_nodes template; do
  RUN_PLAIN python "$CODE/benchmark/run_evaluation.py" \
    --data-root "$DATA" --results-root "$RESULTS" --split "$SPLIT" --baseline "$baseline"
done
# koan_current needs the agents environment for its real imports.
RUN_AGENTS python "$CODE/benchmark/run_evaluation.py" \
  --data-root "$DATA" --results-root "$RESULTS" --split "$SPLIT" --baseline koan_current

echo "== 3b. LLM baselines + ablations, per model =="
for model in "${LLM_MODELS[@]}"; do
  tag="$(tag_of "$model")"
  echo "-- model: $model (tag=$tag) --"
  for baseline in "${LLM_BASELINES[@]}"; do
    KOAN_LLM_MODEL="$model" RUN_LLM python "$CODE/benchmark/run_evaluation.py" \
      --data-root "$DATA" --results-root "$RESULTS" \
      --split "$SPLIT" --baseline "$baseline" --tag "$tag"
  done
done

echo "== 4. fork execution pass (local py-EVM) =="
RUN_PLAIN "${FORK_DEPS[@]}" python \
  "$CODE/safety/fork_simulation.py" --results-root "$RESULTS" --split "$SPLIT" || true

echo "== 5. tables =="
RUN_PLAIN python "$CODE/analysis/make_tables.py" --results-root "$RESULTS" --split "$SPLIT"

echo "== 6. deeper analyses (CIs, construct validity, failure taxonomy, robustness) =="
RUN_PLAIN python "$CODE/analysis/analyze.py" \
  --results-root "$RESULTS" --data-root "$DATA" --split "$SPLIT"

echo "== 7. figure =="
uv run --no-project --with matplotlib python \
  "$CODE/analysis/make_figures.py" --results-root "$RESULTS" --split "$SPLIT" || true

echo "== done: see $RESULTS/tables/$SPLIT, $RESULTS/figures/$SPLIT, "
echo "   $RESULTS/fork/$SPLIT, $RESULTS/analysis/$SPLIT =="
