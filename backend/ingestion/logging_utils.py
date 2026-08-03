"""Structured logging helpers for the ingestion layer."""

from __future__ import annotations

import logging
from typing import Any, Mapping


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """
    Emit a log record with structured contextual metadata.

    Context is attached via ``extra['context']`` and also rendered into the
    message so default formatters remain informative.
    """
    safe_context: dict[str, Any] = {k: v for k, v in context.items() if v is not None}
    suffix = ""
    if safe_context:
        rendered = " ".join(f"{key}={value!r}" for key, value in safe_context.items())
        suffix = f" | {rendered}"
    logger.log(level, f"{message}{suffix}", extra={"context": safe_context})


def merge_context(
    base: Mapping[str, Any] | None,
    **updates: Any,
) -> dict[str, Any]:
    """Return a new context dict combining ``base`` with ``updates``."""
    out = dict(base or {})
    out.update({k: v for k, v in updates.items() if v is not None})
    return out
