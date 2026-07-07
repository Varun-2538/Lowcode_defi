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
SPLIT="${1:-main}"

echo "== regenerate tables + analyses from processed metrics ($SPLIT) =="
uv run --no-project python koan-submission/code/analysis/make_tables.py \
  --results-root "$RESULTS" --split "$SPLIT"
uv run --no-project python koan-submission/code/analysis/analyze.py \
  --results-root "$RESULTS" --data-root "$DATA" --split "$SPLIT" || true
uv run --no-project --with matplotlib python \
  koan-submission/code/analysis/make_figures.py --results-root "$RESULTS" --split "$SPLIT" || true

echo "== copy paper-facing assets =="
cp "$RESULTS/tables/$SPLIT/main_results.tex" "$PAPER/tables/main_results.tex"
cp "$RESULTS/tables/$SPLIT/per_category.tex" "$PAPER/tables/per_category.tex"
cp "$RESULTS/figures/$SPLIT/structural_vs_safe.png" "$PAPER/figures/structural_vs_safe.png"

echo "== build PDF =="
( cd "$PAPER" && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex >/dev/null )
echo "== built $PAPER/main.pdf =="
