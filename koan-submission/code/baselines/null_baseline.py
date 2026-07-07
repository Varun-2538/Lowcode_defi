"""Null baseline: the trivial "do nothing" agent (ABC guideline R.14).

Emits an empty workflow for every prompt. Reporting a trivial agent's score
is a benchmark-reporting best practice: it establishes the floor and guards
against a metric that can be gamed by returning nothing. Because it produces
no nodes, its status is treated as ``needs_clarification`` (an empty graph is
indistinguishable from "I can't build this"), which means it scores 0 on
every workflow prompt's structural/executable/safe layer while
"accidentally" satisfying the clarification axis -- exactly the degenerate
behavior a good benchmark should surface rather than hide.
"""

from __future__ import annotations

from typing import Any


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": prompt["id"],
        "baseline": "null",
        "category": prompt["category"],
        "status": "needs_clarification",
        "error": None,
        "workflow": {"nodes": [], "edges": [], "config": {}, "safety": []},
    }
