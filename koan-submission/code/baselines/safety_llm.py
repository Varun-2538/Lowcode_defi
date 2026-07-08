"""Safety-instruction LLM ablation: direct prompt + explicit safety directive.

Isolates the effect of simply *telling* the model to produce a safe-to-execute
workflow (see ``llm_common._SAFETY_INSTRUCTION``). Identical to ``direct_llm``
except for the added directive. Comparing this to ``direct_llm`` on the same
model answers the obvious reviewer question: is the safety gap just a prompting
artifact that vanishes when you ask for safety? Real but optional; raises
``BaselineSkipped`` when no API key is configured.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_common import run_llm_baseline  # noqa: E402


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    return run_llm_baseline(prompt, name="safety_llm", constrained=False, safety=True)
