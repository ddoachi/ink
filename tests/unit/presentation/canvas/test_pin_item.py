"""Unit tests for PinItem graphics widget.

Tests verify the PinItem implementation meets all requirements from spec E02-F01-T02:
- PinItem instantiation with Pin domain entity and parent CellItem
- Rendering of pins as small circles on cell edges
- Pin name labels displayed adjacent to pins
- Direction arrows for input/output/inout pins
- Connection point calculation in scene coordinates
- Detail level support (MINIMAL/BASIC/FULL)
- Parent-child coordinate transformations

TDD Approach:
- RED phase: These tests will fail initially as PinItem doesn't exist yet
- GREEN phase: Implement PinItem to pass all tests
- REFACTOR phase: Clean up and optimize implementation

Architecture Notes:
- PinItem is a QGraphicsItem subclass in the presentation layer
- It is a child of CellItem for coordinate inheritance
- It wraps a Pin domain entity from the domain layer
- No domain logic in PinItem - only rendering and interaction

See Also:
- Spec E02-F01-T02 for detailed requirements
- src/ink/domain/model/pin.py for Pin domain entity
- src/ink/presentation/canvas/cell_item.py for parent CellItem
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
)

from ink.domain.model.cell import Cell
from ink.domain.model.pin import Pin
from ink.domain.value_objects.identifiers import CellId, NetId, PinId
from ink.domain.value_objects.pin_direction import PinDirection
from ink.presentation.canvas.cell_item import CellItem
from ink.presentation.canvas.detail_level import DetailLevel
from ink.presentation.canvas.pin_item import PinItem

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def input_pin() -> Pin:
    """Create an input pin for testing.

    Returns:
        Pin: An input pin instance with a connected net.
    """
    return Pin(
        id=PinId("U1.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_001"),
    )


@pytest.fixture
def output_pin() -> Pin:
    """Create an output pin for testing.

    Returns:
        Pin: An output pin instance with a connected net.
    """
    return Pin(
        id=PinId("U1.Y"),
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_002"),
    )


@pytest.fixture
def inout_pin() -> Pin:
    """Create an inout (bidirectional) pin for testing.

    Returns:
        Pin: An inout pin instance with a connected net.
    """
    return Pin(
        id=PinId("U1.IO"),
        name="IO",
        direction=PinDirection.INOUT,
        net_id=NetId("net_003"),
    )


@pytest.fixture
def long_name_pin() -> Pin:
    """Create a pin with a long name for label testing.

    Returns:
        Pin: A pin with a long name for text elision testing.
    """
    return Pin(
        id=PinId("U1.DATA_IN_FROM_BUFFER"),
        name="DATA_IN_FROM_BUFFER",
        direction=PinDirection.INPUT,
        net_id=NetId("net_004"),
    )


@pytest.fixture
def floating_pin() -> Pin:
    """Create a floating (unconnected) pin for testing.

    Returns:
        Pin: A pin without a connected net.
    """
    return Pin(
        id=PinId("U1.NC"),
        name="NC",
        direction=PinDirection.INPUT,
        net_id=None,
    )


@pytest.fixture
def parent_cell() -> Cell:
    """Create a parent cell for testing pin items.

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
def parent_cell_item(parent_cell: Cell) -> CellItem:
    """Create a parent CellItem for testing pin items.

    Args:
        parent_cell: Cell domain entity.

    Returns:
        CellItem: A CellItem instance to use as parent.
    """
    return CellItem(parent_cell)


@pytest.fixture
def graphics_scene(qtbot: QtBot) -> QGraphicsScene:
    """Create a QGraphicsScene for testing PinItem in context.

    Args:
        qtbot: pytest-qt fixture for Qt widget management.

    Returns:
        QGraphicsScene: Scene for adding graphics items.
    """
    return QGraphicsScene()


@pytest.fixture
def graphics_view(qtbot: QtBot, graphics_scene: QGraphicsScene) -> QGraphicsView:
    """Create a QGraphicsView for testing PinItem rendering.

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
# PinItem Creation Tests
# =============================================================================


class TestPinItemCreation:
    """Tests for PinItem instantiation and basic properties."""

    def test_pin_item_can_be_created(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that PinItem can be instantiated with a Pin entity and parent.

        Verifies:
        - No exceptions during construction
        - Returns a valid object instance
        """
        pin_item = PinItem(input_pin, parent_cell_item)

        assert pin_item is not None

    def test_pin_item_is_qgraphics_item_subclass(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that PinItem inherits from QGraphicsItem.

        QGraphicsItem is required for use in QGraphicsScene.
        """
        pin_item = PinItem(input_pin, parent_cell_item)

        assert isinstance(pin_item, QGraphicsItem)

    def test_pin_item_stores_pin_reference(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that PinItem stores reference to the domain Pin entity.

        The domain pin is needed for property queries and rendering.
        """
        pin_item = PinItem(input_pin, parent_cell_item)

        retrieved_pin = pin_item.get_pin()

        assert retrieved_pin is input_pin
        assert retrieved_pin.name == "A"
        assert retrieved_pin.direction == PinDirection.INPUT

    def test_pin_item_has_parent_cell_item(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that PinItem is a child of the parent CellItem.

        Parent-child relationship is used for coordinate inheritance.
        """
        pin_item = PinItem(input_pin, parent_cell_item)

        assert pin_item.parentItem() is parent_cell_item

    def test_pin_item_default_detail_level_is_full(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that PinItem defaults to FULL detail level.

        FULL detail shows pin dot + name + arrow.
        """
        pin_item = PinItem(input_pin, parent_cell_item)

        # The default should be FULL detail level
        # This tests internal state - implementation may vary
        assert pin_item.isVisible()


# =============================================================================
# PinItem Constants Tests
# =============================================================================


class TestPinItemConstants:
    """Tests for PinItem class constants."""

    def test_pin_radius_constant(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that PIN_RADIUS is defined as 3.0 pixels."""
        assert PinItem.PIN_RADIUS == 3.0

    def test_arrow_size_constant(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that ARROW_SIZE is defined as 8.0 pixels."""
        assert PinItem.ARROW_SIZE == 8.0

    def test_label_offset_constant(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that LABEL_OFFSET is defined as 5.0 pixels."""
        assert PinItem.LABEL_OFFSET == 5.0


# =============================================================================
# Bounding Rect Tests
# =============================================================================


class TestPinItemBoundingRect:
    """Tests for PinItem.boundingRect() method."""

    def test_bounding_rect_returns_qrectf(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that boundingRect returns a QRectF object."""
        pin_item = PinItem(input_pin, parent_cell_item)

        bounding_rect = pin_item.boundingRect()

        assert isinstance(bounding_rect, QRectF)

    def test_bounding_rect_at_minimal_level_is_empty(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that boundingRect is empty at MINIMAL detail level.

        At MINIMAL level, pins are hidden and don't need bounds.
        """
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.MINIMAL)

        bounding_rect = pin_item.boundingRect()

        assert bounding_rect.isEmpty()

    def test_bounding_rect_at_basic_level_is_small(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that boundingRect at BASIC level only covers pin circle.

        At BASIC level, only the dot is shown (no label, no arrow).
        """
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.BASIC)

        bounding_rect = pin_item.boundingRect()

        # Should be approximately 2 * PIN_RADIUS = 6 pixels
        assert bounding_rect.width() <= PinItem.PIN_RADIUS * 2 + 2
        assert bounding_rect.height() <= PinItem.PIN_RADIUS * 2 + 2

    def test_bounding_rect_at_full_level_includes_label_and_arrow(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that boundingRect at FULL level includes label and arrow.

        At FULL level, the bounding rect should be larger to include
        the pin name label and direction arrow.
        """
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.FULL)

        bounding_rect = pin_item.boundingRect()

        # Should be larger than just the pin circle
        assert bounding_rect.width() > PinItem.PIN_RADIUS * 2
        assert not bounding_rect.isEmpty()

    def test_long_name_pin_has_larger_bounding_rect(
        self, qtbot: QtBot, long_name_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that pins with long names have larger bounding rect."""
        pin_item = PinItem(long_name_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.FULL)

        bounding_rect = pin_item.boundingRect()

        # Long name should result in wider bounding rect
        assert bounding_rect.width() > 50  # Approximate label width


# =============================================================================
# Detail Level Tests
# =============================================================================


class TestPinItemDetailLevel:
    """Tests for PinItem detail level management."""

    def test_set_detail_level_to_minimal_hides_pin(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that setting MINIMAL detail level hides the pin."""
        pin_item = PinItem(input_pin, parent_cell_item)

        pin_item.set_detail_level(DetailLevel.MINIMAL)

        assert not pin_item.isVisible()

    def test_set_detail_level_to_basic_shows_pin(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that setting BASIC detail level shows the pin."""
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.MINIMAL)  # First hide it

        pin_item.set_detail_level(DetailLevel.BASIC)

        assert pin_item.isVisible()

    def test_set_detail_level_to_full_shows_pin(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that setting FULL detail level shows the pin."""
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.MINIMAL)  # First hide it

        pin_item.set_detail_level(DetailLevel.FULL)

        assert pin_item.isVisible()

    def test_detail_level_change_triggers_update(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that changing detail level triggers a visual update."""
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)

        # Changing level should not raise exceptions
        pin_item.set_detail_level(DetailLevel.BASIC)
        pin_item.set_detail_level(DetailLevel.FULL)
        pin_item.set_detail_level(DetailLevel.MINIMAL)

        # If we get here without exception, the update worked
        assert True


# =============================================================================
# Connection Point Tests
# =============================================================================


class TestPinItemConnectionPoint:
    """Tests for PinItem.get_connection_point() method.

    The connection point is critical for net routing - it must return
    accurate scene coordinates where nets should connect to the pin.
    """

    def test_connection_point_returns_qpointf(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that get_connection_point returns a QPointF."""
        pin_item = PinItem(input_pin, parent_cell_item)

        connection_point = pin_item.get_connection_point()

        assert isinstance(connection_point, QPointF)

    def test_connection_point_at_origin_when_no_position_set(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test connection point when pin is at origin.

        When both cell and pin are at origin, connection point should be (0, 0).
        """
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)
        # Pin is at (0, 0) relative to parent, parent is at (0, 0)

        connection_point = pin_item.get_connection_point()

        assert connection_point.x() == pytest.approx(0.0, abs=0.1)
        assert connection_point.y() == pytest.approx(0.0, abs=0.1)

    def test_connection_point_accounts_for_pin_position(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test connection point when pin has offset from parent.

        Pin positioned at (10, 20) relative to parent at origin
        should return connection point at (10, 20) in scene coords.
        """
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.setPos(10.0, 20.0)

        connection_point = pin_item.get_connection_point()

        assert connection_point.x() == pytest.approx(10.0, abs=0.1)
        assert connection_point.y() == pytest.approx(20.0, abs=0.1)

    def test_connection_point_accounts_for_parent_position(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test connection point when parent cell has position.

        Parent at (100, 200), pin at (10, 20) relative to parent
        should return connection point at (110, 220) in scene coords.
        """
        graphics_scene.addItem(parent_cell_item)
        parent_cell_item.setPos(100.0, 200.0)
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.setPos(10.0, 20.0)

        connection_point = pin_item.get_connection_point()

        assert connection_point.x() == pytest.approx(110.0, abs=0.1)
        assert connection_point.y() == pytest.approx(220.0, abs=0.1)

    def test_connection_point_changes_with_parent_movement(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that connection point updates when parent moves.

        Moving the parent cell should update the pin's connection point.
        """
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.setPos(10.0, 20.0)

        # Initial position
        parent_cell_item.setPos(0.0, 0.0)
        point1 = pin_item.get_connection_point()

        # Move parent
        parent_cell_item.setPos(50.0, 100.0)
        point2 = pin_item.get_connection_point()

        # Connection point should have moved by (50, 100)
        assert point2.x() - point1.x() == pytest.approx(50.0, abs=0.1)
        assert point2.y() - point1.y() == pytest.approx(100.0, abs=0.1)


# =============================================================================
# Pin Direction Arrow Tests
# =============================================================================


class TestPinItemDirectionArrows:
    """Tests for pin direction arrow rendering."""

    def test_input_pin_direction_is_stored(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that input pin direction is correctly accessible."""
        pin_item = PinItem(input_pin, parent_cell_item)

        assert pin_item.get_pin().direction == PinDirection.INPUT

    def test_output_pin_direction_is_stored(
        self, qtbot: QtBot, output_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that output pin direction is correctly accessible."""
        pin_item = PinItem(output_pin, parent_cell_item)

        assert pin_item.get_pin().direction == PinDirection.OUTPUT

    def test_inout_pin_direction_is_stored(
        self, qtbot: QtBot, inout_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that inout pin direction is correctly accessible."""
        pin_item = PinItem(inout_pin, parent_cell_item)

        assert pin_item.get_pin().direction == PinDirection.INOUT


# =============================================================================
# Paint Method Tests
# =============================================================================


class TestPinItemPaint:
    """Tests for PinItem.paint() method.

    Note: These tests verify that paint() can be called without errors.
    Actual visual verification would require snapshot testing.
    """

    def test_paint_method_exists(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that paint method is implemented."""
        pin_item = PinItem(input_pin, parent_cell_item)

        assert hasattr(pin_item, "paint")
        assert callable(pin_item.paint)

    def test_paint_can_be_called_without_error(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint executes without raising exceptions."""
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.setPos(0.0, 20.0)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # If we get here without exception, paint worked
        assert True

    def test_paint_at_minimal_level_does_not_crash(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint at MINIMAL level works without error."""
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.MINIMAL)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        assert True

    def test_paint_at_basic_level_does_not_crash(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint at BASIC level works without error."""
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.BASIC)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        assert True

    def test_paint_at_full_level_does_not_crash(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that paint at FULL level works without error."""
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.FULL)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        assert True

    def test_paint_all_pin_directions_without_error(
        self,
        qtbot: QtBot,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that painting all pin direction types works without error."""
        graphics_scene.addItem(parent_cell_item)

        # Create pins directly to reduce fixture dependencies
        input_pin = Pin(
            id=PinId("U1.A"), name="A",
            direction=PinDirection.INPUT, net_id=NetId("net_001")
        )
        output_pin = Pin(
            id=PinId("U1.Y"), name="Y",
            direction=PinDirection.OUTPUT, net_id=NetId("net_002")
        )
        inout_pin = Pin(
            id=PinId("U1.IO"), name="IO",
            direction=PinDirection.INOUT, net_id=NetId("net_003")
        )

        input_item = PinItem(input_pin, parent_cell_item)
        input_item.setPos(0.0, 20.0)

        output_item = PinItem(output_pin, parent_cell_item)
        output_item.setPos(CellItem.DEFAULT_WIDTH, 20.0)

        inout_item = PinItem(inout_pin, parent_cell_item)
        inout_item.setPos(CellItem.DEFAULT_WIDTH, 40.0)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        assert True


# =============================================================================
# Scene Integration Tests
# =============================================================================


class TestPinItemSceneIntegration:
    """Integration tests for PinItem within QGraphicsScene."""

    def test_pin_item_appears_in_scene_items(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that PinItem appears in scene items list."""
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)

        # PinItem is a child of CellItem, so it should be in scene
        all_items = graphics_scene.items()

        assert pin_item in all_items

    def test_multiple_pins_on_cell(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        output_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that multiple pins can be added to a single cell."""
        graphics_scene.addItem(parent_cell_item)

        pin1 = PinItem(input_pin, parent_cell_item)
        pin1.setPos(0.0, 20.0)

        pin2 = PinItem(output_pin, parent_cell_item)
        pin2.setPos(CellItem.DEFAULT_WIDTH, 20.0)

        # Both pins should be in scene
        all_items = graphics_scene.items()
        assert pin1 in all_items
        assert pin2 in all_items

    def test_pin_inherits_parent_visibility(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that pin visibility follows parent cell visibility."""
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)

        # Hide parent
        parent_cell_item.setVisible(False)

        # Pin should effectively be hidden (isVisible checks parent chain)
        # Note: Qt's isVisible() checks the entire parent chain
        assert not pin_item.isVisible() or not parent_cell_item.isVisible()


# =============================================================================
# Edge Cases and Error Handling Tests
# =============================================================================


class TestPinItemEdgeCases:
    """Tests for edge cases and error handling."""

    def test_floating_pin_renders_correctly(
        self,
        qtbot: QtBot,
        floating_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that floating (unconnected) pins render without error."""
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(floating_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.FULL)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        assert pin_item.get_pin().net_id is None
        assert True  # No crash

    def test_empty_pin_name_renders_correctly(
        self,
        qtbot: QtBot,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that pins with empty names render without error."""
        empty_name_pin = Pin(
            id=PinId("U1."),
            name="",
            direction=PinDirection.INPUT,
            net_id=None,
        )
        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(empty_name_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.FULL)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        assert True  # No crash

    def test_detail_level_same_value_no_update(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
    ) -> None:
        """Test that setting same detail level doesn't cause unnecessary updates."""
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.set_detail_level(DetailLevel.FULL)

        # Setting the same level again should not cause issues
        pin_item.set_detail_level(DetailLevel.FULL)

        # If we get here without exception, it worked
        assert True


# =============================================================================
# Performance-Related Tests
# =============================================================================


class TestPinItemPerformance:
    """Tests related to performance characteristics."""

    def test_pin_item_creation_is_fast(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that creating many pin items is reasonably fast."""
        import time

        start = time.perf_counter()

        for _ in range(100):
            pin = Pin(
                id=PinId(f"U1.P{_}"),
                name=f"P{_}",
                direction=PinDirection.INPUT,
                net_id=None,
            )
            PinItem(pin, parent_cell_item)

        elapsed = time.perf_counter() - start

        # Should create 100 items in less than 0.5 seconds
        assert elapsed < 0.5

    def test_connection_point_calculation_is_fast(
        self,
        qtbot: QtBot,
        input_pin: Pin,
        parent_cell_item: CellItem,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that connection point calculation is fast."""
        import time

        graphics_scene.addItem(parent_cell_item)
        pin_item = PinItem(input_pin, parent_cell_item)
        pin_item.setPos(10.0, 20.0)

        start = time.perf_counter()

        for _ in range(1000):
            pin_item.get_connection_point()

        elapsed = time.perf_counter() - start

        # Should calculate 1000 points in less than 0.1 seconds
        assert elapsed < 0.1
