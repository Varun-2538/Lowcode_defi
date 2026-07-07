"""Re-derive LLM workflows + metrics from saved ``raw_output`` (no API calls).

When the parsing/normalization logic changes (e.g. accepting index-based
edges), we must not silently keep stale scores, but we also should not
burn API budget re-querying the model. Every LLM raw record stores the
model's exact ``raw_output`` text, so this script re-parses that text
through the current ``llm_common.parse_model_output`` and rewrites the
run's workflow, per-prompt metrics, and summary in place.

It only touches runs whose raw records contain ``raw_output`` (i.e. LLM
runs); template/koan runs are left alone.

    uv run --project agents python code/benchmark/rescore_llm.py \
        --data-root data --results-root results --split pilot
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "baselines"))
from metrics import aggregate, score_run  # noqa: E402
from llm_common import parse_model_output  # noqa: E402


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--split", default="pilot")
    args = parser.parse_args()

    prompts = read_jsonl(args.data_root / "prompts" / f"{args.split}.jsonl")
    gold_rows = {r["id"]: r for r in read_jsonl(args.data_root / "gold" / f"{args.split}.jsonl")}
    for gid, grow in gold_rows.items():
        grow.setdefault("category", next((p["category"] for p in prompts if p["id"] == gid), "unknown"))

    raw_root = args.results_root / "raw" / args.split
    processed = args.results_root / "processed" / args.split
    if not raw_root.exists():
        print("no raw outputs; nothing to rescore")
        return 1

    rescored_runs = 0
    for run_dir in sorted(p for p in raw_root.iterdir() if p.is_dir()):
        run_id = run_dir.name
        files = sorted(run_dir.glob("*.json"))
        if not files:
            continue
        sample = json.loads(files[0].read_text())
        if "raw_output" not in sample:
            continue  # not an LLM run

        metrics: list[dict[str, Any]] = []
        n_ok = n_error = n_skipped = 0
        for path in files:
            run = json.loads(path.read_text())
            raw_text = run.get("raw_output")
            if run.get("status") == "skipped":
                n_skipped += 1
            elif raw_text:
                try:
                    workflow, status = parse_model_output(raw_text)
                    run["workflow"] = workflow
                    run["status"] = status
                    run["error"] = None
                    n_ok += 1
                except Exception as exc:  # noqa: BLE001
                    run["status"] = "error"
                    run["error"] = f"reparse failed: {exc}"
                    n_error += 1
                path.write_text(json.dumps(run, indent=2) + "\n")
            else:
                n_error += 1

            gold = gold_rows[run["id"]]
            metric = score_run(gold, run).to_dict()
            metric["run_id"] = run_id
            metric["model_tag"] = run.get("model_tag")
            metrics.append(metric)

        (processed / f"{run_id}_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
        summary = aggregate(metrics)
        summary.update({
            "baseline": sample.get("baseline"),
            "run_id": run_id,
            "model_tag": sample.get("model_tag"),
            "split": args.split,
            "n_ok": n_ok, "n_error": n_error, "n_skipped": n_skipped,
            "rescored_at": datetime.now(timezone.utc).isoformat(),
        })
        (processed / f"{run_id}_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        rescored_runs += 1
        print(f"rescored {run_id}: graph_valid={summary.get('graph_valid_rate', 0):.3f} "
              f"exec={summary.get('executable_rate', 0):.3f} "
              f"safe={summary.get('safe_executable_rate', 0):.3f}")

    print(f"rescored {rescored_runs} LLM run(s) from saved raw_output")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
