from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Adapter entrypoint for current Koan generator.")
    parser.add_argument("--prompt-id", required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()
    raise SystemExit(f"Koan adapter not implemented yet for {args.prompt_id}.")


if __name__ == "__main__":
    raise SystemExit(main())

