"""Emit a stratified subset for a second, independent annotation pass.

To measure inter-annotator agreement (Cohen's kappa) we need a genuinely
independent second annotator to re-label a subset *blind* to the primary
gold. This script produces:

- ``data/iaa/subset_prompts.jsonl`` : the prompts to re-annotate (no gold);
- ``data/iaa/second_annotator_template.jsonl`` : one blank record per prompt
  for the second annotator to fill in.

The subset is a deterministic, category-stratified sample (fixed seed) so the
selection is reproducible. Agreement is computed later by
``compute_iaa.py`` once the template is filled in.

Run::

    python3 code/benchmark/make_iaa_subset.py --data-root data --split main \
        --frac 0.25
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", default="main")
    parser.add_argument("--frac", type=float, default=0.25,
                        help="fraction of each category to sample")
    parser.add_argument("--seed", type=int, default=20260707)
    args = parser.parse_args()

    prompts = _read_jsonl(args.data_root / "prompts" / f"{args.split}.jsonl")
    by_cat: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in prompts:
        by_cat[p["category"]].append(p)

    rng = random.Random(args.seed)
    subset: list[dict[str, Any]] = []
    for cat, rows in sorted(by_cat.items()):
        k = max(1, round(len(rows) * args.frac))
        subset.extend(sorted(rng.sample(rows, k), key=lambda r: r["id"]))
    subset.sort(key=lambda r: r["id"])

    out_dir = args.data_root / "iaa"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Prompts to re-annotate (surface only; no gold leaks to the annotator).
    subset_public = [
        {"id": p["id"], "category": p["category"], "prompt": p["prompt"]}
        for p in subset
    ]
    (out_dir / "subset_prompts.jsonl").write_text(
        "\n".join(json.dumps(r) for r in subset_public) + "\n")

    # Blank template for the second annotator, mirroring the gold schema.
    template = [
        {
            "id": p["id"],
            "required_nodes": [],
            "required_edges": [],
            "required_config": {},
            "safety_requirements": [],
            "allowed_extra_nodes": [],
            "expects_clarification": False,
        }
        for p in subset
    ]
    (out_dir / "second_annotator_template.jsonl").write_text(
        "\n".join(json.dumps(r) for r in template) + "\n")

    counts: dict[str, int] = defaultdict(int)
    for p in subset:
        counts[p["category"]] += 1
    print(f"wrote {len(subset)} prompts to {out_dir}/subset_prompts.jsonl")
    print(f"category counts: {dict(counts)}")
    print(f"blank template: {out_dir}/second_annotator_template.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
