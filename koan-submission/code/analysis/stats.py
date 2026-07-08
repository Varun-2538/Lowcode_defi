"""Uncertainty quantification for benchmark rates (ABC guideline R.11).

Pure-stdlib implementations so the analysis has no third-party dependency:

- ``wilson_interval``: score (Wilson) confidence interval for a binomial
  proportion. Preferred over the normal approximation for the small-n,
  near-0/near-1 rates this benchmark produces.
- ``bootstrap_mean_ci``: percentile bootstrap CI for a mean of per-item
  values (used for config-completeness / safety-recall means), with a fixed
  seed for reproducibility.
- ``two_proportion_z``: two-sided z-test on two independent proportions
  (used to test whether an ablation moves a rate).

Every function is deterministic given its inputs.
"""

from __future__ import annotations

import math
import random
from typing import Sequence


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (default 95%)."""
    if n == 0:
        return (0.0, 0.0)
    phat = successes / n
    denom = 1 + z * z / n
    center = (phat + z * z / (2 * n)) / denom
    margin = (z * math.sqrt((phat * (1 - phat) + z * z / (4 * n)) / n)) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def rate_with_ci(successes: int, n: int, z: float = 1.96) -> dict[str, float]:
    lo, hi = wilson_interval(successes, n, z)
    return {
        "rate": (successes / n) if n else 0.0,
        "n": n,
        "successes": successes,
        "ci_low": lo,
        "ci_high": hi,
    }


def bootstrap_mean_ci(values: Sequence[float], n_boot: int = 10_000,
                      alpha: float = 0.05, seed: int = 12345) -> dict[str, float]:
    """Percentile bootstrap CI for the mean of ``values``."""
    vals = list(values)
    n = len(vals)
    if n == 0:
        return {"mean": 0.0, "n": 0, "ci_low": 0.0, "ci_high": 0.0}
    mean = sum(vals) / n
    if n == 1:
        return {"mean": mean, "n": 1, "ci_low": mean, "ci_high": mean}
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        resample = [vals[rng.randrange(n)] for _ in range(n)]
        means.append(sum(resample) / n)
    means.sort()
    lo = means[int((alpha / 2) * n_boot)]
    hi = means[int((1 - alpha / 2) * n_boot) - 1]
    return {"mean": mean, "n": n, "ci_low": lo, "ci_high": hi}


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def two_proportion_z(s1: int, n1: int, s2: int, n2: int) -> dict[str, float]:
    """Two-sided z-test for H0: p1 == p2 (pooled variance)."""
    if n1 == 0 or n2 == 0:
        return {"p1": 0.0, "p2": 0.0, "z": 0.0, "p_value": 1.0, "diff": 0.0}
    p1, p2 = s1 / n1, s2 / n2
    pool = (s1 + s2) / (n1 + n2)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    if se == 0:
        z = 0.0
    else:
        z = (p1 - p2) / se
    p_value = 2 * (1 - _norm_cdf(abs(z)))
    return {"p1": p1, "p2": p2, "z": z, "p_value": p_value, "diff": p1 - p2}
