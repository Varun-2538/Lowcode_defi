#!/usr/bin/env bash
# Regenerate the ICDLT paper from saved results and build the PDF.
#
# Usage: paper/build_icdlt.sh [split]   # split defaults to "main"
#
# Assumes the split has already been evaluated (results/processed/<split> and
# results/fork/<split> exist). It does NOT re-run experiments; it re-derives
# tables/analyses from saved outputs, copies the paper-facing assets, and
# compiles with latexmk.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # paper/
SUB_ROOT="$(dirname "$SCRIPT_DIR")"                          # koan-submission/
REPO_ROOT="$(dirname "$SUB_ROOT")"
cd "$REPO_ROOT"

RESULTS="koan-submission/results"
DATA="koan-submission/data"
PAPER="koan-submission/paper/icdlt2026"

# The paper reports two splits: the development split (default "main") that
# characterizes the gap and tunes Koan-Safe, and the held-out TEST split that
# measures generalization. Both are regenerated; the held-out tables are the
# paper's primary results.
DEV_SPLIT="${1:-main}"
TEST_SPLIT="${2:-heldout}"
MM_SPLIT="${3:-metamorphic}"

for SPLIT in "$DEV_SPLIT" "$TEST_SPLIT"; do
  echo "== regenerate tables + analyses from processed metrics ($SPLIT) =="
  uv run --no-project python koan-submission/code/analysis/make_tables.py \
    --results-root "$RESULTS" --split "$SPLIT"
  uv run --no-project python koan-submission/code/analysis/analyze.py \
    --results-root "$RESULTS" --data-root "$DATA" --split "$SPLIT" || true
  uv run --no-project --with matplotlib python \
    koan-submission/code/analysis/make_figures.py --results-root "$RESULTS" --split "$SPLIT" || true
done

echo "== regenerate metamorphic + cost tables ($MM_SPLIT) =="
uv run --no-project python koan-submission/code/analysis/metamorphic.py \
  --results-root "$RESULTS" --data-root "$DATA" || true
uv run --no-project python koan-submission/code/analysis/cost.py \
  --results-root "$RESULTS" --split "$MM_SPLIT" --price-per-mtok 0.30 || true

echo "== copy paper-facing assets =="
# Primary results = the held-out TEST split.
cp "$RESULTS/tables/$TEST_SPLIT/main_results.tex" "$PAPER/tables/main_results.tex"
cp "$RESULTS/tables/$TEST_SPLIT/per_category.tex" "$PAPER/tables/per_category.tex"
cp "$RESULTS/tables/$TEST_SPLIT/enforcement_ablation.tex" "$PAPER/tables/enforcement_ablation.tex"
cp "$RESULTS/figures/$TEST_SPLIT/structural_vs_safe.png" "$PAPER/figures/structural_vs_safe.png"
# Development-split results, referenced in the text and shown in an appendix-style table.
cp "$RESULTS/tables/$DEV_SPLIT/main_results.tex" "$PAPER/tables/main_results_dev.tex"
cp "$RESULTS/tables/$DEV_SPLIT/enforcement_ablation.tex" "$PAPER/tables/enforcement_ablation_dev.tex"
# Metamorphic safety suite and cost/latency tables.
cp "$RESULTS/tables/$MM_SPLIT/metamorphic.tex" "$PAPER/tables/metamorphic.tex"
cp "$RESULTS/tables/$MM_SPLIT/cost.tex" "$PAPER/tables/cost.tex"
# Mainnet-fidelity table (generated out-of-band by code/safety/fork_fidelity.py,
# which needs an RPC endpoint; copied if present so the build stays offline).
if [ -f "$RESULTS/tables/mainnet/fidelity.tex" ]; then
  cp "$RESULTS/tables/mainnet/fidelity.tex" "$PAPER/tables/fidelity.tex"
fi

echo "== build PDF =="
( cd "$PAPER" && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex >/dev/null )
echo "== built $PAPER/main.pdf =="
