"""Rotating file log for operator forensics. No user identity — the PoC has no login."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOGGER_NAME = "ovadue"
LOG_FILENAME = "ovadue-app.log"
_configured_path: str | None = None


def log_path_for(root: Path) -> Path:
    return Path(root) / "data" / LOG_FILENAME


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def configure_logging(root: Path) -> logging.Logger:
    """Attach a rotating file handler under ``data/`` once per process."""
    global _configured_path
    logger = get_logger()
    logger.setLevel(logging.INFO)
    target = log_path_for(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    resolved = str(target.resolve())
    if _configured_path == resolved:
        return logger
    if _configured_path is not None:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(
        target,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    _configured_path = resolved
    return logger
