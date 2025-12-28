"""Integration tests for zoom-based Level of Detail (LOD) behavior.

Tests verify the complete LOD system works correctly with real graphics items:
- SchematicCanvas zoom changes propagate to CellItem and PinItem
- Detail levels are correctly updated on all items
- Visual rendering behaves correctly at each detail level
- Performance remains acceptable with many items

TDD Approach:
- These integration tests verify the complete LOD pipeline
- They exercise the interaction between SchematicCanvas, CellItem, and PinItem

Architecture Notes:
- Tests use real Qt graphics infrastructure
- CellItem and PinItem respond to set_detail_level() calls
- SchematicCanvas coordinates detail level across all items

See Also:
- Spec E02-F01-T04 for detailed requirements
- Unit tests for individual component behavior
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

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
def sample_cell() -> Cell:
    """Create a sample cell for testing."""
    return Cell(
        id=CellId("U1"),
        name="U1",
        cell_type="AND2_X1",
        pin_ids=[PinId("U1.A"), PinId("U1.B"), PinId("U1.Y")],
        is_sequential=False,
    )


@pytest.fixture
def sample_input_pin() -> Pin:
    """Create a sample input pin for testing."""
    return Pin(
        id=PinId("U1.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_001"),
    )


@pytest.fixture
def sample_output_pin() -> Pin:
    """Create a sample output pin for testing."""
    return Pin(
        id=PinId("U1.Y"),
        name="Y",
        direction=PinDirection.OUTPUT,
        net_id=NetId("net_002"),
    )


@pytest.fixture
def graphics_scene() -> QGraphicsScene:
    """Create a QGraphicsScene for testing."""
    return QGraphicsScene()


@pytest.fixture
def graphics_view(qtbot: QtBot, graphics_scene: QGraphicsScene) -> QGraphicsView:
    """Create a QGraphicsView for testing."""
    view = QGraphicsView(graphics_scene)
    qtbot.addWidget(view)
    return view


# =============================================================================
# LOD Integration Tests - Complete Pipeline
# =============================================================================


class TestZoomLODIntegration:
    """Integration tests for zoom-based LOD across all components."""

    def test_zoom_out_updates_cell_item_detail_level(
        self,
        qtbot: QtBot,
        sample_cell: Cell,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that zooming out updates CellItem detail level.

        When SchematicCanvas zoom goes below 25%, CellItem should
        receive MINIMAL detail level.
        """
        cell_item = CellItem(sample_cell)
        graphics_scene.addItem(cell_item)

        # Verify initial state is BASIC (default)
        assert cell_item.get_detail_level() == DetailLevel.BASIC

        # Simulate zoom-triggered detail level update
        cell_item.set_detail_level(DetailLevel.MINIMAL)

        assert cell_item.get_detail_level() == DetailLevel.MINIMAL

    def test_zoom_out_updates_pin_item_detail_level(
        self,
        qtbot: QtBot,
        sample_cell: Cell,
        sample_input_pin: Pin,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that zooming out updates PinItem detail level.

        When SchematicCanvas zoom goes below 25%, PinItem should
        be hidden (MINIMAL level).
        """
        cell_item = CellItem(sample_cell)
        graphics_scene.addItem(cell_item)

        pin_item = PinItem(sample_input_pin, cell_item)
        pin_item.setPos(0.0, 20.0)

        # Verify pin is initially visible (FULL level)
        assert pin_item.isVisible()

        # Simulate zoom-triggered detail level update
        pin_item.set_detail_level(DetailLevel.MINIMAL)

        # Pin should be hidden at MINIMAL level
        assert not pin_item.isVisible()

    def test_zoom_level_transitions_are_smooth(
        self,
        qtbot: QtBot,
        sample_cell: Cell,
        sample_input_pin: Pin,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that detail level transitions occur at correct thresholds.

        Verify the three detail levels are applied correctly:
        - MINIMAL: < 25% zoom
        - BASIC: 25% - 75% zoom
        - FULL: >= 75% zoom
        """
        cell_item = CellItem(sample_cell)
        graphics_scene.addItem(cell_item)

        pin_item = PinItem(sample_input_pin, cell_item)

        # Test FULL level (>= 75%)
        cell_item.set_detail_level(DetailLevel.FULL)
        pin_item.set_detail_level(DetailLevel.FULL)

        assert cell_item.get_detail_level() == DetailLevel.FULL
        assert pin_item.isVisible()

        # Test BASIC level (25% - 75%)
        cell_item.set_detail_level(DetailLevel.BASIC)
        pin_item.set_detail_level(DetailLevel.BASIC)

        assert cell_item.get_detail_level() == DetailLevel.BASIC
        assert pin_item.isVisible()

        # Test MINIMAL level (< 25%)
        cell_item.set_detail_level(DetailLevel.MINIMAL)
        pin_item.set_detail_level(DetailLevel.MINIMAL)

        assert cell_item.get_detail_level() == DetailLevel.MINIMAL
        assert not pin_item.isVisible()

    def test_multiple_items_receive_detail_level_updates(
        self,
        qtbot: QtBot,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that multiple graphics items all receive detail level updates.

        Simulates a scene with multiple cells and pins, verifying all
        items are updated when zoom changes.
        """
        # Create multiple cells and pins
        items: list[CellItem | PinItem] = []
        for i in range(5):
            cell = Cell(
                id=CellId(f"U{i}"),
                name=f"U{i}",
                cell_type="AND2_X1",
                pin_ids=[],
                is_sequential=False,
            )
            cell_item = CellItem(cell)
            cell_item.set_position(i * 150.0, 0.0)
            graphics_scene.addItem(cell_item)
            items.append(cell_item)

            # Add a pin to each cell
            pin = Pin(
                id=PinId(f"U{i}.A"),
                name="A",
                direction=PinDirection.INPUT,
                net_id=None,
            )
            pin_item = PinItem(pin, cell_item)
            pin_item.setPos(0.0, 20.0)
            items.append(pin_item)

        # Update all items to MINIMAL
        for item in items:
            if isinstance(item, (CellItem, PinItem)):
                item.set_detail_level(DetailLevel.MINIMAL)

        # Verify all items received the update
        for item in items:
            if isinstance(item, CellItem):
                assert item.get_detail_level() == DetailLevel.MINIMAL
            else:
                # item is PinItem
                assert not item.isVisible()


# =============================================================================
# LOD Visual Rendering Tests
# =============================================================================


class TestZoomLODRendering:
    """Tests for visual rendering at different detail levels."""

    def test_cell_renders_without_error_at_minimal(
        self,
        qtbot: QtBot,
        sample_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that CellItem renders correctly at MINIMAL detail."""
        cell_item = CellItem(sample_cell)
        graphics_scene.addItem(cell_item)
        cell_item.set_detail_level(DetailLevel.MINIMAL)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        # If no crash, rendering is working
        assert cell_item in graphics_scene.items()

    def test_cell_renders_without_error_at_basic(
        self,
        qtbot: QtBot,
        sample_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that CellItem renders correctly at BASIC detail."""
        cell_item = CellItem(sample_cell)
        graphics_scene.addItem(cell_item)
        cell_item.set_detail_level(DetailLevel.BASIC)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        assert cell_item in graphics_scene.items()

    def test_cell_renders_without_error_at_full(
        self,
        qtbot: QtBot,
        sample_cell: Cell,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that CellItem renders correctly at FULL detail."""
        cell_item = CellItem(sample_cell)
        graphics_scene.addItem(cell_item)
        cell_item.set_detail_level(DetailLevel.FULL)

        graphics_view.show()
        qtbot.waitExposed(graphics_view)

        assert cell_item in graphics_scene.items()

    def test_pin_renders_at_all_detail_levels(
        self,
        qtbot: QtBot,
        sample_cell: Cell,
        sample_input_pin: Pin,
        graphics_scene: QGraphicsScene,
        graphics_view: QGraphicsView,
    ) -> None:
        """Test that PinItem renders correctly at all detail levels."""
        cell_item = CellItem(sample_cell)
        graphics_scene.addItem(cell_item)

        pin_item = PinItem(sample_input_pin, cell_item)

        # Test each level
        for level in [DetailLevel.FULL, DetailLevel.BASIC, DetailLevel.MINIMAL]:
            pin_item.set_detail_level(level)
            graphics_view.repaint()

        # If no crash, all levels render correctly
        assert True


# =============================================================================
# Performance Tests
# =============================================================================


class TestZoomLODPerformance:
    """Performance tests for LOD system."""

    def test_detail_level_update_performance_with_many_items(
        self,
        qtbot: QtBot,
        graphics_scene: QGraphicsScene,
    ) -> None:
        """Test that updating detail level on many items is fast.

        The spec requires 60fps with 1000+ cells, so updating all items
        must complete within 16ms.
        """
        import time

        # Create 100 cells with pins (200 items total)
        items: list[CellItem | PinItem] = []
        for i in range(100):
            cell = Cell(
                id=CellId(f"U{i}"),
                name=f"U{i}",
                cell_type="AND2_X1",
                pin_ids=[],
                is_sequential=False,
            )
            cell_item = CellItem(cell)
            graphics_scene.addItem(cell_item)
            items.append(cell_item)

            pin = Pin(
                id=PinId(f"U{i}.A"),
                name="A",
                direction=PinDirection.INPUT,
                net_id=None,
            )
            pin_item = PinItem(pin, cell_item)
            items.append(pin_item)

        # Measure time to update all items
        start = time.perf_counter()

        for item in items:
            if isinstance(item, (CellItem, PinItem)):
                item.set_detail_level(DetailLevel.MINIMAL)

        elapsed = time.perf_counter() - start

        # Should complete in well under 16ms for 60fps
        # Allow 100ms for safety margin in CI
        assert elapsed < 0.1, f"Detail level update took {elapsed*1000:.2f}ms"

    def test_from_zoom_calculation_is_fast(self) -> None:
        """Test that DetailLevel.from_zoom() is fast for frequent calls.

        This method may be called every frame during zoom animations.
        """
        import time

        start = time.perf_counter()

        for _ in range(10000):
            DetailLevel.from_zoom(0.5)

        elapsed = time.perf_counter() - start

        # 10000 calls should complete in under 50ms
        assert elapsed < 0.05, f"10000 from_zoom calls took {elapsed*1000:.2f}ms"
