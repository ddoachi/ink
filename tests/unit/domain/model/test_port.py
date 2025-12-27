"""Unit tests for Port domain entity.

This module tests the Port entity which represents a top-level I/O interface.
Port is a frozen dataclass with helper methods for querying direction.

The Port entity is a core domain concept for representing the external
interface of a design (inputs, outputs, and bidirectional pins).
"""

import pytest
from dataclasses import FrozenInstanceError

from ink.domain.model.port import Port
from ink.domain.value_objects.identifiers import PortId, NetId
from ink.domain.value_objects.pin_direction import PinDirection


class TestPortCreation:
    """Test suite for Port entity creation."""

    def test_port_creation_with_all_fields(self) -> None:
        """Should create Port with all required fields."""
        port = Port(
            id=PortId("CLK"),
            name="CLK",
            direction=PinDirection.INPUT,
            net_id=NetId("clk_internal"),
        )

        assert port.id == PortId("CLK")
        assert port.name == "CLK"
        assert port.direction == PinDirection.INPUT
        assert port.net_id == NetId("clk_internal")

    def test_port_creation_as_output(self) -> None:
        """Should create Port with OUTPUT direction."""
        port = Port(
            id=PortId("OUT"),
            name="OUT",
            direction=PinDirection.OUTPUT,
            net_id=NetId("output_net"),
        )

        assert port.direction == PinDirection.OUTPUT

    def test_port_creation_as_inout(self) -> None:
        """Should create Port with INOUT direction for bidirectional I/O."""
        port = Port(
            id=PortId("IO_PAD"),
            name="IO_PAD",
            direction=PinDirection.INOUT,
            net_id=NetId("pad_net"),
        )

        assert port.direction == PinDirection.INOUT

    def test_port_creation_with_none_net_id(self) -> None:
        """Should create Port with None net_id for unconnected ports."""
        port = Port(
            id=PortId("NC_PORT"),
            name="NC_PORT",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        assert port.net_id is None


class TestPortIsInputPort:
    """Test suite for Port.is_input_port() helper method."""

    def test_is_input_port_true_for_input(self) -> None:
        """is_input_port() should return True for INPUT direction."""
        port = Port(
            id=PortId("IN"),
            name="IN",
            direction=PinDirection.INPUT,
            net_id=NetId("in_net"),
        )

        assert port.is_input_port() is True

    def test_is_input_port_true_for_inout(self) -> None:
        """is_input_port() should return True for INOUT direction."""
        port = Port(
            id=PortId("IO"),
            name="IO",
            direction=PinDirection.INOUT,
            net_id=NetId("io_net"),
        )

        assert port.is_input_port() is True

    def test_is_input_port_false_for_output(self) -> None:
        """is_input_port() should return False for OUTPUT direction."""
        port = Port(
            id=PortId("OUT"),
            name="OUT",
            direction=PinDirection.OUTPUT,
            net_id=NetId("out_net"),
        )

        assert port.is_input_port() is False


class TestPortIsOutputPort:
    """Test suite for Port.is_output_port() helper method."""

    def test_is_output_port_true_for_output(self) -> None:
        """is_output_port() should return True for OUTPUT direction."""
        port = Port(
            id=PortId("OUT"),
            name="OUT",
            direction=PinDirection.OUTPUT,
            net_id=NetId("out_net"),
        )

        assert port.is_output_port() is True

    def test_is_output_port_true_for_inout(self) -> None:
        """is_output_port() should return True for INOUT direction."""
        port = Port(
            id=PortId("IO"),
            name="IO",
            direction=PinDirection.INOUT,
            net_id=NetId("io_net"),
        )

        assert port.is_output_port() is True

    def test_is_output_port_false_for_input(self) -> None:
        """is_output_port() should return False for INPUT direction."""
        port = Port(
            id=PortId("IN"),
            name="IN",
            direction=PinDirection.INPUT,
            net_id=NetId("in_net"),
        )

        assert port.is_output_port() is False


class TestPortImmutability:
    """Test suite for Port frozen dataclass immutability."""

    def test_port_id_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign id on frozen Port."""
        port = Port(
            id=PortId("IN"),
            name="IN",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        with pytest.raises(FrozenInstanceError):
            port.id = PortId("OUT")  # type: ignore[misc]

    def test_port_name_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign name on frozen Port."""
        port = Port(
            id=PortId("IN"),
            name="IN",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        with pytest.raises(FrozenInstanceError):
            port.name = "OUT"  # type: ignore[misc]

    def test_port_direction_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign direction on frozen Port."""
        port = Port(
            id=PortId("IN"),
            name="IN",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        with pytest.raises(FrozenInstanceError):
            port.direction = PinDirection.OUTPUT  # type: ignore[misc]

    def test_port_net_id_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign net_id on frozen Port."""
        port = Port(
            id=PortId("IN"),
            name="IN",
            direction=PinDirection.INPUT,
            net_id=None,
        )

        with pytest.raises(FrozenInstanceError):
            port.net_id = NetId("new_net")  # type: ignore[misc]


class TestPortEquality:
    """Test suite for Port equality comparisons."""

    def test_ports_with_same_values_are_equal(self) -> None:
        """Two Ports with identical values should be equal."""
        port1 = Port(
            id=PortId("CLK"),
            name="CLK",
            direction=PinDirection.INPUT,
            net_id=NetId("clk_net"),
        )
        port2 = Port(
            id=PortId("CLK"),
            name="CLK",
            direction=PinDirection.INPUT,
            net_id=NetId("clk_net"),
        )

        assert port1 == port2

    def test_ports_with_different_ids_are_not_equal(self) -> None:
        """Ports with different ids should not be equal."""
        port1 = Port(
            id=PortId("CLK"),
            name="CLK",
            direction=PinDirection.INPUT,
            net_id=NetId("clk_net"),
        )
        port2 = Port(
            id=PortId("RST"),
            name="RST",
            direction=PinDirection.INPUT,
            net_id=NetId("rst_net"),
        )

        assert port1 != port2


class TestPortHashability:
    """Test suite for Port as hashable object (for use in sets/dicts)."""

    def test_port_is_hashable(self) -> None:
        """Port should be usable as dictionary key."""
        port = Port(
            id=PortId("CLK"),
            name="CLK",
            direction=PinDirection.INPUT,
            net_id=NetId("clk_net"),
        )

        d: dict[Port, str] = {port: "clock_port"}
        assert d[port] == "clock_port"

    def test_equal_ports_have_same_hash(self) -> None:
        """Equal Ports should have the same hash."""
        port1 = Port(
            id=PortId("CLK"),
            name="CLK",
            direction=PinDirection.INPUT,
            net_id=NetId("clk_net"),
        )
        port2 = Port(
            id=PortId("CLK"),
            name="CLK",
            direction=PinDirection.INPUT,
            net_id=NetId("clk_net"),
        )

        assert hash(port1) == hash(port2)
