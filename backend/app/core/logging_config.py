"""
Basic logging configuration shared across the app.
"""
import logging
import sys


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    # Quiet down noisy third-party loggers a bit
    logging.getLogger("passlib").setLevel(logging.WARNING)


logger = logging.getLogger("gem_compliance")
