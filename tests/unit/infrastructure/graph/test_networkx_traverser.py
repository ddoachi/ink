"""Unit tests for NetworkXGraphTraverser - TDD RED phase.

These tests define the expected behavior of the NetworkXGraphTraverser class
before implementation. Following Test-Driven Development (TDD), all tests
should fail initially (RED phase) until the implementation is complete.

Test Coverage Goals:
- NetworkXGraphTraverser instantiation
- get_connected_cells(): cells connected to a net
- get_cell_pins(): pins of a cell
- get_pin_net(): net connected to a pin
- get_fanout_cells(): downstream cells with hop count and sequential boundary
- get_fanin_cells(): upstream cells with hop count and sequential boundary
- get_fanout_from_pin(): fanout from specific pin
- get_fanin_to_pin(): fanin to specific pin
- find_path(): shortest path between cells
- Edge cases: cycles, disconnected graphs, sequential boundaries, floating pins

Architecture:
    Layer: Infrastructure Layer
    Pattern: Adapter (adapts NetworkX graph to domain service interface)
    Implements: GraphTraverser protocol from domain layer
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ink.domain.model import Cell, Design, Net, Pin

if TYPE_CHECKING:
    from ink.infrastructure.graph import NetworkXGraphTraverser

from ink.domain.value_objects.identifiers import CellId, NetId, PinId
from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.graph import NetworkXGraphBuilder

# Fixtures - Test Design Factories


@pytest.fixture
def inverter_chain_design() -> Design:
    """Create a simple inverter chain: XI1 → XI2 → XI3.

    Structure:
        XI1 (INV_X1):
            A (INPUT) <- net_in
            Y (OUTPUT) -> net_1

        XI2 (INV_X1):
            A (INPUT) <- net_1
            Y (OUTPUT) -> net_2

        XI3 (INV_X1):
            A (INPUT) <- net_2
            Y (OUTPUT) -> net_out

    Signal flow: net_in -> XI1 -> net_1 -> XI2 -> net_2 -> XI3 -> net_out
    """
    design = Design(name="inverter_chain")

    # Create cells
    for i in range(1, 4):
        cell = Cell(
            id=CellId(f"XI{i}"),
            name=f"XI{i}",
            cell_type="INV_X1",
            pin_ids=[PinId(f"XI{i}.A"), PinId(f"XI{i}.Y")],
            is_sequential=False,
        )
        design.add_cell(cell)

    # Define nets
    nets_data = [
        ("net_in", [PinId("XI1.A")]),
        ("net_1", [PinId("XI1.Y"), PinId("XI2.A")]),
        ("net_2", [PinId("XI2.Y"), PinId("XI3.A")]),
        ("net_out", [PinId("XI3.Y")]),
    ]

    for net_name, pin_ids in nets_data:
        net = Net(id=NetId(net_name), name=net_name, connected_pin_ids=pin_ids)
        design.add_net(net)

    # Create pins with connections
    pins_data = [
        ("XI1.A", "A", PinDirection.INPUT, NetId("net_in")),
        ("XI1.Y", "Y", PinDirection.OUTPUT, NetId("net_1")),
        ("XI2.A", "A", PinDirection.INPUT, NetId("net_1")),
        ("XI2.Y", "Y", PinDirection.OUTPUT, NetId("net_2")),
        ("XI3.A", "A", PinDirection.INPUT, NetId("net_2")),
        ("XI3.Y", "Y", PinDirection.OUTPUT, NetId("net_out")),
    ]

    for pin_id, name, direction, net_id in pins_data:
        pin = Pin(id=PinId(pin_id), name=name, direction=direction, net_id=net_id)
        design.add_pin(pin)

    return design


@pytest.fixture
def fanout_design() -> Design:
    """Create a design with fanout (one output driving multiple inputs).

    Structure:
        XI1 (INV_X1):
            Y (OUTPUT) -> net_fanout

        XI2 (BUF_X1):
            A (INPUT) <- net_fanout

        XI3 (BUF_X1):
            A (INPUT) <- net_fanout

        XI4 (BUF_X1):
            A (INPUT) <- net_fanout

    Signal flow: XI1 -> net_fanout -> [XI2, XI3, XI4]
    """
    design = Design(name="fanout_design")

    # Driver cell
    driver = Cell(
        id=CellId("XI1"),
        name="XI1",
        cell_type="INV_X1",
        pin_ids=[PinId("XI1.A"), PinId("XI1.Y")],
        is_sequential=False,
    )
    design.add_cell(driver)

    # Receiver cells
    for i in range(2, 5):
        cell = Cell(
            id=CellId(f"XI{i}"),
            name=f"XI{i}",
            cell_type="BUF_X1",
            pin_ids=[PinId(f"XI{i}.A"), PinId(f"XI{i}.Y")],
            is_sequential=False,
        )
        design.add_cell(cell)

    # Net with fanout
    net = Net(
        id=NetId("net_fanout"),
        name="net_fanout",
        connected_pin_ids=[
            PinId("XI1.Y"),
            PinId("XI2.A"),
            PinId("XI3.A"),
            PinId("XI4.A"),
        ],
    )
    design.add_net(net)

    # Pins
    pin_driver_a = Pin(
        id=PinId("XI1.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=None,  # Floating input
    )
    pin_driver_y = Pin(
        id=PinId("XI1.Y"),
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_fanout"),
    )
    design.add_pin(pin_driver_a)
    design.add_pin(pin_driver_y)

    for i in range(2, 5):
        pin_a = Pin(
            id=PinId(f"XI{i}.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_fanout"),
        )
        pin_y = Pin(
            id=PinId(f"XI{i}.Y"),
            name="Y",
            direction=PinDirection.OUTPUT,
            net_id=None,  # Floating output
        )
        design.add_pin(pin_a)
        design.add_pin(pin_y)

    return design


@pytest.fixture
def sequential_boundary_design() -> Design:
    """Create a design with sequential element (FF) as boundary.

    Structure:
        XI1 (INV_X1) [combinational]:
            Y (OUTPUT) -> net_1

        XFF (DFF_X1) [sequential]:
            D (INPUT) <- net_1
            Q (OUTPUT) -> net_2

        XI2 (INV_X1) [combinational]:
            A (INPUT) <- net_2

    Signal flow: XI1 -> net_1 -> XFF -> net_2 -> XI2
    Sequential boundary at XFF should stop traversal when stop_at_sequential=True
    """
    design = Design(name="sequential_boundary")

    # Combinational before FF
    cell1 = Cell(
        id=CellId("XI1"),
        name="XI1",
        cell_type="INV_X1",
        pin_ids=[PinId("XI1.A"), PinId("XI1.Y")],
        is_sequential=False,
    )
    design.add_cell(cell1)

    # Sequential element (flip-flop)
    ff = Cell(
        id=CellId("XFF"),
        name="XFF",
        cell_type="DFF_X1",
        pin_ids=[PinId("XFF.D"), PinId("XFF.CLK"), PinId("XFF.Q")],
        is_sequential=True,
    )
    design.add_cell(ff)

    # Combinational after FF
    cell2 = Cell(
        id=CellId("XI2"),
        name="XI2",
        cell_type="INV_X1",
        pin_ids=[PinId("XI2.A"), PinId("XI2.Y")],
        is_sequential=False,
    )
    design.add_cell(cell2)

    # Nets
    nets_data = [
        ("net_1", [PinId("XI1.Y"), PinId("XFF.D")]),
        ("net_2", [PinId("XFF.Q"), PinId("XI2.A")]),
        ("net_clk", [PinId("XFF.CLK")]),
    ]
    for net_name, pin_ids in nets_data:
        net = Net(id=NetId(net_name), name=net_name, connected_pin_ids=pin_ids)
        design.add_net(net)

    # Pins
    pins_data = [
        ("XI1.A", "A", PinDirection.INPUT, None),
        ("XI1.Y", "Y", PinDirection.OUTPUT, NetId("net_1")),
        ("XFF.D", "D", PinDirection.INPUT, NetId("net_1")),
        ("XFF.CLK", "CLK", PinDirection.INPUT, NetId("net_clk")),
        ("XFF.Q", "Q", PinDirection.OUTPUT, NetId("net_2")),
        ("XI2.A", "A", PinDirection.INPUT, NetId("net_2")),
        ("XI2.Y", "Y", PinDirection.OUTPUT, None),
    ]
    for pin_id, name, direction, net_id in pins_data:
        pin = Pin(id=PinId(pin_id), name=name, direction=direction, net_id=net_id)
        design.add_pin(pin)

    return design


@pytest.fixture
def disconnected_design() -> Design:
    """Create a design with disconnected components.

    Structure:
        Component 1:
            XI1 (INV_X1) -> net_1 -> XI2 (INV_X1)

        Component 2 (isolated):
            XI_ISO (INV_X1) - not connected to Component 1
    """
    design = Design(name="disconnected_design")

    # Component 1: Connected cells
    for i in range(1, 3):
        cell = Cell(
            id=CellId(f"XI{i}"),
            name=f"XI{i}",
            cell_type="INV_X1",
            pin_ids=[PinId(f"XI{i}.A"), PinId(f"XI{i}.Y")],
            is_sequential=False,
        )
        design.add_cell(cell)

    # Component 2: Isolated cell
    iso = Cell(
        id=CellId("XI_ISO"),
        name="XI_ISO",
        cell_type="INV_X1",
        pin_ids=[PinId("XI_ISO.A"), PinId("XI_ISO.Y")],
        is_sequential=False,
    )
    design.add_cell(iso)

    # Nets (only connecting Component 1)
    net_1 = Net(
        id=NetId("net_1"),
        name="net_1",
        connected_pin_ids=[PinId("XI1.Y"), PinId("XI2.A")],
    )
    design.add_net(net_1)

    # Pins for Component 1
    pins_1 = [
        ("XI1.A", "A", PinDirection.INPUT, None),
        ("XI1.Y", "Y", PinDirection.OUTPUT, NetId("net_1")),
        ("XI2.A", "A", PinDirection.INPUT, NetId("net_1")),
        ("XI2.Y", "Y", PinDirection.OUTPUT, None),
    ]
    for pin_id, name, direction, net_id in pins_1:
        pin = Pin(id=PinId(pin_id), name=name, direction=direction, net_id=net_id)
        design.add_pin(pin)

    # Pins for Component 2 (isolated)
    for pin_id, name, direction in [
        ("XI_ISO.A", "A", PinDirection.INPUT),
        ("XI_ISO.Y", "Y", PinDirection.OUTPUT),
    ]:
        pin = Pin(id=PinId(pin_id), name=name, direction=direction, net_id=None)
        design.add_pin(pin)

    return design


@pytest.fixture
def cycle_design() -> Design:
    """Create a design with a cycle (feedback loop).

    Structure:
        XI1 -> net_1 -> XI2 -> net_2 -> XI3 -> net_feedback -> XI1

    This creates a combinational loop (should not hang traversal).
    """
    design = Design(name="cycle_design")

    # Cells in cycle
    for i in range(1, 4):
        cell = Cell(
            id=CellId(f"XI{i}"),
            name=f"XI{i}",
            cell_type="INV_X1",
            pin_ids=[PinId(f"XI{i}.A"), PinId(f"XI{i}.Y")],
            is_sequential=False,
        )
        design.add_cell(cell)

    # Nets forming cycle
    nets_data = [
        ("net_1", [PinId("XI1.Y"), PinId("XI2.A")]),
        ("net_2", [PinId("XI2.Y"), PinId("XI3.A")]),
        ("net_feedback", [PinId("XI3.Y"), PinId("XI1.A")]),  # Feedback
    ]
    for net_name, pin_ids in nets_data:
        net = Net(id=NetId(net_name), name=net_name, connected_pin_ids=pin_ids)
        design.add_net(net)

    # Pins
    pins_data = [
        ("XI1.A", "A", PinDirection.INPUT, NetId("net_feedback")),
        ("XI1.Y", "Y", PinDirection.OUTPUT, NetId("net_1")),
        ("XI2.A", "A", PinDirection.INPUT, NetId("net_1")),
        ("XI2.Y", "Y", PinDirection.OUTPUT, NetId("net_2")),
        ("XI3.A", "A", PinDirection.INPUT, NetId("net_2")),
        ("XI3.Y", "Y", PinDirection.OUTPUT, NetId("net_feedback")),
    ]
    for pin_id, name, direction, net_id in pins_data:
        pin = Pin(id=PinId(pin_id), name=name, direction=direction, net_id=net_id)
        design.add_pin(pin)

    return design


def build_traverser(design: Design) -> NetworkXGraphTraverser:
    """Helper to build graph and traverser from design."""
    from ink.infrastructure.graph import NetworkXGraphTraverser

    builder = NetworkXGraphBuilder()
    graph = builder.build_from_design(design)
    return NetworkXGraphTraverser(graph, design)




class TestNetworkXGraphTraverserInstantiation:
    """Tests for NetworkXGraphTraverser instantiation."""

    def test_can_import_traverser(self) -> None:
        """NetworkXGraphTraverser should be importable."""
        from ink.infrastructure.graph import NetworkXGraphTraverser

        assert NetworkXGraphTraverser is not None

    def test_traverser_instantiation(self, inverter_chain_design: Design) -> None:
        """Traverser should be instantiable with graph and design."""
        from ink.infrastructure.graph import NetworkXGraphTraverser

        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(inverter_chain_design)

        traverser = NetworkXGraphTraverser(graph, inverter_chain_design)

        assert traverser is not None

    def test_traverser_implements_protocol(
        self, inverter_chain_design: Design
    ) -> None:
        """NetworkXGraphTraverser should implement GraphTraverser protocol."""
        from ink.infrastructure.graph import NetworkXGraphTraverser

        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(inverter_chain_design)
        traverser = NetworkXGraphTraverser(graph, inverter_chain_design)

        # Check that traverser has all protocol methods
        assert hasattr(traverser, "get_connected_cells")
        assert hasattr(traverser, "get_cell_pins")
        assert hasattr(traverser, "get_pin_net")
        assert hasattr(traverser, "get_fanout_cells")
        assert hasattr(traverser, "get_fanin_cells")
        assert hasattr(traverser, "get_fanout_from_pin")
        assert hasattr(traverser, "get_fanin_to_pin")
        assert hasattr(traverser, "find_path")




class TestGetConnectedCells:
    """Tests for get_connected_cells method."""

    def test_returns_cells_connected_to_net(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return all cells connected to a net."""
        traverser = build_traverser(inverter_chain_design)

        # net_1 connects XI1.Y (output) and XI2.A (input)
        cells = traverser.get_connected_cells(NetId("net_1"))

        assert len(cells) == 2
        cell_names = {cell.name for cell in cells}
        assert cell_names == {"XI1", "XI2"}

    def test_returns_cells_from_fanout_net(self, fanout_design: Design) -> None:
        """Should return all cells on fanout net."""
        traverser = build_traverser(fanout_design)

        # net_fanout connects XI1.Y to XI2.A, XI3.A, XI4.A
        cells = traverser.get_connected_cells(NetId("net_fanout"))

        assert len(cells) == 4
        cell_names = {cell.name for cell in cells}
        assert cell_names == {"XI1", "XI2", "XI3", "XI4"}

    def test_returns_cell_objects(self, inverter_chain_design: Design) -> None:
        """Should return Cell domain entities, not raw node IDs."""
        traverser = build_traverser(inverter_chain_design)

        cells = traverser.get_connected_cells(NetId("net_1"))

        for cell in cells:
            assert isinstance(cell, Cell)

    def test_returns_empty_for_nonexistent_net(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return empty list for non-existent net."""
        traverser = build_traverser(inverter_chain_design)

        cells = traverser.get_connected_cells(NetId("nonexistent"))

        assert cells == []




class TestGetCellPins:
    """Tests for get_cell_pins method."""

    def test_returns_pins_of_cell(self, inverter_chain_design: Design) -> None:
        """Should return all pins of a cell."""
        traverser = build_traverser(inverter_chain_design)

        pins = traverser.get_cell_pins(CellId("XI1"))

        assert len(pins) == 2
        pin_names = {pin.name for pin in pins}
        assert pin_names == {"A", "Y"}

    def test_returns_pin_objects(self, inverter_chain_design: Design) -> None:
        """Should return Pin domain entities."""
        traverser = build_traverser(inverter_chain_design)

        pins = traverser.get_cell_pins(CellId("XI1"))

        for pin in pins:
            assert isinstance(pin, Pin)

    def test_returns_empty_for_nonexistent_cell(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return empty list for non-existent cell."""
        traverser = build_traverser(inverter_chain_design)

        pins = traverser.get_cell_pins(CellId("nonexistent"))

        assert pins == []

    def test_returns_all_pins_for_multipin_cell(
        self, sequential_boundary_design: Design
    ) -> None:
        """Should return all pins including multi-pin cells like FFs."""
        traverser = build_traverser(sequential_boundary_design)

        # FF has D, CLK, Q pins
        pins = traverser.get_cell_pins(CellId("XFF"))

        assert len(pins) == 3
        pin_names = {pin.name for pin in pins}
        assert pin_names == {"D", "CLK", "Q"}




class TestGetPinNet:
    """Tests for get_pin_net method."""

    def test_returns_net_for_connected_pin(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return the net connected to a pin."""
        traverser = build_traverser(inverter_chain_design)

        net = traverser.get_pin_net(PinId("XI1.Y"))

        assert net is not None
        assert isinstance(net, Net)
        assert net.name == "net_1"

    def test_returns_none_for_floating_pin(self, fanout_design: Design) -> None:
        """Should return None for floating (unconnected) pins."""
        traverser = build_traverser(fanout_design)

        # XI1.A is floating (not connected to any net)
        net = traverser.get_pin_net(PinId("XI1.A"))

        assert net is None

    def test_returns_none_for_nonexistent_pin(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return None for non-existent pin."""
        traverser = build_traverser(inverter_chain_design)

        net = traverser.get_pin_net(PinId("nonexistent.pin"))

        assert net is None




class TestGetFanoutCells:
    """Tests for get_fanout_cells method."""

    def test_single_hop_fanout(self, inverter_chain_design: Design) -> None:
        """Should return immediate fanout (1 hop)."""
        traverser = build_traverser(inverter_chain_design)

        # XI1 -> net_1 -> XI2 (1 hop)
        fanout = traverser.get_fanout_cells(CellId("XI1"), hops=1)

        assert len(fanout) == 1
        assert fanout[0].name == "XI2"

    def test_multi_hop_fanout(self, inverter_chain_design: Design) -> None:
        """Should return fanout within 2 hops."""
        traverser = build_traverser(inverter_chain_design)

        # XI1 -> XI2 (1 hop) -> XI3 (2 hops)
        fanout = traverser.get_fanout_cells(CellId("XI1"), hops=2)

        assert len(fanout) == 2
        cell_names = {cell.name for cell in fanout}
        assert cell_names == {"XI2", "XI3"}

    def test_excludes_starting_cell(self, inverter_chain_design: Design) -> None:
        """Should not include starting cell in results."""
        traverser = build_traverser(inverter_chain_design)

        fanout = traverser.get_fanout_cells(CellId("XI1"), hops=1)

        assert not any(cell.name == "XI1" for cell in fanout)

    def test_fanout_with_fanout_net(self, fanout_design: Design) -> None:
        """Should return all cells on fanout net."""
        traverser = build_traverser(fanout_design)

        # XI1 drives net_fanout -> XI2, XI3, XI4
        fanout = traverser.get_fanout_cells(CellId("XI1"), hops=1)

        assert len(fanout) == 3
        cell_names = {cell.name for cell in fanout}
        assert cell_names == {"XI2", "XI3", "XI4"}

    def test_stops_at_sequential_when_enabled(
        self, sequential_boundary_design: Design
    ) -> None:
        """Should stop at sequential cells when stop_at_sequential=True."""
        traverser = build_traverser(sequential_boundary_design)

        # XI1 -> XFF (sequential) -> XI2
        # With stop_at_sequential=True, should stop at XFF (include XFF but not XI2)
        fanout = traverser.get_fanout_cells(
            CellId("XI1"), hops=3, stop_at_sequential=True
        )

        # Should include XFF but NOT traverse through it to XI2
        cell_names = {cell.name for cell in fanout}
        assert "XFF" in cell_names
        assert "XI2" not in cell_names

    def test_traverses_through_sequential_when_disabled(
        self, sequential_boundary_design: Design
    ) -> None:
        """Should traverse through sequential cells when stop_at_sequential=False."""
        traverser = build_traverser(sequential_boundary_design)

        # XI1 -> XFF -> XI2
        fanout = traverser.get_fanout_cells(
            CellId("XI1"), hops=3, stop_at_sequential=False
        )

        # Should include both XFF and XI2
        cell_names = {cell.name for cell in fanout}
        assert "XFF" in cell_names
        assert "XI2" in cell_names

    def test_returns_empty_for_nonexistent_cell(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return empty list for non-existent cell."""
        traverser = build_traverser(inverter_chain_design)

        fanout = traverser.get_fanout_cells(CellId("nonexistent"), hops=1)

        assert fanout == []

    def test_handles_cycle_without_infinite_loop(self, cycle_design: Design) -> None:
        """Should handle cycles without infinite loop."""
        traverser = build_traverser(cycle_design)

        # Cycle: XI1 -> XI2 -> XI3 -> XI1
        # Should not hang, should return reachable cells
        fanout = traverser.get_fanout_cells(CellId("XI1"), hops=5)

        # Should find XI2 and XI3, but not revisit XI1
        cell_names = {cell.name for cell in fanout}
        assert "XI2" in cell_names
        assert "XI3" in cell_names
        # Starting cell should not be in results
        assert "XI1" not in cell_names




class TestGetFaninCells:
    """Tests for get_fanin_cells method."""

    def test_single_hop_fanin(self, inverter_chain_design: Design) -> None:
        """Should return immediate fanin (1 hop)."""
        traverser = build_traverser(inverter_chain_design)

        # XI3 <- XI2 (1 hop)
        fanin = traverser.get_fanin_cells(CellId("XI3"), hops=1)

        assert len(fanin) == 1
        assert fanin[0].name == "XI2"

    def test_multi_hop_fanin(self, inverter_chain_design: Design) -> None:
        """Should return fanin within 2 hops."""
        traverser = build_traverser(inverter_chain_design)

        # XI3 <- XI2 (1 hop) <- XI1 (2 hops)
        fanin = traverser.get_fanin_cells(CellId("XI3"), hops=2)

        assert len(fanin) == 2
        cell_names = {cell.name for cell in fanin}
        assert cell_names == {"XI1", "XI2"}

    def test_excludes_starting_cell(self, inverter_chain_design: Design) -> None:
        """Should not include starting cell in results."""
        traverser = build_traverser(inverter_chain_design)

        fanin = traverser.get_fanin_cells(CellId("XI3"), hops=1)

        assert not any(cell.name == "XI3" for cell in fanin)

    def test_stops_at_sequential_when_enabled(
        self, sequential_boundary_design: Design
    ) -> None:
        """Should stop at sequential cells when stop_at_sequential=True."""
        traverser = build_traverser(sequential_boundary_design)

        # Fanin path: XI1 drives XFF (sequential) which drives XI2
        fanin = traverser.get_fanin_cells(
            CellId("XI2"), hops=3, stop_at_sequential=True
        )

        # Should include XFF but NOT traverse through it to XI1
        cell_names = {cell.name for cell in fanin}
        assert "XFF" in cell_names
        assert "XI1" not in cell_names

    def test_traverses_through_sequential_when_disabled(
        self, sequential_boundary_design: Design
    ) -> None:
        """Should traverse through sequential cells when stop_at_sequential=False."""
        traverser = build_traverser(sequential_boundary_design)

        fanin = traverser.get_fanin_cells(
            CellId("XI2"), hops=3, stop_at_sequential=False
        )

        # Should include both XFF and XI1
        cell_names = {cell.name for cell in fanin}
        assert "XFF" in cell_names
        assert "XI1" in cell_names

    def test_returns_empty_for_nonexistent_cell(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return empty list for non-existent cell."""
        traverser = build_traverser(inverter_chain_design)

        fanin = traverser.get_fanin_cells(CellId("nonexistent"), hops=1)

        assert fanin == []




class TestGetFanoutFromPin:
    """Tests for get_fanout_from_pin method."""

    def test_fanout_from_output_pin(self, inverter_chain_design: Design) -> None:
        """Should return fanout from specific output pin."""
        traverser = build_traverser(inverter_chain_design)

        # XI1.Y -> net_1 -> XI2
        fanout = traverser.get_fanout_from_pin(PinId("XI1.Y"), hops=1)

        assert len(fanout) >= 1
        cell_names = {cell.name for cell in fanout}
        assert "XI2" in cell_names

    def test_returns_empty_for_nonexistent_pin(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return empty list for non-existent pin."""
        traverser = build_traverser(inverter_chain_design)

        fanout = traverser.get_fanout_from_pin(PinId("nonexistent.pin"), hops=1)

        assert fanout == []




class TestGetFaninToPin:
    """Tests for get_fanin_to_pin method."""

    def test_fanin_to_input_pin(self, inverter_chain_design: Design) -> None:
        """Should return fanin to specific input pin."""
        traverser = build_traverser(inverter_chain_design)

        # XI1 -> net_1 -> XI2.A
        fanin = traverser.get_fanin_to_pin(PinId("XI2.A"), hops=1)

        assert len(fanin) >= 1
        cell_names = {cell.name for cell in fanin}
        assert "XI1" in cell_names

    def test_returns_empty_for_nonexistent_pin(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return empty list for non-existent pin."""
        traverser = build_traverser(inverter_chain_design)

        fanin = traverser.get_fanin_to_pin(PinId("nonexistent.pin"), hops=1)

        assert fanin == []




class TestFindPath:
    """Tests for find_path method."""

    def test_finds_shortest_path(self, inverter_chain_design: Design) -> None:
        """Should return shortest path between cells."""
        traverser = build_traverser(inverter_chain_design)

        # Path: XI1 -> XI2 -> XI3
        path = traverser.find_path(CellId("XI1"), CellId("XI3"), max_hops=10)

        assert path is not None
        assert len(path) == 3
        path_names = [cell.name for cell in path]
        assert path_names == ["XI1", "XI2", "XI3"]

    def test_returns_none_when_no_path(self, disconnected_design: Design) -> None:
        """Should return None when no path exists."""
        traverser = build_traverser(disconnected_design)

        # XI1 and XI_ISO are disconnected
        path = traverser.find_path(CellId("XI1"), CellId("XI_ISO"), max_hops=10)

        assert path is None

    def test_returns_none_when_exceeds_max_hops(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return None when path exceeds max_hops."""
        traverser = build_traverser(inverter_chain_design)

        # Path XI1 -> XI3 requires 2 hops, but max_hops=1
        path = traverser.find_path(CellId("XI1"), CellId("XI3"), max_hops=1)

        assert path is None

    def test_path_includes_start_and_end(
        self, inverter_chain_design: Design
    ) -> None:
        """Path should include both start and end cells."""
        traverser = build_traverser(inverter_chain_design)

        path = traverser.find_path(CellId("XI1"), CellId("XI2"), max_hops=5)

        assert path is not None
        assert path[0].name == "XI1"
        assert path[-1].name == "XI2"

    def test_returns_path_of_cell_objects(
        self, inverter_chain_design: Design
    ) -> None:
        """Path should contain Cell domain entities."""
        traverser = build_traverser(inverter_chain_design)

        path = traverser.find_path(CellId("XI1"), CellId("XI2"), max_hops=5)

        assert path is not None
        for cell in path:
            assert isinstance(cell, Cell)

    def test_returns_none_for_nonexistent_cell(
        self, inverter_chain_design: Design
    ) -> None:
        """Should return None for non-existent cells."""
        traverser = build_traverser(inverter_chain_design)

        path = traverser.find_path(CellId("nonexistent"), CellId("XI1"), max_hops=5)

        assert path is None




class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_hops_returns_empty(self, inverter_chain_design: Design) -> None:
        """Zero hops should return empty list."""
        traverser = build_traverser(inverter_chain_design)

        fanout = traverser.get_fanout_cells(CellId("XI1"), hops=0)

        assert fanout == []

    def test_negative_hops_returns_empty(self, inverter_chain_design: Design) -> None:
        """Negative hops should return empty list."""
        traverser = build_traverser(inverter_chain_design)

        fanout = traverser.get_fanout_cells(CellId("XI1"), hops=-1)

        assert fanout == []

    def test_large_hop_count_terminates(self, inverter_chain_design: Design) -> None:
        """Large hop count should terminate (not infinite loop)."""
        traverser = build_traverser(inverter_chain_design)

        # Should not hang with large hop count
        fanout = traverser.get_fanout_cells(CellId("XI1"), hops=100)

        # Should return all reachable cells (2 cells in chain after XI1)
        assert len(fanout) == 2
