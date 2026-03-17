"""
logger.py — Structured logging setup using structlog + rich
All tool calls, LLM requests, RAG retrievals, and DB writes are logged here.
"""
import logging
import sys
import os
from datetime import datetime
import structlog
from rich.logging import RichHandler
from rich.console import Console

console = Console()

# --------------------------------------------------------------------------- #
#  Log directory
# --------------------------------------------------------------------------- #
os.makedirs("logs", exist_ok=True)
LOG_FILE = f"logs/agent_{datetime.utcnow().strftime('%Y%m%d')}.log"


def setup_logging(log_level: str = "DEBUG") -> None:
    """Configure structlog with console (rich) + file output."""
    level = getattr(logging, log_level.upper(), logging.DEBUG)

    # Standard library logging handlers
    handlers = [
        RichHandler(
            console=console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,
            show_path=False,
        ),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]

    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=handlers,
    )

    # Structlog processors
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.ExceptionRenderer(),
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    return structlog.get_logger(name)


# --------------------------------------------------------------------------- #
#  Tool call logger decorator
# --------------------------------------------------------------------------- #
import functools
import time
import json
from typing import Callable, Any

_tool_logger = structlog.get_logger("tool_calls")


def log_tool_call(func: Callable) -> Callable:
    """
    Decorator that logs every @langchain_tool call with:
    - tool name
    - input arguments
    - output result
    - duration in ms
    - any exceptions
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start_ts = time.time()

        # Serialize input safely
        try:
            input_repr = json.dumps(kwargs, default=str, ensure_ascii=False)[:2000]
        except Exception:
            input_repr = str(kwargs)[:2000]

        _tool_logger.info(
            "🔧 TOOL_CALL_START",
            tool=tool_name,
            input=input_repr,
            timestamp=datetime.utcnow().isoformat(),
        )

        try:
            result = func(*args, **kwargs)
            duration_ms = int((time.time() - start_ts) * 1000)

            try:
                output_repr = json.dumps(result, default=str, ensure_ascii=False)[:2000]
            except Exception:
                output_repr = str(result)[:2000]

            _tool_logger.info(
                "✅ TOOL_CALL_SUCCESS",
                tool=tool_name,
                output=output_repr,
                duration_ms=duration_ms,
            )
            return result

        except Exception as exc:
            duration_ms = int((time.time() - start_ts) * 1000)
            _tool_logger.error(
                "❌ TOOL_CALL_ERROR",
                tool=tool_name,
                error=str(exc),
                duration_ms=duration_ms,
                exc_info=True,
            )
            raise

    return wrapper
