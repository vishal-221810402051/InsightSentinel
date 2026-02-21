from __future__ import annotations

import logging
from logging.config import dictConfig


def setup_logging(log_level: str) -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
                }
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default"}
            },
            "root": {"handlers": ["console"], "level": log_level.upper()},
        }
    )
    logging.getLogger("uvicorn.error").setLevel(log_level.upper())
    logging.getLogger("uvicorn.access").setLevel(log_level.upper())