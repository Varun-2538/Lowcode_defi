# Reproducibility

## Environment

- All Python is run through **uv** (no manual venv activation).
- The Koan baseline imports the real project modules under `agents/src`,
  so it must run inside the agents environment:
  `uv run --project agents python ...`. The agents project pins Python
  3.12 (`agents/.python-version`).
- Matplotlib (figure) and the EVM stack (fork pass) are pulled on demand
  via `uv run --no-project --with ...`, so nothing pollutes the agents env.

## One-command pilot

```bash
koan-submission/code/run_pilot.sh
```

Rebuilds the dataset, validates it, runs the two static baselines, runs the
two LLM baselines against **each model in `LLM_MODELS`** (Gemini 3.1 Flash
Lite and GPT-5.4 mini, tagged so runs never overwrite each other), executes
the **fork pass** on a local py-EVM chain, then regenerates tables + figure.

## Individual steps

```bash
# validate
uv run --project agents python koan-submission/code/benchmark/validate_dataset.py \
  --data-root koan-submission/data --split pilot

# run one baseline (optionally tag by model)
KOAN_LLM_MODEL=openai/gpt-5.4-mini \
uv run --project agents python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split pilot --baseline direct_llm --tag openai_gpt-5.4-mini

# on-chain fork pass over all saved raw outputs (EVM deps pulled on demand)
uv run --no-project --with "web3>=6" --with "eth-tester[py-evm]>=0.9.0b1" \
  --with py-solc-x python koan-submission/code/safety/fork_simulation.py \
  --results-root koan-submission/results --split pilot

# tables + figure
uv run --no-project python koan-submission/code/analysis/make_tables.py \
  --results-root koan-submission/results
uv run --no-project --with matplotlib python koan-submission/code/analysis/make_figures.py \
  --results-root koan-submission/results
```

## LLM baselines

`direct_llm` and `constrained_llm` require an API key:

- Set `OPENROUTER_API_KEY` (default model `openai/gpt-4o-mini`) or
  `ANTHROPIC_API_KEY` (default `claude-3-5-sonnet-latest`).
- Override the model with `KOAN_LLM_MODEL` (OpenRouter `provider/model`
  slugs, e.g. `google/gemini-3.1-flash-lite`, `openai/gpt-5.4-mini`).
- Pass `--tag <fs-safe-model>` so per-model runs get distinct `run_id`s
  (`<baseline>__<tag>`) in the results tree.
- Optionally override `OPENROUTER_BASE_URL` (defaults to
  `https://openrouter.ai/api/v1`).
- Each raw run records `model` = {provider, model, temperature} and the
  full `raw_output`. Without a key the runner records `status: skipped`;
  skipped runs are never counted as failures or dropped.

### Re-scoring without new API calls

If parsing/normalization changes, re-derive LLM metrics from the saved
`raw_output` (no re-query, deterministic):

```bash
uv run --project agents python koan-submission/code/benchmark/rescore_llm.py \
  --data-root koan-submission/data --results-root koan-submission/results --split pilot
```

## Fork pass (local EVM, not a mainnet fork)

- Deploys a constant-product AMM (0.3% fee) + mock ERC20s on an in-process
  py-EVM chain via `eth-tester`; solc 0.8.24 is fetched by `py-solc-x`.
- Executes each swap for real (real `transferFrom`, `require` reverts, gas).
  Reserves/prices are seeded deterministically, so outcomes are
  byte-for-byte reproducible. Prices/liquidity are synthetic — this is a
  pinned local snapshot, **not** live mainnet state.
- To move to a true mainnet fork later, point a web3 provider at an
  Anvil/Alchemy fork RPC and route real router calls; the harness interface
  (`ForkChain` / `simulate`) is designed for that swap.

## Rules

- Raw outputs -> `results/raw/`, processed metrics -> `results/processed/`,
  fork outcomes -> `results/fork/`, tables/figures -> `results/tables`,
  `results/figures`.
- Every prompt yields exactly one raw record (ok / error / skipped /
  needs_clarification). Nothing is silently dropped.
- Tables/figures are generated from saved results only, never hand-edited.
- On-chain claims are limited to what the harness actually executes; its
  synthetic-price / local-snapshot nature is stated wherever it is cited.
