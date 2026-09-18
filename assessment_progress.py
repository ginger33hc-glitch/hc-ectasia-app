"""Request-local operational progress for a CER-AI assessment.

The canonical assessment publishes factual milestones through this context-local
sink.  The transport layer may expose them to the active surgeon, while the
clinical workflow and its results remain unchanged.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Iterator


ProgressSink = Callable[[str, dict[str, Any]], Awaitable[None]]
_progress_sink: ContextVar[ProgressSink | None] = ContextVar(
    "cerai_assessment_progress_sink", default=None
)


@contextmanager
def bind_progress_sink(sink: ProgressSink) -> Iterator[None]:
    """Bind one job's progress receiver for its assessment task tree."""
    token = _progress_sink.set(sink)
    try:
        yield
    finally:
        _progress_sink.reset(token)


async def publish_progress(code: str, **details: Any) -> None:
    """Publish an operational milestone when the caller belongs to a job."""
    sink = _progress_sink.get()
    if sink is not None:
        await sink(code, details)
