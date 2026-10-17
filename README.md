# tinytrace

`tinytrace` is a small, dependency-free tracing shim for Python services and
batch jobs. It records spans in memory, supports a context manager API, and
exports records as newline-delimited JSON that can be shipped to any
collector.

The library is intentionally narrow: no exporters, no background threads, no
global state beyond a context variable. Applications decide what to do with
the finished spans.

## Install

```bash
python -m pip install tinytrace
```

## Use

```python
from tinytrace import Tracer

tracer = Tracer("billing", sample_ratio=0.25)
with tracer.span("invoice.render", invoice_id=42):
    ...
```

Dump the recorded spans:

```python
from tinytrace import to_jsonl

print(to_jsonl(tracer.finished(), "billing"))
```

## CLI

```bash
tinytrace --spans 5 --format jsonl
```

## Requirements

- Python 3.11 or newer

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check src tests
```
