"""Unit tests for NetClassificationConfig.

This module tests the YAML-based configuration for power/ground net classification.
The tests follow TDD methodology - written BEFORE the implementation.

Test Categories:
    1. Loading Configuration: Tests for NetClassificationConfig.load()
    2. Saving Configuration: Tests for NetClassificationConfig.save()
    3. Round-trip: Tests that save then load preserves data
    4. Edge Cases: Empty files, missing sections, invalid YAML

See Also:
    - Spec E01-F01-T06 for requirements
    - src/ink/infrastructure/config/net_classification_config.py for implementation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class TestNetClassificationConfigLoad:
    """Tests for loading configuration from YAML files."""

    def test_load_returns_defaults_when_no_file(self, tmp_path: Path) -> None:
        """Test that missing config file returns empty defaults.

        When no .ink/net_classification.yaml exists, load() should return
        a NetClassificationConfig with empty lists and False override.
        """
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig.load(tmp_path)

        assert config.power_names == []
        assert config.power_patterns == []
        assert config.ground_names == []
        assert config.ground_patterns == []
        assert config.override_defaults is False

    def test_load_parses_power_names(self, tmp_path: Path) -> None:
        """Test loading power net names from YAML."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        # Create config file
        config_dir = tmp_path / ".ink"
        config_dir.mkdir()
        config_file = config_dir / "net_classification.yaml"
        config_file.write_text("""
version: 1
power_nets:
  names:
    - AVDD
    - DVDD
    - VDD_CORE
  patterns: []
ground_nets:
  names: []
  patterns: []
override_defaults: false
""")

        config = NetClassificationConfig.load(tmp_path)

        assert config.power_names == ["AVDD", "DVDD", "VDD_CORE"]

    def test_load_parses_ground_patterns(self, tmp_path: Path) -> None:
        """Test loading ground patterns from YAML."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config_dir = tmp_path / ".ink"
        config_dir.mkdir()
        config_file = config_dir / "net_classification.yaml"
        config_file.write_text("""
version: 1
power_nets:
  names: []
  patterns: []
ground_nets:
  names: []
  patterns:
    - "^VSSQ[0-9]*$"
    - "^GND_.*$"
override_defaults: false
""")

        config = NetClassificationConfig.load(tmp_path)

        assert config.ground_patterns == ["^VSSQ[0-9]*$", "^GND_.*$"]

    def test_load_handles_missing_sections(self, tmp_path: Path) -> None:
        """Test graceful handling of missing YAML sections.

        If power_nets or ground_nets sections are missing, load() should
        return empty lists rather than raising an error.
        """
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config_dir = tmp_path / ".ink"
        config_dir.mkdir()
        config_file = config_dir / "net_classification.yaml"
        config_file.write_text("""
version: 1
override_defaults: true
""")

        config = NetClassificationConfig.load(tmp_path)

        assert config.power_names == []
        assert config.power_patterns == []
        assert config.ground_names == []
        assert config.ground_patterns == []
        assert config.override_defaults is True

    def test_load_handles_empty_file(self, tmp_path: Path) -> None:
        """Test handling of empty YAML file."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config_dir = tmp_path / ".ink"
        config_dir.mkdir()
        config_file = config_dir / "net_classification.yaml"
        config_file.write_text("")

        config = NetClassificationConfig.load(tmp_path)

        assert config.power_names == []
        assert config.override_defaults is False

    def test_load_handles_partial_sections(self, tmp_path: Path) -> None:
        """Test handling when only names or patterns are specified."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config_dir = tmp_path / ".ink"
        config_dir.mkdir()
        config_file = config_dir / "net_classification.yaml"
        config_file.write_text("""
version: 1
power_nets:
  names:
    - AVDD
ground_nets:
  patterns:
    - "^GND_.*$"
""")

        config = NetClassificationConfig.load(tmp_path)

        assert config.power_names == ["AVDD"]
        assert config.power_patterns == []
        assert config.ground_names == []
        assert config.ground_patterns == ["^GND_.*$"]


class TestNetClassificationConfigSave:
    """Tests for saving configuration to YAML files."""

    def test_save_creates_ink_directory(self, tmp_path: Path) -> None:
        """Test that .ink directory is created if missing."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig(
            power_names=["AVDD"],
            power_patterns=[],
            ground_names=[],
            ground_patterns=[],
            override_defaults=False,
        )

        config.save(tmp_path)

        assert (tmp_path / ".ink").is_dir()
        assert (tmp_path / ".ink" / "net_classification.yaml").is_file()

    def test_save_writes_valid_yaml(self, tmp_path: Path) -> None:
        """Test that saved YAML can be parsed back."""
        import yaml

        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig(
            power_names=["AVDD", "DVDD"],
            power_patterns=["^PWR_.*$"],
            ground_names=["AVSS"],
            ground_patterns=["^GND_.*$"],
            override_defaults=True,
        )

        config.save(tmp_path)

        config_file = tmp_path / ".ink" / "net_classification.yaml"
        data = yaml.safe_load(config_file.read_text())

        assert data["version"] == 1
        assert data["power_nets"]["names"] == ["AVDD", "DVDD"]
        assert data["power_nets"]["patterns"] == ["^PWR_.*$"]
        assert data["ground_nets"]["names"] == ["AVSS"]
        assert data["ground_nets"]["patterns"] == ["^GND_.*$"]
        assert data["override_defaults"] is True


class TestNetClassificationConfigRoundTrip:
    """Tests for save then load preserving data."""

    def test_round_trip_preserves_all_fields(self, tmp_path: Path) -> None:
        """Test round-trip: save then load returns same data."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        original = NetClassificationConfig(
            power_names=["AVDD", "DVDD", "VDD_CORE"],
            power_patterns=["^VDDQ[0-9]*$", "^PWR_.*$"],
            ground_names=["AVSS", "DVSS"],
            ground_patterns=["^VSSQ[0-9]*$"],
            override_defaults=True,
        )

        original.save(tmp_path)
        loaded = NetClassificationConfig.load(tmp_path)

        assert loaded.power_names == original.power_names
        assert loaded.power_patterns == original.power_patterns
        assert loaded.ground_names == original.ground_names
        assert loaded.ground_patterns == original.ground_patterns
        assert loaded.override_defaults == original.override_defaults

    def test_round_trip_with_empty_config(self, tmp_path: Path) -> None:
        """Test round-trip with empty configuration."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        original = NetClassificationConfig()

        original.save(tmp_path)
        loaded = NetClassificationConfig.load(tmp_path)

        assert loaded.power_names == []
        assert loaded.power_patterns == []
        assert loaded.ground_names == []
        assert loaded.ground_patterns == []
        assert loaded.override_defaults is False


class TestNetClassificationConfigValidation:
    """Tests for configuration validation."""

    def test_config_is_dataclass(self) -> None:
        """Test that NetClassificationConfig is a proper dataclass."""
        from dataclasses import is_dataclass

        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        assert is_dataclass(NetClassificationConfig)

    def test_config_has_expected_fields(self) -> None:
        """Test that config has all expected fields."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig()

        assert hasattr(config, "power_names")
        assert hasattr(config, "power_patterns")
        assert hasattr(config, "ground_names")
        assert hasattr(config, "ground_patterns")
        assert hasattr(config, "override_defaults")
