"""Unit tests for identifier value objects.

This module tests the NewType-based identifier types used throughout the domain layer:
- CellId: Unique identifier for cell instances
- NetId: Unique identifier for nets (wires)
- PinId: Unique identifier for pins on cells
- PortId: Unique identifier for top-level ports

These are type aliases using NewType, providing compile-time type safety without
runtime overhead. Tests verify they behave as expected string wrappers.
"""

from ink.domain.value_objects.identifiers import CellId, NetId, PinId, PortId


class TestCellId:
    """Test suite for CellId identifier type."""

    def test_cellid_wraps_string(self) -> None:
        """CellId should wrap a string value."""
        cell_id = CellId("XI1")
        # NewType returns the same value at runtime
        assert cell_id == "XI1"

    def test_cellid_preserves_value(self) -> None:
        """CellId should preserve the exact string value."""
        cell_id = CellId("XI_CORE/U_ALU/XI_ADD")
        assert cell_id == "XI_CORE/U_ALU/XI_ADD"

    def test_cellid_can_be_empty(self) -> None:
        """CellId can technically be empty (validation is at aggregate level)."""
        cell_id = CellId("")
        assert cell_id == ""

    def test_cellid_is_hashable(self) -> None:
        """CellId should be usable as dictionary key."""
        cell_id = CellId("XI1")
        d: dict[CellId, str] = {cell_id: "test"}
        assert d[cell_id] == "test"

    def test_cellid_equality_with_same_value(self) -> None:
        """CellIds with same value should be equal."""
        id1 = CellId("XI1")
        id2 = CellId("XI1")
        assert id1 == id2


class TestNetId:
    """Test suite for NetId identifier type."""

    def test_netid_wraps_string(self) -> None:
        """NetId should wrap a string value."""
        net_id = NetId("net_123")
        assert net_id == "net_123"

    def test_netid_preserves_bus_notation(self) -> None:
        """NetId should preserve bus notation in the name."""
        net_id = NetId("data[7]")
        assert net_id == "data[7]"

    def test_netid_is_hashable(self) -> None:
        """NetId should be usable as dictionary key."""
        net_id = NetId("clk")
        d: dict[NetId, str] = {net_id: "clock"}
        assert d[net_id] == "clock"

    def test_netid_can_be_used_in_set(self) -> None:
        """NetId should be usable in sets."""
        ids = {NetId("net1"), NetId("net2"), NetId("net1")}
        # Set should deduplicate
        assert len(ids) == 2


class TestPinId:
    """Test suite for PinId identifier type."""

    def test_pinid_wraps_string(self) -> None:
        """PinId should wrap a string value."""
        pin_id = PinId("XI1.A")
        assert pin_id == "XI1.A"

    def test_pinid_with_hierarchical_name(self) -> None:
        """PinId should support hierarchical instance.pin format."""
        pin_id = PinId("XI_CORE/U_ALU/XI_ADD.Y")
        assert pin_id == "XI_CORE/U_ALU/XI_ADD.Y"

    def test_pinid_is_hashable(self) -> None:
        """PinId should be usable as dictionary key."""
        pin_id = PinId("XI1.CLK")
        d: dict[PinId, str] = {pin_id: "clock input"}
        assert d[pin_id] == "clock input"


class TestPortId:
    """Test suite for PortId identifier type."""

    def test_portid_wraps_string(self) -> None:
        """PortId should wrap a string value."""
        port_id = PortId("IN")
        assert port_id == "IN"

    def test_portid_with_bus_port(self) -> None:
        """PortId should support bus port names."""
        port_id = PortId("DATA[31]")
        assert port_id == "DATA[31]"

    def test_portid_is_hashable(self) -> None:
        """PortId should be usable as dictionary key."""
        port_id = PortId("CLK")
        d: dict[PortId, str] = {port_id: "clock port"}
        assert d[port_id] == "clock port"


class TestIdentifierTypeDistinction:
    """Test that different identifier types remain distinguishable to type checkers.

    Note: At runtime, NewType doesn't enforce type distinction. These tests
    document expected behavior but the real protection comes from mypy.
    """

    def test_ids_are_strings_at_runtime(self) -> None:
        """All ID types are strings at runtime (NewType behavior)."""
        cell_id = CellId("test")
        net_id = NetId("test")
        pin_id = PinId("test")
        port_id = PortId("test")

        # At runtime, they're all equal strings
        # Type safety is enforced at compile time by mypy
        assert cell_id == net_id == pin_id == port_id == "test"
