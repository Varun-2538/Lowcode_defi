# Second-Annotator Guide (Inter-Annotator Agreement)

This guide lets a second, independent annotator re-label a stratified subset of
DeFiFlowBench so we can report **inter-annotator agreement (IAA)** — a standard
credibility requirement for a human-authored benchmark. The primary author has
already produced the gold in `data/gold/main.jsonl`; the second annotator must
work **blind** to that gold.

## What you get

- `data/iaa/subset_prompts.jsonl` — 31 prompts (25% of the main split,
  category-stratified: 10 swap / 8 limit_order / 8 cross_chain / 5
  compositional). Each line has only `id`, `category`, and `prompt`.
- `data/iaa/second_annotator_template.jsonl` — one blank record per prompt to
  fill in, in the gold schema.

## Your task

For each prompt, decide **independently** (do not look at `data/gold/`):

1. **`expects_clarification`** (`true`/`false`): is the request too
   underspecified or internally contradictory to build a concrete, correct
   workflow? If yes, the correct system response is to *ask*, so set `true`
   and you may leave the rest minimal. If no, set `false` and annotate the
   workflow.
2. **`required_nodes`**: the minimum node *types* (from the vocabulary below)
   a correct workflow must contain.
3. **`required_edges`**: the directed `[from, to]` type-pairs that must exist.
4. **`required_config`**: the config keys that must hold a concrete value for
   the workflow to execute (values are descriptions; only the *keys* are
   scored).
5. **`safety_requirements`**: the safety predicates that must hold (names from
   the fixed vocabulary below).
6. **`allowed_extra_nodes`**: optional nodes that shouldn't be penalized.

Use the field definitions in `docs/annotation_guide.md` — the same rubric the
primary annotator used. Do **not** change prompt text or ids.

### Node vocabulary
`walletConnector, tokenSelector, chainSelector, oneInchQuote, oneInchSwap,
priceImpactCalculator, transactionMonitor, limitOrder, fusionPlus, fusionSwap,
portfolioAPI, defiDashboard`

### Safety-predicate vocabulary
`slippage_bound, price_impact_gate, transaction_monitoring, price_bound,
expiry_set, destination_chain_check, bridge_confirmation`

## How agreement is computed

After you fill in `second_annotator_template.jsonl` (or a copy), run:

```bash
python3 code/benchmark/compute_iaa.py --data-root data --split main \
    --second data/iaa/second_annotator_template.jsonl --results-root results
```

This reports, into `results/analysis/main/iaa.json`:

- **Cohen's kappa** on `expects_clarification` (chance-corrected binary
  agreement);
- **mean Jaccard** on `required_nodes`, on `required_config` keys, and on
  `safety_requirements` (set-overlap agreement).

## Adjudication protocol

Where the two annotators disagree, resolve by discussion against
`docs/annotation_guide.md`; if the rubric is silent, extend the rubric (note it
in `docs/decision_log.md`) and re-derive the affected gold via
`code/benchmark/build_dataset.py`. Report the pre-adjudication IAA numbers in
the paper (post-hoc "fixing" to inflate agreement is not permitted).

> Note: until a human completes this pass, the IAA number is intentionally
> absent from the paper rather than estimated. The protocol and tooling are in
> place so it is a fill-in-and-run away.
