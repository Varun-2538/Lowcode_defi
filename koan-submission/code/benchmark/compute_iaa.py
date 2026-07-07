"""Compute inter-annotator agreement between primary gold and a 2nd pass.

Given a second annotator's completed labels (same schema as gold) for the IAA
subset, this computes agreement on the decisions that matter for scoring:

- ``expects_clarification`` : Cohen's kappa on the binary clarify/answer call.
- ``required_nodes``        : mean per-prompt Jaccard over node sets.
- ``required_config`` keys  : mean per-prompt Jaccard over config-key sets.
- ``safety_requirements``   : mean per-prompt Jaccard over safety-predicate sets.

Cohen's kappa is used for the binary axis (chance-corrected); set-valued
fields use Jaccard, which is the natural agreement measure for label *sets*
and avoids an ill-defined "category" space. Results are written to
``results/analysis/<split>/iaa.json``.

This script does nothing until a human fills in
``data/iaa/second_annotator_template.jsonl``; it is the reporting half of the
IAA protocol, provided now so the number is a fill-in-and-run away.

Run::

    python3 code/benchmark/compute_iaa.py --data-root data --split main \
        --second data/iaa/second_annotator_template.jsonl \
        --results-root results
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def cohen_kappa_binary(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1 - pe)


def jaccard(s1: set, s2: set) -> float:
    if not s1 and not s2:
        return 1.0
    return len(s1 & s2) / len(s1 | s2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", default="main")
    parser.add_argument("--second", type=Path, required=True,
                        help="second annotator's completed labels (gold schema)")
    parser.add_argument("--results-root", type=Path, required=True)
    args = parser.parse_args()

    gold = {r["id"]: r for r in _read_jsonl(args.data_root / "gold" / f"{args.split}.jsonl")}
    second = {r["id"]: r for r in _read_jsonl(args.second)}
    ids = [i for i in second if i in gold]
    if not ids:
        print("no overlapping ids; fill in the second-annotator template first")
        return 1

    # Skip prompts the second annotator left entirely blank (unfilled template).
    def is_filled(r: dict[str, Any]) -> bool:
        return bool(r.get("required_nodes")) or r.get("expects_clarification")

    filled = [i for i in ids if is_filled(second[i])]
    if not filled:
        print("second-annotator template is still blank; nothing to score yet")
        return 1

    clar_a = [bool(gold[i].get("expects_clarification")) for i in filled]
    clar_b = [bool(second[i].get("expects_clarification")) for i in filled]
    kappa = cohen_kappa_binary(clar_a, clar_b)

    def mean_jaccard(field: str, keys: bool = False) -> float:
        vals = []
        for i in filled:
            g = gold[i].get(field)
            s = second[i].get(field)
            gs = set(g.keys()) if keys else set(map(_hash, g or []))
            ss = set(s.keys()) if keys else set(map(_hash, s or []))
            vals.append(jaccard(gs, ss))
        return sum(vals) / len(vals) if vals else float("nan")

    result = {
        "split": args.split,
        "n_subset": len(ids),
        "n_scored": len(filled),
        "clarification_cohen_kappa": kappa,
        "node_set_mean_jaccard": mean_jaccard("required_nodes"),
        "config_key_mean_jaccard": mean_jaccard("required_config", keys=True),
        "safety_set_mean_jaccard": mean_jaccard("safety_requirements"),
    }
    out_dir = args.results_root / "analysis" / args.split
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "iaa.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


def _hash(x: Any) -> Any:
    return tuple(x) if isinstance(x, list) else x


if __name__ == "__main__":
    raise SystemExit(main())
