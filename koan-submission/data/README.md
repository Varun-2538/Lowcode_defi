# Data Layout

Each benchmark split has three files:

- `prompts/<split>.jsonl`: natural-language tasks and metadata.
- `gold/<split>.jsonl`: gold workflow graph and safety requirements.
- `splits/<split>.json`: split metadata and prompt IDs.

The pilot split is intentionally small. It exists to validate schema, metrics, baseline execution, and paper framing before scaling.

