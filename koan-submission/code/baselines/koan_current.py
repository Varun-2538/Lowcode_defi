"""Koan baseline: drives the *real* Koan generation pipeline offline.

This adapter imports the actual project modules
(``agents/src/agents/architecture_mapper.py`` and
``agents/src/workflow/generator.py``) and runs Koan's deterministic path:

1. ``ArchitectureMapperAgent._fallback_analysis`` -- the regex intent
   parser used when no LLM is reachable. This requires no API key and is
   fully reproducible, so it is what we evaluate here.
2. ``WorkflowGenerator.generate_workflow`` -- the real DAG builder,
   including its pattern-based node presets and template-mode config.

The resulting Koan ``WorkflowDefinition`` is normalized into evaluator
format and its declared safety predicates are derived with the same
uniform function used for every other baseline.

Run this baseline inside the agents environment so the imports resolve::

    uv run --project agents python code/benchmark/run_evaluation.py \
        --baseline koan_current ...
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[3]
_AGENTS_SRC = _REPO_ROOT / "agents" / "src"
_BENCH = _HERE.parents[1] / "benchmark"
_ADAPTER = _HERE.parents[1] / "koan_adapter"

for path in (_AGENTS_SRC, _BENCH, _ADAPTER):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from workflow_utils import derive_safety  # noqa: E402
from normalize_workflow import normalize_workflow  # noqa: E402


def _load_koan():
    from agents.architecture_mapper import ArchitectureMapperAgent  # noqa: E402
    from workflow.generator import WorkflowGenerator  # noqa: E402
    return ArchitectureMapperAgent(), WorkflowGenerator()


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    mapper, generator = _load_koan()

    # Deterministic, offline intent parsing (regex fallback path).
    requirements = mapper._fallback_analysis(prompt["prompt"])

    # Conversational / underspecified -> Koan emits no nodes. We report
    # this as a clarification request, which is the correct behavior for
    # underspecified prompts (and a failure for concrete ones).
    if requirements.get("pattern") == "conversational" or not requirements.get("suggested_nodes"):
        return {
            "id": prompt["id"],
            "baseline": "koan_current",
            "category": prompt["category"],
            "status": "needs_clarification",
            "error": None,
            "requirements": requirements,
            "workflow": {"nodes": [], "edges": [], "config": {}, "safety": []},
        }

    workflow_def = asyncio.run(generator.generate_workflow(requirements))
    normalized = normalize_workflow(workflow_def)
    normalized["safety"] = derive_safety(normalized["nodes"], normalized["config"])

    return {
        "id": prompt["id"],
        "baseline": "koan_current",
        "category": prompt["category"],
        "status": "ok",
        "error": None,
        "requirements": requirements,
        "workflow": normalized,
    }
