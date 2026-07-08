#!/usr/bin/env bash
# Reproduce the full pilot end-to-end from a clean checkout.
#
# Usage:
#   koan-submission/code/run_pilot.sh
#
# Requirements: uv (https://docs.astral.sh/uv/). The Koan baseline imports
# the real project modules under agents/src, so every step runs inside the
# agents uv environment via `uv run --project agents`.
#
# Non-LLM baselines (template, koan_current) run once. LLM baselines
# (direct_llm, constrained_llm) are run once per model in LLM_MODELS, each
# tagged so parallel runs never overwrite each other. Without
# OPENROUTER_API_KEY / ANTHROPIC_API_KEY the LLM runs are recorded as
# skipped, not dropped.
#
# The fork pass executes every generated workflow on a local py-EVM chain
# (real AMM + ERC20s); it is NOT a mainnet fork (no external RPC here).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUB_ROOT="$(dirname "$SCRIPT_DIR")"
REPO_ROOT="$(dirname "$SUB_ROOT")"
cd "$REPO_ROOT"

# Load LLM credentials from the (gitignored) submission .env if present.
if [ -f "$SUB_ROOT/.env" ]; then
  set -a; . "$SUB_ROOT/.env"; set +a
  echo "loaded $SUB_ROOT/.env"
fi

DATA="koan-submission/data"
RESULTS="koan-submission/results"
CODE="koan-submission/code"
SPLIT="pilot"

# Models to evaluate the LLM baselines against (OpenRouter slugs).
LLM_MODELS=("google/gemini-3.1-flash-lite" "openai/gpt-5.4-mini")

FORK_DEPS=(--with "web3>=6" --with "eth-tester[py-evm]>=0.9.0b1" --with "py-solc-x")

RUN() { echo "+ $*"; uv run --project agents "$@"; }

# tag_of "provider/model-name" -> "provider_model-name" (filesystem-safe)
tag_of() { echo "$1" | tr '/:' '__'; }

echo "== 1. (re)build pilot dataset =="
RUN python "$CODE/benchmark/build_dataset.py" --data-root "$DATA" --split "$SPLIT"

echo "== 2. validate dataset =="
RUN python "$CODE/benchmark/validate_dataset.py" --data-root "$DATA" --split "$SPLIT"

echo "== 3a. run non-LLM baselines =="
for baseline in template koan_current; do
  RUN python "$CODE/benchmark/run_evaluation.py" \
    --data-root "$DATA" --results-root "$RESULTS" \
    --split "$SPLIT" --baseline "$baseline"
done

echo "== 3b. run LLM baselines per model =="
for model in "${LLM_MODELS[@]}"; do
  tag="$(tag_of "$model")"
  echo "-- model: $model (tag=$tag) --"
  for baseline in direct_llm constrained_llm; do
    KOAN_LLM_MODEL="$model" RUN python "$CODE/benchmark/run_evaluation.py" \
      --data-root "$DATA" --results-root "$RESULTS" \
      --split "$SPLIT" --baseline "$baseline" --tag "$tag"
  done
done

echo "== 4. fork execution pass (local py-EVM; deps pulled on demand) =="
uv run --no-project "${FORK_DEPS[@]}" python \
  "$CODE/safety/fork_simulation.py" --results-root "$RESULTS" --split "$SPLIT" || true

echo "== 5. build tables =="
RUN python "$CODE/analysis/make_tables.py" --results-root "$RESULTS" --split "$SPLIT"

echo "== 6. build figure (matplotlib on demand) =="
uv run --no-project --with matplotlib python \
  "$CODE/analysis/make_figures.py" --results-root "$RESULTS" --split "$SPLIT" || true

echo "== done: see $RESULTS/tables, $RESULTS/figures, $RESULTS/fork =="
