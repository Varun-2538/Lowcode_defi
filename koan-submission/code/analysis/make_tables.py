"""Build summary and per-category tables from processed metrics + fork results.

A "run" is one (baseline, model) pair, identified by ``run_id``
(``baseline`` or ``baseline__<model-tag>``). Static metrics come from
``results/processed/<split>/<run_id>_metrics.json``; on-chain execution
outcomes come from ``results/fork/<split>/<run_id>_summary.json``.

Outputs (under ``results/tables``):
- ``summary.json``       : one row per run with static + fork rates.
- ``per_category.json``  : run x category structural/executable/safe.
- ``main_results.tex``   : LaTeX headline table.
- ``per_category.tex``   : LaTeX per-category table.

All numbers are derived from saved outputs; nothing is hand-edited.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats import wilson_interval  # noqa: E402


BASELINE_ORDER = [
    "oracle", "null", "random_nodes", "template", "koan_current",
    "direct_llm", "constrained_llm", "fewshot_llm", "safety_llm",
]
BASELINE_LABEL = {
    "oracle": "Oracle (ceiling)",
    "null": "Null (floor)",
    "random_nodes": "Random nodes",
    "template": "Template-only",
    "koan_current": "Koan (regex+gen)",
    "direct_llm": "Direct LLM",
    "constrained_llm": "Constrained LLM",
    "fewshot_llm": "Few-shot LLM",
    "safety_llm": "Safety-instruct LLM",
}
CATEGORIES = ["swap", "limit_order", "cross_chain", "compositional"]

MODEL_LABEL = {
    "google_gemini-3.1-flash-lite": "Gemini 3.1 FL",
    "openai_gpt-5.4-mini": "GPT-5.4 mini",
}


def _rate(rows: list[dict[str, Any]], key: str) -> float:
    return sum(1 for r in rows if r[key]) / len(rows) if rows else 0.0


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    return sum(r[key] for r in rows) / len(rows) if rows else 0.0


def _split_run_id(run_id: str) -> tuple[str, str | None]:
    if "__" in run_id:
        base, tag = run_id.split("__", 1)
        return base, tag
    return run_id, None


def _label(run_id: str) -> str:
    base, tag = _split_run_id(run_id)
    base_label = BASELINE_LABEL.get(base, base)
    if tag is None:
        return base_label
    return f"{base_label} ({MODEL_LABEL.get(tag, tag)})"


def _order_key(run_id: str) -> tuple[int, str]:
    base, tag = _split_run_id(run_id)
    base_idx = BASELINE_ORDER.index(base) if base in BASELINE_ORDER else len(BASELINE_ORDER)
    return base_idx, tag or ""


def load_metrics(results_root: Path, split: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    processed = results_root / "processed" / split
    for path in sorted(processed.glob("*_metrics.json")):
        run_id = path.name.replace("_metrics.json", "")
        out[run_id] = json.loads(path.read_text())
    return dict(sorted(out.items(), key=lambda kv: _order_key(kv[0])))


def load_fork(results_root: Path, split: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    fork_dir = results_root / "fork" / split
    if not fork_dir.exists():
        return out
    for path in sorted(fork_dir.glob("*_summary.json")):
        run_id = path.name.replace("_summary.json", "")
        out[run_id] = json.loads(path.read_text())
    return out


def summary_rows(metrics: dict[str, list[dict[str, Any]]],
                 fork: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for run_id, data in metrics.items():
        wf = [m for m in data if not m["expects_clarification"]]
        clarify = [m for m in data if m["expects_clarification"]]
        fk = fork.get(run_id, {})
        n_wf = len(wf)
        n_safe_ok = sum(1 for m in wf if m["safe_executable_proxy"])
        safe_lo, safe_hi = wilson_interval(n_safe_ok, n_wf)
        rows.append({
            "run_id": run_id,
            "label": _label(run_id),
            "n_workflow": n_wf,
            "graph_valid": _rate(wf, "graph_valid"),
            "executable": _rate(wf, "executable_proxy"),
            "safe_executable": _rate(wf, "safe_executable_proxy"),
            "safe_ci_low": safe_lo,
            "safe_ci_high": safe_hi,
            "config_completeness": _mean(wf, "config_completeness"),
            "safety_recall": _mean(wf, "safety_recall"),
            "extra_nodes": _mean(wf, "extra_nodes"),
            "clarification_correct": _rate(clarify, "clarification_correct"),
            "n_skipped": sum(1 for m in data if m["status"] == "skipped"),
            # fork (on-chain) execution outcomes
            "fork_definite": fk.get("n_attempted_definite", 0),
            "fork_safe": fk.get("n_safe", 0),
            "fork_unsafe_executed": fk.get("n_unsafe_executed", 0),
            "fork_safe_rate": fk.get("fork_safe_execution_rate", 0.0),
        })
    return rows


def per_category_rows(metrics: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows = []
    for run_id, data in metrics.items():
        for cat in CATEGORIES:
            wf = [m for m in data if m["category"] == cat and not m["expects_clarification"]]
            if not wf:
                continue
            rows.append({
                "run_id": run_id,
                "label": _label(run_id),
                "category": cat,
                "n": len(wf),
                "graph_valid": _rate(wf, "graph_valid"),
                "executable": _rate(wf, "executable_proxy"),
                "safe_executable": _rate(wf, "safe_executable_proxy"),
            })
    return rows


def _tex_escape(text: str) -> str:
    return text.replace("_", r"\_").replace("+", r"$+$").replace("%", r"\%")


def main_results_tex(rows: list[dict[str, Any]], split: str) -> str:
    n_wf = max((r["n_workflow"] for r in rows), default=0)
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Static structural/executable/safe metrics vs.\ on-chain "
        f"execution on the {split} split (${{n{{=}}{n_wf}}}$ workflow prompts). "
        r"Safe (cfg) is reported with a 95\% Wilson interval. Fork-Unsafe "
        r"counts workflows that executed on a local py-EVM at $>$5\% own-trade "
        r"price impact with no price-impact gate; Fork safe-rate is over "
        r"prompts with a definite on-chain outcome. Oracle and the "
        r"null/random baselines bound the ceiling and floor. LLM baselines run "
        r"at temperature~0.}",
        r"\label{tab:main-results}",
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r"System & Graph & Exec. & Safe (cfg) & Fork & Fork \\",
        r"       & valid & (cfg) & [95\% CI] & unsafe & safe-rate \\",
        r"\midrule",
    ]
    for r in rows:
        if r["n_skipped"] and r["graph_valid"] == 0.0:
            lines.append(
                f"{_tex_escape(r['label'])} & \\multicolumn{{5}}{{c}}{{skipped (no API key)}} \\\\"
            )
            continue
        # fork safe-rate is only meaningful when something executed on-chain
        fork_rate = f"{r['fork_safe_rate']:.2f}" if r["fork_definite"] else r"n/a"
        safe_ci = (f"{r['safe_executable']:.2f} "
                   f"[{r['safe_ci_low']:.2f},{r['safe_ci_high']:.2f}]")
        lines.append(
            f"{_tex_escape(r['label'])} & {r['graph_valid']:.2f} & {r['executable']:.2f} "
            f"& {safe_ci} & {r['fork_unsafe_executed']:d} "
            f"& {fork_rate} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def per_category_tex(rows: list[dict[str, Any]], split: str) -> str:
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Graph-valid / safe-executable rate per category "
        f"({split} split).}}",
        r"\label{tab:per-category}",
        r"\begin{tabular}{llcc}",
        r"\toprule",
        r"System & Category & Graph valid & Safe-exec. \\",
        r"\midrule",
    ]
    for r in rows:
        lines.append(
            f"{_tex_escape(r['label'])} & {_tex_escape(r['category'])} & "
            f"{r['graph_valid']:.2f} & {r['safe_executable']:.2f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--split", default="pilot")
    args = parser.parse_args()

    metrics = load_metrics(args.results_root, args.split)
    if not metrics:
        print("no processed metrics found; run run_evaluation.py first")
        return 1
    fork = load_fork(args.results_root, args.split)

    table_dir = args.results_root / "tables" / args.split
    table_dir.mkdir(parents=True, exist_ok=True)

    summary = summary_rows(metrics, fork)
    per_cat = per_category_rows(metrics)

    (table_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (table_dir / "per_category.json").write_text(json.dumps(per_cat, indent=2) + "\n")
    (table_dir / "main_results.tex").write_text(main_results_tex(summary, args.split))
    (table_dir / "per_category.tex").write_text(per_category_tex(per_cat, args.split))

    print(f"wrote tables to {table_dir}")
    for r in summary:
        tag = " (skipped)" if r["n_skipped"] else ""
        print(f"  {r['label']:<28} graph={r['graph_valid']:.2f} exec={r['executable']:.2f} "
              f"safe={r['safe_executable']:.2f} fork_unsafe={r['fork_unsafe_executed']} "
              f"fork_safe_rate={r['fork_safe_rate']:.2f}{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
