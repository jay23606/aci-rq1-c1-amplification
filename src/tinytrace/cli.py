"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys

from .core import Tracer, use_tracer
from .export import to_jsonl


def demo_spans(service: str, count: int) -> Tracer:
    tracer = Tracer(service)
    token = use_tracer(tracer)
    try:
        for index in range(count):
            with tracer.span("request", index=index):
                with tracer.span("parse"):
                    pass
                with tracer.span("write"):
                    pass
    finally:
        from .core import reset_tracer

        reset_tracer(token)
    return tracer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tinytrace")
    parser.add_argument("--service", default="demo")
    parser.add_argument("--spans", type=int, default=3)
    parser.add_argument("--format", choices=["jsonl", "summary"], default="summary")
    args = parser.parse_args(argv)

    tracer = demo_spans(args.service, args.spans)
    if args.format == "jsonl":
        print(to_jsonl(tracer.finished(), args.service))
        return 0

    summary = {
        "service": args.service,
        "spans": len(tracer.finished()),
        "mean_ms": round(
            sum(s.duration_ms or 0 for s in tracer.finished()) / max(len(tracer.finished()), 1),
            3,
        ),
    }
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
