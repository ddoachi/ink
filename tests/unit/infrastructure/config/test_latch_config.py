"""Unit tests for LatchIdentificationConfig.

This module tests the YAML-based configuration for sequential cell (latch/flip-flop)
pattern matching. The tests follow TDD methodology - written BEFORE the implementation.

Test Categories:
    1. Default Configuration: Tests for default patterns and factory method
    2. Loading Configuration: Tests for LatchIdentificationConfig.load_from_yaml()
    3. Error Handling: Missing files, invalid YAML, empty patterns
    4. Pattern Validation: Tests for glob-style pattern support

See Also:
    - Spec E01-F04-T01 for requirements
    - src/ink/infrastructure/config/latch_config.py for implementation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


class TestDefaultSequentialPatterns:
    """Tests for DEFAULT_SEQUENTIAL_PATTERNS constant."""

    def test_default_patterns_constant_exists(self) -> None:
        """Test that DEFAULT_SEQUENTIAL_PATTERNS constant is defined.

        The constant should contain default patterns for matching common
        sequential cell naming conventions like DFF, LATCH, FF.
        """
        from ink.infrastructure.config.latch_config import DEFAULT_SEQUENTIAL_PATTERNS

        assert DEFAULT_SEQUENTIAL_PATTERNS is not None
        assert isinstance(DEFAULT_SEQUENTIAL_PATTERNS, list)

    def test_default_patterns_contains_dff(self) -> None:
        """Test that default patterns include *DFF* pattern.

        This pattern matches: DFFR_X1, SDFFR_X2, DFF_POS, etc.
        """
        from ink.infrastructure.config.latch_config import DEFAULT_SEQUENTIAL_PATTERNS

        assert "*DFF*" in DEFAULT_SEQUENTIAL_PATTERNS

    def test_default_patterns_contains_latch(self) -> None:
        """Test that default patterns include *LATCH* pattern.

        This pattern matches: LATCH_X1, DLATCH_X2, etc.
        """
        from ink.infrastructure.config.latch_config import DEFAULT_SEQUENTIAL_PATTERNS

        assert "*LATCH*" in DEFAULT_SEQUENTIAL_PATTERNS

    def test_default_patterns_contains_ff(self) -> None:
        """Test that default patterns include *FF* pattern.

        This pattern is a broader fallback matching: FF_X1, JKFF_X1, SRFF_X1, etc.
        """
        from ink.infrastructure.config.latch_config import DEFAULT_SEQUENTIAL_PATTERNS

        assert "*FF*" in DEFAULT_SEQUENTIAL_PATTERNS

    def test_default_patterns_order_is_specific_to_general(self) -> None:
        """Test that patterns are ordered from specific to general.

        More specific patterns (*DFF*, *LATCH*) should come before
        broader patterns (*FF*) for efficient matching.
        """
        from ink.infrastructure.config.latch_config import DEFAULT_SEQUENTIAL_PATTERNS

        dff_index = DEFAULT_SEQUENTIAL_PATTERNS.index("*DFF*")
        latch_index = DEFAULT_SEQUENTIAL_PATTERNS.index("*LATCH*")
        ff_index = DEFAULT_SEQUENTIAL_PATTERNS.index("*FF*")

        # *FF* should be last (broadest pattern)
        assert ff_index > dff_index
        assert ff_index > latch_index


class TestLatchIdentificationConfigDataclass:
    """Tests for LatchIdentificationConfig dataclass structure."""

    def test_config_is_frozen_dataclass(self) -> None:
        """Test that config is an immutable (frozen) dataclass.

        Immutability prevents accidental modification after creation,
        ensuring thread-safety and predictable behavior.
        """
        from dataclasses import is_dataclass

        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        assert is_dataclass(LatchIdentificationConfig)

        # Test that it's frozen by attempting modification
        config = LatchIdentificationConfig(patterns=["*DFF*"], case_sensitive=False)
        with pytest.raises(AttributeError):
            config.patterns = ["*LATCH*"]  # type: ignore[misc]

    def test_config_has_patterns_field(self) -> None:
        """Test that config has 'patterns' field as a sequence of strings."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config = LatchIdentificationConfig(patterns=["*DFF*", "*LATCH*"])
        assert hasattr(config, "patterns")
        # Patterns are stored as tuple for immutability
        assert list(config.patterns) == ["*DFF*", "*LATCH*"]

    def test_config_has_case_sensitive_field(self) -> None:
        """Test that config has 'case_sensitive' field defaulting to False."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        # Test default value
        config = LatchIdentificationConfig(patterns=["*DFF*"])
        assert hasattr(config, "case_sensitive")
        assert config.case_sensitive is False

        # Test explicit value
        config_sensitive = LatchIdentificationConfig(patterns=["*DFF*"], case_sensitive=True)
        assert config_sensitive.case_sensitive is True


class TestLatchIdentificationConfigDefault:
    """Tests for LatchIdentificationConfig.default() factory method."""

    def test_default_factory_returns_config(self) -> None:
        """Test that default() returns a LatchIdentificationConfig instance."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config = LatchIdentificationConfig.default()
        assert isinstance(config, LatchIdentificationConfig)

    def test_default_factory_uses_default_patterns(self) -> None:
        """Test that default() uses DEFAULT_SEQUENTIAL_PATTERNS."""
        from ink.infrastructure.config.latch_config import (
            DEFAULT_SEQUENTIAL_PATTERNS,
            LatchIdentificationConfig,
        )

        config = LatchIdentificationConfig.default()
        # Compare as lists since patterns are stored as tuple
        assert list(config.patterns) == DEFAULT_SEQUENTIAL_PATTERNS

    def test_default_factory_is_case_insensitive(self) -> None:
        """Test that default() sets case_sensitive to False."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config = LatchIdentificationConfig.default()
        assert config.case_sensitive is False


class TestLatchIdentificationConfigLoadFromYaml:
    """Tests for LatchIdentificationConfig.load_from_yaml()."""

    def test_load_valid_yaml_file(self, tmp_path: Path) -> None:
        """Test loading a valid YAML configuration file.

        The file contains custom patterns that should override defaults.
        """
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        # Create valid YAML config file
        config_file = tmp_path / "latch_patterns.yaml"
        config_file.write_text("""
latch_identification:
  patterns:
    - "*DFF*"
    - "*LATCH*"
    - "*REGF*"
  case_sensitive: false
""")

        config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == ["*DFF*", "*LATCH*", "*REGF*"]
        assert config.case_sensitive is False

    def test_load_yaml_with_case_sensitive_true(self, tmp_path: Path) -> None:
        """Test loading YAML with case_sensitive set to true."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config_file = tmp_path / "latch_patterns.yaml"
        config_file.write_text("""
latch_identification:
  patterns:
    - "*DFF*"
  case_sensitive: true
""")

        config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert config.case_sensitive is True

    def test_load_yaml_with_comments(self, tmp_path: Path) -> None:
        """Test that YAML comments are handled correctly."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config_file = tmp_path / "latch_patterns.yaml"
        config_file.write_text("""
# Configuration for latch identification
latch_identification:
  # Patterns for detecting sequential cells
  patterns:
    - "*DFF*"      # Standard D flip-flops
    - "*LATCH*"    # Latch elements
  case_sensitive: false  # Case-insensitive matching
""")

        config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == ["*DFF*", "*LATCH*"]

    def test_load_yaml_with_missing_case_sensitive(self, tmp_path: Path) -> None:
        """Test that missing case_sensitive defaults to False."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config_file = tmp_path / "latch_patterns.yaml"
        config_file.write_text("""
latch_identification:
  patterns:
    - "*DFF*"
""")

        config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert config.case_sensitive is False


class TestLatchIdentificationConfigErrorHandling:
    """Tests for error handling in configuration loading."""

    def test_missing_file_returns_default_config(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that missing config file returns default configuration.

        Should log a warning but not raise an exception.
        """
        from ink.infrastructure.config.latch_config import (
            DEFAULT_SEQUENTIAL_PATTERNS,
            LatchIdentificationConfig,
        )

        missing_file = tmp_path / "nonexistent.yaml"

        with caplog.at_level(logging.WARNING):
            config = LatchIdentificationConfig.load_from_yaml(missing_file)

        assert list(config.patterns) == DEFAULT_SEQUENTIAL_PATTERNS
        assert config.case_sensitive is False
        assert "missing" in caplog.text.lower() or "not found" in caplog.text.lower()

    def test_invalid_yaml_returns_default_config(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that invalid YAML syntax returns default configuration.

        Should log an error and return defaults.
        """
        from ink.infrastructure.config.latch_config import (
            DEFAULT_SEQUENTIAL_PATTERNS,
            LatchIdentificationConfig,
        )

        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("""
latch_identification:
  patterns:
    - *DFF*  # Missing quotes - invalid YAML
    - *LATCH*
""")

        with caplog.at_level(logging.ERROR):
            config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == DEFAULT_SEQUENTIAL_PATTERNS
        assert "error" in caplog.text.lower() or "invalid" in caplog.text.lower()

    def test_empty_yaml_file_returns_default_config(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that empty YAML file returns default configuration."""
        from ink.infrastructure.config.latch_config import (
            DEFAULT_SEQUENTIAL_PATTERNS,
            LatchIdentificationConfig,
        )

        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        with caplog.at_level(logging.WARNING):
            config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == DEFAULT_SEQUENTIAL_PATTERNS

    def test_empty_patterns_list_returns_default_patterns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that empty patterns list is replaced with defaults.

        Empty patterns would result in no latch detection, which is
        likely a configuration error.
        """
        from ink.infrastructure.config.latch_config import (
            DEFAULT_SEQUENTIAL_PATTERNS,
            LatchIdentificationConfig,
        )

        config_file = tmp_path / "empty_patterns.yaml"
        config_file.write_text("""
latch_identification:
  patterns: []
  case_sensitive: false
""")

        with caplog.at_level(logging.WARNING):
            config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == DEFAULT_SEQUENTIAL_PATTERNS
        assert "empty" in caplog.text.lower()

    def test_missing_patterns_key_returns_default_patterns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that missing patterns key uses default patterns."""
        from ink.infrastructure.config.latch_config import (
            DEFAULT_SEQUENTIAL_PATTERNS,
            LatchIdentificationConfig,
        )

        config_file = tmp_path / "missing_patterns.yaml"
        config_file.write_text("""
latch_identification:
  case_sensitive: true
""")

        with caplog.at_level(logging.WARNING):
            config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == DEFAULT_SEQUENTIAL_PATTERNS

    def test_missing_latch_identification_section_returns_defaults(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that missing top-level section uses defaults."""
        from ink.infrastructure.config.latch_config import (
            DEFAULT_SEQUENTIAL_PATTERNS,
            LatchIdentificationConfig,
        )

        config_file = tmp_path / "wrong_structure.yaml"
        config_file.write_text("""
some_other_config:
  key: value
""")

        with caplog.at_level(logging.WARNING):
            config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == DEFAULT_SEQUENTIAL_PATTERNS


class TestLatchIdentificationConfigPatternFormat:
    """Tests for pattern format and validation."""

    def test_patterns_with_wildcards_are_accepted(self, tmp_path: Path) -> None:
        """Test that glob-style wildcards are accepted in patterns."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config_file = tmp_path / "wildcards.yaml"
        config_file.write_text("""
latch_identification:
  patterns:
    - "*DFF*"
    - "LATCH_?"
    - "FF*"
    - "*_REG"
""")

        config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == ["*DFF*", "LATCH_?", "FF*", "*_REG"]

    def test_patterns_preserve_order(self, tmp_path: Path) -> None:
        """Test that pattern order is preserved from YAML file."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config_file = tmp_path / "ordered.yaml"
        config_file.write_text("""
latch_identification:
  patterns:
    - "*LATCH*"
    - "*DFF*"
    - "*FF*"
""")

        config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == ["*LATCH*", "*DFF*", "*FF*"]
        assert config.patterns[0] == "*LATCH*"  # First pattern preserved

    def test_unicode_patterns_are_supported(self, tmp_path: Path) -> None:
        """Test that Unicode characters in patterns are supported.

        Some international cell libraries may use non-ASCII characters.
        """
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config_file = tmp_path / "unicode.yaml"
        config_file.write_text(
            """
latch_identification:
  patterns:
    - "*DFF*"
    - "*レジスタ*"
""",
            encoding="utf-8",
        )

        config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert "*レジスタ*" in config.patterns


class TestLatchIdentificationConfigIntegration:
    """Integration tests for configuration with file system."""

    def test_load_from_project_config_directory(self, tmp_path: Path) -> None:
        """Test loading from a project's config directory."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        # Create config directory structure
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "latch_patterns.yaml"
        config_file.write_text("""
latch_identification:
  patterns:
    - "*DFF*"
    - "*LATCH*"
""")

        config = LatchIdentificationConfig.load_from_yaml(config_file)

        assert list(config.patterns) == ["*DFF*", "*LATCH*"]

    def test_config_file_with_whitespace_patterns(self, tmp_path: Path) -> None:
        """Test that patterns with extra whitespace are handled correctly."""
        from ink.infrastructure.config.latch_config import LatchIdentificationConfig

        config_file = tmp_path / "whitespace.yaml"
        config_file.write_text("""
latch_identification:
  patterns:
    - "  *DFF*  "
    - "*LATCH*"
""")

        config = LatchIdentificationConfig.load_from_yaml(config_file)

        # Patterns should be stripped of leading/trailing whitespace
        # or handled consistently by the pattern matcher
        assert len(config.patterns) == 2
