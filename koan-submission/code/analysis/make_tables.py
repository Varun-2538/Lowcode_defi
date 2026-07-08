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
    "koan_safe_rules", "koan_safe_llm", "koan_safe_hybrid",
    # enforcement-off ablations sort last
    "koan_safe_rules__noenforce", "koan_safe_llm__noenforce",
    "koan_safe_hybrid__noenforce",
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
    "koan_safe_rules": "Koan-Safe (rules)",
    "koan_safe_llm": "Koan-Safe (LLM)",
    "koan_safe_hybrid": "Koan-Safe (hybrid)",
}
CATEGORIES = ["swap", "limit_order", "cross_chain", "compositional"]

MODEL_LABEL = {
    "google_gemini-3.1-flash-lite": "Gemini 3.1 FL",
    "openai_gpt-5.4-mini": "GPT-5.4 mini",
    "noenforce": "no enforce",
}

# Koan-Safe systems whose enforcement layer can be toggled off for ablation.
KOAN_SAFE_SYSTEMS = ["koan_safe_rules", "koan_safe_llm", "koan_safe_hybrid"]


def _is_ablation(run_id: str) -> bool:
    """True for enforcement-off ablation runs (tag ends in 'noenforce')."""
    _base, tag = _split_run_id(run_id)
    return tag is not None and tag.endswith("noenforce")


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
    # a tag may be "<model>" or "<model>__noenforce" or "noenforce"
    parts = [MODEL_LABEL.get(p, p) for p in tag.split("__")]
    return f"{base_label} ({', '.join(parts)})"


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


SPLIT_DISPLAY = {
    "main": "development",
    "heldout": "held-out test",
    "pilot": "pilot",
}

# Row groups for the main table, separated by midrules.
REFERENCE_BASES = {"oracle", "null", "random_nodes"}
PROPOSED_BASES = set(KOAN_SAFE_SYSTEMS)


def main_results_tex(rows: list[dict[str, Any]], split: str) -> str:
    n_wf = max((r["n_workflow"] for r in rows), default=0)
    split_name = SPLIT_DISPLAY.get(split, split)
    # bold the best non-reference safe-executability
    non_ref = [r for r in rows
               if _split_run_id(r["run_id"])[0] not in REFERENCE_BASES]
    best_safe = max((r["safe_executable"] for r in non_ref), default=None)
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{\textbf{Main results on the " + split_name + " split} "
        f"(${{n{{=}}{n_wf}}}$ workflow prompts). Static levels of the safety "
        r"ladder (graph-valid, executable, statically safe with a 95\% Wilson "
        r"interval) and on-chain outcomes on the local EVM: Unsafe counts "
        r"workflows that mined at $>$5\% own-trade price impact with no "
        r"price-impact gate; safe-rate is over prompts with a definite "
        r"on-chain outcome. Oracle and null/random baselines calibrate the "
        r"ceiling and floor. LLM systems run at temperature~0; the best "
        r"non-reference safe rate is \textbf{bold}.}",
        r"\label{tab:main-results}",
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r" & \multicolumn{3}{c}{Static safety-ladder levels} & "
        r"\multicolumn{2}{c}{On-chain (local EVM)} \\",
        r"\cmidrule(lr){2-4}\cmidrule(lr){5-6}",
        r"System & Graph-valid & Executable & Statically safe [CI] "
        r"& Unsafe & Safe-rate \\",
        r"\midrule",
    ]
    prev_group = None
    for r in rows:
        base, _ = _split_run_id(r["run_id"])
        group = ("ref" if base in REFERENCE_BASES
                 else "proposed" if base in PROPOSED_BASES else "baseline")
        if prev_group is not None and group != prev_group:
            lines.append(r"\midrule")
        prev_group = group
        if r["n_skipped"] and r["graph_valid"] == 0.0:
            lines.append(
                f"{_tex_escape(r['label'])} & \\multicolumn{{5}}{{c}}{{skipped (no API key)}} \\\\"
            )
            continue
        # fork safe-rate is only meaningful when something executed on-chain
        fork_rate = f"{r['fork_safe_rate']:.2f}" if r["fork_definite"] else r"--"
        safe_val = f"{r['safe_executable']:.2f}"
        if group != "ref" and best_safe is not None and \
                abs(r["safe_executable"] - best_safe) < 1e-9:
            safe_val = rf"\textbf{{{safe_val}}}"
        safe_ci = (f"{safe_val} "
                   f"[{r['safe_ci_low']:.2f},{r['safe_ci_high']:.2f}]")
        unsafe = str(r["fork_unsafe_executed"]) if r["fork_definite"] else "--"
        lines.append(
            f"{_tex_escape(r['label'])} & {r['graph_valid']:.2f} & {r['executable']:.2f} "
            f"& {safe_ci} & {unsafe} "
            f"& {fork_rate} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def per_category_tex(rows: list[dict[str, Any]], split: str) -> str:
    """Pivoted per-category table: one row per system, category columns.

    Graph-valid (G) and safe-executable (S) are shown side by side for each
    category. The trivially-constant reference baselines (oracle/null/random/
    template) are omitted here -- they are reported in the main table -- so the
    table stays compact and fits a two-column page as a full-width float.
    """
    skip = {"oracle", "null", "random_nodes", "template"}
    cat_short = {"swap": "Swap", "limit_order": "Limit",
                 "cross_chain": "Cross", "compositional": "Compo"}
    # group rows by run label, preserving BASELINE_ORDER via input order
    by_label: dict[str, dict[str, dict[str, float]]] = {}
    order: list[str] = []
    for r in rows:
        base, _ = _split_run_id(r["run_id"])
        if base in skip:
            continue
        if r["label"] not in by_label:
            by_label[r["label"]] = {}
            order.append(r["label"])
        by_label[r["label"]][r["category"]] = r

    header_cat = " & ".join(fr"\multicolumn{{2}}{{c}}{{{cat_short[c]}}}"
                            for c in CATEGORIES)
    subhdr = " & ".join(["G & S"] * len(CATEGORIES))
    split_name = SPLIT_DISPLAY.get(split, split)
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Per-category graph-valid (G) and statically-safe (S) rate "
        f"on the {split_name} split. Reference floor/ceiling baselines "
        r"(all constant) are omitted; see Table~\ref{tab:main-results}.}",
        r"\label{tab:per-category}",
        r"\begin{tabular}{l" + "cc" * len(CATEGORIES) + "}",
        r"\toprule",
        f"System & {header_cat} \\\\",
        f"& {subhdr} \\\\",
        r"\midrule",
    ]
    for label in order:
        cats = by_label[label]
        cells = []
        for c in CATEGORIES:
            r = cats.get(c)
            if r is None:
                cells.append("-- & --")
            else:
                cells.append(f"{r['graph_valid']:.2f} & {r['safe_executable']:.2f}")
        lines.append(f"{_tex_escape(label)} & " + " & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}", ""]
    return "\n".join(lines)


def enforcement_ablation_rows(summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pair each Koan-Safe run with its enforcement-off ablation.

    A row is emitted only when both the enforced and the ``__noenforce``
    variant of the same (system, model) exist, so the delta is a like-for-like
    measurement of the enforcement layer's effect.
    """
    by_id = {r["run_id"]: r for r in summary}
    rows: list[dict[str, Any]] = []
    for run_id, r in by_id.items():
        if _is_ablation(run_id):
            continue
        base, tag = _split_run_id(run_id)
        if base not in KOAN_SAFE_SYSTEMS:
            continue
        off_id = f"{base}__noenforce" if tag is None else f"{base}__{tag}__noenforce"
        off = by_id.get(off_id)
        if off is None:
            continue
        rows.append({
            "system": r["label"],
            "on_safe": r["safe_executable"], "off_safe": off["safe_executable"],
            "on_exec": r["executable"], "off_exec": off["executable"],
            "on_fork_unsafe": r["fork_unsafe_executed"],
            "off_fork_unsafe": off["fork_unsafe_executed"],
            "on_fork_rate": r["fork_safe_rate"], "off_fork_rate": off["fork_safe_rate"],
        })
    return rows


def enforcement_ablation_tex(rows: list[dict[str, Any]], split: str) -> str:
    split_name = SPLIT_DISPLAY.get(split, split)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Enforcement-layer ablation on the "
        f"{split_name} split: each Koan-Safe generator with the "
        r"safety-enforcement layer on vs.\ off (same parser and generator; "
        r"LLM and hybrid use Gemini~3.1~FL). The layer is what drives "
        r"on-chain unsafe executions to zero.}",
        r"\label{tab:enforcement-ablation}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r" & \multicolumn{2}{c}{Statically safe} & "
        r"\multicolumn{2}{c}{On-chain unsafe} \\",
        r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
        r"System & off & on & off & on \\",
        r"\midrule",
    ]
    for r in rows:
        # strip the model suffix; the caption states the model family
        label = r["system"].split(" (Gemini")[0].split(" (GPT")[0]
        lines.append(
            f"{_tex_escape(label)} & {r['off_safe']:.2f} & {r['on_safe']:.2f} "
            f"& {r['off_fork_unsafe']:d} & {r['on_fork_unsafe']:d} \\\\"
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

    # The enforcement-off runs belong only in the ablation table.
    main_summary = [r for r in summary if not _is_ablation(r["run_id"])]
    main_percat = [r for r in per_cat if not _is_ablation(r["run_id"])]

    (table_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (table_dir / "per_category.json").write_text(json.dumps(per_cat, indent=2) + "\n")
    (table_dir / "main_results.tex").write_text(main_results_tex(main_summary, args.split))
    (table_dir / "per_category.tex").write_text(per_category_tex(main_percat, args.split))

    ablation = enforcement_ablation_rows(summary)
    if ablation:
        (table_dir / "enforcement_ablation.json").write_text(
            json.dumps(ablation, indent=2) + "\n")
        (table_dir / "enforcement_ablation.tex").write_text(
            enforcement_ablation_tex(ablation, args.split))

    print(f"wrote tables to {table_dir}")
    for r in summary:
        tag = " (skipped)" if r["n_skipped"] else ""
        print(f"  {r['label']:<28} graph={r['graph_valid']:.2f} exec={r['executable']:.2f} "
              f"safe={r['safe_executable']:.2f} fork_unsafe={r['fork_unsafe_executed']} "
              f"fork_safe_rate={r['fork_safe_rate']:.2f}{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
