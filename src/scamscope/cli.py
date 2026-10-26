"""Command-line interface for ScamScope AI.

    python -m scamscope.cli baseline "message text"
    python -m scamscope.cli tooled   "message text"
    echo "message" | python -m scamscope.cli baseline -
"""
from __future__ import annotations

import argparse
import sys


def _read_message(arg: str) -> str:
    if arg == "-":
        return sys.stdin.read().strip()
    return arg


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scamscope",
        description="Analyse a suspicious message for phishing warning signs.",
    )
    parser.add_argument(
        "mode",
        choices=["baseline", "tooled"],
        help="baseline = Phase 1 (no tools); tooled = Phase 2 (+ URL reputation).",
    )
    parser.add_argument(
        "message",
        help="The suspicious message text, or '-' to read it from stdin.",
    )
    args = parser.parse_args(argv)

    message = _read_message(args.message)
    if not message:
        print("No message provided.", file=sys.stderr)
        return 2

    # Import lazily so `baseline` works even if Phase-2-only env is unset, and so a
    # missing Strands install produces a clear error only when actually invoked.
    if args.mode == "baseline":
        from .agent_baseline import analyse
    else:
        from .agent_tooled import analyse

    print(f"[scamscope:{args.mode}] analysing message...\n", file=sys.stderr)
    try:
        output = analyse(message)
    except Exception as exc:  # noqa: BLE001 — surface a readable error on the CLI
        print(f"Agent error: {exc}", file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
