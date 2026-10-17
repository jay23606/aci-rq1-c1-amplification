"""tinytrace: minimal span recording with no runtime dependencies."""

from .core import Span, Tracer, current_tracer
from .export import to_jsonl, to_record

__all__ = ["Span", "Tracer", "current_tracer", "to_jsonl", "to_record"]
__version__ = "0.4.2"
