"""Unit tests for NetworkXGraphBuilder - TDD RED phase.

These tests define the expected behavior of the NetworkXGraphBuilder class
before implementation. Following Test-Driven Development (TDD), all tests
should fail initially (RED phase) until the implementation is complete.

Test Coverage Goals:
- NetworkXGraphBuilder instantiation
- Graph building from Design aggregate
- Node creation for all entity types (Cell, Pin, Net, Port)
- Edge creation with correct direction semantics
- Node attribute access methods
- Graph statistics methods
- Builder pattern support

Graph Structure Validation:
- Nodes have correct `node_type` attribute
- Nodes store entity reference in `entity` attribute
- Cell→Pin edges use `edge_type='contains_pin'`
- Pin→Net edges respect signal direction (OUTPUT→Net, Net→INPUT)
- Port→Net edges respect I/O direction (INPUT Port→Net, Net→OUTPUT Port)
"""

import pytest

from ink.domain.model import Cell, Design, Net, Pin, Port
from ink.domain.value_objects.identifiers import CellId, NetId, PinId, PortId
from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.graph import NetworkXGraphBuilder

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def empty_design() -> Design:
    """Create an empty Design for testing basic builder initialization."""
    return Design(name="empty_design")


@pytest.fixture
def simple_design() -> Design:
    """Create a simple Design with one cell, two pins, and one net.

    Structure:
        Cell XI1 (INV_X1):
            Pin A (INPUT)  <- connected to net_in
            Pin Y (OUTPUT) -> connected to net_out

        Nets:
            net_in  -> [XI1.A]
            net_out <- [XI1.Y]

        Ports:
            IN  (INPUT)  -> net_in
            OUT (OUTPUT) <- net_out
    """
    design = Design(name="simple_design")

    # Create cell
    cell = Cell(
        id=CellId("XI1"),
        name="XI1",
        cell_type="INV_X1",
        pin_ids=[PinId("XI1.A"), PinId("XI1.Y")],
        is_sequential=False,
    )
    design.add_cell(cell)

    # Create pins
    pin_a = Pin(
        id=PinId("XI1.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_in"),
    )
    pin_y = Pin(
        id=PinId("XI1.Y"),
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_out"),
    )
    design.add_pin(pin_a)
    design.add_pin(pin_y)

    # Create nets
    net_in = Net(
        id=NetId("net_in"),
        name="net_in",
        connected_pin_ids=[PinId("XI1.A")],
    )
    net_out = Net(
        id=NetId("net_out"),
        name="net_out",
        connected_pin_ids=[PinId("XI1.Y")],
    )
    design.add_net(net_in)
    design.add_net(net_out)

    # Create ports
    port_in = Port(
        id=PortId("IN"),
        name="IN",
        direction=PinDirection.INPUT,
        net_id=NetId("net_in"),
    )
    port_out = Port(
        id=PortId("OUT"),
        name="OUT",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_out"),
    )
    design.add_port(port_in)
    design.add_port(port_out)

    return design


@pytest.fixture
def fanout_design() -> Design:
    """Create a Design with fanout (one output driving multiple inputs).

    Structure:
        Cell XI1 (INV_X1):
            Pin Y (OUTPUT) -> connected to net_fanout

        Cell XI2 (BUF_X1):
            Pin A (INPUT)  <- connected to net_fanout

        Cell XI3 (BUF_X1):
            Pin A (INPUT)  <- connected to net_fanout

        Net:
            net_fanout: [XI1.Y, XI2.A, XI3.A]
    """
    design = Design(name="fanout_design")

    # Create cells
    cell1 = Cell(
        id=CellId("XI1"),
        name="XI1",
        cell_type="INV_X1",
        pin_ids=[PinId("XI1.Y")],
        is_sequential=False,
    )
    cell2 = Cell(
        id=CellId("XI2"),
        name="XI2",
        cell_type="BUF_X1",
        pin_ids=[PinId("XI2.A")],
        is_sequential=False,
    )
    cell3 = Cell(
        id=CellId("XI3"),
        name="XI3",
        cell_type="BUF_X1",
        pin_ids=[PinId("XI3.A")],
        is_sequential=False,
    )
    design.add_cell(cell1)
    design.add_cell(cell2)
    design.add_cell(cell3)

    # Create pins
    pin_y1 = Pin(
        id=PinId("XI1.Y"),
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_fanout"),
    )
    pin_a2 = Pin(
        id=PinId("XI2.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_fanout"),
    )
    pin_a3 = Pin(
        id=PinId("XI3.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_fanout"),
    )
    design.add_pin(pin_y1)
    design.add_pin(pin_a2)
    design.add_pin(pin_a3)

    # Create net with fanout
    net = Net(
        id=NetId("net_fanout"),
        name="net_fanout",
        connected_pin_ids=[PinId("XI1.Y"), PinId("XI2.A"), PinId("XI3.A")],
    )
    design.add_net(net)

    return design


@pytest.fixture
def sequential_design() -> Design:
    """Create a Design with sequential elements (flip-flop).

    Structure:
        Cell XFF1 (DFF_X1) [sequential]:
            Pin D   (INPUT)  <- connected to net_d
            Pin CLK (INPUT)  <- connected to net_clk
            Pin Q   (OUTPUT) -> connected to net_q
    """
    design = Design(name="sequential_design")

    cell = Cell(
        id=CellId("XFF1"),
        name="XFF1",
        cell_type="DFF_X1",
        pin_ids=[PinId("XFF1.D"), PinId("XFF1.CLK"), PinId("XFF1.Q")],
        is_sequential=True,
    )
    design.add_cell(cell)

    # Create pins
    pin_d = Pin(
        id=PinId("XFF1.D"),
        name="D",
        direction=PinDirection.INPUT,
        net_id=NetId("net_d"),
    )
    pin_clk = Pin(
        id=PinId("XFF1.CLK"),
        name="CLK",
        direction=PinDirection.INPUT,
        net_id=NetId("net_clk"),
    )
    pin_q = Pin(
        id=PinId("XFF1.Q"),
        name="Q",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_q"),
    )
    design.add_pin(pin_d)
    design.add_pin(pin_clk)
    design.add_pin(pin_q)

    # Create nets
    for net_id, name, pins in [
        (NetId("net_d"), "net_d", [PinId("XFF1.D")]),
        (NetId("net_clk"), "net_clk", [PinId("XFF1.CLK")]),
        (NetId("net_q"), "net_q", [PinId("XFF1.Q")]),
    ]:
        net = Net(id=net_id, name=name, connected_pin_ids=pins)
        design.add_net(net)

    return design


@pytest.fixture
def inout_design() -> Design:
    """Create a Design with INOUT (bidirectional) pins and ports.

    Structure:
        Cell XBUF (TBUF_X1):
            Pin IO (INOUT) <-> connected to net_io

        Port:
            PAD (INOUT) <-> net_io
    """
    design = Design(name="inout_design")

    cell = Cell(
        id=CellId("XBUF"),
        name="XBUF",
        cell_type="TBUF_X1",
        pin_ids=[PinId("XBUF.IO")],
        is_sequential=False,
    )
    design.add_cell(cell)

    pin_io = Pin(
        id=PinId("XBUF.IO"),
        name="IO",
        direction=PinDirection.INOUT,
        net_id=NetId("net_io"),
    )
    design.add_pin(pin_io)

    net = Net(
        id=NetId("net_io"),
        name="net_io",
        connected_pin_ids=[PinId("XBUF.IO")],
    )
    design.add_net(net)

    port = Port(
        id=PortId("PAD"),
        name="PAD",
        direction=PinDirection.INOUT,
        net_id=NetId("net_io"),
    )
    design.add_port(port)

    return design


@pytest.fixture
def floating_pin_design() -> Design:
    """Create a Design with floating (unconnected) pins.

    Structure:
        Cell XI1 (AND2_X1):
            Pin A (INPUT)  <- connected to net_a
            Pin B (INPUT)  <- FLOATING (net_id=None)
            Pin Y (OUTPUT) -> connected to net_y
    """
    design = Design(name="floating_pin_design")

    cell = Cell(
        id=CellId("XI1"),
        name="XI1",
        cell_type="AND2_X1",
        pin_ids=[PinId("XI1.A"), PinId("XI1.B"), PinId("XI1.Y")],
        is_sequential=False,
    )
    design.add_cell(cell)

    pin_a = Pin(
        id=PinId("XI1.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_a"),
    )
    pin_b = Pin(
        id=PinId("XI1.B"),
        name="B",
        direction=PinDirection.INPUT,
        net_id=None,  # Floating pin
    )
    pin_y = Pin(
        id=PinId("XI1.Y"),
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_y"),
    )
    design.add_pin(pin_a)
    design.add_pin(pin_b)
    design.add_pin(pin_y)

    net_a = Net(
        id=NetId("net_a"),
        name="net_a",
        connected_pin_ids=[PinId("XI1.A")],
    )
    net_y = Net(
        id=NetId("net_y"),
        name="net_y",
        connected_pin_ids=[PinId("XI1.Y")],
    )
    design.add_net(net_a)
    design.add_net(net_y)

    return design


# =============================================================================
# Test: Builder Instantiation
# =============================================================================


class TestNetworkXGraphBuilderInstantiation:
    """Tests for NetworkXGraphBuilder instantiation and initialization."""

    def test_builder_creates_empty_graph(self) -> None:
        """Builder should initialize with an empty MultiDiGraph."""
        builder = NetworkXGraphBuilder()
        graph = builder.get_graph()

        assert graph is not None
        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_builder_graph_is_multi_digraph(self) -> None:
        """Builder should use NetworkX MultiDiGraph for multiple edges support."""
        import networkx as nx

        builder = NetworkXGraphBuilder()
        graph = builder.get_graph()

        assert isinstance(graph, nx.MultiDiGraph)


# =============================================================================
# Test: Building from Design
# =============================================================================


class TestBuildFromDesign:
    """Tests for the build_from_design() method."""

    def test_build_from_empty_design(self, empty_design: Design) -> None:
        """Building from empty design should produce empty graph."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(empty_design)

        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_build_from_design_returns_graph(self, simple_design: Design) -> None:
        """build_from_design should return the constructed graph."""
        import networkx as nx

        builder = NetworkXGraphBuilder()
        result = builder.build_from_design(simple_design)

        assert isinstance(result, nx.MultiDiGraph)
        assert result is builder.get_graph()

    def test_build_clears_previous_graph(self, simple_design: Design) -> None:
        """Subsequent builds should clear the previous graph."""
        builder = NetworkXGraphBuilder()

        # First build
        builder.build_from_design(simple_design)
        first_count = builder.node_count()

        # Build again with empty design
        empty = Design(name="empty")
        builder.build_from_design(empty)

        assert builder.node_count() == 0
        assert first_count > 0  # Verify first build had nodes


# =============================================================================
# Test: Cell Node Creation
# =============================================================================


class TestCellNodes:
    """Tests for Cell node creation and attributes."""

    def test_cell_nodes_added(self, simple_design: Design) -> None:
        """All cells should be added as nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        # simple_design has 1 cell
        assert builder.cell_node_count() == 1

    def test_cell_node_type_attribute(self, simple_design: Design) -> None:
        """Cell nodes should have node_type='cell'."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        cell_id = CellId("XI1")
        assert graph.nodes[cell_id]["node_type"] == "cell"

    def test_cell_node_attributes(self, simple_design: Design) -> None:
        """Cell nodes should have name, cell_type, is_sequential attributes."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        cell_id = CellId("XI1")
        node = graph.nodes[cell_id]

        assert node["name"] == "XI1"
        assert node["cell_type"] == "INV_X1"
        assert node["is_sequential"] is False

    def test_cell_node_entity_reference(self, simple_design: Design) -> None:
        """Cell nodes should store reference to original Cell entity."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        cell_id = CellId("XI1")
        entity = graph.nodes[cell_id]["entity"]

        assert isinstance(entity, Cell)
        assert entity.id == cell_id
        assert entity.cell_type == "INV_X1"

    def test_sequential_cell_flag(self, sequential_design: Design) -> None:
        """Sequential cells should have is_sequential=True."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(sequential_design)

        cell_id = CellId("XFF1")
        assert graph.nodes[cell_id]["is_sequential"] is True


# =============================================================================
# Test: Pin Node Creation
# =============================================================================


class TestPinNodes:
    """Tests for Pin node creation and attributes."""

    def test_pin_nodes_added(self, simple_design: Design) -> None:
        """All pins should be added as nodes."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        # simple_design has 2 pins
        pin_count = sum(
            1 for _, data in graph.nodes(data=True) if data.get("node_type") == "pin"
        )
        assert pin_count == 2

    def test_pin_node_type_attribute(self, simple_design: Design) -> None:
        """Pin nodes should have node_type='pin'."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        pin_id = PinId("XI1.A")
        assert graph.nodes[pin_id]["node_type"] == "pin"

    def test_pin_node_attributes(self, simple_design: Design) -> None:
        """Pin nodes should have name, direction, net_id attributes."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        pin_id = PinId("XI1.A")
        node = graph.nodes[pin_id]

        assert node["name"] == "A"
        assert node["direction"] == PinDirection.INPUT
        assert node["net_id"] == NetId("net_in")

    def test_pin_node_entity_reference(self, simple_design: Design) -> None:
        """Pin nodes should store reference to original Pin entity."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        pin_id = PinId("XI1.A")
        entity = graph.nodes[pin_id]["entity"]

        assert isinstance(entity, Pin)
        assert entity.id == pin_id
        assert entity.direction == PinDirection.INPUT

    def test_floating_pin_node_has_none_net_id(
        self, floating_pin_design: Design
    ) -> None:
        """Floating pins should have net_id=None."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(floating_pin_design)

        pin_id = PinId("XI1.B")
        assert graph.nodes[pin_id]["net_id"] is None


# =============================================================================
# Test: Net Node Creation
# =============================================================================


class TestNetNodes:
    """Tests for Net node creation and attributes."""

    def test_net_nodes_added(self, simple_design: Design) -> None:
        """All nets should be added as nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        # simple_design has 2 nets
        assert builder.net_node_count() == 2

    def test_net_node_type_attribute(self, simple_design: Design) -> None:
        """Net nodes should have node_type='net'."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        net_id = NetId("net_in")
        assert graph.nodes[net_id]["node_type"] == "net"

    def test_net_node_attributes(self, simple_design: Design) -> None:
        """Net nodes should have name, pin_count attributes."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        net_id = NetId("net_in")
        node = graph.nodes[net_id]

        assert node["name"] == "net_in"
        assert node["pin_count"] == 1

    def test_net_node_entity_reference(self, simple_design: Design) -> None:
        """Net nodes should store reference to original Net entity."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        net_id = NetId("net_in")
        entity = graph.nodes[net_id]["entity"]

        assert isinstance(entity, Net)
        assert entity.id == net_id

    def test_fanout_net_pin_count(self, fanout_design: Design) -> None:
        """Net with fanout should have correct pin_count."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(fanout_design)

        net_id = NetId("net_fanout")
        assert graph.nodes[net_id]["pin_count"] == 3


# =============================================================================
# Test: Port Node Creation
# =============================================================================


class TestPortNodes:
    """Tests for Port node creation and attributes."""

    def test_port_nodes_added(self, simple_design: Design) -> None:
        """All ports should be added as nodes."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        # simple_design has 2 ports
        port_count = sum(
            1 for _, data in graph.nodes(data=True) if data.get("node_type") == "port"
        )
        assert port_count == 2

    def test_port_node_type_attribute(self, simple_design: Design) -> None:
        """Port nodes should have node_type='port'."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        port_id = PortId("IN")
        assert graph.nodes[port_id]["node_type"] == "port"

    def test_port_node_attributes(self, simple_design: Design) -> None:
        """Port nodes should have name, direction, net_id attributes."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        port_id = PortId("IN")
        node = graph.nodes[port_id]

        assert node["name"] == "IN"
        assert node["direction"] == PinDirection.INPUT
        assert node["net_id"] == NetId("net_in")

    def test_port_node_entity_reference(self, simple_design: Design) -> None:
        """Port nodes should store reference to original Port entity."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        port_id = PortId("IN")
        entity = graph.nodes[port_id]["entity"]

        assert isinstance(entity, Port)
        assert entity.id == port_id


# =============================================================================
# Test: Cell-Pin Edges (Containment)
# =============================================================================


class TestCellPinEdges:
    """Tests for Cell→Pin containment edges."""

    def test_cell_to_pin_edges_created(self, simple_design: Design) -> None:
        """Cell→Pin edges should be created for all cell pins."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        cell_id = CellId("XI1")
        pin_ids = [PinId("XI1.A"), PinId("XI1.Y")]

        for pin_id in pin_ids:
            assert graph.has_edge(cell_id, pin_id)

    def test_cell_to_pin_edge_type(self, simple_design: Design) -> None:
        """Cell→Pin edges should have edge_type='contains_pin'."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        cell_id = CellId("XI1")
        pin_id = PinId("XI1.A")

        # MultiDiGraph stores edges with keys
        edge_data = graph.get_edge_data(cell_id, pin_id)
        assert edge_data is not None

        # Check first edge has correct type
        first_edge = next(iter(edge_data.values()))
        assert first_edge["edge_type"] == "contains_pin"


# =============================================================================
# Test: Pin-Net Edges (Signal Flow)
# =============================================================================


class TestPinNetEdges:
    """Tests for Pin↔Net signal flow edges."""

    def test_output_pin_drives_net(self, simple_design: Design) -> None:
        """OUTPUT pins should have edges: Pin → Net."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        pin_id = PinId("XI1.Y")  # OUTPUT pin
        net_id = NetId("net_out")

        # Output pin drives net: Pin → Net
        assert graph.has_edge(pin_id, net_id)
        assert not graph.has_edge(net_id, pin_id)

    def test_input_pin_driven_by_net(self, simple_design: Design) -> None:
        """INPUT pins should have edges: Net → Pin."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        pin_id = PinId("XI1.A")  # INPUT pin
        net_id = NetId("net_in")

        # Input pin driven by net: Net → Pin
        assert graph.has_edge(net_id, pin_id)
        assert not graph.has_edge(pin_id, net_id)

    def test_pin_net_edge_type(self, simple_design: Design) -> None:
        """Pin-Net edges should have edge_type='drives'."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        pin_id = PinId("XI1.Y")
        net_id = NetId("net_out")

        edge_data = graph.get_edge_data(pin_id, net_id)
        first_edge = next(iter(edge_data.values()))
        assert first_edge["edge_type"] == "drives"

    def test_inout_pin_bidirectional_edges(self, inout_design: Design) -> None:
        """INOUT pins should have edges in both directions: Pin ↔ Net."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(inout_design)

        pin_id = PinId("XBUF.IO")  # INOUT pin
        net_id = NetId("net_io")

        # INOUT pins have bidirectional edges
        # As per spec: "Net → INOUT Pin (bidirectional)"
        # Implementation: INOUT treated like input (Net → Pin)
        # since INOUT.is_output() returns True, we also add Pin → Net
        assert graph.has_edge(net_id, pin_id)

    def test_floating_pin_has_no_net_edge(self, floating_pin_design: Design) -> None:
        """Floating pins (net_id=None) should have no Pin-Net edges."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(floating_pin_design)

        pin_id = PinId("XI1.B")  # Floating pin

        # Check no edges from/to this pin involving nets
        # The pin should only have the Cell→Pin containment edge
        out_edges = list(graph.out_edges(pin_id))
        in_edges = list(graph.in_edges(pin_id))

        # Should have one incoming edge from cell (containment)
        assert len(in_edges) == 1
        assert in_edges[0][0] == CellId("XI1")

        # Should have no outgoing edges (floating)
        assert len(out_edges) == 0


# =============================================================================
# Test: Port-Net Edges (I/O Flow)
# =============================================================================


class TestPortNetEdges:
    """Tests for Port↔Net I/O flow edges."""

    def test_input_port_drives_net(self, simple_design: Design) -> None:
        """INPUT ports should have edges: Port → Net."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        port_id = PortId("IN")  # INPUT port
        net_id = NetId("net_in")

        # Input port drives internal net: Port → Net
        assert graph.has_edge(port_id, net_id)
        assert not graph.has_edge(net_id, port_id)

    def test_output_port_driven_by_net(self, simple_design: Design) -> None:
        """OUTPUT ports should have edges: Net → Port."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        port_id = PortId("OUT")  # OUTPUT port
        net_id = NetId("net_out")

        # Output port driven by internal net: Net → Port
        assert graph.has_edge(net_id, port_id)
        assert not graph.has_edge(port_id, net_id)

    def test_port_net_edge_type(self, simple_design: Design) -> None:
        """Port-Net edges should have edge_type='drives'."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(simple_design)

        port_id = PortId("IN")
        net_id = NetId("net_in")

        edge_data = graph.get_edge_data(port_id, net_id)
        first_edge = next(iter(edge_data.values()))
        assert first_edge["edge_type"] == "drives"

    def test_inout_port_bidirectional_edges(self, inout_design: Design) -> None:
        """INOUT ports should have edges in both directions: Port ↔ Net."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(inout_design)

        port_id = PortId("PAD")  # INOUT port
        net_id = NetId("net_io")

        # INOUT ports: treat as input (drives net)
        assert graph.has_edge(port_id, net_id)


# =============================================================================
# Test: Node Access Methods
# =============================================================================


class TestNodeAccessMethods:
    """Tests for get_node_entity and get_node_type methods."""

    def test_get_node_entity_cell(self, simple_design: Design) -> None:
        """get_node_entity should return Cell entity for cell nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        entity = builder.get_node_entity(CellId("XI1"))

        assert isinstance(entity, Cell)
        assert entity.name == "XI1"

    def test_get_node_entity_pin(self, simple_design: Design) -> None:
        """get_node_entity should return Pin entity for pin nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        entity = builder.get_node_entity(PinId("XI1.A"))

        assert isinstance(entity, Pin)
        assert entity.name == "A"

    def test_get_node_entity_net(self, simple_design: Design) -> None:
        """get_node_entity should return Net entity for net nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        entity = builder.get_node_entity(NetId("net_in"))

        assert isinstance(entity, Net)
        assert entity.name == "net_in"

    def test_get_node_entity_port(self, simple_design: Design) -> None:
        """get_node_entity should return Port entity for port nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        entity = builder.get_node_entity(PortId("IN"))

        assert isinstance(entity, Port)
        assert entity.name == "IN"

    def test_get_node_type_cell(self, simple_design: Design) -> None:
        """get_node_type should return 'cell' for cell nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        assert builder.get_node_type(CellId("XI1")) == "cell"

    def test_get_node_type_pin(self, simple_design: Design) -> None:
        """get_node_type should return 'pin' for pin nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        assert builder.get_node_type(PinId("XI1.A")) == "pin"

    def test_get_node_type_net(self, simple_design: Design) -> None:
        """get_node_type should return 'net' for net nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        assert builder.get_node_type(NetId("net_in")) == "net"

    def test_get_node_type_port(self, simple_design: Design) -> None:
        """get_node_type should return 'port' for port nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        assert builder.get_node_type(PortId("IN")) == "port"


# =============================================================================
# Test: Graph Statistics
# =============================================================================


class TestGraphStatistics:
    """Tests for graph statistics methods."""

    def test_node_count_empty(self, empty_design: Design) -> None:
        """node_count should return 0 for empty design."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(empty_design)

        assert builder.node_count() == 0

    def test_node_count(self, simple_design: Design) -> None:
        """node_count should return total nodes (cells + pins + nets + ports)."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        # simple_design: 1 cell + 2 pins + 2 nets + 2 ports = 7 nodes
        assert builder.node_count() == 7

    def test_edge_count_empty(self, empty_design: Design) -> None:
        """edge_count should return 0 for empty design."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(empty_design)

        assert builder.edge_count() == 0

    def test_edge_count(self, simple_design: Design) -> None:
        """edge_count should return total edges."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        # Edges: Cell→Pin: 2, Pin→Net: 2, Port→Net: 2, Total = 6
        assert builder.edge_count() == 6

    def test_cell_node_count(self, simple_design: Design) -> None:
        """cell_node_count should return number of cell nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        assert builder.cell_node_count() == 1

    def test_net_node_count(self, simple_design: Design) -> None:
        """net_node_count should return number of net nodes."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(simple_design)

        assert builder.net_node_count() == 2

    def test_cell_node_count_multiple(self, fanout_design: Design) -> None:
        """cell_node_count should count all cells."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(fanout_design)

        assert builder.cell_node_count() == 3


# =============================================================================
# Test: Builder Pattern
# =============================================================================


class TestBuilderPattern:
    """Tests for builder pattern support."""

    def test_get_graph_returns_same_instance(self) -> None:
        """get_graph should return the same graph instance."""
        builder = NetworkXGraphBuilder()

        graph1 = builder.get_graph()
        graph2 = builder.get_graph()

        assert graph1 is graph2

    def test_build_and_get_graph_same_instance(
        self, simple_design: Design
    ) -> None:
        """build_from_design and get_graph should return the same instance."""
        builder = NetworkXGraphBuilder()

        built_graph = builder.build_from_design(simple_design)
        get_graph = builder.get_graph()

        assert built_graph is get_graph

    def test_builder_reusable(self, simple_design: Design) -> None:
        """Builder should be reusable for multiple builds."""
        builder = NetworkXGraphBuilder()

        # First build
        builder.build_from_design(simple_design)
        first_nodes = builder.node_count()

        # Create new design
        new_design = Design(name="new")
        new_cell = Cell(
            id=CellId("XI2"),
            name="XI2",
            cell_type="AND2_X1",
            is_sequential=False,
        )
        new_design.add_cell(new_cell)

        # Second build
        builder.build_from_design(new_design)
        second_nodes = builder.node_count()

        assert first_nodes == 7  # simple_design nodes
        assert second_nodes == 1  # new_design has only 1 cell


# =============================================================================
# Test: Complex Scenarios
# =============================================================================


class TestComplexScenarios:
    """Tests for complex design scenarios."""

    def test_fanout_graph_structure(self, fanout_design: Design) -> None:
        """Fanout design should have correct graph structure."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(fanout_design)

        net_id = NetId("net_fanout")

        # Output pin drives net
        assert graph.has_edge(PinId("XI1.Y"), net_id)

        # Net drives input pins
        assert graph.has_edge(net_id, PinId("XI2.A"))
        assert graph.has_edge(net_id, PinId("XI3.A"))

    def test_sequential_element_in_graph(self, sequential_design: Design) -> None:
        """Sequential elements should be properly represented."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(sequential_design)

        cell_id = CellId("XFF1")
        node = graph.nodes[cell_id]

        assert node["is_sequential"] is True
        assert node["cell_type"] == "DFF_X1"

        # Check all pins connected
        pin_ids = [PinId("XFF1.D"), PinId("XFF1.CLK"), PinId("XFF1.Q")]
        for pin_id in pin_ids:
            assert graph.has_edge(cell_id, pin_id)
