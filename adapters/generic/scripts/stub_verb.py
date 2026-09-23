#!/usr/bin/env python3
"""Generic adapter verb stub — exit 3 naming the missing tool when unavailable."""

from __future__ import annotations

import argparse
import shutil
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("verb")
    parser.add_argument(
        "--require",
        default="python",
        help="Toolchain binary that must exist on PATH (default: python)",
    )
    args, _rest = parser.parse_known_args()
    tool = args.require
    if shutil.which(tool) is None and shutil.which(f"{tool}.cmd") is None:
        print(f"[generic:{args.verb}] missing tool: {tool}", file=sys.stderr)
        return 3
    print(f"[generic:{args.verb}] OK (tool={tool} present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
