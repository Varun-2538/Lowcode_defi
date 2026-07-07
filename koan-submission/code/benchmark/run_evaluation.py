"""Run one baseline over a split, save raw outputs and processed metrics.

Every prompt produces exactly one raw record (including errors and
skips), so nothing is silently dropped. Per-prompt scores and an
aggregate summary are written under ``results/processed``.
"""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
from metrics import aggregate, score_run  # noqa: E402


BASELINE_FILES = {
    "template": "template_baseline.py",
    "direct_llm": "direct_llm.py",
    "constrained_llm": "constrained_llm.py",
    "koan_current": "koan_current.py",
    # floor / ceiling reference baselines (ABC R.13-R.14: trivial + oracle)
    "oracle": "oracle_baseline.py",
    "null": "null_baseline.py",
    "random_nodes": "random_baseline.py",
    # LLM ablations (isolate one prompt-design factor each)
    "fewshot_llm": "fewshot_llm.py",
    "safety_llm": "safety_llm.py",
    # proposed method: parser + generator-agnostic safety-enforcement layer
    "koan_safe_rules": "koan_safe_rules_baseline.py",
    "koan_safe_llm": "koan_safe_llm_baseline.py",
    "koan_safe_hybrid": "koan_safe_hybrid_baseline.py",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load_baseline(name: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    if name not in BASELINE_FILES:
        raise ValueError(f"unknown baseline {name}; expected {sorted(BASELINE_FILES)}")
    path = Path(__file__).resolve().parents[1] / "baselines" / BASELINE_FILES[name]
    spec = importlib.util.spec_from_file_location(f"baseline_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load baseline from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.generate


def _skipped(name: str) -> type[Exception] | None:
    """Return the BaselineSkipped class if the baseline defines one."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "baselines"))
        from llm_common import BaselineSkipped  # noqa: E402
        return BaselineSkipped
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--baseline", required=True, choices=sorted(BASELINE_FILES))
    parser.add_argument("--tag", default="",
                        help="optional run tag (e.g. a model slug) to keep parallel runs separate")
    args = parser.parse_args()

    # A run_id identifies one (baseline, model) run in the results tree.
    run_id = args.baseline if not args.tag else f"{args.baseline}__{args.tag}"

    prompts = read_jsonl(args.data_root / "prompts" / f"{args.split}.jsonl")
    gold_rows = {r["id"]: r for r in read_jsonl(args.data_root / "gold" / f"{args.split}.jsonl")}
    for gid, grow in gold_rows.items():
        grow.setdefault("category", next((p["category"] for p in prompts if p["id"] == gid), "unknown"))
    generate = load_baseline(args.baseline)
    skipped_cls = _skipped(args.baseline)

    raw_dir = args.results_root / "raw" / args.split / run_id
    processed_dir = args.results_root / "processed" / args.split
    log_dir = args.results_root / "logs"
    for d in (raw_dir, processed_dir, log_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Some baselines (e.g. the oracle) need the gold record; pass it only if
    # the baseline's generate() declares a second parameter.
    wants_gold = len(inspect.signature(generate).parameters) >= 2

    metrics: list[dict[str, Any]] = []
    n_ok = n_error = n_skipped = 0

    for prompt in prompts:
        try:
            run = generate(prompt, gold_rows[prompt["id"]]) if wants_gold else generate(prompt)
        except Exception as exc:  # noqa: BLE001
            is_skip = skipped_cls is not None and isinstance(exc, skipped_cls)
            status = "skipped" if is_skip else "error"
            run = {
                "id": prompt["id"], "baseline": args.baseline, "category": prompt["category"],
                "status": status, "error": str(exc),
                "workflow": {"nodes": [], "edges": [], "config": {}, "safety": []},
            }
            if is_skip:
                n_skipped += 1
            else:
                n_error += 1
        else:
            n_ok += 1

        run.setdefault("run_id", run_id)
        if args.tag:
            run.setdefault("model_tag", args.tag)
        (raw_dir / f"{prompt['id']}.json").write_text(json.dumps(run, indent=2) + "\n")
        metric = score_run(gold_rows[prompt["id"]], run).to_dict()
        metric["run_id"] = run_id
        metric["model_tag"] = args.tag or None
        metrics.append(metric)

    (processed_dir / f"{run_id}_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    summary = aggregate(metrics)
    summary.update({
        "baseline": args.baseline,
        "run_id": run_id,
        "model_tag": args.tag or None,
        "split": args.split,
        "n_ok": n_ok, "n_error": n_error, "n_skipped": n_skipped,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    (processed_dir / f"{run_id}_summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    log_line = json.dumps({"baseline": args.baseline, "run_id": run_id, "model_tag": args.tag or None,
                           "split": args.split,
                           "n_ok": n_ok, "n_error": n_error, "n_skipped": n_skipped,
                           "at": summary["generated_at"]}) + "\n"
    with (log_dir / "runs.log").open("a") as fh:
        fh.write(log_line)

    print(f"run_id={run_id} ok={n_ok} error={n_error} skipped={n_skipped}")
    if summary.get("n_workflow"):
        print(f"  graph_valid={summary['graph_valid_rate']:.3f} "
              f"executable={summary['executable_rate']:.3f} "
              f"safe_executable={summary['safe_executable_rate']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
