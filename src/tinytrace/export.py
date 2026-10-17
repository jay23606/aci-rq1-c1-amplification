"""Serialization helpers for recorded spans."""

from __future__ import annotations

import json
from collections.abc import Iterable

from .core import Span


def to_record(span: Span, service: str = "unknown") -> dict:
    record = {
        "service": service,
        "name": span.name,
        "trace_id": span.trace_id,
        "span_id": span.span_id,
        "parent_id": span.parent_id,
        "start_ns": span.start_ns,
        "end_ns": span.end_ns,
        "duration_ms": round(span.duration_ms, 3) if span.duration_ms is not None else None,
        "status": span.status,
        "attributes": span.attributes,
    }
    return record


def to_jsonl(spans: Iterable[Span], service: str = "unknown") -> str:
    lines = [json.dumps(to_record(span, service), ensure_ascii=False) for span in spans]
    return "\n".join(lines)
