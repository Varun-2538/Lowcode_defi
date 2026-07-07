"""Direct LLM baseline: prompt -> workflow JSON, no structural constraints.

Real but optional. Requires ``OPENROUTER_API_KEY`` or ``ANTHROPIC_API_KEY``;
otherwise raises ``BaselineSkipped`` and the runner records a skip.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_common import run_llm_baseline  # noqa: E402


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    return run_llm_baseline(prompt, name="direct_llm", constrained=False)
