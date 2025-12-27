"""Unit tests for SymbolLayoutCalculator.

Tests verify the SymbolLayoutCalculator implementation meets all requirements
from spec E02-F01-T03:
- Calculate pin positions on cell edges based on direction
- Evenly distribute multiple pins along each edge
- Handle edge cases (1 pin, many pins, unequal input/output counts)
- Provide position data for both pin graphics and net routing
- Support configurable cell dimensions and spacing

TDD Approach:
- RED phase: These tests define expected behavior before implementation
- GREEN phase: Implement SymbolLayoutCalculator to pass all tests
- REFACTOR phase: Clean up and optimize implementation

Architecture Notes:
- SymbolLayoutCalculator is a presentation layer utility
- It works with Cell domain entities and Pin domain entities
- Uses PinDirection value object to determine edge placement
- Returns PinLayout value objects with position data

See Also:
- Spec E02-F01-T03 for detailed requirements
- src/ink/domain/model/cell.py for Cell domain entity
- src/ink/domain/model/pin.py for Pin domain entity
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF, QRectF

from ink.domain.model.cell import Cell
from ink.domain.model.design import Design
from ink.domain.model.pin import Pin
from ink.domain.value_objects.identifiers import CellId, NetId, PinId
from ink.domain.value_objects.pin_direction import PinDirection
from ink.presentation.canvas.symbol_layout_calculator import (
    PinLayout,
    SymbolLayoutCalculator,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def design() -> Design:
    """Create a Design aggregate for managing cells and pins.

    Returns:
        Design: Empty design ready for entities.
    """
    return Design(name="test_design")


@pytest.fixture
def simple_cell(design: Design) -> Cell:
    """Create a simple cell with 2 inputs and 1 output.

    Returns:
        Cell: AND2 gate with A, B inputs and Y output.
    """
    # Create pins
    pin_a = Pin(
        id=PinId("U1.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_a"),
    )
    pin_b = Pin(
        id=PinId("U1.B"),
        name="B",
        direction=PinDirection.INPUT,
        net_id=NetId("net_b"),
    )
    pin_y = Pin(
        id=PinId("U1.Y"),
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_y"),
    )

    # Add pins to design
    design.add_pin(pin_a)
    design.add_pin(pin_b)
    design.add_pin(pin_y)

    # Create cell
    cell = Cell(
        id=CellId("U1"),
        name="U1",
        cell_type="AND2_X1",
        pin_ids=[PinId("U1.A"), PinId("U1.B"), PinId("U1.Y")],
        is_sequential=False,
    )
    design.add_cell(cell)

    return cell


@pytest.fixture
def single_io_cell(design: Design) -> Cell:
    """Create a cell with 1 input and 1 output.

    Returns:
        Cell: Inverter with A input and Y output.
    """
    # Create pins
    pin_a = Pin(
        id=PinId("XI1.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_a"),
    )
    pin_y = Pin(
        id=PinId("XI1.Y"),
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_y"),
    )

    design.add_pin(pin_a)
    design.add_pin(pin_y)

    cell = Cell(
        id=CellId("XI1"),
        name="XI1",
        cell_type="INV_X1",
        pin_ids=[PinId("XI1.A"), PinId("XI1.Y")],
        is_sequential=False,
    )
    design.add_cell(cell)

    return cell


@pytest.fixture
def many_pins_cell(design: Design) -> Cell:
    """Create a cell with many inputs (8) and outputs (2).

    Returns:
        Cell: Large mux-like cell with many pins.
    """
    pin_ids = []

    # Create 8 input pins
    for i in range(8):
        pin = Pin(
            id=PinId(f"UMUX.D{i}"),
            name=f"D{i}",
            direction=PinDirection.INPUT,
            net_id=NetId(f"net_d{i}"),
        )
        design.add_pin(pin)
        pin_ids.append(PinId(f"UMUX.D{i}"))

    # Create 2 output pins
    for i in range(2):
        pin = Pin(
            id=PinId(f"UMUX.Y{i}"),
            name=f"Y{i}",
            direction=PinDirection.OUTPUT,
            net_id=NetId(f"net_y{i}"),
        )
        design.add_pin(pin)
        pin_ids.append(PinId(f"UMUX.Y{i}"))

    cell = Cell(
        id=CellId("UMUX"),
        name="UMUX",
        cell_type="MUX8_X1",
        pin_ids=pin_ids,
        is_sequential=False,
    )
    design.add_cell(cell)

    return cell


@pytest.fixture
def unequal_io_cell(design: Design) -> Cell:
    """Create a cell with unequal input/output counts (5 inputs, 1 output).

    Returns:
        Cell: NAND5 gate with 5 inputs and 1 output.
    """
    pin_ids = []

    # Create 5 input pins
    for i in range(5):
        pin = Pin(
            id=PinId(f"UNAND.A{i}"),
            name=f"A{i}",
            direction=PinDirection.INPUT,
            net_id=NetId(f"net_a{i}"),
        )
        design.add_pin(pin)
        pin_ids.append(PinId(f"UNAND.A{i}"))

    # Create 1 output pin
    pin_y = Pin(
        id=PinId("UNAND.Y"),
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_y"),
    )
    design.add_pin(pin_y)
    pin_ids.append(PinId("UNAND.Y"))

    cell = Cell(
        id=CellId("UNAND"),
        name="UNAND",
        cell_type="NAND5_X1",
        pin_ids=pin_ids,
        is_sequential=False,
    )
    design.add_cell(cell)

    return cell


@pytest.fixture
def inout_cell(design: Design) -> Cell:
    """Create a cell with an INOUT pin.

    Returns:
        Cell: Bidirectional buffer with IO pin.
    """
    pin_a = Pin(
        id=PinId("UBUF.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_a"),
    )
    pin_io = Pin(
        id=PinId("UBUF.IO"),
        name="IO",
        direction=PinDirection.INOUT,
        net_id=NetId("net_io"),
    )
    pin_en = Pin(
        id=PinId("UBUF.EN"),
        name="EN",
        direction=PinDirection.INPUT,
        net_id=NetId("net_en"),
    )

    design.add_pin(pin_a)
    design.add_pin(pin_io)
    design.add_pin(pin_en)

    cell = Cell(
        id=CellId("UBUF"),
        name="UBUF",
        cell_type="BIDIR_X1",
        pin_ids=[PinId("UBUF.A"), PinId("UBUF.IO"), PinId("UBUF.EN")],
        is_sequential=False,
    )
    design.add_cell(cell)

    return cell


# =============================================================================
# PinLayout Value Object Tests
# =============================================================================


class TestPinLayout:
    """Tests for PinLayout value object."""

    def test_pin_layout_is_frozen_dataclass(self) -> None:
        """Test that PinLayout is immutable (frozen)."""
        layout = PinLayout(
            pin_id="U1.A",
            position=QPointF(0.0, 25.0),
            connection_point=QPointF(100.0, 225.0),
            side="left",
        )

        # Should not be able to modify attributes
        with pytest.raises(AttributeError):
            layout.pin_id = "U1.B"  # type: ignore[misc]

    def test_pin_layout_stores_all_fields(self) -> None:
        """Test that PinLayout stores all required fields."""
        layout = PinLayout(
            pin_id="U1.A",
            position=QPointF(0.0, 25.0),
            connection_point=QPointF(100.0, 225.0),
            side="left",
        )

        assert layout.pin_id == "U1.A"
        assert layout.position == QPointF(0.0, 25.0)
        assert layout.connection_point == QPointF(100.0, 225.0)
        assert layout.side == "left"

    def test_pin_layout_position_is_relative_to_cell(self) -> None:
        """Test that position is relative to cell origin."""
        layout = PinLayout(
            pin_id="U1.A",
            position=QPointF(0.0, 25.0),  # Relative to cell (0,0)
            connection_point=QPointF(100.0, 225.0),  # Scene coords
            side="left",
        )

        # Position is relative (small values)
        assert 0 <= layout.position.x() <= 120
        assert 0 <= layout.position.y() <= 80

    def test_pin_layout_valid_sides(self) -> None:
        """Test that side field accepts valid values."""
        # All four sides should be valid
        for side in ["left", "right", "top", "bottom"]:
            layout = PinLayout(
                pin_id="U1.A",
                position=QPointF(0.0, 25.0),
                connection_point=QPointF(0.0, 25.0),
                side=side,
            )
            assert layout.side == side


# =============================================================================
# SymbolLayoutCalculator Creation Tests
# =============================================================================


class TestSymbolLayoutCalculatorCreation:
    """Tests for SymbolLayoutCalculator instantiation."""

    def test_calculator_can_be_created_with_defaults(self) -> None:
        """Test that calculator can be instantiated with default dimensions."""
        calculator = SymbolLayoutCalculator()

        assert calculator is not None

    def test_calculator_uses_default_cell_width(self) -> None:
        """Test that default cell width is 120.0."""
        assert SymbolLayoutCalculator.DEFAULT_CELL_WIDTH == 120.0

    def test_calculator_uses_default_cell_height(self) -> None:
        """Test that default cell height is 80.0."""
        assert SymbolLayoutCalculator.DEFAULT_CELL_HEIGHT == 80.0

    def test_calculator_uses_min_pin_spacing(self) -> None:
        """Test that minimum pin spacing is 15.0."""
        assert SymbolLayoutCalculator.MIN_PIN_SPACING == 15.0

    def test_calculator_uses_pin_margin(self) -> None:
        """Test that pin margin is 10.0."""
        assert SymbolLayoutCalculator.PIN_MARGIN == 10.0

    def test_calculator_accepts_custom_dimensions(self) -> None:
        """Test that calculator accepts custom cell dimensions."""
        calculator = SymbolLayoutCalculator(
            cell_width=150.0,
            cell_height=100.0,
        )

        # Should store custom dimensions
        assert calculator._cell_width == 150.0
        assert calculator._cell_height == 100.0


# =============================================================================
# Calculate Pin Layouts Tests
# =============================================================================


class TestCalculatePinLayouts:
    """Tests for calculate_pin_layouts method."""

    def test_calculate_returns_dict(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that calculate_pin_layouts returns a dictionary."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        assert isinstance(layouts, dict)

    def test_calculate_returns_layout_for_each_pin(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that result contains a PinLayout for each pin."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # Should have 3 pins: A, B (inputs), Y (output)
        assert len(layouts) == 3
        assert "U1.A" in layouts
        assert "U1.B" in layouts
        assert "U1.Y" in layouts

    def test_calculate_returns_pin_layout_objects(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that values are PinLayout objects."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        for pin_id, layout in layouts.items():
            assert isinstance(layout, PinLayout)
            assert layout.pin_id == pin_id


# =============================================================================
# Pin Direction Edge Placement Tests
# =============================================================================


class TestPinDirectionPlacement:
    """Tests for pin placement based on direction."""

    def test_input_pins_placed_on_left_edge(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that INPUT pins are positioned on the left edge."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # Input pins A and B should be on left edge
        assert layouts["U1.A"].side == "left"
        assert layouts["U1.B"].side == "left"

    def test_output_pins_placed_on_right_edge(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that OUTPUT pins are positioned on the right edge."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # Output pin Y should be on right edge
        assert layouts["U1.Y"].side == "right"

    def test_inout_pins_placed_on_right_edge_by_default(
        self, design: Design, inout_cell: Cell
    ) -> None:
        """Test that INOUT pins are positioned on the right edge by default."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(inout_cell, design)

        # INOUT pin should be on right edge
        assert layouts["UBUF.IO"].side == "right"

    def test_left_edge_pins_have_x_at_zero(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that left edge pins have x=0 position."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # Left edge pins should have x=0
        assert layouts["U1.A"].position.x() == 0.0
        assert layouts["U1.B"].position.x() == 0.0

    def test_right_edge_pins_have_x_at_cell_width(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that right edge pins have x=cell_width position."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # Right edge pins should have x=cell_width (120.0)
        assert layouts["U1.Y"].position.x() == 120.0


# =============================================================================
# Pin Distribution Tests
# =============================================================================


class TestPinDistribution:
    """Tests for even pin distribution along edges."""

    def test_single_input_centered_vertically(
        self, design: Design, single_io_cell: Cell
    ) -> None:
        """Test that a single input pin is centered on the left edge."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(single_io_cell, design)

        # Single pin should be at vertical center: height/2 = 40.0
        assert layouts["XI1.A"].position.y() == 40.0

    def test_single_output_centered_vertically(
        self, design: Design, single_io_cell: Cell
    ) -> None:
        """Test that a single output pin is centered on the right edge."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(single_io_cell, design)

        # Single pin should be at vertical center: height/2 = 40.0
        assert layouts["XI1.Y"].position.y() == 40.0

    def test_two_inputs_evenly_distributed(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that two input pins are evenly distributed."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # With 2 pins, available height = 80 - 2*10 = 60
        # spacing = 60 / (2+1) = 20
        # y positions: margin + 1*spacing = 10+20 = 30
        #              margin + 2*spacing = 10+40 = 50
        y_positions = [
            layouts["U1.A"].position.y(),
            layouts["U1.B"].position.y(),
        ]
        y_positions.sort()

        # Check even distribution
        assert y_positions[0] == pytest.approx(30.0, abs=0.1)
        assert y_positions[1] == pytest.approx(50.0, abs=0.1)

    def test_many_pins_evenly_distributed(
        self, design: Design, many_pins_cell: Cell
    ) -> None:
        """Test that many pins are evenly distributed."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(many_pins_cell, design)

        # Collect y positions for input pins (D0-D7)
        input_y_positions = []
        for i in range(8):
            pin_id = f"UMUX.D{i}"
            input_y_positions.append(layouts[pin_id].position.y())

        input_y_positions.sort()

        # Check that pins are evenly spaced
        for i in range(1, len(input_y_positions)):
            spacing = input_y_positions[i] - input_y_positions[i - 1]
            # All spacings should be equal
            expected_spacing = (
                input_y_positions[-1] - input_y_positions[0]
            ) / 7
            assert spacing == pytest.approx(expected_spacing, abs=0.1)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases in layout calculation."""

    def test_unequal_input_output_counts(
        self, design: Design, unequal_io_cell: Cell
    ) -> None:
        """Test handling of unequal input/output counts."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(unequal_io_cell, design)

        # 5 inputs should all be on left
        for i in range(5):
            assert layouts[f"UNAND.A{i}"].side == "left"

        # 1 output should be on right (and centered)
        assert layouts["UNAND.Y"].side == "right"
        assert layouts["UNAND.Y"].position.y() == 40.0  # Centered

    def test_cell_with_no_pins(self, design: Design) -> None:
        """Test handling of cell with no pins."""
        cell = Cell(
            id=CellId("UEMPTY"),
            name="UEMPTY",
            cell_type="EMPTY_X1",
            pin_ids=[],
            is_sequential=False,
        )
        design.add_cell(cell)

        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(cell, design)

        assert layouts == {}


# =============================================================================
# Height Adjustment Tests
# =============================================================================


class TestHeightAdjustment:
    """Tests for automatic cell height adjustment."""

    def test_adjust_height_returns_default_for_few_pins(self) -> None:
        """Test that default height is used for few pins per edge.

        With MIN_PIN_SPACING=15 and PIN_MARGIN=10:
        - 4 pins require: (4 * 15) + (2 * 10) = 60 + 20 = 80 (matches default)
        - So 4 or fewer pins per edge fit in default height
        """
        calculator = SymbolLayoutCalculator()

        # 4 inputs, 4 outputs should fit in default height (80px)
        new_height = calculator.adjust_cell_height_for_pins(4, 4)

        assert new_height == 80.0

    def test_adjust_height_increases_for_many_pins(self) -> None:
        """Test that height increases for more than 6 pins per edge."""
        calculator = SymbolLayoutCalculator()

        # 10 inputs should require more height
        new_height = calculator.adjust_cell_height_for_pins(10, 1)

        # Required: (10 * 15) + (2 * 10) = 150 + 20 = 170
        assert new_height > 80.0
        assert new_height >= 170.0

    def test_adjust_height_uses_max_pin_count(self) -> None:
        """Test that height is based on the edge with most pins."""
        calculator = SymbolLayoutCalculator()

        # 8 inputs, 2 outputs - use input count
        height_more_inputs = calculator.adjust_cell_height_for_pins(8, 2)

        # 2 inputs, 8 outputs - use output count
        height_more_outputs = calculator.adjust_cell_height_for_pins(2, 8)

        # Both should result in same height (based on 8 pins)
        assert height_more_inputs == height_more_outputs


# =============================================================================
# Connection Point Tests
# =============================================================================


class TestConnectionPoints:
    """Tests for connection point calculations."""

    def test_connection_point_offset_from_position(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that connection points are properly offset for routing."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(
            simple_cell, design, cell_scene_pos=QPointF(100.0, 200.0)
        )

        # Connection point should be position + cell_scene_pos
        layout_a = layouts["U1.A"]

        expected_x = 100.0 + layout_a.position.x()
        expected_y = 200.0 + layout_a.position.y()

        assert layout_a.connection_point.x() == pytest.approx(expected_x, abs=0.1)
        assert layout_a.connection_point.y() == pytest.approx(expected_y, abs=0.1)

    def test_connection_point_uses_default_scene_pos(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that default scene position is (0, 0)."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # Without scene pos, connection point equals position
        layout_a = layouts["U1.A"]
        assert layout_a.connection_point.x() == layout_a.position.x()
        assert layout_a.connection_point.y() == layout_a.position.y()


# =============================================================================
# Custom Dimensions Tests
# =============================================================================


class TestCustomDimensions:
    """Tests for custom cell dimensions."""

    def test_custom_width_affects_right_edge_position(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that custom width changes right edge pin position."""
        calculator = SymbolLayoutCalculator(cell_width=150.0, cell_height=80.0)

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # Right edge should be at x=150
        assert layouts["U1.Y"].position.x() == 150.0

    def test_custom_height_affects_vertical_distribution(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that custom height changes pin vertical positions."""
        calculator = SymbolLayoutCalculator(cell_width=120.0, cell_height=100.0)

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # Single output should be centered at height/2 = 50
        assert layouts["U1.Y"].position.y() == 50.0


# =============================================================================
# Private Method Tests
# =============================================================================


class TestPrivateMethods:
    """Tests for internal calculation methods."""

    def test_distribute_pins_on_edge_single_pin(self) -> None:
        """Test _distribute_pins_on_edge with a single pin."""
        calculator = SymbolLayoutCalculator()

        # Create a mock pin
        pin = Pin(
            id=PinId("U1.A"),
            name="A",
            direction=PinDirection.INPUT,
            net_id=NetId("net_a"),
        )

        cell_rect = QRectF(0, 0, 120, 80)
        layouts = calculator._distribute_pins_on_edge([pin], "left", cell_rect)

        assert len(layouts) == 1
        # Single pin should be centered
        assert layouts[0].position.y() == 40.0

    def test_distribute_pins_on_edge_multiple_pins(self) -> None:
        """Test _distribute_pins_on_edge with multiple pins."""
        calculator = SymbolLayoutCalculator()

        pins = [
            Pin(
                id=PinId(f"U1.A{i}"),
                name=f"A{i}",
                direction=PinDirection.INPUT,
                net_id=NetId(f"net_a{i}"),
            )
            for i in range(3)
        ]

        cell_rect = QRectF(0, 0, 120, 80)
        layouts = calculator._distribute_pins_on_edge(pins, "left", cell_rect)

        assert len(layouts) == 3
        # Check all on left edge
        for layout in layouts:
            assert layout.position.x() == 0.0

    def test_calculate_pin_position_left_edge(self) -> None:
        """Test _calculate_pin_position for left edge."""
        calculator = SymbolLayoutCalculator()
        cell_rect = QRectF(0, 0, 120, 80)

        pos = calculator._calculate_pin_position("left", 0, 2, cell_rect)

        assert pos.x() == 0.0
        assert 0 < pos.y() < 80

    def test_calculate_pin_position_right_edge(self) -> None:
        """Test _calculate_pin_position for right edge."""
        calculator = SymbolLayoutCalculator()
        cell_rect = QRectF(0, 0, 120, 80)

        pos = calculator._calculate_pin_position("right", 0, 2, cell_rect)

        assert pos.x() == 120.0
        assert 0 < pos.y() < 80


# =============================================================================
# Integration Tests
# =============================================================================


class TestLayoutIntegration:
    """Integration tests for layout calculation with CellItem."""

    def test_layouts_compatible_with_qpointf(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that layouts can be used with Qt positioning."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        # All positions should be valid QPointF objects
        for layout in layouts.values():
            assert isinstance(layout.position, QPointF)
            assert isinstance(layout.connection_point, QPointF)

    def test_layouts_within_cell_bounds(
        self, design: Design, simple_cell: Cell
    ) -> None:
        """Test that all pin positions are within cell bounds."""
        calculator = SymbolLayoutCalculator()

        layouts = calculator.calculate_pin_layouts(simple_cell, design)

        for layout in layouts.values():
            # x should be 0 (left) or cell_width (right)
            assert layout.position.x() in [0.0, 120.0]
            # y should be within cell height
            assert 0 <= layout.position.y() <= 80
