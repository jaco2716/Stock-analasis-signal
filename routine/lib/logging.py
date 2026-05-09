"""Structured logger setup; called once from the orchestrator."""

import logging
import sys

from .config import get_settings


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else getattr(logging, get_settings().log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger()
    # Idempotent: replace handlers so re-invocation in tests stays clean.
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    # Tame noisy deps.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
