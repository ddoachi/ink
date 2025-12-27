"""Configuration module for Ink infrastructure layer.

This module provides configuration classes for various Ink settings,
particularly the net classification configuration which allows users
to define custom power and ground net names per project.

Exports:
    NetClassificationConfig: Configuration for power/ground net classification.
"""

from ink.infrastructure.config.net_classification_config import (
    NetClassificationConfig,
)

__all__ = ["NetClassificationConfig"]
