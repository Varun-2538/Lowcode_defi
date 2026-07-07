"""Static executable/safety checks over a normalized workflow.

These are the *static proxy* checks used by the pilot. They do not touch
a chain. The true executable check (running the workflow against a pinned
mainnet fork) belongs in ``fork_simulation.py`` and is not yet
implemented; do not claim on-chain results from this module.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmark"))
from workflow_utils import concrete_config, derive_safety  # noqa: E402


def missing_config(workflow: dict[str, Any], required_config: dict[str, Any]) -> list[str]:
    config = workflow.get("config", {})
    return [key for key in required_config if not concrete_config(config, key)]


def missing_safety(workflow: dict[str, Any], required_safety: list[str]) -> list[str]:
    declared = set(workflow.get("safety") or derive_safety(
        workflow.get("nodes", []), workflow.get("config", {})
    ))
    return [s for s in required_safety if s not in declared]


def executable_proxy(workflow: dict[str, Any], gold: dict[str, Any]) -> bool:
    return not missing_config(workflow, gold.get("required_config", {}))


def safe_executable_proxy(workflow: dict[str, Any], gold: dict[str, Any]) -> bool:
    return executable_proxy(workflow, gold) and not missing_safety(
        workflow, gold.get("safety_requirements", [])
    )
