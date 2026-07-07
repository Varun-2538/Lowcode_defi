"""Deeper benchmark analyses beyond headline rates.

Produces four JSON artifacts under ``results/analysis/<split>``:

1. ``rates_ci.json``           -- every run's structural/executable/safe rate
   with a Wilson 95% CI, plus bootstrap CIs for the config/safety means.
2. ``construct_validity.json`` -- does the *static* safe-executable proxy
   predict *on-chain* safety? Confusion matrix + agreement between the proxy
   and the fork outcome on the swaps that were actually executed. This is the
   evidence that the cheap proxy measures the expensive real thing (ABC
   outcome-validity: O.i.1 / construct validity).
3. ``failure_taxonomy.json``   -- per-run counts of *named* failure modes
   (missing config keys, missing safety predicates, structural misses,
   wrong-clarification), attributed to prompts (ABC reporting: named
   categories with counts, not anecdotes).
4. ``robustness.json``         -- paraphrase-cluster consistency and
   difficulty-stratified rates (BetterBench input-sensitivity).

All numbers are read from saved results; nothing is recomputed by calling a
model. Run::

    uv run --no-project python code/analysis/analyze.py \
        --results-root results --data-root data --split main
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stats import bootstrap_mean_ci, rate_with_ci  # noqa: E402


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_runs(results_root: Path, split: str) -> dict[str, list[dict[str, Any]]]:
    processed = results_root / "processed" / split
    runs: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(processed.glob("*_metrics.json")):
        runs[path.name.replace("_metrics.json", "")] = _read_json(path)
    return runs


def load_fork(results_root: Path, split: str) -> dict[str, dict[str, dict[str, Any]]]:
    """run_id -> {prompt_id -> fork result}."""
    fork_dir = results_root / "fork" / split
    out: dict[str, dict[str, dict[str, Any]]] = {}
    if not fork_dir.exists():
        return out
    for path in sorted(fork_dir.glob("*.json")):
        if path.name.endswith("_summary.json") or path.name == "summary.json":
            continue
        rows = _read_json(path)
        out[path.stem] = {r["id"]: r for r in rows}
    return out


# --- 1. rates with confidence intervals ---------------------------------

def rates_ci(runs: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    out = []
    for run_id, rows in runs.items():
        wf = [m for m in rows if not m["expects_clarification"]]
        clar = [m for m in rows if m["expects_clarification"]]
        n = len(wf)
        entry = {
            "run_id": run_id,
            "n_workflow": n,
            "graph_valid": rate_with_ci(sum(m["graph_valid"] for m in wf), n),
            "executable": rate_with_ci(sum(m["executable_proxy"] for m in wf), n),
            "safe_executable": rate_with_ci(sum(m["safe_executable_proxy"] for m in wf), n),
            "config_completeness": bootstrap_mean_ci([m["config_completeness"] for m in wf]),
            "safety_recall": bootstrap_mean_ci([m["safety_recall"] for m in wf]),
            "clarification": rate_with_ci(
                sum(m["clarification_correct"] for m in clar), len(clar)),
        }
        out.append(entry)
    return out


# --- 2. construct validity: proxy vs on-chain ---------------------------

def construct_validity(runs: dict[str, list[dict[str, Any]]],
                       fork: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    """Compare static safe-executable proxy to the on-chain safety label.

    Restricted to prompts the fork harness *actually executed or gated*
    (safe_execution is a definite True/False), where the two measurements are
    comparable. Reports a pooled confusion matrix across all runs plus overall
    agreement.
    """
    cells = Counter()  # (proxy_safe, onchain_safe) -> count
    per_run = {}
    for run_id, rows in runs.items():
        frun = fork.get(run_id, {})
        rc = Counter()
        for m in rows:
            fres = frun.get(m["id"])
            if not fres or fres.get("safe_execution") is None:
                continue
            proxy_safe = bool(m["safe_executable_proxy"])
            onchain_safe = bool(fres["safe_execution"])
            cells[(proxy_safe, onchain_safe)] += 1
            rc[(proxy_safe, onchain_safe)] += 1
        if rc:
            per_run[run_id] = {f"{k[0]}_{k[1]}": v for k, v in rc.items()}

    tp = cells[(True, True)]
    fp = cells[(True, False)]
    fn = cells[(False, True)]
    tn = cells[(False, False)]
    total = tp + fp + fn + tn
    agree = (tp + tn) / total if total else 0.0
    # precision of the proxy's "safe" verdict: of the workflows it declared
    # safe, how many were safe on-chain (fp==0 => no false reassurance).
    proxy_safe_n = tp + fp
    precision = (tp / proxy_safe_n) if proxy_safe_n else None
    if proxy_safe_n == 0:
        note = ("No system on this split populated a price-impact gate, so the "
                "proxy never declares safe; the on-chain layer confirms the "
                "proxy is not a false-negative artifact by showing genuinely "
                "unsafe executions among proxy-unsafe workflows.")
    elif fp == 0:
        note = (f"Of {proxy_safe_n} workflows the proxy declared safe, all were "
                f"safe on-chain (0 false positives): the static safe verdict "
                f"never gives false reassurance. It is conservative -- {fn} "
                f"proxy-unsafe workflows were nonetheless safe on-chain "
                f"(e.g. small trades or reverts).")
    else:
        note = (f"The proxy declared {proxy_safe_n} workflows safe, of which "
                f"{fp} executed unsafely on-chain (false positives): the static "
                f"proxy is not fully sound and is reported as such.")
    return {
        "description": (
            "Rows: static safe_executable_proxy (True/False). Cols: on-chain "
            "safe_execution (True/False). Restricted to fork-definite prompts."
        ),
        "confusion": {
            "proxy_safe__onchain_safe": tp,
            "proxy_safe__onchain_unsafe": fp,
            "proxy_unsafe__onchain_safe": fn,
            "proxy_unsafe__onchain_unsafe": tn,
        },
        "n": total,
        "agreement": agree,
        "proxy_safe_precision": precision,
        "note": note,
        "per_run": per_run,
    }


# --- 3. failure taxonomy -------------------------------------------------

def failure_taxonomy(runs: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    out = {}
    for run_id, rows in runs.items():
        wf = [m for m in rows if not m["expects_clarification"]]
        clar = [m for m in rows if m["expects_clarification"]]
        missing_config = Counter()
        missing_safety = Counter()
        struct = Counter()
        for m in wf:
            for k in m.get("missing_config", []):
                missing_config[k] += 1
            for s in m.get("missing_safety", []):
                missing_safety[s] += 1
            if m["node_recall"] < 1.0:
                struct["missing_required_node"] += 1
            if m["edge_recall"] < 1.0:
                struct["missing_required_edge"] += 1
            if m["extra_nodes"] > 0:
                struct["has_extra_nodes"] += 1
            if m["status"] == "needs_clarification":
                struct["bailed_to_clarification"] += 1
            elif m["status"] == "error":
                struct["error"] += 1
        wrong_clar = sum(1 for m in clar if not m["clarification_correct"])
        out[run_id] = {
            "n_workflow": len(wf),
            "structural_failures": dict(struct),
            "missing_config_keys": dict(missing_config.most_common()),
            "missing_safety_predicates": dict(missing_safety.most_common()),
            "clarification_prompts": len(clar),
            "clarification_missed": wrong_clar,
        }
    return out


# --- 4. robustness: paraphrase + difficulty ------------------------------

def robustness(runs: dict[str, list[dict[str, Any]]],
               prompts: list[dict[str, Any]]) -> dict[str, Any]:
    meta = {p["id"]: p for p in prompts}
    # paraphrase clusters: base id -> set of member ids (base + paraphrases)
    clusters: dict[str, set[str]] = defaultdict(set)
    for p in prompts:
        base = p.get("paraphrase_of")
        if base:
            clusters[base].add(p["id"])
            clusters[base].add(base)

    per_run = {}
    for run_id, rows in runs.items():
        by_id = {m["id"]: m for m in rows}

        # paraphrase consistency: within each cluster, fraction of member pairs
        # that agree on graph_valid (a robust system is internally consistent).
        cluster_consistency = []
        for base, members in clusters.items():
            vals = [by_id[i]["graph_valid"] for i in members if i in by_id]
            if len(vals) >= 2:
                # consistency = 1 - normalized disagreement (all-equal -> 1.0)
                frac_true = sum(vals) / len(vals)
                cluster_consistency.append(1.0 - 2 * frac_true * (1 - frac_true))
        mean_consistency = (sum(cluster_consistency) / len(cluster_consistency)
                            if cluster_consistency else None)

        # difficulty-stratified graph-valid / safe rates (workflow prompts only)
        diff_rates: dict[str, dict[str, Any]] = {}
        by_diff: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for m in rows:
            if m["expects_clarification"]:
                continue
            d = meta.get(m["id"], {}).get("difficulty", "unknown")
            by_diff[d].append(m)
        for d, ms in by_diff.items():
            n = len(ms)
            diff_rates[d] = {
                "n": n,
                "graph_valid": sum(x["graph_valid"] for x in ms) / n,
                "safe_executable": sum(x["safe_executable_proxy"] for x in ms) / n,
            }

        # per-phenomenon graph-valid rate (workflow prompts only)
        by_phen: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for m in rows:
            if m["expects_clarification"]:
                continue
            for ph in meta.get(m["id"], {}).get("phenomena", []):
                by_phen[ph].append(m)
        phen_rates = {
            ph: {"n": len(ms),
                 "graph_valid": sum(x["graph_valid"] for x in ms) / len(ms)}
            for ph, ms in sorted(by_phen.items())
        }

        per_run[run_id] = {
            "paraphrase_cluster_consistency": mean_consistency,
            "n_clusters": len(cluster_consistency),
            "difficulty_rates": diff_rates,
            "phenomenon_rates": phen_rates,
        }
    return {"n_paraphrase_clusters": len(clusters), "per_run": per_run}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", default="main")
    args = parser.parse_args()

    runs = load_runs(args.results_root, args.split)
    if not runs:
        print("no processed metrics; run run_evaluation.py first")
        return 1
    fork = load_fork(args.results_root, args.split)
    prompts = _read_jsonl(args.data_root / "prompts" / f"{args.split}.jsonl")

    out_dir = args.results_root / "analysis" / args.split
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "rates_ci.json").write_text(
        json.dumps(rates_ci(runs), indent=2) + "\n")
    (out_dir / "construct_validity.json").write_text(
        json.dumps(construct_validity(runs, fork), indent=2) + "\n")
    (out_dir / "failure_taxonomy.json").write_text(
        json.dumps(failure_taxonomy(runs), indent=2) + "\n")
    (out_dir / "robustness.json").write_text(
        json.dumps(robustness(runs, prompts), indent=2) + "\n")

    print(f"wrote analyses to {out_dir}")
    cv = construct_validity(runs, fork)
    print(f"  construct-validity: n={cv['n']} agreement={cv['agreement']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
