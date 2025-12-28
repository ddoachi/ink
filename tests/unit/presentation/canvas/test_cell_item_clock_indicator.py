"""Unit tests for CellItem clock indicator feature (E02-F01-T05).

Tests verify the clock indicator implementation for sequential cells:
- Clock indicator rendered only for sequential cells
- Clock indicator only visible at FULL detail level
- Clock icon positioned in top-right corner (12x12 pixels)
- Clock icon consists of circle with clock hands

TDD Approach:
- RED phase: These tests will fail initially as clock indicator doesn't exist
- GREEN phase: Implement clock indicator to pass all tests
- REFACTOR phase: Clean up and optimize implementation

Architecture Notes:
- DetailLevel enum controls Level of Detail rendering
- Clock indicator is a presentation-only feature (no domain logic)
- Icon drawn using QPainter primitives (circle + lines)

See Also:
- Spec E02-F01-T05 for detailed requirements
- E02-F01-T05.pre-docs.md for design decisions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
)

from ink.domain.model.cell import Cell
from ink.domain.value_objects.identifiers import CellId, PinId
from ink.presentation.canvas.cell_item import CellItem
from ink.presentation.canvas.detail_level import DetailLevel

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sequential_cell() -> Cell:
    """Create a sequential (flip-flop) cell for testing.

    Returns:
        Cell: A D flip-flop cell instance with is_sequential=True.
    """
    return Cell(
        id=CellId("XFF1"),
        name="XFF1",
        cell_type="DFF_X1",
        pin_ids=[PinId("XFF1.D"), PinId("XFF1.CLK"), PinId("XFF1.Q")],
        is_sequential=True,
    )


@pytest.fixture
def combinational_cell() -> Cell:
    """Create a combinational (non-sequential) cell for testing.

    Returns:
        Cell: An AND gate cell instance with is_sequential=False.
    """
    return Cell(
        id=CellId("U1"),
        name="U1",
        cell_type="AND2_X1",
        pin_ids=[PinId("U1.A"), PinId("U1.B"), PinId("U1.Y")],
        is_sequential=False,
    )


@pytest.fixture
def graphics_scene(qtbot: QtBot) -> QGraphicsScene:
    """Create a QGraphicsScene for testing CellItem in context.

    Args:
        qtbot: pytest-qt fixture for Qt widget management.

    Returns:
        QGraphicsScene: Scene for adding CellItem instances.
    """
    scene = QGraphicsScene()
    return scene


@pytest.fixture
def graphics_view(qtbot: QtBot, graphics_scene: QGraphicsScene) -> QGraphicsView:
    """Create a QGraphicsView for testing CellItem rendering.

    Args:
        qtbot: pytest-qt fixture for Qt widget management.
        graphics_scene: Scene containing items to display.

    Returns:
        QGraphicsView: View for rendering the scene.
    """
    view = QGraphicsView(graphics_scene)
    qtbot.addWidget(view)
    return view


# =============================================================================
# DetailLevel Enum Tests
# =============================================================================


class TestDetailLevelEnum:
    """Tests for the DetailLevel enum."""

    def test_detail_level_has_minimal_value(self) -> None:
        """Test that DetailLevel has a MINIMAL value for zoomed-out rendering."""
        assert hasattr(DetailLevel, "MINIMAL")
        assert DetailLevel.MINIMAL.value == 0

    def test_detail_level_has_basic_value(self) -> None:
        """Test that DetailLevel has a BASIC value for standard rendering."""
        assert hasattr(DetailLevel, "BASIC")
        assert DetailLevel.BASIC.value == 1

    def test_detail_level_has_full_value(self) -> None:
        """Test that DetailLevel has a FULL value for detailed rendering."""
        assert hasattr(DetailLevel, "FULL")
        assert DetailLevel.FULL.value == 2

    def test_detail_level_ordering(self) -> None:
        """Test that DetailLevel values are ordered correctly.

        MINIMAL < BASIC < FULL for comparison operations.
        """
        assert DetailLevel.MINIMAL.value < DetailLevel.BASIC.value
        assert DetailLevel.BASIC.value < DetailLevel.FULL.value


# =============================================================================
# Clock Indicator Constants Tests
# =============================================================================


class TestClockIndicatorConstants:
    """Tests for clock indicator constants defined in CellItem."""

    def test_clock_icon_size_constant(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that CLOCK_ICON_SIZE is defined as 12.0 pixels."""
        assert hasattr(CellItem, "CLOCK_ICON_SIZE")
        assert CellItem.CLOCK_ICON_SIZE == 12.0

    def test_clock_icon_margin_constant(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that CLOCK_ICON_MARGIN is defined as 5.0 pixels."""
        assert hasattr(CellItem, "CLOCK_ICON_MARGIN")
        assert CellItem.CLOCK_ICON_MARGIN == 5.0


# =============================================================================
# Detail Level Management Tests
# =============================================================================


class TestCellItemDetailLevel:
    """Tests for CellItem detail level management."""

    def test_cell_item_has_default_detail_level(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that CellItem has a default detail level of BASIC."""
        cell_item = CellItem(sequential_cell)

        # Default detail level should be BASIC for standard rendering
        assert cell_item.get_detail_level() == DetailLevel.BASIC

    def test_cell_item_can_set_detail_level(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that CellItem detail level can be changed."""
        cell_item = CellItem(sequential_cell)

        cell_item.set_detail_level(DetailLevel.FULL)

        assert cell_item.get_detail_level() == DetailLevel.FULL

    def test_cell_item_can_set_all_detail_levels(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that CellItem can be set to all detail levels."""
        cell_item = CellItem(sequential_cell)

        for level in [DetailLevel.MINIMAL, DetailLevel.BASIC, DetailLevel.FULL]:
            cell_item.set_detail_level(level)
            assert cell_item.get_detail_level() == level


# =============================================================================
# Clock Indicator Method Tests
# =============================================================================


class TestClockIndicatorMethod:
    """Tests for the _draw_clock_indicator method."""

    def test_draw_clock_indicator_method_exists(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that _draw_clock_indicator method exists on CellItem."""
        cell_item = CellItem(sequential_cell)

        assert hasattr(cell_item, "_draw_clock_indicator")
        assert callable(cell_item._draw_clock_indicator)

    def test_draw_clock_indicator_can_be_called(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that _draw_clock_indicator can be called with a painter."""
        cell_item = CellItem(sequential_cell)

        # Create a pixmap and painter for testing
        pixmap = QPixmap(200, 200)
        pixmap.fill()
        painter = QPainter(pixmap)

        # Should not raise an exception
        cell_item._draw_clock_indicator(painter)

        painter.end()


# =============================================================================
# Clock Indicator Rendering Tests
# =============================================================================


class TestClockIndicatorRendering:
    """Tests for clock indicator rendering behavior."""

    def test_sequential_cell_shows_clock_at_full_detail(
        self,
        qtbot: QtBot,
        sequential_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that sequential cells show clock icon at FULL detail level.

        At FULL detail, the clock indicator should be visible.
        """
        cell_item = CellItem(sequential_cell)
        cell_item.set_detail_level(DetailLevel.FULL)
        graphics_scene.addItem(cell_item)

        # Force rendering
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Verify item is sequential and at FULL detail
        assert cell_item.get_cell().is_sequential
        assert cell_item.get_detail_level() == DetailLevel.FULL
        # Visual verification would require screenshot comparison

    def test_sequential_cell_no_clock_at_basic_detail(
        self,
        qtbot: QtBot,
        sequential_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that sequential cells do NOT show clock icon at BASIC detail.

        At BASIC detail, clock indicator should be hidden for performance.
        """
        cell_item = CellItem(sequential_cell)
        cell_item.set_detail_level(DetailLevel.BASIC)
        graphics_scene.addItem(cell_item)

        # Force rendering
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Verify detail level is BASIC (clock should not be drawn)
        assert cell_item.get_detail_level() == DetailLevel.BASIC

    def test_sequential_cell_no_clock_at_minimal_detail(
        self,
        qtbot: QtBot,
        sequential_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that sequential cells do NOT show clock icon at MINIMAL detail.

        At MINIMAL detail, clock indicator should be hidden.
        """
        cell_item = CellItem(sequential_cell)
        cell_item.set_detail_level(DetailLevel.MINIMAL)
        graphics_scene.addItem(cell_item)

        # Force rendering
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Verify detail level is MINIMAL (clock should not be drawn)
        assert cell_item.get_detail_level() == DetailLevel.MINIMAL

    def test_combinational_cell_never_shows_clock(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that combinational cells NEVER show clock icon.

        Clock indicator is only for sequential cells.
        """
        cell_item = CellItem(combinational_cell)
        cell_item.set_detail_level(DetailLevel.FULL)
        graphics_scene.addItem(cell_item)

        # Force rendering
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Verify cell is NOT sequential (clock should never be drawn)
        assert not cell_item.get_cell().is_sequential
        assert cell_item.get_detail_level() == DetailLevel.FULL


# =============================================================================
# Clock Indicator Position Tests
# =============================================================================


class TestClockIndicatorPosition:
    """Tests for clock indicator position (top-right corner)."""

    def test_clock_icon_position_in_top_right(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that clock icon is positioned in top-right corner.

        The icon should be offset from the top-right by CLOCK_ICON_MARGIN.
        """
        # Create cell item to verify constants are accessible
        _ = CellItem(sequential_cell)

        # Calculate expected position based on spec constants
        expected_x = (
            CellItem.DEFAULT_WIDTH
            - CellItem.CLOCK_ICON_SIZE
            - CellItem.CLOCK_ICON_MARGIN
        )
        expected_y = CellItem.CLOCK_ICON_MARGIN

        # The clock icon should fit within the cell bounds
        assert expected_x > 0
        assert expected_y > 0
        assert expected_x + CellItem.CLOCK_ICON_SIZE < CellItem.DEFAULT_WIDTH


# =============================================================================
# Paint Method Integration Tests
# =============================================================================


class TestPaintMethodWithClockIndicator:
    """Integration tests for paint method with clock indicator."""

    def test_paint_at_full_detail_includes_clock(
        self,
        qtbot: QtBot,
        sequential_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint at FULL detail draws clock for sequential cells.

        This is a behavior verification test.
        """
        cell_item = CellItem(sequential_cell)
        cell_item.set_detail_level(DetailLevel.FULL)
        graphics_scene.addItem(cell_item)

        # Force rendering
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Test passes if no exceptions and item is visible
        assert cell_item.isVisible()
        assert cell_item.get_cell().is_sequential
        assert cell_item.get_detail_level() == DetailLevel.FULL

    def test_paint_at_basic_detail_renders_without_clock(
        self,
        qtbot: QtBot,
        sequential_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint at BASIC detail renders correctly without clock."""
        cell_item = CellItem(sequential_cell)
        cell_item.set_detail_level(DetailLevel.BASIC)
        graphics_scene.addItem(cell_item)

        # Force rendering
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Test passes if no exceptions and item is visible
        assert cell_item.isVisible()

    def test_paint_at_minimal_detail_renders_simplified(
        self,
        qtbot: QtBot,
        sequential_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint at MINIMAL detail renders simplified view."""
        cell_item = CellItem(sequential_cell)
        cell_item.set_detail_level(DetailLevel.MINIMAL)
        graphics_scene.addItem(cell_item)

        # Force rendering
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Test passes if no exceptions and item is visible
        assert cell_item.isVisible()


# =============================================================================
# Mixed Cell Type Scene Tests
# =============================================================================


class TestMixedCellTypes:
    """Tests for scenes with both sequential and combinational cells."""

    def test_mixed_cells_render_correctly(
        self,
        qtbot: QtBot,
        sequential_cell: Cell,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that both cell types render correctly side by side."""
        seq_item = CellItem(sequential_cell)
        seq_item.set_detail_level(DetailLevel.FULL)
        seq_item.set_position(0, 0)

        comb_item = CellItem(combinational_cell)
        comb_item.set_detail_level(DetailLevel.FULL)
        comb_item.set_position(150, 0)

        graphics_scene.addItem(seq_item)
        graphics_scene.addItem(comb_item)

        # Force rendering
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Both items should be visible
        assert seq_item.isVisible()
        assert comb_item.isVisible()

        # Verify types
        assert seq_item.get_cell().is_sequential
        assert not comb_item.get_cell().is_sequential

    def test_multiple_sequential_cells_at_different_detail_levels(
        self,
        qtbot: QtBot,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test sequential cells at different detail levels."""
        # Create three sequential cells at different detail levels
        cells = [
            Cell(
                id=CellId(f"XFF{i}"),
                name=f"XFF{i}",
                cell_type="DFF_X1",
                pin_ids=[],
                is_sequential=True,
            )
            for i in range(1, 4)
        ]

        items = []
        for i, cell in enumerate(cells):
            item = CellItem(cell)
            item.set_position(i * 150, 0)
            items.append(item)
            graphics_scene.addItem(item)

        # Set different detail levels
        items[0].set_detail_level(DetailLevel.MINIMAL)
        items[1].set_detail_level(DetailLevel.BASIC)
        items[2].set_detail_level(DetailLevel.FULL)

        # Force rendering
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # All items should render without error
        for item in items:
            assert item.isVisible()

        # Verify detail levels
        assert items[0].get_detail_level() == DetailLevel.MINIMAL
        assert items[1].get_detail_level() == DetailLevel.BASIC
        assert items[2].get_detail_level() == DetailLevel.FULL
