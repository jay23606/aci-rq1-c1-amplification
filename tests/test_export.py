import json

from tinytrace import Tracer, to_jsonl
from tinytrace.cli import main


def test_jsonl_roundtrip():
    tracer = Tracer("svc")
    with tracer.span("one"):
        pass
    payload = to_jsonl(tracer.finished(), "svc")
    record = json.loads(payload.splitlines()[0])
    assert record["trace_id"]
    assert record["status"] == "ok"


def test_cli_summary(capsys):
    assert main(["--spans", "2"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["service"] == "demo"
    assert out["spans"] == 6
