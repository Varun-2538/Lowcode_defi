"""Generate the headline figure from processed metrics.

Produces ``results/figures/structural_vs_safe.png``: a grouped bar chart
of graph-valid, executable, and safe-executable rates per (non-skipped)
baseline. Requires matplotlib; run with::

    uv run --no-project --with matplotlib python \
        code/analysis/make_figures.py --results-root results

If matplotlib is unavailable the script exits cleanly without claiming a
figure was produced.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--split", default="pilot")
    args = parser.parse_args()

    summary_path = args.results_root / "tables" / args.split / "summary.json"
    if not summary_path.exists():
        # fall back to the legacy flat location for older runs
        legacy = args.results_root / "tables" / "summary.json"
        summary_path = legacy if legacy.exists() else summary_path
    if not summary_path.exists():
        print("no summary.json; run make_tables.py first")
        return 1
    summary = json.loads(summary_path.read_text())

    # Exclude reference floor/ceiling baselines from the headline figure; they
    # are shown in the table. Keep only the systems under test.
    reference = {"oracle", "null", "random_nodes"}
    rows = [r for r in summary if not r["n_skipped"] and r["run_id"] not in reference]
    if not rows:
        print("no non-skipped baselines to plot")
        return 0

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        print(f"matplotlib unavailable ({exc}); skipping figure generation")
        return 0

    labels = [r["label"] for r in rows]
    metrics = [
        ("Graph valid", [r["graph_valid"] for r in rows]),
        ("Executable (cfg)", [r["executable"] for r in rows]),
        ("Safe-executable (cfg)", [r["safe_executable"] for r in rows]),
    ]

    x = range(len(labels))
    width = 0.22
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, (name, values) in enumerate(metrics):
        ax.bar([p + i * width for p in x], values, width, label=name)

    # annotate on-chain unsafe executions (the concrete safety failures)
    for p, r in zip(x, rows):
        if r["fork_unsafe_executed"]:
            ax.annotate(f"{r['fork_unsafe_executed']} unsafe\non-chain",
                        xy=(p + width, 0.5), ha="center", va="center",
                        fontsize=8, color="crimson",
                        bbox=dict(boxstyle="round", fc="mistyrose", ec="crimson"))

    ax.set_ylabel("Rate")
    ax.set_ylim(0, 1.05)
    ax.set_title("Structural validity does not imply safe executability")
    ax.set_xticks([p + width for p in x])
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.legend()
    fig.tight_layout()

    fig_dir = args.results_root / "figures" / args.split
    fig_dir.mkdir(parents=True, exist_ok=True)
    out = fig_dir / "structural_vs_safe.png"
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
