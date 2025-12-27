"""Net classification configuration for power/ground net names.

This module provides the NetClassificationConfig dataclass for managing
per-project power and ground net classification settings. Configuration
is stored in YAML format at {project_root}/.ink/net_classification.yaml.

The configuration allows users to:
    1. Define exact net names for power/ground classification
    2. Add custom regex patterns for matching power/ground nets
    3. Optionally override default patterns (VDD*, VSS*, etc.)

Configuration File Format:
    The YAML file follows this structure:

    ```yaml
    version: 1

    power_nets:
      names:
        - AVDD
        - DVDD
      patterns:
        - "^VDDQ[0-9]*$"

    ground_nets:
      names:
        - AVSS
      patterns:
        - "^GND_.*$"

    override_defaults: false
    ```

Design Decisions:
    - Uses YAML for human-readable configuration that can be version-controlled
    - Stores config in .ink/ folder to separate from user files
    - Gracefully handles missing files/sections with empty defaults
    - Version field for future migration support

See Also:
    - Spec E01-F01-T06 for requirements
    - NetNormalizer for using this configuration
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from pathlib import Path

# Configuration file constants
# We use .ink/ as the configuration folder to keep Ink settings separate
# from user project files and to follow the dotfile convention
CONFIG_DIR = ".ink"
CONFIG_FILENAME = "net_classification.yaml"

# Current configuration version - increment when making breaking changes
# to the YAML schema to support future migrations
CONFIG_VERSION = 1


@dataclass
class NetClassificationConfig:
    """Configuration for power/ground net classification.

    This dataclass holds the user-defined configuration for classifying
    nets as power or ground in a CDL netlist. It supports both exact
    net name matching and regex pattern matching.

    The configuration is designed to work with NetNormalizer to allow
    users to customize net classification on a per-project basis without
    modifying code.

    Attributes:
        power_names: Exact power net names (case-insensitive matching).
            Example: ["AVDD", "DVDD", "IOVDD", "VDD_CORE"]
        power_patterns: Regex patterns for power nets.
            Example: ["^VDDQ[0-9]*$", "^PWR_.*$"]
        ground_names: Exact ground net names (case-insensitive matching).
            Example: ["AVSS", "DVSS", "VSS_CORE"]
        ground_patterns: Regex patterns for ground nets.
            Example: ["^VSSQ[0-9]*$", "^GND_.*$"]
        override_defaults: If True, ignore default VDD/VSS patterns from
            NetNormalizer and only use custom names/patterns.

    Example:
        >>> # Load from project directory
        >>> config = NetClassificationConfig.load(Path("/path/to/project"))
        >>> print(config.power_names)
        ['AVDD', 'DVDD']

        >>> # Create programmatically
        >>> config = NetClassificationConfig(
        ...     power_names=["AVDD", "DVDD"],
        ...     ground_names=["AVSS", "DVSS"],
        ...     override_defaults=False,
        ... )
        >>> config.save(Path("/path/to/project"))
    """

    power_names: list[str] = field(default_factory=list)
    power_patterns: list[str] = field(default_factory=list)
    ground_names: list[str] = field(default_factory=list)
    ground_patterns: list[str] = field(default_factory=list)
    override_defaults: bool = False

    @classmethod
    def load(cls, project_path: Path) -> NetClassificationConfig:
        """Load configuration from project directory.

        Reads the YAML configuration file from {project_path}/.ink/net_classification.yaml.
        If the file doesn't exist, returns a default configuration with empty lists.

        This method is designed to be resilient to missing or malformed files:
        - Missing file: Returns empty defaults
        - Empty file: Returns empty defaults
        - Missing sections: Uses empty lists for missing sections

        Args:
            project_path: Path to the project root directory.

        Returns:
            NetClassificationConfig with values from file or empty defaults.

        Example:
            >>> config = NetClassificationConfig.load(Path("/my/project"))
            >>> if config.power_names:
            ...     print(f"Custom power nets: {config.power_names}")
            ... else:
            ...     print("Using default power net patterns")
        """
        config_file = project_path / CONFIG_DIR / CONFIG_FILENAME

        # Return defaults if config file doesn't exist
        # This allows the tool to work without any configuration
        if not config_file.exists():
            return cls()

        # Parse YAML file - safe_load prevents code execution
        with config_file.open(encoding="utf-8") as f:
            data: dict[str, Any] | None = yaml.safe_load(f)

        # Handle empty file (safe_load returns None for empty file)
        if data is None:
            return cls()

        # Extract power_nets section with fallbacks for missing keys
        # This allows partial configuration files to work
        power_nets = data.get("power_nets", {})
        if not isinstance(power_nets, dict):
            power_nets = {}

        # Extract ground_nets section with same fallback pattern
        ground_nets = data.get("ground_nets", {})
        if not isinstance(ground_nets, dict):
            ground_nets = {}

        return cls(
            power_names=power_nets.get("names", []) or [],
            power_patterns=power_nets.get("patterns", []) or [],
            ground_names=ground_nets.get("names", []) or [],
            ground_patterns=ground_nets.get("patterns", []) or [],
            override_defaults=bool(data.get("override_defaults", False)),
        )

    def save(self, project_path: Path) -> None:
        """Save configuration to project directory.

        Writes the configuration to {project_path}/.ink/net_classification.yaml.
        Creates the .ink directory if it doesn't exist.

        The saved YAML file includes:
        - A version field for future migration support
        - Power nets (names and patterns)
        - Ground nets (names and patterns)
        - Override defaults flag

        Args:
            project_path: Path to the project root directory.

        Example:
            >>> config = NetClassificationConfig(
            ...     power_names=["AVDD", "DVDD"],
            ...     override_defaults=True,
            ... )
            >>> config.save(Path("/my/project"))
            >>> # Creates /my/project/.ink/net_classification.yaml
        """
        # Ensure .ink directory exists
        config_dir = project_path / CONFIG_DIR
        config_dir.mkdir(parents=True, exist_ok=True)

        # Build YAML structure
        # We use explicit structure rather than dataclass-to-dict
        # to maintain the desired YAML layout and ordering
        data: dict[str, Any] = {
            "version": CONFIG_VERSION,
            "power_nets": {
                "names": self.power_names,
                "patterns": self.power_patterns,
            },
            "ground_nets": {
                "names": self.ground_names,
                "patterns": self.ground_patterns,
            },
            "override_defaults": self.override_defaults,
        }

        # Write YAML file with human-readable formatting
        # - default_flow_style=False: Use block style (multiline) for readability
        # - sort_keys=False: Preserve the order we defined above
        config_file = config_dir / CONFIG_FILENAME
        with config_file.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
