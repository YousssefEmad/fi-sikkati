"""Structured logging with structlog.

Every log line is JSON in staging/production and human-readable in development. The request id
is bound through ``structlog.contextvars`` by the request-id middleware so every line emitted
during a request carries it. A scrubbing processor removes secrets and personal data before
anything is rendered (security.md §10).
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

from app.core.config import LogFormat

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(password|passwd|secret|token|authorization|cookie|set-cookie|api[_-]?key|"
    r"national[_-]?id|phone|email|document|refresh|access[_-]?token|csrf)",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"
_MAX_VALUE_LENGTH = 2_000


def scrub_sensitive_data(
    _logger: object, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """Redact keys that look sensitive and truncate very long values, recursively."""
    for key in list(event_dict.keys()):
        event_dict[key] = _scrub_value(key, event_dict[key])
    return event_dict


def _scrub_value(key: str, value: Any) -> Any:
    if _SENSITIVE_KEY_PATTERN.search(key):
        return _REDACTED
    if isinstance(value, Mapping):
        return {k: _scrub_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_scrub_value(key, item) for item in value]
    if isinstance(value, str) and len(value) > _MAX_VALUE_LENGTH:
        return value[:_MAX_VALUE_LENGTH] + "…[truncated]"
    return value


def configure_logging(*, level: str, log_format: LogFormat) -> None:
    """Configure structlog and route the standard library (uvicorn, sqlalchemy) through it."""
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        scrub_sensitive_data,
    ]

    renderer: structlog.types.Processor
    if log_format == "json":
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # uvicorn's access log duplicates our request log; keep its error channel only.
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
        logging.getLogger(name).propagate = True
    logging.getLogger("uvicorn.access").disabled = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[no-any-return]
