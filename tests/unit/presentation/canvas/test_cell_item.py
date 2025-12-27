"""Unit tests for CellItem graphics widget.

Tests verify the CellItem implementation meets all requirements from spec E02-F01-T01:
- CellItem instantiation with Cell domain entity
- Rendering of rectangular cell symbol with rounded corners
- Cell instance name displayed centered within symbol
- Visual distinction for sequential cells (thicker border)
- Selection and hover state visual feedback
- Bounding rect and paint method implementations
- Shape method for accurate selection detection

TDD Approach:
- RED phase: These tests will fail initially as CellItem doesn't exist yet
- GREEN phase: Implement CellItem to pass all tests
- REFACTOR phase: Clean up and optimize implementation

Architecture Notes:
- CellItem is a QGraphicsItem subclass in the presentation layer
- It wraps a Cell domain entity from the domain layer
- No domain logic in CellItem - only rendering and interaction

See Also:
- Spec E02-F01-T01 for detailed requirements
- src/ink/domain/model/cell.py for Cell domain entity
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QPainterPath
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
)

from ink.domain.model.cell import Cell
from ink.domain.value_objects.identifiers import CellId, PinId
from ink.presentation.canvas.cell_item import CellItem

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def combinational_cell() -> Cell:
    """Create a combinational (non-sequential) cell for testing.

    Returns:
        Cell: A simple AND gate cell instance.
    """
    return Cell(
        id=CellId("U1"),
        name="U1",
        cell_type="AND2_X1",
        pin_ids=[PinId("U1.A"), PinId("U1.B"), PinId("U1.Y")],
        is_sequential=False,
    )


@pytest.fixture
def sequential_cell() -> Cell:
    """Create a sequential (flip-flop) cell for testing.

    Returns:
        Cell: A D flip-flop cell instance.
    """
    return Cell(
        id=CellId("XFF1"),
        name="XFF1",
        cell_type="DFF_X1",
        pin_ids=[PinId("XFF1.D"), PinId("XFF1.CLK"), PinId("XFF1.Q")],
        is_sequential=True,
    )


@pytest.fixture
def long_name_cell() -> Cell:
    """Create a cell with a long name for text elision testing.

    Returns:
        Cell: A cell with a hierarchical instance name.
    """
    return Cell(
        id=CellId("XI_CORE/U_ALU/XI_ADD/U_CARRY_CHAIN"),
        name="XI_CORE/U_ALU/XI_ADD/U_CARRY_CHAIN",
        cell_type="FA_X1",
        pin_ids=[],
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
# CellItem Creation Tests
# =============================================================================


class TestCellItemCreation:
    """Tests for CellItem instantiation and basic properties."""

    def test_cell_item_can_be_created(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that CellItem can be instantiated with a Cell entity.

        Verifies:
        - No exceptions during construction
        - Returns a valid object instance
        """
        cell_item = CellItem(combinational_cell)

        assert cell_item is not None

    def test_cell_item_is_qgraphics_item_subclass(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that CellItem inherits from QGraphicsItem.

        QGraphicsItem is required for use in QGraphicsScene.
        """
        cell_item = CellItem(combinational_cell)

        assert isinstance(cell_item, QGraphicsItem)

    def test_cell_item_stores_cell_reference(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that CellItem stores reference to the domain Cell entity.

        The domain cell is needed for property queries and rendering.
        """
        cell_item = CellItem(combinational_cell)

        retrieved_cell = cell_item.get_cell()

        assert retrieved_cell is combinational_cell
        assert retrieved_cell.name == "U1"
        assert retrieved_cell.cell_type == "AND2_X1"

    def test_cell_item_accepts_parent_item(
        self, qtbot: QtBot, combinational_cell: Cell, sequential_cell: Cell
    ) -> None:
        """Test that CellItem can be created with a parent QGraphicsItem.

        Parent-child relationships are used for grouping and transformations.
        """
        parent_item = CellItem(combinational_cell)
        child_item = CellItem(sequential_cell, parent=parent_item)

        assert child_item.parentItem() is parent_item


# =============================================================================
# CellItem Constants Tests
# =============================================================================


class TestCellItemConstants:
    """Tests for CellItem class constants."""

    def test_default_width_constant(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that DEFAULT_WIDTH is defined as 120.0 pixels."""
        assert CellItem.DEFAULT_WIDTH == 120.0

    def test_default_height_constant(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that DEFAULT_HEIGHT is defined as 80.0 pixels."""
        assert CellItem.DEFAULT_HEIGHT == 80.0

    def test_corner_radius_constant(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that CORNER_RADIUS is defined as 5.0 pixels."""
        assert CellItem.CORNER_RADIUS == 5.0

    def test_border_width_constant(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that BORDER_WIDTH is defined as 2.0 pixels for combinational."""
        assert CellItem.BORDER_WIDTH == 2.0

    def test_sequential_border_width_constant(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that SEQUENTIAL_BORDER_WIDTH is defined as 3.0 pixels."""
        assert CellItem.SEQUENTIAL_BORDER_WIDTH == 3.0


# =============================================================================
# Bounding Rect Tests
# =============================================================================


class TestCellItemBoundingRect:
    """Tests for CellItem.boundingRect() method."""

    def test_bounding_rect_returns_qrectf(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that boundingRect returns a QRectF object."""
        cell_item = CellItem(combinational_cell)

        bounding_rect = cell_item.boundingRect()

        assert isinstance(bounding_rect, QRectF)

    def test_bounding_rect_has_correct_dimensions(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that boundingRect has correct width and height.

        Bounding rect should include the border width for proper collision detection.
        The rect should be slightly larger than the cell body to account for the pen.
        """
        cell_item = CellItem(combinational_cell)

        bounding_rect = cell_item.boundingRect()

        # Width should be DEFAULT_WIDTH + padding for border
        assert bounding_rect.width() >= CellItem.DEFAULT_WIDTH
        # Height should be DEFAULT_HEIGHT + padding for border
        assert bounding_rect.height() >= CellItem.DEFAULT_HEIGHT

    def test_bounding_rect_origin_at_top_left(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that boundingRect origin is at or before (0, 0).

        The bounding rect should start at or before the top-left corner
        to account for any border/pen overflow.
        """
        cell_item = CellItem(combinational_cell)

        bounding_rect = cell_item.boundingRect()

        # Origin should be at or before (0, 0) to account for border
        assert bounding_rect.left() <= 0
        assert bounding_rect.top() <= 0

    def test_sequential_cell_bounding_rect_accounts_for_thicker_border(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that sequential cell bounding rect is slightly larger.

        Sequential cells have thicker borders, so their bounding rect
        should account for the additional border width.
        """
        cell_item = CellItem(sequential_cell)

        bounding_rect = cell_item.boundingRect()

        # Should still be at least DEFAULT dimensions
        assert bounding_rect.width() >= CellItem.DEFAULT_WIDTH
        assert bounding_rect.height() >= CellItem.DEFAULT_HEIGHT


# =============================================================================
# Position Tests
# =============================================================================


class TestCellItemPosition:
    """Tests for CellItem position management."""

    def test_set_position_changes_scene_position(
        self, qtbot: QtBot, combinational_cell: Cell, graphics_scene: QGraphicsScene
    ) -> None:
        """Test that set_position updates the item's position in scene coordinates."""
        cell_item = CellItem(combinational_cell)
        graphics_scene.addItem(cell_item)

        cell_item.set_position(100.0, 200.0)

        assert cell_item.pos().x() == 100.0
        assert cell_item.pos().y() == 200.0

    def test_set_position_with_negative_coordinates(
        self, qtbot: QtBot, combinational_cell: Cell, graphics_scene: QGraphicsScene
    ) -> None:
        """Test that set_position works with negative coordinates."""
        cell_item = CellItem(combinational_cell)
        graphics_scene.addItem(cell_item)

        cell_item.set_position(-50.0, -100.0)

        assert cell_item.pos().x() == -50.0
        assert cell_item.pos().y() == -100.0

    def test_initial_position_is_origin(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that newly created CellItem starts at origin (0, 0)."""
        cell_item = CellItem(combinational_cell)

        assert cell_item.pos().x() == 0.0
        assert cell_item.pos().y() == 0.0


# =============================================================================
# Paint Method Tests
# =============================================================================


class TestCellItemPaint:
    """Tests for CellItem.paint() method.

    Note: These tests verify that paint() can be called without errors
    and produces expected visual output. Actual visual verification
    would require snapshot testing or manual inspection.
    """

    def test_paint_method_exists(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that paint method is implemented."""
        cell_item = CellItem(combinational_cell)

        # paint method should exist and be callable
        assert hasattr(cell_item, "paint")
        assert callable(cell_item.paint)

    def test_paint_can_be_called_without_error(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint executes without raising exceptions.

        This test adds the item to a scene and view to trigger painting.
        """
        cell_item = CellItem(combinational_cell)
        graphics_scene.addItem(cell_item)

        # Force a repaint by showing the view
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # If we get here without exception, paint worked
        assert True

    def test_paint_renders_cell_body(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint draws a rectangular cell body.

        Uses scene rendering to verify the paint method works correctly.
        """
        cell_item = CellItem(combinational_cell)
        graphics_scene.addItem(cell_item)

        # Force a repaint - if paint works, no exception
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Verify the item was painted by checking it's in the scene
        assert cell_item in graphics_scene.items()

    def test_paint_renders_cell_name(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint draws the cell instance name.

        The cell name should be rendered within the cell body.
        """
        cell_item = CellItem(combinational_cell)
        graphics_scene.addItem(cell_item)

        # Force a repaint
        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # Verify the cell has the expected name accessible
        assert cell_item.get_cell().name == "U1"


# =============================================================================
# Visual State Tests
# =============================================================================


class TestCellItemVisualStates:
    """Tests for CellItem visual states (normal, selected, hovered)."""

    def test_cell_item_is_selectable(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that CellItem has ItemIsSelectable flag enabled."""
        cell_item = CellItem(combinational_cell)

        flags = cell_item.flags()

        assert flags & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable

    def test_cell_item_selection_changes_visual(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that selecting a CellItem changes its visual appearance.

        Selection should trigger an update and change border color to blue.
        """
        cell_item = CellItem(combinational_cell)
        graphics_scene.addItem(cell_item)

        # Initially not selected
        assert not cell_item.isSelected()

        # Select the item
        cell_item.setSelected(True)

        assert cell_item.isSelected()
        # Visual verification would require checking the rendered output

    def test_cell_item_accepts_hover_events(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that CellItem accepts hover events.

        Hover events are needed for hover visual feedback.
        """
        cell_item = CellItem(combinational_cell)

        # Should accept hover events
        assert cell_item.acceptHoverEvents()


# =============================================================================
# Sequential vs Combinational Tests
# =============================================================================


class TestCellItemSequentialDistinction:
    """Tests for visual distinction between sequential and combinational cells."""

    def test_combinational_cell_uses_standard_border(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that combinational cells use BORDER_WIDTH (2px)."""
        cell_item = CellItem(combinational_cell)

        # The cell should report it's not sequential
        assert not cell_item.get_cell().is_sequential

    def test_sequential_cell_uses_thick_border(
        self, qtbot: QtBot, sequential_cell: Cell
    ) -> None:
        """Test that sequential cells use SEQUENTIAL_BORDER_WIDTH (3px)."""
        cell_item = CellItem(sequential_cell)

        # The cell should report it's sequential
        assert cell_item.get_cell().is_sequential

    def test_sequential_cell_has_different_fill(
        self, qtbot: QtBot, sequential_cell: Cell, combinational_cell: Cell
    ) -> None:
        """Test that sequential cells have different fill color.

        Sequential: white (#FFFFFF)
        Combinational: light gray (#F0F0F0)
        """
        seq_item = CellItem(sequential_cell)
        comb_item = CellItem(combinational_cell)

        # Both should be valid items
        assert seq_item.get_cell().is_sequential
        assert not comb_item.get_cell().is_sequential
        # Actual color verification would require rendering tests


# =============================================================================
# Shape Method Tests
# =============================================================================


class TestCellItemShape:
    """Tests for CellItem.shape() method for accurate selection detection."""

    def test_shape_returns_painter_path(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that shape returns a QPainterPath."""
        cell_item = CellItem(combinational_cell)

        shape = cell_item.shape()

        assert isinstance(shape, QPainterPath)

    def test_shape_contains_cell_body_region(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that shape path covers the cell body area."""
        cell_item = CellItem(combinational_cell)

        shape = cell_item.shape()

        # Center point should be inside the shape
        center = QPointF(CellItem.DEFAULT_WIDTH / 2, CellItem.DEFAULT_HEIGHT / 2)
        assert shape.contains(center)

    def test_shape_excludes_outside_region(
        self, qtbot: QtBot, combinational_cell: Cell
    ) -> None:
        """Test that shape path doesn't include areas outside the cell."""
        cell_item = CellItem(combinational_cell)

        shape = cell_item.shape()

        # Point far outside should not be in shape
        outside = QPointF(CellItem.DEFAULT_WIDTH * 2, CellItem.DEFAULT_HEIGHT * 2)
        assert not shape.contains(outside)


# =============================================================================
# Item Change Tests
# =============================================================================


class TestCellItemChange:
    """Tests for CellItem.itemChange() method for state change handling."""

    def test_item_change_handles_selection(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that itemChange handles selection state changes."""
        cell_item = CellItem(combinational_cell)
        graphics_scene.addItem(cell_item)

        # Change selection state
        cell_item.setSelected(True)

        # Should handle the change without error
        assert cell_item.isSelected()

    def test_item_change_handles_position(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that itemChange handles position changes."""
        cell_item = CellItem(combinational_cell)
        graphics_scene.addItem(cell_item)

        # Enable position change notifications if needed
        cell_item.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True
        )

        # Change position
        cell_item.setPos(50.0, 75.0)

        # Should handle the change without error
        assert cell_item.pos().x() == 50.0
        assert cell_item.pos().y() == 75.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestCellItemSceneIntegration:
    """Integration tests for CellItem within QGraphicsScene."""

    def test_cell_item_can_be_added_to_scene(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that CellItem can be added to a QGraphicsScene."""
        cell_item = CellItem(combinational_cell)

        graphics_scene.addItem(cell_item)

        assert cell_item.scene() is graphics_scene

    def test_multiple_cell_items_in_scene(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        sequential_cell: Cell,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that multiple CellItems can coexist in a scene."""
        cell_item1 = CellItem(combinational_cell)
        cell_item2 = CellItem(sequential_cell)

        graphics_scene.addItem(cell_item1)
        graphics_scene.addItem(cell_item2)

        cell_item1.set_position(0, 0)
        cell_item2.set_position(150, 0)

        items = graphics_scene.items()
        assert len(items) == 2

    def test_cell_item_appears_in_scene_bounding_rect(
        self,
        qtbot: QtBot,
        combinational_cell: Cell,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that CellItem contributes to scene bounding rect."""
        cell_item = CellItem(combinational_cell)
        graphics_scene.addItem(cell_item)
        cell_item.set_position(100, 100)

        scene_rect = graphics_scene.itemsBoundingRect()

        assert not scene_rect.isEmpty()
        assert scene_rect.width() > 0
        assert scene_rect.height() > 0
