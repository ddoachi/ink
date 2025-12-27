"""Latch identification configuration for sequential cell detection.

This module provides the LatchIdentificationConfig dataclass for managing
configurable pattern matching to identify sequential cells (latches, flip-flops)
in gate-level netlists.

The configuration allows users to:
    1. Define glob-style patterns for matching sequential cell types
    2. Configure case-sensitivity for pattern matching
    3. Load patterns from YAML configuration files
    4. Fall back to default patterns when configuration is missing/invalid

Configuration File Format:
    The YAML file follows this structure:

    ```yaml
    latch_identification:
      patterns:
        - "*DFF*"      # Matches DFFR_X1, SDFFR_X2, etc.
        - "*LATCH*"    # Matches LATCH_X1, DLATCH_X2, etc.
        - "*FF*"       # Broader fallback for generic flip-flops
      case_sensitive: false
    ```

Pattern Syntax (Glob-Style):
    - `*` matches any sequence of characters (including none)
    - `?` matches any single character
    - Patterns are matched against cell_type field, not cell instance name

Design Decisions:
    - Uses YAML for human-readable configuration that field engineers can edit
    - Glob patterns instead of regex for simplicity and familiarity
    - Case-insensitive by default to handle varying library conventions
    - Frozen dataclass for immutability and thread-safety
    - Graceful fallback to defaults for missing/invalid configuration

See Also:
    - Spec E01-F04-T01 for requirements
    - Downstream: E01-F04-T02 (Latch Detector Service) consumes this configuration
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

# Configure logging for this module
# Using __name__ ensures log messages are properly namespaced
logger = logging.getLogger(__name__)

# Default patterns for sequential cell identification
# These patterns cover common naming conventions across cell libraries:
# - *DFF*: D flip-flops (DFFR_X1, SDFFR_X2, DFF_POS, SCAN_DFF, etc.)
# - *LATCH*: Latch elements (LATCH_X1, DLATCH_X2, HLATCH, etc.)
# - *FF*: Broader fallback for generic flip-flops (JKFF, SRFF, FF_X1, etc.)
#
# Order matters: more specific patterns first, broader patterns last
# This allows early exit in pattern matching when a specific match is found
DEFAULT_SEQUENTIAL_PATTERNS: list[str] = [
    "*DFF*",  # D flip-flops - most common sequential element
    "*LATCH*",  # Latch elements - level-sensitive storage
    "*FF*",  # Generic flip-flops - broader fallback (includes JK, SR, etc.)
]


@dataclass(frozen=True)
class LatchIdentificationConfig:
    """Configuration for sequential cell (latch/flip-flop) identification.

    This immutable dataclass holds the user-defined configuration for identifying
    sequential cells in a gate-level netlist. It uses glob-style pattern matching
    against cell types.

    The configuration is designed to work with the LatchDetectorService to allow
    users to customize sequential cell identification on a per-project basis
    without modifying code.

    Attributes:
        patterns: Glob-style patterns for matching sequential cell types.
            Each pattern is matched against the cell_type field.
            Example: ["*DFF*", "*LATCH*", "*FF*"]
        case_sensitive: Whether pattern matching is case-sensitive.
            Default is False for robustness across different library conventions.

    Example:
        >>> # Load from YAML file
        >>> config = LatchIdentificationConfig.load_from_yaml(
        ...     Path("config/latch_patterns.yaml")
        ... )
        >>> print(config.patterns)
        ['*DFF*', '*LATCH*', '*FF*']

        >>> # Create programmatically
        >>> config = LatchIdentificationConfig(
        ...     patterns=["*REGF*", "*DFF*"],
        ...     case_sensitive=False,
        ... )

        >>> # Use default configuration
        >>> config = LatchIdentificationConfig.default()

    Note:
        The dataclass is frozen (immutable) to prevent accidental modification
        after creation. This ensures thread-safety and predictable behavior
        during netlist processing.
    """

    patterns: tuple[str, ...]
    """Glob-style patterns for matching sequential cell types."""

    case_sensitive: bool = False
    """Whether pattern matching is case-sensitive. Default: False."""

    def __init__(self, patterns: list[str] | tuple[str, ...], case_sensitive: bool = False) -> None:
        """Initialize LatchIdentificationConfig with patterns.

        Args:
            patterns: List or tuple of glob-style patterns for matching
                sequential cell types.
            case_sensitive: Whether pattern matching should be case-sensitive.
                Defaults to False for robustness.

        Note:
            Patterns are stored as a tuple internally to ensure immutability.
            If a list is provided, it will be converted to a tuple.
        """
        # Convert list to tuple for immutability
        # Using object.__setattr__ because dataclass is frozen
        if isinstance(patterns, list):
            object.__setattr__(self, "patterns", tuple(patterns))
        else:
            object.__setattr__(self, "patterns", patterns)
        object.__setattr__(self, "case_sensitive", case_sensitive)

    @staticmethod
    def default() -> LatchIdentificationConfig:
        """Create default configuration with standard sequential patterns.

        Returns a configuration with the default patterns for common sequential
        cell naming conventions. Use this when no custom configuration is needed.

        Returns:
            LatchIdentificationConfig with DEFAULT_SEQUENTIAL_PATTERNS and
            case_sensitive=False.

        Example:
            >>> config = LatchIdentificationConfig.default()
            >>> print(config.patterns)
            ('*DFF*', '*LATCH*', '*FF*')
            >>> print(config.case_sensitive)
            False
        """
        return LatchIdentificationConfig(
            patterns=DEFAULT_SEQUENTIAL_PATTERNS,
            case_sensitive=False,
        )

    @staticmethod
    def load_from_yaml(config_path: Path) -> LatchIdentificationConfig:
        """Load configuration from a YAML file.

        Reads the YAML configuration file and extracts latch identification
        patterns. If the file is missing, invalid, or has empty patterns,
        returns a default configuration with appropriate logging.

        Error Handling Strategy:
            - Missing file: Return defaults + log warning
            - Invalid YAML syntax: Return defaults + log error
            - Empty file: Return defaults + log warning
            - Empty patterns list: Return defaults + log warning
            - Missing sections: Return defaults + log warning

        Args:
            config_path: Path to the YAML configuration file.

        Returns:
            LatchIdentificationConfig with values from file or defaults.

        Example:
            >>> config = LatchIdentificationConfig.load_from_yaml(
            ...     Path("config/latch_patterns.yaml")
            ... )
            >>> if config.patterns:
            ...     print(f"Using patterns: {config.patterns}")
        """
        # Try to load and parse YAML data
        data = LatchIdentificationConfig._load_yaml_data(config_path)
        if data is None:
            return LatchIdentificationConfig.default()

        # Extract and validate configuration from parsed YAML
        return LatchIdentificationConfig._parse_config_data(data, config_path)

    @staticmethod
    def _load_yaml_data(config_path: Path) -> dict[str, Any] | None:
        """Load and parse YAML data from config file.

        Returns parsed data dict, or None if file is missing, invalid, or empty.
        Logs appropriate warnings/errors for each failure case.
        """
        # Handle missing configuration file - common for fresh installations
        if not config_path.exists():
            logger.warning(
                "Latch configuration file not found: %s. Using default patterns.",
                config_path,
            )
            return None

        # Try to parse YAML file
        try:
            with config_path.open(encoding="utf-8") as f:
                data: dict[str, Any] | None = yaml.safe_load(f)
        except yaml.YAMLError as e:
            logger.error(
                "Invalid YAML in latch configuration file %s: %s. Using default patterns.",
                config_path,
                e,
            )
            return None

        # Handle empty file (safe_load returns None for empty file)
        if data is None:
            logger.warning(
                "Empty latch configuration file: %s. Using default patterns.",
                config_path,
            )
            return None

        return data

    @staticmethod
    def _parse_config_data(data: dict[str, Any], config_path: Path) -> LatchIdentificationConfig:
        """Parse latch configuration from YAML data dict.

        Extracts patterns and case_sensitive from the latch_identification section.
        Falls back to default patterns if section is missing or invalid.
        """
        # Extract latch_identification section
        latch_config = data.get("latch_identification", {})

        # Validate section type and content
        if not isinstance(latch_config, dict) or not latch_config:
            logger.warning(
                "Missing or invalid 'latch_identification' section in %s. Using default patterns.",
                config_path,
            )
            return LatchIdentificationConfig.default()

        # Extract case_sensitive with default of False
        case_sensitive = latch_config.get("case_sensitive", False)

        # Extract patterns, validating for missing or empty
        patterns = latch_config.get("patterns", None)
        if not patterns:  # None or empty list
            warning_msg = "Empty patterns list" if patterns == [] else "Missing 'patterns' key"
            logger.warning(
                "%s in latch configuration %s. Using default patterns.",
                warning_msg,
                config_path,
            )
            patterns = DEFAULT_SEQUENTIAL_PATTERNS

        return LatchIdentificationConfig(
            patterns=patterns,
            case_sensitive=case_sensitive,
        )
