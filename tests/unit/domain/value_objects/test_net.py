"""Unit tests for Net value objects.

These tests verify the NetInfo and NetType domain value objects
used to represent normalized net information.

TDD Phase: RED - Tests written before implementation.
"""

import pytest

from ink.domain.value_objects.net import NetInfo, NetType


class TestNetType:
    """Tests for the NetType enumeration."""

    def test_signal_type_value(self) -> None:
        """Test SIGNAL type has correct value."""
        assert NetType.SIGNAL.value == "signal"

    def test_power_type_value(self) -> None:
        """Test POWER type has correct value."""
        assert NetType.POWER.value == "power"

    def test_ground_type_value(self) -> None:
        """Test GROUND type has correct value."""
        assert NetType.GROUND.value == "ground"

    def test_all_types_defined(self) -> None:
        """Test that all expected types are defined."""
        expected_types = {"SIGNAL", "POWER", "GROUND"}
        actual_types = {member.name for member in NetType}

        assert expected_types <= actual_types


class TestNetInfo:
    """Tests for the NetInfo value object."""

    def test_create_signal_net(self) -> None:
        """Test creating a signal net."""
        info = NetInfo(
            original_name="data",
            normalized_name="data",
            net_type=NetType.SIGNAL,
            is_bus=False,
        )

        assert info.original_name == "data"
        assert info.normalized_name == "data"
        assert info.net_type == NetType.SIGNAL
        assert info.is_bus is False
        assert info.bus_index is None

    def test_create_bus_net(self) -> None:
        """Test creating a bus net with index."""
        info = NetInfo(
            original_name="data<7>",
            normalized_name="data[7]",
            net_type=NetType.SIGNAL,
            is_bus=True,
            bus_index=7,
        )

        assert info.original_name == "data<7>"
        assert info.normalized_name == "data[7]"
        assert info.is_bus is True
        assert info.bus_index == 7

    def test_create_power_net(self) -> None:
        """Test creating a power net."""
        info = NetInfo(
            original_name="VDD!",
            normalized_name="VDD",
            net_type=NetType.POWER,
            is_bus=False,
        )

        assert info.net_type == NetType.POWER
        assert info.normalized_name == "VDD"

    def test_create_ground_net(self) -> None:
        """Test creating a ground net."""
        info = NetInfo(
            original_name="VSS",
            normalized_name="VSS",
            net_type=NetType.GROUND,
            is_bus=False,
        )

        assert info.net_type == NetType.GROUND

    def test_immutability(self) -> None:
        """Test that NetInfo is immutable (frozen dataclass)."""
        info = NetInfo(
            original_name="data",
            normalized_name="data",
            net_type=NetType.SIGNAL,
            is_bus=False,
        )

        # Attempting to modify should raise an error
        with pytest.raises(AttributeError):
            info.normalized_name = "modified"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Test that two NetInfo with same values are equal."""
        info1 = NetInfo(
            original_name="data",
            normalized_name="data",
            net_type=NetType.SIGNAL,
            is_bus=False,
        )
        info2 = NetInfo(
            original_name="data",
            normalized_name="data",
            net_type=NetType.SIGNAL,
            is_bus=False,
        )

        assert info1 == info2

    def test_inequality_different_name(self) -> None:
        """Test that NetInfo with different names are not equal."""
        info1 = NetInfo(
            original_name="data",
            normalized_name="data",
            net_type=NetType.SIGNAL,
            is_bus=False,
        )
        info2 = NetInfo(
            original_name="addr",
            normalized_name="addr",
            net_type=NetType.SIGNAL,
            is_bus=False,
        )

        assert info1 != info2

    def test_hashable(self) -> None:
        """Test that NetInfo is hashable (can be used in sets/dicts)."""
        info = NetInfo(
            original_name="data",
            normalized_name="data",
            net_type=NetType.SIGNAL,
            is_bus=False,
        )

        # Should be able to add to a set
        net_set = {info}
        assert info in net_set

        # Should be able to use as dict key
        net_dict = {info: "value"}
        assert net_dict[info] == "value"

    def test_bus_index_default_none(self) -> None:
        """Test that bus_index defaults to None for non-bus nets."""
        info = NetInfo(
            original_name="clk",
            normalized_name="clk",
            net_type=NetType.SIGNAL,
            is_bus=False,
        )

        assert info.bus_index is None

    def test_repr(self) -> None:
        """Test that NetInfo has a readable string representation."""
        info = NetInfo(
            original_name="data<7>",
            normalized_name="data[7]",
            net_type=NetType.SIGNAL,
            is_bus=True,
            bus_index=7,
        )

        repr_str = repr(info)
        # Should contain key information
        assert "data<7>" in repr_str or "data[7]" in repr_str
        assert "SIGNAL" in repr_str or "signal" in repr_str.lower()
