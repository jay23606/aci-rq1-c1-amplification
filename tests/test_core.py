import pytest

from tinytrace import Span, Tracer, to_record
from tinytrace.core import reset_tracer, use_tracer


def test_span_finish_sets_status_and_duration():
    span = Span("work")
    span.finish()
    assert span.status == "ok"
    assert span.duration_ms is not None
    assert span.duration_ms >= 0


def test_span_records_error_status():
    with pytest.raises(RuntimeError), Span("boom"):
        raise RuntimeError("stop")
    span = Span("boom")
    with pytest.raises(RuntimeError), span:
        raise RuntimeError("stop")
    assert span.status == "error"


def test_nested_spans_share_trace_id():
    tracer = Tracer("svc")
    with tracer.span("outer") as outer, tracer.span("inner") as inner:
        pass
    assert inner.trace_id == outer.trace_id
    assert inner.parent_id == outer.span_id
    assert len(tracer.finished()) == 2


def test_sample_ratio_validation():
    with pytest.raises(ValueError):
        Tracer("svc", sample_ratio=1.5)


def test_tracer_context_roundtrip():
    tracer = Tracer("svc")
    token = use_tracer(tracer)
    from tinytrace import current_tracer

    assert current_tracer() is tracer
    reset_tracer(token)
    assert current_tracer() is None


def test_record_shape():
    tracer = Tracer("svc")
    with tracer.span("op", key="value"):
        pass
    record = to_record(tracer.finished()[0], "svc")
    assert record["service"] == "svc"
    assert record["attributes"] == {"key": "value"}
    assert record["name"] == "op"
