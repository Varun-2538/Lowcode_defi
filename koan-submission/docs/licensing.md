# Licensing (pending author decision)

The benchmark cannot be published without an explicit license, and the parent
Koan repository is currently **"All Rights Reserved"** (see repo-root
`LICENSE`). Releasing DeFiFlowBench as a research artifact requires the authors
to make a deliberate licensing decision. This file records the recommendation
and the open question; it is **not** itself a license grant.

## Recommendation

| Artifact | Path | Recommended license | Rationale |
|---|---|---|---|
| Dataset (prompts, gold, splits) | `data/` | CC BY 4.0 | Standard for released benchmark datasets (NeurIPS D&B guidance). |
| Code (benchmark, baselines, analysis) | `code/` | MIT or Apache-2.0 | Permissive, reproducibility-friendly. |
| Paper text/figures | `paper/` | Venue copyright / CC BY as venue allows | Follows the target venue's policy. |

## Open questions for the authors

1. Is the team authorized to relicense this subset of the repository openly,
   given the proprietary root `LICENSE`? (The benchmark artifacts under
   `koan-submission/` are newly authored for the paper.)
2. Does the target venue (ICDLT 2026) impose a specific copyright transfer that
   affects the paper (not the dataset/code)?

Once decided, add the actual `LICENSE` files (`koan-submission/LICENSE` for
code, `koan-submission/data/LICENSE` for data) and update the datasheet's
Distribution section to point at them.
