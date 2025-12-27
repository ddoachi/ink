"""Configuration module for Ink infrastructure layer.

This module provides configuration classes for various Ink settings,
including net classification and latch identification configurations.

Exports:
    NetClassificationConfig: Configuration for power/ground net classification.
    LatchIdentificationConfig: Configuration for sequential cell pattern matching.
    DEFAULT_SEQUENTIAL_PATTERNS: Default patterns for latch/flip-flop detection.
"""

from ink.infrastructure.config.latch_config import (
    DEFAULT_SEQUENTIAL_PATTERNS,
    LatchIdentificationConfig,
)
from ink.infrastructure.config.net_classification_config import (
    NetClassificationConfig,
)

__all__ = [
    "DEFAULT_SEQUENTIAL_PATTERNS",
    "LatchIdentificationConfig",
    "NetClassificationConfig",
]
