#!/usr/bin/env bash
# Regenerate the ICDLT paper from saved results and build the PDF.
#
# Assumes the pilot has already run (results/tables/*.tex exist). It does
# NOT re-run experiments; it only re-derives tables from processed metrics,
# copies the paper-facing assets, and compiles with latexmk.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # paper/
SUB_ROOT="$(dirname "$SCRIPT_DIR")"                          # koan-submission/
REPO_ROOT="$(dirname "$SUB_ROOT")"
cd "$REPO_ROOT"

RESULTS="koan-submission/results"
PAPER="koan-submission/paper/icdlt2026"

echo "== regenerate tables from processed metrics =="
uv run --no-project python koan-submission/code/analysis/make_tables.py \
  --results-root "$RESULTS" --split pilot
uv run --no-project --with matplotlib python \
  koan-submission/code/analysis/make_figures.py --results-root "$RESULTS" --split pilot || true

echo "== copy paper-facing assets =="
cp "$RESULTS/tables/main_results.tex" "$PAPER/tables/main_results.tex"
cp "$RESULTS/tables/per_category.tex" "$PAPER/tables/per_category.tex"
cp "$RESULTS/figures/structural_vs_safe.png" "$PAPER/figures/structural_vs_safe.png"

echo "== build PDF =="
( cd "$PAPER" && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex >/dev/null )
echo "== built $PAPER/main.pdf =="
