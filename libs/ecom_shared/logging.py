# libs/ecom_shared/logging.py
"""
Standardized logging configuration for all services.
"""

import logging
import sys
from typing import Optional

# from .config import config


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name, typically __name__ from the calling module

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        # Create handler
        handler = logging.StreamHandler(sys.stdout)

        # # Set format based on structured logging config
        # if config.enable_structured_logging:
        #     # JSON structured logging for production
        #     formatter = logging.Formatter(
        #         '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
        #         '"logger": "%(name)s", "message": "%(message)s"}'
        #     )
        # else:
        #     # Simple format for development
        #     formatter = logging.Formatter(
        #         '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        #     )
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # # Set level based on debug config
        # if config.debug:
        #     logger.setLevel(logging.DEBUG)
        # else:
        #     logger.setLevel(logging.INFO)

    return logger
