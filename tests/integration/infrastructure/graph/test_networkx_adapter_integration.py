"""Integration tests for NetworkXGraphBuilder with realistic design scenarios.

These tests verify the NetworkXGraphBuilder works correctly with larger,
more realistic Design aggregates representing actual circuit patterns.

Test Scenarios:
1. Small circuits (10-20 cells): Inverter chains, simple logic
2. Medium circuits (50-100 cells): Multi-stage pipelines
3. Sequential circuits: Flip-flops with combinational logic
4. Complex connectivity: High-fanout nets, buses

Performance baseline:
- Small designs (<100 cells): < 10ms
- Medium designs (~500 cells): < 50ms
- Large designs (~1000 cells): < 100ms (per spec requirement)
"""

import pytest

from ink.domain.model import Cell, Design, Net, Pin, Port
from ink.domain.value_objects.identifiers import CellId, NetId, PinId, PortId
from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.graph import NetworkXGraphBuilder

# =============================================================================
# Test Helpers
# =============================================================================


def create_inverter_cell(
    design: Design, instance_name: str, input_net: str, output_net: str
) -> None:
    """Helper to create an inverter cell with input A and output Y."""
    cell_id = CellId(instance_name)
    pin_a_id = PinId(f"{instance_name}.A")
    pin_y_id = PinId(f"{instance_name}.Y")

    cell = Cell(
        id=cell_id,
        name=instance_name,
        cell_type="INV_X1",
        pin_ids=[pin_a_id, pin_y_id],
        is_sequential=False,
    )
    design.add_cell(cell)

    pin_a = Pin(
        id=pin_a_id,
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId(input_net),
    )
    pin_y = Pin(
        id=pin_y_id,
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId(output_net),
    )
    design.add_pin(pin_a)
    design.add_pin(pin_y)


def create_flipflop_cell(
    design: Design,
    instance_name: str,
    d_net: str,
    clk_net: str,
    q_net: str,
) -> None:
    """Helper to create a D flip-flop cell."""
    cell_id = CellId(instance_name)
    pin_d_id = PinId(f"{instance_name}.D")
    pin_clk_id = PinId(f"{instance_name}.CLK")
    pin_q_id = PinId(f"{instance_name}.Q")

    cell = Cell(
        id=cell_id,
        name=instance_name,
        cell_type="DFF_X1",
        pin_ids=[pin_d_id, pin_clk_id, pin_q_id],
        is_sequential=True,
    )
    design.add_cell(cell)

    pin_d = Pin(
        id=pin_d_id,
        name="D",
        direction=PinDirection.INPUT,
        net_id=NetId(d_net),
    )
    pin_clk = Pin(
        id=pin_clk_id,
        name="CLK",
        direction=PinDirection.INPUT,
        net_id=NetId(clk_net),
    )
    pin_q = Pin(
        id=pin_q_id,
        name="Q",
        direction=PinDirection.OUTPUT,
        net_id=NetId(q_net),
    )
    design.add_pin(pin_d)
    design.add_pin(pin_clk)
    design.add_pin(pin_q)


def create_net_if_not_exists(design: Design, net_name: str, pin_ids: list[str]) -> None:
    """Helper to create a net if it doesn't already exist."""
    net_id = NetId(net_name)
    if design.get_net(net_id) is None:
        net = Net(
            id=net_id,
            name=net_name,
            connected_pin_ids=[PinId(pid) for pid in pin_ids],
        )
        design.add_net(net)


# =============================================================================
# Test: Inverter Chain (10 stages)
# =============================================================================


class TestInverterChainIntegration:
    """Integration tests with an inverter chain circuit."""

    @pytest.fixture
    def inverter_chain_design(self) -> Design:
        """Create a 10-stage inverter chain design.

        Circuit: IN -> XI1 -> XI2 -> ... -> XI10 -> OUT

        Entities:
        - 10 cells (inverters)
        - 20 pins (2 per cell)
        - 11 nets (input + 10 internal)
        - 2 ports (IN, OUT)
        """
        design = Design(name="inverter_chain_10")

        # Create input port
        port_in = Port(
            id=PortId("IN"),
            name="IN",
            direction=PinDirection.INPUT,
            net_id=NetId("net_0"),
        )
        design.add_port(port_in)

        # Create inverter chain
        for i in range(10):
            input_net = f"net_{i}"
            output_net = f"net_{i + 1}"
            create_inverter_cell(design, f"XI{i + 1}", input_net, output_net)

        # Create output port
        port_out = Port(
            id=PortId("OUT"),
            name="OUT",
            direction=PinDirection.OUTPUT,
            net_id=NetId("net_10"),
        )
        design.add_port(port_out)

        # Create nets
        for i in range(11):
            pin_ids = []
            if i == 0:
                pin_ids.append("XI1.A")
            else:
                pin_ids.append(f"XI{i}.Y")
            if i < 10:
                pin_ids.append(f"XI{i + 1}.A")

            net = Net(
                id=NetId(f"net_{i}"),
                name=f"net_{i}",
                connected_pin_ids=[PinId(pid) for pid in pin_ids],
            )
            design.add_net(net)

        return design

    def test_inverter_chain_node_count(self, inverter_chain_design: Design) -> None:
        """Verify correct node count for inverter chain."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(inverter_chain_design)

        # 10 cells + 20 pins + 11 nets + 2 ports = 43 nodes
        assert builder.node_count() == 43

    def test_inverter_chain_cell_count(self, inverter_chain_design: Design) -> None:
        """Verify correct cell count."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(inverter_chain_design)

        assert builder.cell_node_count() == 10

    def test_inverter_chain_net_count(self, inverter_chain_design: Design) -> None:
        """Verify correct net count."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(inverter_chain_design)

        assert builder.net_node_count() == 11

    def test_inverter_chain_edge_count(self, inverter_chain_design: Design) -> None:
        """Verify correct edge count."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(inverter_chain_design)

        # Cell→Pin: 10 cells * 2 pins = 20, Pin→Net: 20, Port→Net: 2, Total = 42
        assert builder.edge_count() == 42

    def test_inverter_chain_signal_path(self, inverter_chain_design: Design) -> None:
        """Verify signal path from input to output."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(inverter_chain_design)

        import networkx as nx

        # Check path exists from input port to output port
        # Signal path: IN → net_0 → XI1.A → XI1 → XI1.Y → net_1 → ...
        # Note: need to traverse containment edges in reverse for input pins
        port_in = PortId("IN")
        port_out = PortId("OUT")

        # Check undirected path exists (simplified connectivity check)
        undirected = graph.to_undirected()
        assert nx.has_path(undirected, port_in, port_out)


# =============================================================================
# Test: Pipeline with Flip-Flops
# =============================================================================


class TestPipelineIntegration:
    """Integration tests with a pipeline circuit containing flip-flops."""

    @pytest.fixture
    def pipeline_design(self) -> Design:
        """Create a 3-stage pipeline with combinational logic.

        Each stage: FF -> INV -> INV -> FF

        Circuit structure:
        IN -> FF1 -> INV1 -> INV2 -> FF2 -> INV3 -> INV4 -> FF3 -> OUT
        CLK -> [all FFs]
        """
        design = Design(name="pipeline_3stage")

        # Create ports
        design.add_port(Port(
            id=PortId("IN"),
            name="IN",
            direction=PinDirection.INPUT,
            net_id=NetId("net_in"),
        ))
        design.add_port(Port(
            id=PortId("OUT"),
            name="OUT",
            direction=PinDirection.OUTPUT,
            net_id=NetId("net_out"),
        ))
        design.add_port(Port(
            id=PortId("CLK"),
            name="CLK",
            direction=PinDirection.INPUT,
            net_id=NetId("clk"),
        ))

        # Stage 1: FF1 -> INV1 -> INV2
        create_flipflop_cell(design, "XFF1", "net_in", "clk", "net_ff1_q")
        create_inverter_cell(design, "XINV1", "net_ff1_q", "net_inv1_y")
        create_inverter_cell(design, "XINV2", "net_inv1_y", "net_stage1_out")

        # Stage 2: FF2 -> INV3 -> INV4
        create_flipflop_cell(design, "XFF2", "net_stage1_out", "clk", "net_ff2_q")
        create_inverter_cell(design, "XINV3", "net_ff2_q", "net_inv3_y")
        create_inverter_cell(design, "XINV4", "net_inv3_y", "net_stage2_out")

        # Stage 3: FF3
        create_flipflop_cell(design, "XFF3", "net_stage2_out", "clk", "net_out")

        # Create nets with connected pins
        nets_data = [
            ("net_in", ["XFF1.D"]),
            ("clk", ["XFF1.CLK", "XFF2.CLK", "XFF3.CLK"]),
            ("net_ff1_q", ["XFF1.Q", "XINV1.A"]),
            ("net_inv1_y", ["XINV1.Y", "XINV2.A"]),
            ("net_stage1_out", ["XINV2.Y", "XFF2.D"]),
            ("net_ff2_q", ["XFF2.Q", "XINV3.A"]),
            ("net_inv3_y", ["XINV3.Y", "XINV4.A"]),
            ("net_stage2_out", ["XINV4.Y", "XFF3.D"]),
            ("net_out", ["XFF3.Q"]),
        ]

        for net_name, pin_ids in nets_data:
            net = Net(
                id=NetId(net_name),
                name=net_name,
                connected_pin_ids=[PinId(pid) for pid in pin_ids],
            )
            design.add_net(net)

        return design

    def test_pipeline_has_sequential_cells(self, pipeline_design: Design) -> None:
        """Verify flip-flops are marked as sequential."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(pipeline_design)

        sequential_count = sum(
            1 for _, data in graph.nodes(data=True)
            if data.get("node_type") == "cell" and data.get("is_sequential")
        )

        assert sequential_count == 3  # 3 flip-flops

    def test_pipeline_clock_fanout(self, pipeline_design: Design) -> None:
        """Verify clock net drives all flip-flop CLK pins."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(pipeline_design)

        clk_net = NetId("clk")

        # Clock net should have edges to 3 CLK pins
        out_edges = list(graph.out_edges(clk_net))
        assert len(out_edges) == 3

        # All targets should be CLK pins
        for _, target in out_edges:
            assert str(target).endswith(".CLK")

    def test_pipeline_cell_count(self, pipeline_design: Design) -> None:
        """Verify correct cell count (3 FFs + 4 INVs = 7)."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(pipeline_design)

        assert builder.cell_node_count() == 7


# =============================================================================
# Test: High Fanout Design
# =============================================================================


class TestHighFanoutIntegration:
    """Integration tests with high-fanout nets."""

    @pytest.fixture
    def high_fanout_design(self) -> Design:
        """Create a design with a clock net driving 50 flip-flops."""
        design = Design(name="high_fanout_50")

        # Create clock port
        design.add_port(Port(
            id=PortId("CLK"),
            name="CLK",
            direction=PinDirection.INPUT,
            net_id=NetId("clk"),
        ))

        # Create 50 flip-flops
        clk_connected_pins = []
        for i in range(50):
            cell_id = CellId(f"XFF{i}")
            pin_d_id = PinId(f"XFF{i}.D")
            pin_clk_id = PinId(f"XFF{i}.CLK")
            pin_q_id = PinId(f"XFF{i}.Q")

            cell = Cell(
                id=cell_id,
                name=f"XFF{i}",
                cell_type="DFF_X1",
                pin_ids=[pin_d_id, pin_clk_id, pin_q_id],
                is_sequential=True,
            )
            design.add_cell(cell)

            # Add pins
            for pin_id, name, direction, net_id in [
                (pin_d_id, "D", PinDirection.INPUT, NetId(f"d_{i}")),
                (pin_clk_id, "CLK", PinDirection.INPUT, NetId("clk")),
                (pin_q_id, "Q", PinDirection.OUTPUT, NetId(f"q_{i}")),
            ]:
                pin = Pin(id=pin_id, name=name, direction=direction, net_id=net_id)
                design.add_pin(pin)

            clk_connected_pins.append(f"XFF{i}.CLK")

        # Create clock net with high fanout
        clk_net = Net(
            id=NetId("clk"),
            name="clk",
            connected_pin_ids=[PinId(pid) for pid in clk_connected_pins],
        )
        design.add_net(clk_net)

        # Create individual D and Q nets
        for i in range(50):
            d_net = Net(
                id=NetId(f"d_{i}"),
                name=f"d_{i}",
                connected_pin_ids=[PinId(f"XFF{i}.D")],
            )
            q_net = Net(
                id=NetId(f"q_{i}"),
                name=f"q_{i}",
                connected_pin_ids=[PinId(f"XFF{i}.Q")],
            )
            design.add_net(d_net)
            design.add_net(q_net)

        return design

    def test_high_fanout_clock_edges(self, high_fanout_design: Design) -> None:
        """Clock net should have 50 outgoing edges."""
        builder = NetworkXGraphBuilder()
        graph = builder.build_from_design(high_fanout_design)

        clk_net = NetId("clk")
        out_edges = list(graph.out_edges(clk_net))

        assert len(out_edges) == 50

    def test_high_fanout_node_count(self, high_fanout_design: Design) -> None:
        """Verify correct node count for 50 FF design."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(high_fanout_design)

        # 50 cells + 150 pins (3 per cell) + 101 nets (1 clk + 50 d + 50 q) + 1 port
        expected = 50 + 150 + 101 + 1
        assert builder.node_count() == expected


# =============================================================================
# Test: Medium Size Design (100 cells)
# =============================================================================


class TestMediumDesignIntegration:
    """Integration tests with medium-sized designs."""

    @pytest.fixture
    def medium_design(self) -> Design:
        """Create a design with 100 cells in a grid pattern."""
        design = Design(name="grid_100")

        # Create 100 inverters in a 10x10 grid pattern
        for row in range(10):
            for col in range(10):
                instance_name = f"XI_{row}_{col}"

                # Input comes from previous cell or input port
                input_net = f"row_{row}_in" if col == 0 else f"net_{row}_{col - 1}_out"

                # Output net
                output_net = f"net_{row}_{col}_out"

                create_inverter_cell(design, instance_name, input_net, output_net)

        # Create row input/output ports
        for row in range(10):
            design.add_port(Port(
                id=PortId(f"IN_{row}"),
                name=f"IN_{row}",
                direction=PinDirection.INPUT,
                net_id=NetId(f"row_{row}_in"),
            ))
            design.add_port(Port(
                id=PortId(f"OUT_{row}"),
                name=f"OUT_{row}",
                direction=PinDirection.OUTPUT,
                net_id=NetId(f"net_{row}_9_out"),
            ))

        # Create nets
        # Row input nets
        for row in range(10):
            net = Net(
                id=NetId(f"row_{row}_in"),
                name=f"row_{row}_in",
                connected_pin_ids=[PinId(f"XI_{row}_0.A")],
            )
            design.add_net(net)

        # Internal and output nets
        for row in range(10):
            for col in range(10):
                pin_ids = [f"XI_{row}_{col}.Y"]
                if col < 9:
                    pin_ids.append(f"XI_{row}_{col + 1}.A")

                net = Net(
                    id=NetId(f"net_{row}_{col}_out"),
                    name=f"net_{row}_{col}_out",
                    connected_pin_ids=[PinId(pid) for pid in pin_ids],
                )
                design.add_net(net)

        return design

    def test_medium_design_node_count(self, medium_design: Design) -> None:
        """Verify node count for 100-cell grid design."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(medium_design)

        # 100 cells + 200 pins + 110 nets (10 input + 100 internal) + 20 ports
        expected = 100 + 200 + 110 + 20
        assert builder.node_count() == expected

    def test_medium_design_cell_count(self, medium_design: Design) -> None:
        """Verify cell count."""
        builder = NetworkXGraphBuilder()
        builder.build_from_design(medium_design)

        assert builder.cell_node_count() == 100

    def test_medium_design_builds_quickly(self, medium_design: Design) -> None:
        """Graph building should complete in reasonable time (<100ms)."""
        import time

        builder = NetworkXGraphBuilder()

        start = time.perf_counter()
        builder.build_from_design(medium_design)
        elapsed = time.perf_counter() - start

        # Should complete in less than 100ms (spec says <100ms for 1000 cells)
        # For 100 cells, should be much faster
        assert elapsed < 0.1  # 100ms
