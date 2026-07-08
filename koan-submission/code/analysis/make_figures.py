"""Generate the paper figures from processed metrics + fork outcomes.

Produces two vector PDFs under ``results/figures/<split>/``:

* ``onchain_fates.pdf`` (full page width): vertical stacked bars, one per
  system, decomposing the on-chain fate of every in-scope prompt on the
  local EVM. Distinguishes the two ways of being "zero unsafe": inert
  systems whose outputs cannot execute vs. Koan-Safe, whose injected
  price-impact gate blocks the dangerous trades the LLM baselines mine.
* ``safety_ladder.pdf`` (single column): slope chart of each system's
  survival across the three nested static levels (graph-valid ->
  executable -> statically safe).

Both panels show the Gemini variant of each LLM system (the stronger
baseline family; GPT rows appear in the main table). No in-axes titles
(captions carry them), rounded bar segments, Okabe-Ito palette.

Run with::

    uv run --no-project --with matplotlib python \
        code/analysis/make_figures.py --results-root results --split heldout

If matplotlib is unavailable the script exits cleanly.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Okabe-Ito colorblind-safe palette.
OI = {
    "orange": "#E69F00",
    "skyblue": "#56B4E9",
    "green": "#009E73",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "grey": "#999999",
}

# (run_id, display label, color, linestyle, emphasis)
SYSTEMS = [
    ("template", "Template-\nonly", OI["grey"], ":", False),
    ("koan_current", "Koan\n(deployed)", OI["grey"], "--", False),
    ("direct_llm__google_gemini-3.1-flash-lite", "Direct\nLLM", OI["vermillion"], "-", False),
    ("constrained_llm__google_gemini-3.1-flash-lite", "Constrained\nLLM", OI["orange"], "-", False),
    ("fewshot_llm__google_gemini-3.1-flash-lite", "Few-shot\nLLM", OI["purple"], "-", False),
    ("safety_llm__google_gemini-3.1-flash-lite", "Safety-instr.\nLLM", OI["green"], "-", False),
    ("koan_safe_rules", "Koan-Safe\n(rules)", OI["skyblue"], "-", True),
    ("koan_safe_llm__google_gemini-3.1-flash-lite", "Koan-Safe\n(LLM)", OI["blue"], "--", True),
    ("koan_safe_hybrid__google_gemini-3.1-flash-lite", "Koan-Safe\n(hybrid)", OI["blue"], "-", True),
]

LEVELS = ["Graph-\nvalid", "Executable", "Statically\nsafe"]

# On-chain fate stack, bottom-up: danger at the bottom so the orange sits
# on the axis and reads first. (json keys, legend label, color)
FATES = [
    (("unsafe_executed",), "Executed unsafely", OI["vermillion"]),
    (("executed_safe",), "Executed safely", OI["green"]),
    (("aborted_price_impact", "reverted_slippage"),
     "Blocked by safety gate", OI["blue"]),
    (("pending_not_filled",), "Order placed, not filled", "#C4C4C4"),
    (("not_executable",), "Inert (nothing to run)", "#E8E8E8"),
]


def _load(results_root: Path, split: str):
    summary_path = results_root / "tables" / split / "summary.json"
    summary = {r["run_id"]: r for r in json.loads(summary_path.read_text())}
    fork = {}
    for path in sorted((results_root / "fork" / split).glob("*_summary.json")):
        fork[path.name.replace("_summary.json", "")] = json.loads(path.read_text())
    return summary, fork


def make_fates(summary, fork, out: Path) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle, Patch

    rows = [(rid, lbl.replace("\n", " ") if False else lbl)
            for rid, lbl, *_ in SYSTEMS
            if rid in fork and not summary[rid]["n_skipped"]]

    fig, ax = plt.subplots(figsize=(7.1, 2.5))
    bar_w = 0.58
    for xi, (rid, lbl) in enumerate(rows):
        oc = fork[rid]["outcome_counts"]
        denom = fork[rid]["n_total"] - oc.get("not_simulated", 0)
        y0 = 0.0
        for keys, _, color in FATES:
            frac = sum(oc.get(k, 0) for k in keys) / denom
            if frac <= 0:
                continue
            r = min(0.035, frac / 3)
            if r < 0.008:
                ax.add_patch(Rectangle((xi - bar_w / 2, y0), bar_w, frac,
                                       facecolor=color, edgecolor="white",
                                       linewidth=0.8, zorder=3))
            else:
                ax.add_patch(FancyBboxPatch(
                    (xi - bar_w / 2 + 0.03, y0 + r), bar_w - 0.06,
                    frac - 2 * r,
                    boxstyle=f"round,pad={r}", mutation_aspect=0.30,
                    facecolor=color, edgecolor="white", linewidth=0.8,
                    zorder=3))
            y0 += frac
        # annotate counts inside every colored (non-grey) segment large
        # enough to hold the label; tiny slivers stay unnumbered
        y0 = 0.0
        for i, (keys, _, _) in enumerate(FATES):
            n = sum(oc.get(k, 0) for k in keys)
            frac = n / denom
            if i < 3 and n and frac >= 0.055:
                ax.text(xi, y0 + frac / 2, str(n), ha="center",
                        va="center", fontsize=8, color="white",
                        fontweight="bold", zorder=4)
            y0 += frac

    ax.set_xlim(-0.55, len(rows) - 0.45)
    ax.set_ylim(0, 1.0)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([lbl for _, lbl in rows], fontsize=7.6)
    ax.set_ylabel("Fraction of in-scope prompts", fontsize=8.5)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(length=0)
    ax.grid(axis="y", linewidth=0.4, color="#DDDDDD", zorder=1)
    ax.set_axisbelow(True)

    handles = [Patch(facecolor=c, label=l) for _, l, c in FATES]
    ax.legend(handles=handles, fontsize=7.2, frameon=False, ncol=5,
              loc="lower center", bbox_to_anchor=(0.5, 1.01),
              handlelength=1.2, columnspacing=1.0)

    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print(f"wrote {out}")


def make_ladder(summary, out: Path) -> None:
    import matplotlib.pyplot as plt

    rows = [(rid, lbl.replace("-\n", "-").replace("\n", " "), c, ls, emph)
            for rid, lbl, c, ls, emph in SYSTEMS
            if rid in summary and not summary[rid]["n_skipped"]]

    fig, ax = plt.subplots(figsize=(3.4, 2.9))
    for rid, label, color, ls, emph in rows:
        r = summary[rid]
        vals = [r["graph_valid"], r["executable"], r["safe_executable"]]
        ax.plot(range(3), vals, marker="o", markersize=3.4, color=color,
                linestyle=ls, linewidth=2.0 if emph else 1.2,
                alpha=1.0 if emph else 0.85, label=label, clip_on=False,
                zorder=3)

    ax.set_xticks(range(3))
    ax.set_xticklabels([l.replace("-\n", "-").replace("\n", " ")
                        for l in LEVELS], fontsize=8)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Rate on held-out split", fontsize=8.5)
    ax.set_xlim(-0.05, 2.05)
    ax.tick_params(length=0)
    ax.grid(axis="y", linewidth=0.4, color="#DDDDDD", zorder=1)
    ax.set_axisbelow(True)
    ax.legend(fontsize=6.2, frameon=False, ncol=3, loc="lower center",
              bbox_to_anchor=(0.5, -0.46), handlelength=1.5,
              columnspacing=0.7, labelspacing=0.4)

    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    print(f"wrote {out}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", type=Path, required=True)
    parser.add_argument("--split", default="heldout")
    args = parser.parse_args()

    summary_path = args.results_root / "tables" / args.split / "summary.json"
    if not summary_path.exists():
        print("no summary.json; run make_tables.py first")
        return 1

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        print(f"matplotlib unavailable ({exc}); skipping figure generation")
        return 0

    plt.rcParams.update({
        "font.size": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })

    summary, fork = _load(args.results_root, args.split)
    fig_dir = args.results_root / "figures" / args.split
    fig_dir.mkdir(parents=True, exist_ok=True)

    make_fates(summary, fork, fig_dir / "onchain_fates.pdf")
    make_ladder(summary, fig_dir / "safety_ladder.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
