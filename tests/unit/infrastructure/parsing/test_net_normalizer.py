"""Unit tests for NetNormalizer.

These tests verify the net name normalization and classification functionality
used to process CDL netlist net names into a consistent format.

TDD Phase: RED - Tests written before implementation.
"""

from collections.abc import Iterable

import pytest

from ink.domain.value_objects.net import NetInfo, NetType
from ink.infrastructure.parsing.net_normalizer import NetNormalizer


class TestNetNormalizerBusNotation:
    """Tests for bus notation normalization (e.g., data<7> -> data[7])."""

    def test_normalize_simple_bus_bit(self) -> None:
        """Test normalizing a single bus bit: data<7> -> data[7]."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("data<7>")

        assert info.normalized_name == "data[7]"
        assert info.is_bus is True
        assert info.bus_index == 7
        assert info.original_name == "data<7>"
        assert info.net_type == NetType.SIGNAL

    def test_normalize_bus_bit_zero(self) -> None:
        """Test normalizing bus bit zero: addr<0> -> addr[0]."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("addr<0>")

        assert info.normalized_name == "addr[0]"
        assert info.is_bus is True
        assert info.bus_index == 0

    def test_normalize_bus_with_large_index(self) -> None:
        """Test normalizing bus with large index: mem<255> -> mem[255]."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("mem<255>")

        assert info.normalized_name == "mem[255]"
        assert info.is_bus is True
        assert info.bus_index == 255

    def test_normalize_bus_with_underscore_name(self) -> None:
        """Test normalizing bus with underscores: data_in<3> -> data_in[3]."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("data_in<3>")

        assert info.normalized_name == "data_in[3]"
        assert info.is_bus is True
        assert info.bus_index == 3


class TestNetNormalizerPowerNets:
    """Tests for power net detection and classification."""

    @pytest.mark.parametrize(
        "net_name",
        [
            "VDD",
            "VDDA",
            "VDDIO",
            "VDDCORE",
            "VCC",
            "VCCA",
            "VPWR",
        ],
    )
    def test_power_net_detection(self, net_name: str) -> None:
        """Test that common power net names are detected."""
        normalizer = NetNormalizer()
        info = normalizer.normalize(net_name)

        assert info.net_type == NetType.POWER
        assert info.is_bus is False

    def test_power_net_with_trailing_exclamation(self) -> None:
        """Test power net with trailing !: VDD! -> VDD."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("VDD!")

        assert info.normalized_name == "VDD"
        assert info.net_type == NetType.POWER
        assert info.original_name == "VDD!"

    def test_power_net_case_insensitive_lower(self) -> None:
        """Test case-insensitive power detection: vdd."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("vdd")

        assert info.net_type == NetType.POWER

    def test_power_net_case_insensitive_mixed(self) -> None:
        """Test case-insensitive power detection: Vdd."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("Vdd")

        assert info.net_type == NetType.POWER


class TestNetNormalizerGroundNets:
    """Tests for ground net detection and classification."""

    @pytest.mark.parametrize(
        "net_name",
        [
            "VSS",
            "VSSA",
            "VSSIO",
            "VSSCORE",
            "GND",
            "GNDA",
            "GNDIO",
            "VGND",
        ],
    )
    def test_ground_net_detection(self, net_name: str) -> None:
        """Test that common ground net names are detected."""
        normalizer = NetNormalizer()
        info = normalizer.normalize(net_name)

        assert info.net_type == NetType.GROUND
        assert info.is_bus is False

    def test_ground_net_with_trailing_exclamation(self) -> None:
        """Test ground net with trailing !: VSS! -> VSS."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("VSS!")

        assert info.normalized_name == "VSS"
        assert info.net_type == NetType.GROUND
        assert info.original_name == "VSS!"

    def test_ground_net_case_insensitive_lower(self) -> None:
        """Test case-insensitive ground detection: gnd."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("gnd")

        assert info.net_type == NetType.GROUND

    def test_ground_net_case_insensitive_mixed(self) -> None:
        """Test case-insensitive ground detection: Vss."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("Vss")

        assert info.net_type == NetType.GROUND


class TestNetNormalizerSpecialCharacters:
    """Tests for handling trailing special characters."""

    def test_strip_trailing_exclamation(self) -> None:
        """Test removal of trailing ! from net names."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("VDD!")

        assert info.normalized_name == "VDD"
        assert info.original_name == "VDD!"

    def test_strip_trailing_question(self) -> None:
        """Test removal of trailing ? from net names."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("net1?")

        assert info.normalized_name == "net1"
        assert info.original_name == "net1?"

    def test_strip_multiple_trailing_special_chars(self) -> None:
        """Test removal of multiple trailing special chars: net!? -> net."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("net!?")

        assert info.normalized_name == "net"

    def test_preserve_internal_special_chars(self) -> None:
        """Test that special chars within the name are preserved: a!b -> a!b."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("a!b")

        # Internal special chars should be preserved
        assert info.normalized_name == "a!b"


class TestNetNormalizerSignalNets:
    """Tests for normal signal net classification."""

    @pytest.mark.parametrize(
        "net_name",
        [
            "net1",
            "clk",
            "data_valid",
            "addr_15",
            "reset_n",
            "clock_div2",
            "signal_out",
        ],
    )
    def test_signal_net_classification(self, net_name: str) -> None:
        """Test normal signal nets are classified as SIGNAL type."""
        normalizer = NetNormalizer()
        info = normalizer.normalize(net_name)

        assert info.net_type == NetType.SIGNAL
        assert info.is_bus is False
        assert info.normalized_name == net_name

    def test_signal_net_not_matching_power_pattern(self) -> None:
        """Test nets that look similar but aren't power: VDATA."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("VDATA")

        # VDATA should not match VDD pattern
        assert info.net_type == NetType.SIGNAL


class TestNetNormalizerCache:
    """Tests for caching functionality."""

    def test_cache_returns_same_object(self) -> None:
        """Test that repeated normalize calls return the same cached object."""
        normalizer = NetNormalizer()

        info1 = normalizer.normalize("data<7>")
        info2 = normalizer.normalize("data<7>")

        # Should return the exact same object (identity check)
        assert info1 is info2

    def test_cache_different_nets(self) -> None:
        """Test that different nets are cached separately."""
        normalizer = NetNormalizer()

        info1 = normalizer.normalize("data<7>")
        info2 = normalizer.normalize("data<8>")

        assert info1 is not info2
        assert info1.bus_index == 7
        assert info2.bus_index == 8


class TestNetNormalizerHelperMethods:
    """Tests for helper methods like is_power_or_ground."""

    def test_is_power_or_ground_power(self) -> None:
        """Test is_power_or_ground returns True for power nets."""
        normalizer = NetNormalizer()

        assert normalizer.is_power_or_ground("VDD") is True
        assert normalizer.is_power_or_ground("VCC") is True
        assert normalizer.is_power_or_ground("VPWR") is True

    def test_is_power_or_ground_ground(self) -> None:
        """Test is_power_or_ground returns True for ground nets."""
        normalizer = NetNormalizer()

        assert normalizer.is_power_or_ground("VSS") is True
        assert normalizer.is_power_or_ground("GND") is True
        assert normalizer.is_power_or_ground("VGND") is True

    def test_is_power_or_ground_signal(self) -> None:
        """Test is_power_or_ground returns False for signal nets."""
        normalizer = NetNormalizer()

        assert normalizer.is_power_or_ground("net1") is False
        assert normalizer.is_power_or_ground("clk") is False
        assert normalizer.is_power_or_ground("data<7>") is False


class TestNetNormalizerEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_net_name(self) -> None:
        """Test handling of empty net name."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("")

        assert info.normalized_name == ""
        assert info.net_type == NetType.SIGNAL
        assert info.is_bus is False

    def test_only_special_characters(self) -> None:
        """Test handling of net name with only special characters."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("!?")

        assert info.normalized_name == ""
        assert info.net_type == NetType.SIGNAL

    def test_numeric_only_net_name(self) -> None:
        """Test handling of numeric-only net names."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("123")

        assert info.normalized_name == "123"
        assert info.net_type == NetType.SIGNAL
        assert info.is_bus is False

    def test_very_long_net_name(self) -> None:
        """Test handling of very long net names (>256 chars)."""
        normalizer = NetNormalizer()
        long_name = "a" * 300
        info = normalizer.normalize(long_name)

        assert info.normalized_name == long_name
        assert info.net_type == NetType.SIGNAL

    def test_net_name_with_spaces(self) -> None:
        """Test handling of net names containing spaces."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("net with spaces")

        # Spaces should be preserved in the normalized name
        assert info.normalized_name == "net with spaces"
        assert info.net_type == NetType.SIGNAL

    def test_bus_notation_only_angle_brackets(self) -> None:
        """Test net name that is only angle bracket notation: <5>.

        A net name with no base name before the angle brackets is unusual
        and is NOT treated as a bus notation. It's kept as a literal string.
        """
        normalizer = NetNormalizer()
        info = normalizer.normalize("<5>")

        # No base name means this is not a valid bus notation
        # Keep as literal string since this is an unusual edge case
        assert info.is_bus is False
        assert info.bus_index is None
        assert info.normalized_name == "<5>"

    def test_nested_angle_brackets_not_bus(self) -> None:
        """Test that nested angle brackets are not treated as bus: a<<7>>."""
        normalizer = NetNormalizer()
        info = normalizer.normalize("a<<7>>")

        # Nested brackets should not match the bus pattern
        assert info.is_bus is False
        assert info.normalized_name == "a<<7>>"


class TestNetNormalizerCustomNets:
    """Tests for custom power/ground net name configuration."""

    def test_custom_power_net_single(self) -> None:
        """Test single custom power net name."""
        normalizer = NetNormalizer(power_nets=["AVDD"])
        info = normalizer.normalize("AVDD")

        assert info.net_type == NetType.POWER
        assert info.normalized_name == "AVDD"

    def test_custom_power_nets_multiple(self) -> None:
        """Test multiple custom power net names."""
        normalizer = NetNormalizer(power_nets=["AVDD", "DVDD", "IOVDD"])

        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("DVDD").net_type == NetType.POWER
        assert normalizer.normalize("IOVDD").net_type == NetType.POWER

    def test_custom_ground_net_single(self) -> None:
        """Test single custom ground net name."""
        normalizer = NetNormalizer(ground_nets=["AVSS"])
        info = normalizer.normalize("AVSS")

        assert info.net_type == NetType.GROUND
        assert info.normalized_name == "AVSS"

    def test_custom_ground_nets_multiple(self) -> None:
        """Test multiple custom ground net names."""
        normalizer = NetNormalizer(ground_nets=["AVSS", "DVSS", "IOVSS"])

        assert normalizer.normalize("AVSS").net_type == NetType.GROUND
        assert normalizer.normalize("DVSS").net_type == NetType.GROUND
        assert normalizer.normalize("IOVSS").net_type == NetType.GROUND

    def test_custom_nets_case_insensitive(self) -> None:
        """Test that custom net names are case-insensitive."""
        normalizer = NetNormalizer(
            power_nets=["AVDD"],
            ground_nets=["AVSS"],
        )

        # Various case combinations should all match
        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("avdd").net_type == NetType.POWER
        assert normalizer.normalize("Avdd").net_type == NetType.POWER
        assert normalizer.normalize("AVSS").net_type == NetType.GROUND
        assert normalizer.normalize("avss").net_type == NetType.GROUND

    def test_custom_nets_with_underscore(self) -> None:
        """Test custom net names with underscores."""
        normalizer = NetNormalizer(
            power_nets=["VDD_CORE", "VDD_IO", "VDD_PLL"],
            ground_nets=["VSS_CORE", "VSS_IO"],
        )

        assert normalizer.normalize("VDD_CORE").net_type == NetType.POWER
        assert normalizer.normalize("VDD_IO").net_type == NetType.POWER
        assert normalizer.normalize("VSS_CORE").net_type == NetType.GROUND

    def test_custom_nets_with_trailing_chars(self) -> None:
        """Test that trailing ! is stripped before custom net matching."""
        normalizer = NetNormalizer(power_nets=["AVDD"])
        info = normalizer.normalize("AVDD!")

        assert info.net_type == NetType.POWER
        assert info.normalized_name == "AVDD"
        assert info.original_name == "AVDD!"

    def test_custom_nets_combined_with_defaults(self) -> None:
        """Test that custom nets work alongside default patterns."""
        normalizer = NetNormalizer(
            power_nets=["AVDD"],  # Custom
            ground_nets=["AVSS"],  # Custom
        )

        # Custom nets should work
        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("AVSS").net_type == NetType.GROUND

        # Default patterns should still work
        assert normalizer.normalize("VDD").net_type == NetType.POWER
        assert normalizer.normalize("VDDA").net_type == NetType.POWER
        assert normalizer.normalize("VSS").net_type == NetType.GROUND
        assert normalizer.normalize("GND").net_type == NetType.GROUND

    def test_custom_nets_priority_over_patterns(self) -> None:
        """Test that custom nets take priority (though usually irrelevant)."""
        # This tests that even if a name matches both custom and pattern,
        # the custom check happens first (for performance)
        normalizer = NetNormalizer(power_nets=["VDD"])  # Same as pattern

        # Should still be detected as POWER
        assert normalizer.normalize("VDD").net_type == NetType.POWER

    def test_empty_custom_nets(self) -> None:
        """Test that empty custom net lists work (uses only defaults)."""
        normalizer = NetNormalizer(power_nets=[], ground_nets=[])

        # Should use default patterns
        assert normalizer.normalize("VDD").net_type == NetType.POWER
        assert normalizer.normalize("VSS").net_type == NetType.GROUND
        assert normalizer.normalize("clk").net_type == NetType.SIGNAL

    def test_custom_nets_only_no_defaults(self) -> None:
        """Test that unrecognized nets are still SIGNAL with custom nets."""
        normalizer = NetNormalizer(
            power_nets=["AVDD"],
            ground_nets=["AVSS"],
        )

        # Unknown net should be SIGNAL
        assert normalizer.normalize("custom_signal").net_type == NetType.SIGNAL

    def test_custom_nets_from_tuple(self) -> None:
        """Test that tuples work as input (any Iterable)."""
        normalizer = NetNormalizer(
            power_nets=("AVDD", "DVDD"),
            ground_nets=("AVSS", "DVSS"),
        )

        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("AVSS").net_type == NetType.GROUND

    def test_custom_nets_from_generator(self) -> None:
        """Test that generators work as input."""
        def power_gen() -> Iterable[str]:
            yield "AVDD"
            yield "DVDD"

        normalizer = NetNormalizer(power_nets=power_gen())

        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("DVDD").net_type == NetType.POWER


class TestNetNormalizerFromConfig:
    """Tests for creating NetNormalizer from NetClassificationConfig.

    These tests verify the from_config() factory method that creates a
    NetNormalizer instance from a NetClassificationConfig object.

    TDD Phase: RED - Tests written before implementation.
    """

    def test_from_config_uses_custom_power_names(self) -> None:
        """Test factory uses power_names from config."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig(
            power_names=["AVDD", "DVDD"],
            power_patterns=[],
            ground_names=[],
            ground_patterns=[],
            override_defaults=False,
        )

        normalizer = NetNormalizer.from_config(config)

        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("DVDD").net_type == NetType.POWER

    def test_from_config_uses_custom_ground_names(self) -> None:
        """Test factory uses ground_names from config."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig(
            power_names=[],
            power_patterns=[],
            ground_names=["AVSS", "DVSS"],
            ground_patterns=[],
            override_defaults=False,
        )

        normalizer = NetNormalizer.from_config(config)

        assert normalizer.normalize("AVSS").net_type == NetType.GROUND
        assert normalizer.normalize("DVSS").net_type == NetType.GROUND

    def test_from_config_adds_custom_power_patterns(self) -> None:
        """Test factory adds custom power patterns to normalizer."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig(
            power_names=[],
            power_patterns=["^PWR_.*$"],
            ground_names=[],
            ground_patterns=[],
            override_defaults=False,
        )

        normalizer = NetNormalizer.from_config(config)

        # Custom pattern should match
        assert normalizer.normalize("PWR_CORE").net_type == NetType.POWER
        assert normalizer.normalize("PWR_IO").net_type == NetType.POWER
        # Non-matching should be SIGNAL
        assert normalizer.normalize("POWER_CORE").net_type == NetType.SIGNAL

    def test_from_config_adds_custom_ground_patterns(self) -> None:
        """Test factory adds custom ground patterns to normalizer."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig(
            power_names=[],
            power_patterns=[],
            ground_names=[],
            ground_patterns=["^GND_.*$"],
            override_defaults=False,
        )

        normalizer = NetNormalizer.from_config(config)

        # Custom pattern should match
        assert normalizer.normalize("GND_CORE").net_type == NetType.GROUND
        assert normalizer.normalize("GND_IO").net_type == NetType.GROUND

    def test_from_config_preserves_defaults_when_override_false(self) -> None:
        """Test factory keeps default patterns when override_defaults=False."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig(
            power_names=["AVDD"],
            power_patterns=[],
            ground_names=["AVSS"],
            ground_patterns=[],
            override_defaults=False,
        )

        normalizer = NetNormalizer.from_config(config)

        # Custom names should work
        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("AVSS").net_type == NetType.GROUND
        # Default patterns should still work
        assert normalizer.normalize("VDD").net_type == NetType.POWER
        assert normalizer.normalize("VSS").net_type == NetType.GROUND
        assert normalizer.normalize("VDDA").net_type == NetType.POWER
        assert normalizer.normalize("GND").net_type == NetType.GROUND

    def test_from_config_clears_defaults_when_override_true(self) -> None:
        """Test factory clears default patterns when override_defaults=True."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig(
            power_names=["AVDD"],
            power_patterns=[],
            ground_names=["AVSS"],
            ground_patterns=[],
            override_defaults=True,
        )

        normalizer = NetNormalizer.from_config(config)

        # Custom names should work
        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("AVSS").net_type == NetType.GROUND
        # Default patterns should NOT work (override=True)
        assert normalizer.normalize("VDD").net_type == NetType.SIGNAL
        assert normalizer.normalize("VSS").net_type == NetType.SIGNAL
        assert normalizer.normalize("VDDA").net_type == NetType.SIGNAL
        assert normalizer.normalize("GND").net_type == NetType.SIGNAL

    def test_from_config_with_empty_config(self) -> None:
        """Test factory with empty configuration."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig()

        normalizer = NetNormalizer.from_config(config)

        # Default patterns should work
        assert normalizer.normalize("VDD").net_type == NetType.POWER
        assert normalizer.normalize("VSS").net_type == NetType.GROUND
        assert normalizer.normalize("clk").net_type == NetType.SIGNAL

    def test_from_config_with_combined_names_and_patterns(self) -> None:
        """Test factory with both names and patterns configured."""
        from ink.infrastructure.config.net_classification_config import (
            NetClassificationConfig,
        )

        config = NetClassificationConfig(
            power_names=["AVDD"],
            power_patterns=["^VDDQ[0-9]*$"],
            ground_names=["AVSS"],
            ground_patterns=["^VSSQ[0-9]*$"],
            override_defaults=False,
        )

        normalizer = NetNormalizer.from_config(config)

        # Custom names
        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("AVSS").net_type == NetType.GROUND
        # Custom patterns
        assert normalizer.normalize("VDDQ0").net_type == NetType.POWER
        assert normalizer.normalize("VDDQ1").net_type == NetType.POWER
        assert normalizer.normalize("VSSQ0").net_type == NetType.GROUND
        assert normalizer.normalize("VSSQ1").net_type == NetType.GROUND
        # Default patterns
        assert normalizer.normalize("VDD").net_type == NetType.POWER
        assert normalizer.normalize("VSS").net_type == NetType.GROUND


class TestNetNormalizerPatternMethods:
    """Tests for pattern management methods on NetNormalizer.

    These tests verify the add_power_patterns(), add_ground_patterns(),
    and clear_default_patterns() methods.

    TDD Phase: RED - Tests written before implementation.
    """

    def test_add_power_patterns_single(self) -> None:
        """Test adding a single power pattern."""
        normalizer = NetNormalizer()
        normalizer.add_power_patterns(["^PWR_.*$"])

        assert normalizer.normalize("PWR_CORE").net_type == NetType.POWER

    def test_add_power_patterns_multiple(self) -> None:
        """Test adding multiple power patterns."""
        normalizer = NetNormalizer()
        normalizer.add_power_patterns(["^PWR_.*$", "^VDDQ[0-9]*$"])

        assert normalizer.normalize("PWR_CORE").net_type == NetType.POWER
        assert normalizer.normalize("VDDQ0").net_type == NetType.POWER
        assert normalizer.normalize("VDDQ1").net_type == NetType.POWER

    def test_add_ground_patterns_single(self) -> None:
        """Test adding a single ground pattern."""
        normalizer = NetNormalizer()
        normalizer.add_ground_patterns(["^GND_.*$"])

        assert normalizer.normalize("GND_CORE").net_type == NetType.GROUND

    def test_add_ground_patterns_multiple(self) -> None:
        """Test adding multiple ground patterns."""
        normalizer = NetNormalizer()
        normalizer.add_ground_patterns(["^GND_.*$", "^VSSQ[0-9]*$"])

        assert normalizer.normalize("GND_CORE").net_type == NetType.GROUND
        assert normalizer.normalize("VSSQ0").net_type == NetType.GROUND
        assert normalizer.normalize("VSSQ1").net_type == NetType.GROUND

    def test_add_patterns_invalidates_cache(self) -> None:
        """Test that adding patterns invalidates the cache."""
        normalizer = NetNormalizer()

        # First normalize - should be SIGNAL (no matching pattern)
        info1 = normalizer.normalize("PWR_CORE")
        assert info1.net_type == NetType.SIGNAL

        # Add pattern
        normalizer.add_power_patterns(["^PWR_.*$"])

        # Normalize again - should be POWER (pattern added, cache invalidated)
        info2 = normalizer.normalize("PWR_CORE")
        assert info2.net_type == NetType.POWER

        # Should NOT be the same object (cache was invalidated)
        assert info1 is not info2

    def test_clear_default_patterns(self) -> None:
        """Test clearing default patterns."""
        normalizer = NetNormalizer()

        # Before clearing - defaults work
        assert normalizer.normalize("VDD").net_type == NetType.POWER
        assert normalizer.normalize("VSS").net_type == NetType.GROUND

        # Clear defaults
        normalizer.clear_default_patterns()

        # After clearing - defaults don't work
        assert normalizer.normalize("VDD_test").net_type == NetType.SIGNAL
        assert normalizer.normalize("VSS_test").net_type == NetType.SIGNAL

    def test_clear_default_patterns_preserves_custom_names(self) -> None:
        """Test that clearing defaults preserves custom names."""
        normalizer = NetNormalizer(power_nets=["AVDD"], ground_nets=["AVSS"])
        normalizer.clear_default_patterns()

        # Custom names should still work
        assert normalizer.normalize("AVDD").net_type == NetType.POWER
        assert normalizer.normalize("AVSS").net_type == NetType.GROUND

    def test_clear_default_patterns_preserves_custom_patterns(self) -> None:
        """Test that clearing defaults preserves custom patterns."""
        normalizer = NetNormalizer()
        normalizer.add_power_patterns(["^PWR_.*$"])
        normalizer.add_ground_patterns(["^GND_.*$"])
        normalizer.clear_default_patterns()

        # Custom patterns should still work
        assert normalizer.normalize("PWR_CORE").net_type == NetType.POWER
        assert normalizer.normalize("GND_CORE").net_type == NetType.GROUND

    def test_clear_default_patterns_invalidates_cache(self) -> None:
        """Test that clearing defaults invalidates the cache."""
        normalizer = NetNormalizer()

        # Normalize with defaults
        info1 = normalizer.normalize("VDD")
        assert info1.net_type == NetType.POWER

        # Clear defaults
        normalizer.clear_default_patterns()

        # Normalize again - VDD no longer matches (different result)
        info2 = normalizer.normalize("VDD_new")
        assert info2.net_type == NetType.SIGNAL
