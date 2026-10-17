"""Span lifecycle and context propagation."""

from __future__ import annotations

import contextvars
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Self

_current_tracer: contextvars.ContextVar[Tracer | None] = contextvars.ContextVar(
    "tinytrace_tracer", default=None
)


@dataclass
class Span:
    """A single unit of work inside a trace."""

    name: str
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_id: str | None = None
    start_ns: int = field(default_factory=time.perf_counter_ns)
    end_ns: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "unset"

    def set_attribute(self, key: str, value: Any) -> Span:
        self.attributes[key] = value
        return self

    def finish(self, status: str = "ok") -> Span:
        if self.end_ns is None:
            self.end_ns = time.perf_counter_ns()
            self.status = status
        return self

    @property
    def duration_ms(self) -> float | None:
        if self.end_ns is None:
            return None
        return (self.end_ns - self.start_ns) / 1_000_000

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.finish("error" if exc_type else "ok")


class Tracer:
    """Collects finished spans in memory."""

    def __init__(self, service: str, sample_ratio: float = 1.0) -> None:
        if not 0.0 <= sample_ratio <= 1.0:
            raise ValueError("sample_ratio must be within [0, 1]")
        self.service = service
        self.sample_ratio = sample_ratio
        self.spans: list[Span] = []
        self._stack: list[Span] = []

    def start_span(self, name: str, **attributes: Any) -> Span:
        parent = self._stack[-1] if self._stack else None
        span = Span(
            name=name,
            trace_id=parent.trace_id if parent else uuid.uuid4().hex,
            parent_id=parent.span_id if parent else None,
            attributes=dict(attributes),
        )
        return span

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[Span]:
        span = self.start_span(name, **attributes)
        self._stack.append(span)
        try:
            with span:
                yield span
        finally:
            self._stack.pop()
            self.spans.append(span)

    def finished(self) -> list[Span]:
        return [span for span in self.spans if span.end_ns is not None]


def current_tracer() -> Tracer | None:
    return _current_tracer.get()


def use_tracer(tracer: Tracer) -> contextvars.Token:
    """Install ``tracer`` as the ambient tracer for the current context."""
    return _current_tracer.set(tracer)


def reset_tracer(token: contextvars.Token) -> None:
    _current_tracer.reset(token)
