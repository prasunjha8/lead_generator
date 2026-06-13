"""
Logging configuration.
Logs to both console and logs/app.log with rotation.
"""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_file: Path, level: int = logging.INFO):
    log_file.parent.mkdir(parents=True, exist_ok=True)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(level)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(ch)

    # File handler with rotation (10 MB × 3 backups)
    fh = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(fmt, datefmt))
    root.addHandler(fh)

    # Quiet noisy third-party loggers
    for noisy in ["aiohttp", "asyncio", "urllib3", "chardet"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)
