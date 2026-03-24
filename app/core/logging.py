"""Structured logging helpers for the application."""

from __future__ import annotations

import logging
from typing import Optional


def setup_logging(debug: bool = False) -> None:
	"""Configure root logging once for the process."""
	level = logging.DEBUG if debug else logging.INFO

	root = logging.getLogger()
	if root.handlers:
		# Keep existing handlers (e.g. uvicorn) and only adjust level.
		root.setLevel(level)
		return

	logging.basicConfig(
		level=level,
		format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
	)


def get_logger(name: Optional[str] = None) -> logging.Logger:
	"""Return a named logger instance."""
	return logging.getLogger(name)
