"""Koan-Safe (rules): deterministic parser + rules generator + enforcement.

Fully offline, free, and deterministic. Reads only the raw prompt text.
The enforcement layer can be disabled with ``KOAN_SAFE_ENFORCE=0`` to run
the generator-vs-enforcement ablation.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from koan_safe_core import (  # noqa: E402
    build_result, parse_intent, synthesize_rules,
)


def generate(prompt: dict[str, Any]) -> dict[str, Any]:
    intent = parse_intent(prompt["prompt"])
    candidate = synthesize_rules(intent)
    return build_result(prompt, "koan_safe_rules", candidate, intent)
