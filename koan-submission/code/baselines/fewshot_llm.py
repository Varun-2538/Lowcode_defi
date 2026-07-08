"""Few-shot LLM ablation: direct prompt + one worked in-context example.

Isolates the effect of in-context demonstration. Identical to ``direct_llm``
except a single worked example is prepended (see ``llm_common._FEWSHOT_EXAMPLE``).
Comparing this to ``direct_llm`` on the same model answers: does a worked
example close the structural-vs-safe gap? Real but optional; raises
``BaselineSkipped`` when no API key is configured.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_common import run_llm_baseline  # noqa: E402


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    return run_llm_baseline(prompt, name="fewshot_llm", constrained=False, fewshot=True)
