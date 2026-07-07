"""Random-node baseline: a non-trivial floor (ABC guideline R.14 / O.h.2).

Emits a random-but-plausible workflow: a random-size sample of nodes from
the real vocabulary wired in a random linear chain, with no config. This is
a stronger floor than the null agent -- it can occasionally satisfy node
recall by luck -- so it quantifies how much of a system's ``graph_valid``
score could be obtained *without understanding the request*. If real systems
do not clearly beat this floor, apparent competence is an artifact.

Determinism: the RNG is seeded from the prompt id, so the baseline is
byte-for-byte reproducible across runs.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))
from workflow_utils import derive_safety  # noqa: E402
from llm_common import NODE_VOCAB  # noqa: E402


def _edges(nodes: list[str]) -> list[list[str]]:
    return [[nodes[i], nodes[i + 1]] for i in range(len(nodes) - 1)]


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    rng = random.Random(f"random_nodes::{prompt['id']}")
    k = rng.randint(3, 7)
    nodes = rng.sample(NODE_VOCAB, k)
    edges = _edges(nodes)
    config: dict[str, Any] = {}  # no parsing -> no concrete execution config
    safety = derive_safety(nodes, config)
    return {
        "id": prompt["id"],
        "baseline": "random_nodes",
        "category": prompt["category"],
        "status": "ok",
        "error": None,
        "workflow": {"nodes": nodes, "edges": edges, "config": config, "safety": safety},
    }
