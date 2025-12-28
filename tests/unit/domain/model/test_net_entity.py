"""Unit tests for Net domain entity.

This module tests the Net entity which represents a wire connecting multiple pins.
Net is a frozen dataclass with helper methods for querying fanout and pin count.

The Net entity is a core domain concept used in graph traversal to determine
connectivity between cells.

Note: This file is named test_net_entity.py to avoid conflict with the existing
test_net.py that tests NetInfo value object.
"""

from dataclasses import FrozenInstanceError

import pytest

from ink.domain.model.net import Net
from ink.domain.value_objects.identifiers import NetId, PinId


class TestNetCreation:
    """Test suite for Net entity creation."""

    def test_net_creation_with_all_fields(self) -> None:
        """Should create Net with all fields including connected pins."""
        net = Net(
            id=NetId("net_123"),
            name="net_123",
            connected_pin_ids=[PinId("XI1.Y"), PinId("XI2.A"), PinId("XI3.A")],
        )

        assert net.id == NetId("net_123")
        assert net.name == "net_123"
        assert len(net.connected_pin_ids) == 3

    def test_net_creation_with_default_empty_pins(self) -> None:
        """Should create Net with empty connected_pin_ids by default."""
        net = Net(
            id=NetId("net_empty"),
            name="net_empty",
        )

        assert net.id == NetId("net_empty")
        assert net.name == "net_empty"
        assert net.connected_pin_ids == ()

    def test_net_creation_with_single_pin(self) -> None:
        """Should create Net connected to a single pin."""
        net = Net(
            id=NetId("net_single"),
            name="net_single",
            connected_pin_ids=[PinId("XI1.Y")],
        )

        assert len(net.connected_pin_ids) == 1
        assert net.connected_pin_ids[0] == PinId("XI1.Y")


class TestNetIsMultiFanout:
    """Test suite for Net.is_multi_fanout() helper method."""

    def test_is_multi_fanout_true_for_multiple_pins(self) -> None:
        """is_multi_fanout() should return True when >1 pins connected."""
        net = Net(
            id=NetId("net_multi"),
            name="net_multi",
            connected_pin_ids=[PinId("XI1.Y"), PinId("XI2.A")],
        )

        assert net.is_multi_fanout() is True

    def test_is_multi_fanout_true_for_many_pins(self) -> None:
        """is_multi_fanout() should return True for nets with many fanout."""
        net = Net(
            id=NetId("net_bus"),
            name="net_bus",
            connected_pin_ids=[
                PinId("XI1.Y"),
                PinId("XI2.A"),
                PinId("XI3.A"),
                PinId("XI4.A"),
                PinId("XI5.A"),
            ],
        )

        assert net.is_multi_fanout() is True

    def test_is_multi_fanout_false_for_single_pin(self) -> None:
        """is_multi_fanout() should return False for single-pin nets."""
        net = Net(
            id=NetId("net_single"),
            name="net_single",
            connected_pin_ids=[PinId("XI1.Y")],
        )

        assert net.is_multi_fanout() is False

    def test_is_multi_fanout_false_for_empty_net(self) -> None:
        """is_multi_fanout() should return False for nets with no pins."""
        net = Net(
            id=NetId("net_empty"),
            name="net_empty",
            connected_pin_ids=[],
        )

        assert net.is_multi_fanout() is False


class TestNetPinCount:
    """Test suite for Net.pin_count() helper method."""

    def test_pin_count_returns_zero_for_empty_net(self) -> None:
        """pin_count() should return 0 for nets with no connected pins."""
        net = Net(
            id=NetId("net_empty"),
            name="net_empty",
        )

        assert net.pin_count() == 0

    def test_pin_count_returns_one_for_single_pin(self) -> None:
        """pin_count() should return 1 for nets with one connected pin."""
        net = Net(
            id=NetId("net_single"),
            name="net_single",
            connected_pin_ids=[PinId("XI1.Y")],
        )

        assert net.pin_count() == 1

    def test_pin_count_returns_correct_count_for_multiple_pins(self) -> None:
        """pin_count() should return correct count for multiple pins."""
        net = Net(
            id=NetId("net_multi"),
            name="net_multi",
            connected_pin_ids=[
                PinId("XI1.Y"),
                PinId("XI2.A"),
                PinId("XI3.A"),
            ],
        )

        assert net.pin_count() == 3


class TestNetImmutability:
    """Test suite for Net frozen dataclass immutability."""

    def test_net_id_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign id on frozen Net."""
        net = Net(
            id=NetId("net_123"),
            name="net_123",
        )

        with pytest.raises(FrozenInstanceError):
            net.id = NetId("net_456")  # type: ignore[misc]

    def test_net_name_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign name on frozen Net."""
        net = Net(
            id=NetId("net_123"),
            name="net_123",
        )

        with pytest.raises(FrozenInstanceError):
            net.name = "new_name"  # type: ignore[misc]

    def test_net_connected_pin_ids_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign connected_pin_ids."""
        net = Net(
            id=NetId("net_123"),
            name="net_123",
            connected_pin_ids=[PinId("XI1.Y")],
        )

        with pytest.raises(FrozenInstanceError):
            net.connected_pin_ids = [PinId("XI2.A")]  # type: ignore[misc, assignment]

    def test_net_connected_pin_ids_tuple_is_immutable(self) -> None:
        """connected_pin_ids should be a tuple (immutable)."""
        net = Net(
            id=NetId("net_123"),
            name="net_123",
            connected_pin_ids=[PinId("XI1.Y")],
        )

        # Tuple doesn't have append method
        assert not hasattr(net.connected_pin_ids, "append")


class TestNetEquality:
    """Test suite for Net equality comparisons."""

    def test_nets_with_same_values_are_equal(self) -> None:
        """Two Nets with identical values should be equal."""
        net1 = Net(
            id=NetId("net_123"),
            name="net_123",
            connected_pin_ids=[PinId("XI1.Y"), PinId("XI2.A")],
        )
        net2 = Net(
            id=NetId("net_123"),
            name="net_123",
            connected_pin_ids=[PinId("XI1.Y"), PinId("XI2.A")],
        )

        assert net1 == net2

    def test_nets_with_different_ids_are_not_equal(self) -> None:
        """Nets with different ids should not be equal."""
        net1 = Net(
            id=NetId("net_123"),
            name="net_123",
            connected_pin_ids=[PinId("XI1.Y")],
        )
        net2 = Net(
            id=NetId("net_456"),
            name="net_456",
            connected_pin_ids=[PinId("XI1.Y")],
        )

        assert net1 != net2


class TestNetHashability:
    """Test suite for Net as hashable object (for use in sets/dicts)."""

    def test_net_is_hashable(self) -> None:
        """Net should be usable as dictionary key."""
        net = Net(
            id=NetId("net_123"),
            name="net_123",
            connected_pin_ids=[PinId("XI1.Y")],
        )

        d: dict[Net, str] = {net: "test_value"}
        assert d[net] == "test_value"

    def test_equal_nets_have_same_hash(self) -> None:
        """Equal Nets should have the same hash."""
        net1 = Net(
            id=NetId("net_123"),
            name="net_123",
            connected_pin_ids=[PinId("XI1.Y")],
        )
        net2 = Net(
            id=NetId("net_123"),
            name="net_123",
            connected_pin_ids=[PinId("XI1.Y")],
        )

        assert hash(net1) == hash(net2)
