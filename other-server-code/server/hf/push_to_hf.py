#!/usr/bin/env python
import sys
from pathlib import Path

try:
    # python -m server.hf.push_to_hf
    from .cli.args import parse_args
    from .services.push import run_push
except Exception:
    # python server/hf/push_to_hf.py
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from server.hf.cli.args import parse_args
    from server.hf.services.push import run_push


def main():
    args = parse_args()
    run_push(args)


if __name__ == "__main__":
    main()
