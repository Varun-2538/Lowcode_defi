from __future__ import annotations

import argparse
import json
from pathlib import Path


PROMPT_REQUIRED = {"id", "split", "category", "prompt", "entities"}
GOLD_REQUIRED = {"id", "required_nodes", "required_edges", "required_config", "safety_requirements"}
VALID_CATEGORIES = {"swap", "limit_order", "cross_chain", "compositional"}


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict] = []
    for line_no, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows


def validate_prompt(row: dict, split: str) -> None:
    missing = PROMPT_REQUIRED - set(row)
    if missing:
        raise ValueError(f"{row.get('id', '<unknown>')}: prompt missing {sorted(missing)}")
    if row["split"] != split:
        raise ValueError(f"{row['id']}: split mismatch {row['split']} != {split}")
    if row["category"] not in VALID_CATEGORIES:
        raise ValueError(f"{row['id']}: invalid category {row['category']}")
    if not row["prompt"].strip():
        raise ValueError(f"{row['id']}: empty prompt")


def validate_gold(row: dict) -> None:
    missing = GOLD_REQUIRED - set(row)
    if missing:
        raise ValueError(f"{row.get('id', '<unknown>')}: gold missing {sorted(missing)}")
    if not row["required_nodes"]:
        raise ValueError(f"{row['id']}: no required nodes")
    node_set = set(row["required_nodes"])
    for edge in row["required_edges"]:
        if not isinstance(edge, list) or len(edge) != 2:
            raise ValueError(f"{row['id']}: invalid edge {edge}")
        for endpoint in edge:
            if endpoint not in node_set:
                raise ValueError(f"{row['id']}: edge endpoint {endpoint!r} not in required_nodes")
    if not isinstance(row["required_config"], dict) or not row["required_config"]:
        raise ValueError(f"{row['id']}: required_config must be a non-empty object")
    if not isinstance(row["safety_requirements"], list) or not row["safety_requirements"]:
        raise ValueError(f"{row['id']}: safety_requirements must be a non-empty list")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--split", required=True)
    args = parser.parse_args()

    prompts = read_jsonl(args.data_root / "prompts" / f"{args.split}.jsonl")
    gold = read_jsonl(args.data_root / "gold" / f"{args.split}.jsonl")
    split_meta = json.loads((args.data_root / "splits" / f"{args.split}.json").read_text())

    prompt_ids = [row["id"] for row in prompts]
    gold_ids = [row["id"] for row in gold]
    if len(prompt_ids) != len(set(prompt_ids)):
        raise ValueError("duplicate prompt IDs")
    if len(gold_ids) != len(set(gold_ids)):
        raise ValueError("duplicate gold IDs")

    for row in prompts:
        validate_prompt(row, args.split)
    for row in gold:
        validate_gold(row)

    expected_ids = set(split_meta.get("prompt_ids", []))
    if expected_ids and set(prompt_ids) != expected_ids:
        raise ValueError("prompt IDs do not match split metadata")
    if set(gold_ids) != set(prompt_ids):
        raise ValueError("gold IDs do not match prompt IDs")

    counts: dict[str, int] = {}
    for row in prompts:
        counts[row["category"]] = counts.get(row["category"], 0) + 1

    print(f"validated split={args.split} prompts={len(prompts)} categories={counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
