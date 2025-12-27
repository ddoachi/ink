"""Unit tests for Pin domain entity.

This module tests the Pin entity which represents a connection point on a cell.
Pin is a frozen dataclass with immutability and helper methods for querying
connection state.

The Pin entity is a core domain concept used in graph traversal to determine
connectivity between cells via nets.
"""

import pytest
from dataclasses import FrozenInstanceError

from ink.domain.model.pin import Pin
from ink.domain.value_objects.identifiers import PinId, NetId
from ink.domain.value_objects.pin_direction import PinDirection


class TestPinCreation:
    """Test suite for Pin entity creation."""

    def test_pin_creation_with_all_fields(self) -> None:
        """Should create Pin with all required and optional fields."""
        pin = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )

        assert pin.id == PinId("XI1.A")
        assert pin.name == "A"
        assert pin.direction == PinDirection.INPUT
        assert pin.net_id == NetId("net_123")

    def test_pin_creation_with_output_direction(self) -> None:
        """Should create Pin with OUTPUT direction."""
        pin = Pin(
            id=PinId("XI1.Y"),
            name="Y",
            direction=PinDirection.OUTPUT,
            net_id=NetId("net_out"),
        )

        assert pin.direction == PinDirection.OUTPUT

    def test_pin_creation_with_inout_direction(self) -> None:
        """Should create Pin with INOUT direction for bidirectional pins."""
        pin = Pin(
            id=PinId("XI1.IO"),
            name="IO",
            direction=PinDirection.INOUT,
            net_id=NetId("net_io"),
        )

        assert pin.direction == PinDirection.INOUT

    def test_pin_creation_with_none_net_id(self) -> None:
        """Should create Pin with None net_id for floating pins."""
        pin = Pin(
            id=PinId("XI1.NC"),
            name="NC",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        assert pin.net_id is None


class TestPinIsConnected:
    """Test suite for Pin.is_connected() helper method."""

    def test_is_connected_returns_true_when_net_id_present(self) -> None:
        """is_connected() should return True when net_id is not None."""
        pin = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )

        assert pin.is_connected() is True

    def test_is_connected_returns_false_when_net_id_none(self) -> None:
        """is_connected() should return False when net_id is None (floating pin)."""
        pin = Pin(
            id=PinId("XI1.NC"),
            name="NC",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        assert pin.is_connected() is False


class TestPinImmutability:
    """Test suite for Pin frozen dataclass immutability."""

    def test_pin_id_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign id on frozen Pin."""
        pin = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        with pytest.raises(FrozenInstanceError):
            pin.id = PinId("XI1.B")  # type: ignore[misc]

    def test_pin_name_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign name on frozen Pin."""
        pin = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        with pytest.raises(FrozenInstanceError):
            pin.name = "B"  # type: ignore[misc]

    def test_pin_direction_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign direction on frozen Pin."""
        pin = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        with pytest.raises(FrozenInstanceError):
            pin.direction = PinDirection.OUTPUT  # type: ignore[misc]

    def test_pin_net_id_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign net_id on frozen Pin."""
        pin = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        with pytest.raises(FrozenInstanceError):
            pin.net_id = NetId("new_net")  # type: ignore[misc]


class TestPinEquality:
    """Test suite for Pin equality comparisons."""

    def test_pins_with_same_values_are_equal(self) -> None:
        """Two Pins with identical values should be equal."""
        pin1 = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )
        pin2 = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )

        assert pin1 == pin2

    def test_pins_with_different_ids_are_not_equal(self) -> None:
        """Pins with different ids should not be equal."""
        pin1 = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )
        pin2 = Pin(
            id=PinId("XI2.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )

        assert pin1 != pin2


class TestPinHashability:
    """Test suite for Pin as hashable object (for use in sets/dicts)."""

    def test_pin_is_hashable(self) -> None:
        """Pin should be usable as dictionary key."""
        pin = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )

        d: dict[Pin, str] = {pin: "test_value"}
        assert d[pin] == "test_value"

    def test_equal_pins_have_same_hash(self) -> None:
        """Equal Pins should have the same hash."""
        pin1 = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )
        pin2 = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )

        assert hash(pin1) == hash(pin2)

    def test_pins_can_be_used_in_sets(self) -> None:
        """Pins should be usable in sets with proper deduplication."""
        pin1 = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )
        pin2 = Pin(
            id=PinId("XI1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_123"),
        )
        pin3 = Pin(
            id=PinId("XI1.B"),
            name="B",
            direction=PinDirection.OUTPUT,
            net_id=NetId("net_456"),
        )

        pin_set = {pin1, pin2, pin3}
        # pin1 and pin2 are equal, so set should have 2 elements
        assert len(pin_set) == 2
