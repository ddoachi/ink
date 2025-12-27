"""Performance tests for NetworkXGraphBuilder.

These tests verify the graph builder meets the performance requirements:
- Build graph from 1000-cell design in < 100ms

Performance testing strategy:
1. Generate realistic synthetic designs of various sizes
2. Measure graph building time
3. Verify results meet acceptance criteria
"""

import time

import pytest

from ink.domain.model import Cell, Design, Net, Pin, Port
from ink.domain.value_objects.identifiers import CellId, NetId, PinId, PortId
from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.graph import NetworkXGraphBuilder

# =============================================================================
# Synthetic Design Generator
# =============================================================================


def generate_synthetic_design(
    num_cells: int,
    avg_pins_per_cell: int = 3,
    sequential_ratio: float = 0.1,
) -> Design:
    """Generate a synthetic design with the specified number of cells.

    Creates a realistic design with:
    - Combinational and sequential cells
    - Input/output ports
    - Fully connected nets

    Args:
        num_cells: Number of cells to create
        avg_pins_per_cell: Average pins per cell (2-5)
        sequential_ratio: Fraction of cells that are sequential (0.0-1.0)

    Returns:
        Design aggregate with the specified structure
    """
    design = Design(name=f"synthetic_{num_cells}")

    # Track all pins for net creation
    input_pins: list[str] = []
    output_pins: list[str] = []

    # Create cells with pins
    for i in range(num_cells):
        cell_id = CellId(f"X{i}")
        is_sequential = i < int(num_cells * sequential_ratio)
        cell_type = "DFF_X1" if is_sequential else "BUF_X1"

        # Create 2-3 pins per cell (1-2 inputs + 1 output)
        num_input_pins = 1 if not is_sequential else 2  # D, CLK for FF

        pin_ids = []

        # Input pins
        for p in range(num_input_pins):
            pin_name = ["D", "CLK"][p] if is_sequential else "A"
            pin_id = PinId(f"X{i}.{pin_name}")
            pin_ids.append(pin_id)

            # Connect to a net (will create net later)
            net_id = NetId(f"net_{i}_in{p}")
            pin = Pin(
                id=pin_id,
                name=pin_name,
                direction=PinDirection.INPUT,
                net_id=net_id,
            )
            design.add_pin(pin)
            input_pins.append(f"X{i}.{pin_name}")

        # Output pin
        out_pin_name = "Q" if is_sequential else "Y"
        out_pin_id = PinId(f"X{i}.{out_pin_name}")
        pin_ids.append(out_pin_id)

        out_net_id = NetId(f"net_{i}_out")
        out_pin = Pin(
            id=out_pin_id,
            name=out_pin_name,
            direction=PinDirection.OUTPUT,
            net_id=out_net_id,
        )
        design.add_pin(out_pin)
        output_pins.append(f"X{i}.{out_pin_name}")

        # Create cell
        cell = Cell(
            id=cell_id,
            name=f"X{i}",
            cell_type=cell_type,
            pin_ids=pin_ids,
            is_sequential=is_sequential,
        )
        design.add_cell(cell)

    # Create nets connecting cells
    # Input nets for each cell
    for i in range(num_cells):
        is_sequential = i < int(num_cells * sequential_ratio)
        num_input_pins = 1 if not is_sequential else 2

        for p in range(num_input_pins):
            pin_name = ["D", "CLK"][p] if is_sequential else "A"
            net = Net(
                id=NetId(f"net_{i}_in{p}"),
                name=f"net_{i}_in{p}",
                connected_pin_ids=[PinId(f"X{i}.{pin_name}")],
            )
            design.add_net(net)

    # Output nets
    for i in range(num_cells):
        is_sequential = i < int(num_cells * sequential_ratio)
        out_pin_name = "Q" if is_sequential else "Y"
        net = Net(
            id=NetId(f"net_{i}_out"),
            name=f"net_{i}_out",
            connected_pin_ids=[PinId(f"X{i}.{out_pin_name}")],
        )
        design.add_net(net)

    # Create input and output ports
    design.add_port(Port(
        id=PortId("IN"),
        name="IN",
        direction=PinDirection.INPUT,
        net_id=NetId("net_0_in0"),
    ))
    design.add_port(Port(
        id=PortId("OUT"),
        name="OUT",
        direction=PinDirection.OUTPUT,
        net_id=NetId(f"net_{num_cells - 1}_out"),
    ))

    return design


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformanceRequirements:
    """Tests for performance requirements from spec."""

    @pytest.mark.slow
    def test_1000_cell_design_under_100ms(self) -> None:
        """Build graph from 1000-cell design in < 100ms.

        This is the primary performance requirement from the spec:
        "Performance test: build graph from 1000-cell design in < 100ms"
        """
        # Generate 1000-cell design
        design = generate_synthetic_design(
            num_cells=1000,
            sequential_ratio=0.1,
        )

        builder = NetworkXGraphBuilder()

        # Warm-up run (JIT, caching, etc.)
        _ = builder.build_from_design(design)

        # Timed run
        start = time.perf_counter()
        builder.build_from_design(design)
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Verify graph was built correctly
        assert builder.cell_node_count() == 1000

        # Verify performance requirement: < 100ms
        assert elapsed_ms < 100, f"Build took {elapsed_ms:.2f}ms, expected < 100ms"

        # Print timing for diagnostics
        print(f"\n1000-cell graph build time: {elapsed_ms:.2f}ms")
        print(f"  Nodes: {builder.node_count()}")
        print(f"  Edges: {builder.edge_count()}")

    @pytest.mark.slow
    def test_500_cell_design_under_50ms(self) -> None:
        """Build graph from 500-cell design in < 50ms."""
        design = generate_synthetic_design(num_cells=500)

        builder = NetworkXGraphBuilder()

        # Warm-up
        _ = builder.build_from_design(design)

        # Timed run
        start = time.perf_counter()
        builder.build_from_design(design)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert builder.cell_node_count() == 500
        assert elapsed_ms < 50, f"Build took {elapsed_ms:.2f}ms, expected < 50ms"

    @pytest.mark.slow
    def test_100_cell_design_under_10ms(self) -> None:
        """Build graph from 100-cell design in < 10ms."""
        design = generate_synthetic_design(num_cells=100)

        builder = NetworkXGraphBuilder()

        # Warm-up
        _ = builder.build_from_design(design)

        # Timed run
        start = time.perf_counter()
        builder.build_from_design(design)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert builder.cell_node_count() == 100
        assert elapsed_ms < 10, f"Build took {elapsed_ms:.2f}ms, expected < 10ms"


class TestScalingBehavior:
    """Tests for understanding scaling behavior."""

    @pytest.mark.slow
    def test_linear_scaling(self) -> None:
        """Verify build time scales approximately linearly with cell count."""
        sizes = [100, 200, 500, 1000]
        times = []

        builder = NetworkXGraphBuilder()

        for size in sizes:
            design = generate_synthetic_design(num_cells=size)

            # Warm-up
            _ = builder.build_from_design(design)

            # Timed run (average of 3)
            elapsed_total = 0.0
            for _ in range(3):
                start = time.perf_counter()
                builder.build_from_design(design)
                elapsed_total += time.perf_counter() - start

            avg_time = (elapsed_total / 3) * 1000
            times.append(avg_time)
            print(f"\n{size} cells: {avg_time:.2f}ms")

        # Check roughly linear scaling (10x cells should be ~10x time)
        # Allow wide margin for system variance and CI environments
        ratio_100_to_1000 = times[3] / times[0]
        print(f"\nScaling ratio (1000/100): {ratio_100_to_1000:.1f}x (expected ~10x)")

        # Should be within 3-50x (linear would be 10x, but small inputs have
        # high variance due to fixed overhead dominating)
        assert 3 <= ratio_100_to_1000 <= 50, (
            f"Unexpected scaling: {ratio_100_to_1000:.1f}x"
        )
