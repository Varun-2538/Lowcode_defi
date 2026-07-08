"""Constrained LLM baseline: prompt -> workflow JSON with structural rules.

Same model/provider selection as ``direct_llm`` but the prompt injects
per-category structural and safety constraints. Real but optional;
raises ``BaselineSkipped`` when no API key is configured.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_common import run_llm_baseline  # noqa: E402


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    return run_llm_baseline(prompt, name="constrained_llm", constrained=True)
