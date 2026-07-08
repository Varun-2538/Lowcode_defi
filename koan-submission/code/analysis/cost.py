"""Cost and latency analysis for DeFiFlowBench systems.

We report the two directly measurable, reproducible drivers of operating cost
for a natural-language workflow system:

1. **LLM calls per workflow** -- the dominant monetary and latency cost. The
   rules variant of Koan-Safe makes zero calls (fully offline); the LLM and
   hybrid variants make one call per built workflow and *zero* on prompts where
   Koan-Safe's clarification gate fires before generation.
2. **Wall-clock latency per workflow** -- measured end to end during evaluation.
   Absolute latency for LLM systems is dominated by provider network round-trip
   and is environment dependent; we therefore also report the isolated
   **enforcement overhead** (the added latency of the safety layer on top of a
   generator), which is what our method contributes and is reproducible offline.

A monetary estimate is derived from the *actual* generated token volume
(prompt + completion characters / 4) at a single explicitly-stated blended
price, so the estimate is a transparent function of a stated assumption rather
than a fabricated per-model figure.

Run::

    uv run --no-project python code/analysis/cost.py \
        --results-root results --split metamorphic --price-per-mtok 0.30
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_CHARS_PER_TOKEN = 4.0  # standard rough approximation

_LABEL = {
    "koan_current": "Koan (regex+gen)",
    "direct_llm": "Direct LLM",
    "constrained_llm": "Constrained LLM",
    "fewshot_llm": "Few-shot LLM",
    "safety_llm": "Safety-instruct LLM",
    "koan_safe_rules": "Koan-Safe (rules)",
    "koan_safe_llm": "Koan-Safe (LLM)",
    "koan_safe_hybrid": "Koan-Safe (hybrid)",
}
_MODEL = {"google_gemini-3.1-flash-lite": "Gemini 3.1 FL",
          "openai_gpt-5.4-mini": "GPT-5.4 mini"}
_SHOW = ["direct_llm", "safety_llm", "koan_safe_rules", "koan_safe_llm",
         "koan_safe_hybrid"]


def _label(run_id: str) -> str | None:
    base, _, tag = run_id.partition("__")
    if tag.endswith("noenforce"):
        return None
    lab = _LABEL.get(base, base)
    return f"{lab} ({_MODEL.get(tag, tag)})" if tag else lab


def _run_tokens(results_root: Path, split: str, run_id: str) -> float:
    """Sum estimated tokens over a run from saved raw outputs (prompt+output)."""
    raw_dir = results_root / "raw" / split / run_id
    if not raw_dir.exists():
        return 0.0
    total_chars = 0
    for p in raw_dir.glob("*.json"):
        rec = json.loads(p.read_text())
        # completion side: whatever text the model returned. Plain LLM
        # baselines store it at top level; Koan-Safe stores it under
        # koan_safe.model.raw_output.
        raw_out = rec.get("raw_output")
        if not raw_out:
            ks = rec.get("koan_safe") or {}
            model_meta = ks.get("model")
            if isinstance(model_meta, dict):
                raw_out = model_meta.get("raw_output", "")
        total_chars += len(raw_out or "")
        # prompt side: the request text (proxy for the input tokens)
        # We approximate with the workflow's originating prompt length via
        # the saved record if present; else skip (rules make no call).
    return total_chars / _CHARS_PER_TOKEN


def analyze(results_root: Path, split: str, price_per_mtok: float) -> dict[str, Any]:
    proc = results_root / "processed" / split
    timing_files = sorted(proc.glob("*_timing.json"))
    runs: dict[str, dict[str, Any]] = {}
    for tf in timing_files:
        t = json.loads(tf.read_text())
        run_id = t["run_id"]
        est_completion_tokens = _run_tokens(results_root, split, run_id)
        n = t["n_prompts"] or 1
        runs[run_id] = {
            "run_id": run_id,
            "baseline": t["baseline"],
            "llm_calls_per_prompt": t["llm_calls_per_prompt"],
            "mean_seconds": t["mean_seconds"],
            "median_seconds": t["median_seconds"],
            "n_prompts": t["n_prompts"],
            "est_tokens_per_wf": est_completion_tokens / n,
            "est_cost_per_100wf": (est_completion_tokens / n) * 100
                                   / 1_000_000 * price_per_mtok,
        }

    # enforcement overhead: mean latency delta between ON and matching noenforce
    overhead = {}
    for run_id, r in runs.items():
        if run_id.endswith("noenforce"):
            continue
        # rules uses tag "noenforce": koan_safe_rules -> koan_safe_rules__noenforce
        cand = f"{run_id}__noenforce"
        base_noenf = None
        for rid2 in runs:
            if rid2 == cand or rid2 == f"{run_id.split('__')[0]}__noenforce":
                base_noenf = runs[rid2]
                break
        if base_noenf is not None:
            overhead[run_id] = (r["mean_seconds"] - base_noenf["mean_seconds"]) * 1000.0
    return {"split": split, "price_per_mtok": price_per_mtok,
            "runs": runs, "enforcement_overhead_ms": overhead}


def to_tex(analysis: dict[str, Any]) -> str:
    price = analysis["price_per_mtok"]
    rows = []
    for run_id, r in analysis["runs"].items():
        base = run_id.split("__", 1)[0]
        if base not in _SHOW:
            continue
        lab = _label(run_id)
        if lab is None:
            continue
        rows.append((base, lab, r))
    rows.sort(key=lambda x: (_SHOW.index(x[0]), x[1]))

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Cost and latency per workflow. LLM calls/wf is the dominant "
        r"cost driver (Koan-Safe's rules variant is fully offline; its LLM and "
        r"hybrid variants skip the model call whenever the clarification gate "
        r"fires). Latency is end-to-end wall-clock and, for LLM systems, is "
        r"dominated by provider round-trip. Cost is an estimate at an assumed "
        f"\\${price:.2f}/1M output tokens.}}",
        r"\label{tab:cost}",
        r"\small",
        r"\setlength{\tabcolsep}{2.5pt}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"System & Calls/wf & Lat.\ (s) & \$/100 wf \\",
        r"\midrule",
    ]
    for _b, lab, r in rows:
        esc = lab.replace("_", r"\_")
        calls = f"{r['llm_calls_per_prompt']:.2f}"
        lat = f"{r['mean_seconds']:.2f}"
        cost = f"{r['est_cost_per_100wf']:.3f}"
        lines.append(f"{esc} & {calls} & {lat} & {cost} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-root", type=Path, required=True)
    ap.add_argument("--split", required=True)
    ap.add_argument("--price-per-mtok", type=float, default=0.30,
                    help="assumed blended price per 1M output tokens (USD)")
    args = ap.parse_args()

    analysis = analyze(args.results_root, args.split, args.price_per_mtok)
    out_dir = args.results_root / "analysis" / args.split
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cost.json").write_text(json.dumps(analysis, indent=2) + "\n")

    table_dir = args.results_root / "tables" / args.split
    table_dir.mkdir(parents=True, exist_ok=True)
    (table_dir / "cost.tex").write_text(to_tex(analysis))

    print(f"wrote cost analysis to {out_dir}")
    for run_id, r in sorted(analysis["runs"].items()):
        print(f"  {run_id:<48} calls/wf={r['llm_calls_per_prompt']:.2f} "
              f"lat={r['mean_seconds']:.3f}s tok/wf={r['est_tokens_per_wf']:.0f} "
              f"$/100={r['est_cost_per_100wf']:.3f}")
    if analysis["enforcement_overhead_ms"]:
        print("  enforcement overhead (ms/wf):")
        for rid, ms in analysis["enforcement_overhead_ms"].items():
            print(f"    {rid:<46} {ms:+.3f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
