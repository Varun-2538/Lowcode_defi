# Reproducibility

## Environment

- All Python is run through **uv** (no manual venv activation).
- The Koan baseline imports the real project modules under `agents/src`,
  so it must run inside the agents environment:
  `uv run --project agents python ...`. The agents project pins Python
  3.12 (`agents/.python-version`).
- Matplotlib (figure) and the EVM stack (fork pass) are pulled on demand
  via `uv run --no-project --with ...`, so nothing pollutes the agents env.

## One-command run (main or pilot)

```bash
koan-submission/code/run_benchmark.sh main    # or: ... pilot
```

Rebuilds the dataset, validates it, runs the reference baselines (`oracle`,
`null`, `random_nodes`, `template`, `koan_current`), runs the four LLM
baselines/ablations (`direct_llm`, `constrained_llm`, `fewshot_llm`,
`safety_llm`) against **each model in `LLM_MODELS`** (Gemini 3.1 Flash Lite
and GPT-5.4 mini, tagged so runs never overwrite each other), executes the
**fork pass** on a local py-EVM chain, then regenerates tables, the deeper
analyses (CIs / construct validity / failure taxonomy / robustness), and the
figure. (`code/run_pilot.sh` is retained for the original pilot-only flow.)

## Individual steps

```bash
# build + validate
uv run --no-project python koan-submission/code/benchmark/build_dataset.py \
  --data-root koan-submission/data --split main
uv run --no-project python koan-submission/code/benchmark/validate_dataset.py \
  --data-root koan-submission/data --split main

# an offline reference baseline (oracle needs no key; runs plain)
uv run --no-project python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline oracle
# koan_current needs the agents env:
uv run --project agents python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline koan_current

# an LLM baseline / ablation (tag by model)
KOAN_LLM_MODEL=openai/gpt-5.4-mini \
uv run --no-project --with "openai>=1.0" \
  python koan-submission/code/benchmark/run_evaluation.py \
  --data-root koan-submission/data --results-root koan-submission/results \
  --split main --baseline safety_llm --tag openai_gpt-5.4-mini

# on-chain fork pass over all saved raw outputs (EVM deps pulled on demand)
uv run --no-project --with "web3>=6" --with "eth-tester[py-evm]>=0.9.0b1" \
  --with py-solc-x python koan-submission/code/safety/fork_simulation.py \
  --results-root koan-submission/results --split main

# tables + analyses + figure (all split-aware; outputs under results/<kind>/<split>)
uv run --no-project python koan-submission/code/analysis/make_tables.py \
  --results-root koan-submission/results --split main
uv run --no-project python koan-submission/code/analysis/analyze.py \
  --results-root koan-submission/results --data-root koan-submission/data --split main
uv run --no-project --with matplotlib python koan-submission/code/analysis/make_figures.py \
  --results-root koan-submission/results --split main
```

## LLM baselines

`direct_llm`, `constrained_llm`, `fewshot_llm`, and `safety_llm` require an
API key:

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
uv run --no-project python koan-submission/code/benchmark/rescore_llm.py \
  --data-root koan-submission/data --results-root koan-submission/results --split main
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

## Mainnet-fidelity validation (read-only, needs an RPC)

- `code/safety/fork_fidelity.py` validates that the local AMM is a faithful
  reimplementation of Uniswap V2. It reads each benchmark pair's **real** V2
  reserves at a pinned mainnet block over a read-only RPC, seeds the identical
  harness AMM contract, and compares local quotes + real on-chain executions
  to the live V2 router across trade sizes from 1e-6 to 0.5 of the pool.
- Requires `ETH_RPC_URL` in `koan-submission/.env` (any mainnet HTTP RPC).
  Run:
  ```
  uv run --no-project --with 'web3>=6' --with 'eth-tester[py-evm]>=0.9.0b1' \
    --with py-solc-x python koan-submission/code/safety/fork_fidelity.py \
    --results-root koan-submission/results
  ```
- Result (pinned block recorded in the output): worst relative error = 0
  across 11 pairs x 7 sizes; every local quote equals the V2 integer formula
  exactly. Writes `results/fork/mainnet/fidelity.json` +
  `results/tables/mainnet/fidelity.tex` (paper Table VI).
- This makes **read-only** mainnet state calls only; it never submits a
  transaction or moves funds.

## Rules

- Every results kind is split-scoped: raw -> `results/raw/<split>/`,
  processed -> `results/processed/<split>/`, fork -> `results/fork/<split>/`,
  tables -> `results/tables/<split>/`, figures -> `results/figures/<split>/`,
  deeper analyses -> `results/analysis/<split>/`.
- Every prompt yields exactly one raw record (ok / error / skipped /
  needs_clarification). Nothing is silently dropped.
- Reference baselines (`oracle`, `null`, `random_nodes`) run offline and need
  no key: `oracle` is the ceiling (reconstructs gold), `null`/`random_nodes`
  are the floor. They are what pins the metric as solvable-but-not-gameable.
- Tables/figures/analyses are generated from saved results only, never
  hand-edited.
- On-chain claims are limited to what the harness actually executes; its
  synthetic-price / local-snapshot nature is stated wherever it is cited.
