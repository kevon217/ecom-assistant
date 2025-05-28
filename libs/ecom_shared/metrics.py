# libs/ecom_shared/metrics.py
"""
Simple metrics collection utilities.
"""

from typing import Any, Dict

from .logging import get_logger

logger = get_logger(__name__)


class Metrics:
    """
    Simple metrics collection class.
    In production, this would integrate with monitoring systems.
    """

    @staticmethod
    def counter(name: str, labels: Dict[str, str] = None):
        """
        Record a counter metric.

        Args:
            name: Metric name
            labels: Optional labels dictionary
        """
        labels_str = ", ".join(f"{k}={v}" for k, v in (labels or {}).items())
        logger.debug(f"METRIC: counter {name} {labels_str}")

    @staticmethod
    def histogram(name: str, value: float, labels: Dict[str, str] = None):
        """
        Record a histogram metric.

        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels dictionary
        """
        labels_str = ", ".join(f"{k}={v}" for k, v in (labels or {}).items())
        logger.debug(f"METRIC: histogram {name}={value} {labels_str}")

    @staticmethod
    def gauge(name: str, value: float, labels: Dict[str, str] = None):
        """
        Record a gauge metric.

        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels dictionary
        """
        labels_str = ", ".join(f"{k}={v}" for k, v in (labels or {}).items())
        logger.debug(f"METRIC: gauge {name}={value} {labels_str}")
