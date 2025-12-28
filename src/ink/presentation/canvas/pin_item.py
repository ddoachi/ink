"""PinItem graphics item for pin rendering on cell symbols.

This module provides the PinItem class, a custom QGraphicsItem subclass that
renders pins (connection points) on cell symbols in the schematic canvas.
PinItem is the visual representation of a Pin domain entity.

Architecture Notes:
    - PinItem lives in the presentation layer
    - It is a child of CellItem for coordinate inheritance
    - It wraps a Pin domain entity but contains no domain logic
    - All rendering, interaction, and visual state logic is encapsulated here
    - Follows Qt's QGraphicsItem pattern for scene-based graphics

Visual Specifications:
    - Pin body: Small circle (3px radius) on cell edges
    - Color: Dark gray (#333333)
    - Direction arrows at FULL detail level:
        - INPUT: Arrow pointing into cell (→)
        - OUTPUT: Arrow pointing out of cell (←)
        - INOUT: Bidirectional arrow (↔)
    - Pin name label: Sans-serif 8pt, positioned adjacent to pin

Level of Detail (LOD) Rendering:
    - MINIMAL: Pin hidden completely (not rendered)
    - BASIC: Pin circle only (no label, no arrow)
    - FULL: Pin circle + name label + direction arrow

Performance Considerations:
    - Simple rendering primitives for efficiency
    - Connection point calculation uses Qt's mapToScene() for accuracy
    - Bounding rect adapts to detail level for optimal culling

See Also:
    - Spec E02-F01-T02 for detailed requirements
    - src/ink/domain/model/pin.py for Pin domain entity
    - src/ink/presentation/canvas/cell_item.py for parent CellItem

Example:
    >>> from ink.domain.model.pin import Pin
    >>> from ink.domain.value_objects.identifiers import PinId, NetId
    >>> from ink.domain.value_objects.pin_direction import PinDirection
    >>> from ink.presentation.canvas.pin_item import PinItem
    >>> from ink.presentation.canvas.cell_item import CellItem
    >>>
    >>> # Create domain pin
    >>> pin = Pin(
    ...     id=PinId("U1.A"),
    ...     name="A",
    ...     direction=PinDirection.INPUT,
    ...     net_id=NetId("net_001")
    ... )
    >>>
    >>> # Create graphics item as child of cell item
    >>> cell_item = CellItem(cell)
    >>> pin_item = PinItem(pin, cell_item)
    >>> pin_item.setPos(0.0, 20.0)  # Position relative to cell
    >>>
    >>> # Get connection point for net routing
    >>> connection_point = pin_item.get_connection_point()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QStyleOptionGraphicsItem,
    QWidget,
)

from ink.domain.value_objects.pin_direction import PinDirection
from ink.presentation.canvas.detail_level import DetailLevel

if TYPE_CHECKING:
    from ink.domain.model.pin import Pin


class PinItem(QGraphicsItem):
    """QGraphicsItem representing a pin on a cell symbol.

    PinItem renders connection points on cell symbols as small circles with
    optional direction arrows and name labels. It is a child of CellItem,
    inheriting coordinate transformations for proper scene positioning.

    The item supports three detail levels:
    - MINIMAL: Hidden (not rendered)
    - BASIC: Circle only
    - FULL: Circle + name label + direction arrow

    Class Constants:
        PIN_RADIUS: Radius of the pin circle in pixels (3.0)
        PIN_COLOR: Color for pin circle and arrows (dark gray #333333)
        ARROW_SIZE: Size of direction arrows in pixels (8.0)
        LABEL_OFFSET: Offset between pin and label in pixels (5.0)
        LABEL_FONT_SIZE: Font size for pin labels in points (8)

    Attributes:
        _pin: The domain Pin entity this item represents
        _detail_level: Current detail level for rendering

    Args:
        pin: Domain Pin entity to visualize
        parent_cell_item: Parent CellItem for coordinate inheritance

    Example:
        >>> pin = Pin(id=PinId("U1.A"), name="A", direction=PinDirection.INPUT,
        ...           net_id=NetId("net_001"))
        >>> cell_item = CellItem(cell)
        >>> pin_item = PinItem(pin, cell_item)
        >>> pin_item.setPos(0.0, 20.0)
        >>> connection_pt = pin_item.get_connection_point()
    """

    # ==========================================================================
    # Class Constants - Geometry
    # ==========================================================================
    # These values define the pin visual dimensions as specified in E02-F01-T02.

    PIN_RADIUS: float = 3.0
    """Radius of the pin circle in pixels. Small for compact appearance."""

    ARROW_SIZE: float = 8.0
    """Size of direction arrows in pixels. Visible but not overwhelming."""

    LABEL_OFFSET: float = 5.0
    """Offset between pin circle and label text in pixels."""

    LABEL_FONT_SIZE: int = 8
    """Font size for pin name labels in points. Smaller than cell names."""

    # ==========================================================================
    # Class Constants - Colors
    # ==========================================================================
    # Color palette follows the spec for consistent appearance.

    PIN_COLOR = QColor("#333333")
    """Dark gray color for pin circle and direction arrows."""

    _LABEL_COLOR = QColor("#000000")
    """Black color for pin name labels."""

    def __init__(
        self, pin: Pin, parent_cell_item: QGraphicsItem
    ) -> None:
        """Initialize pin graphics item.

        Sets up the item as a child of the parent cell item for proper
        coordinate inheritance. The pin position should be set via setPos()
        after construction (typically by SymbolLayoutCalculator).

        Args:
            pin: Domain pin entity containing pin data (name, direction)
            parent_cell_item: Parent CellItem for coordinate inheritance.
                Pin positions are relative to the parent cell's origin.
        """
        # Initialize as child of parent cell item
        # This establishes the parent-child relationship for coordinate transforms
        super().__init__(parent_cell_item)

        # Store reference to domain entity for property queries
        # The pin provides name, direction, and connection info
        self._pin = pin

        # Default to FULL detail level for maximum visibility
        # SchematicCanvas will update this based on zoom level (T04)
        self._detail_level = DetailLevel.FULL

    # ==========================================================================
    # QGraphicsItem Required Methods
    # ==========================================================================

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle for collision detection and rendering.

        The bounding rect must encompass all painted areas including the pin
        circle, direction arrow, and name label. The size varies based on
        the current detail level:
        - MINIMAL: Empty rect (nothing rendered)
        - BASIC: Small rect for pin circle only
        - FULL: Larger rect including label and arrow

        Returns:
            QRectF: Rectangle encompassing the entire painted area.
                    Empty rect if detail level is MINIMAL.

        Note:
            Qt uses this rect for:
            - Collision detection (item at point queries)
            - Scene update optimization (dirty region tracking)
            - View culling (items outside view aren't painted)
        """
        # MINIMAL level: Pin is hidden, return empty bounds
        if self._detail_level == DetailLevel.MINIMAL:
            return QRectF()

        # BASIC level: Only pin circle, small bounds
        if self._detail_level == DetailLevel.BASIC:
            return QRectF(
                -self.PIN_RADIUS,
                -self.PIN_RADIUS,
                self.PIN_RADIUS * 2,
                self.PIN_RADIUS * 2,
            )

        # FULL level: Include label and arrow extents
        # Start with pin circle bounds
        bounds = QRectF(
            -self.PIN_RADIUS,
            -self.PIN_RADIUS,
            self.PIN_RADIUS * 2,
            self.PIN_RADIUS * 2,
        )

        # Calculate label and arrow extents based on direction
        arrow_extent = self.ARROW_SIZE + 2
        label_extent = self._estimate_label_width() + self.LABEL_OFFSET

        # Expand bounds based on pin direction
        # Input pins have arrows on the right, labels on the left
        # Output pins have arrows on the left, labels on the right
        # Inout pins have arrows on both sides
        if self._pin.direction == PinDirection.INPUT:
            # Arrow points right (into cell), label on left
            bounds.adjust(-label_extent, -5, arrow_extent, 5)
        elif self._pin.direction == PinDirection.OUTPUT:
            # Arrow points left (out of cell), label on right
            bounds.adjust(-arrow_extent, -5, label_extent, 5)
        else:  # INOUT
            # Bidirectional, expand both sides
            extent = max(arrow_extent, label_extent)
            bounds.adjust(-extent, -5, extent, 5)

        return bounds

    def paint(
        self,
        painter: QPainter,
        _option: QStyleOptionGraphicsItem,
        _widget: QWidget | None = None,
    ) -> None:
        """Render the pin with appropriate detail level.

        Draws the pin based on the current detail level:
        - MINIMAL: Nothing (hidden)
        - BASIC: Pin circle only
        - FULL: Pin circle + name label + direction arrow

        Args:
            painter: QPainter configured for rendering
            _option: Style options (unused for pins)
            _widget: Target widget (may be None for off-screen rendering)

        Note:
            This method is called by Qt's graphics view framework whenever
            the item needs repainting. Keep it efficient for smooth scrolling.
        """
        # MINIMAL level: Don't render anything
        if self._detail_level == DetailLevel.MINIMAL:
            return

        # =======================================================================
        # Draw Pin Circle (BASIC and FULL levels)
        # =======================================================================
        # Pin is rendered as a small filled circle at the item's origin
        painter.setPen(QPen(self.PIN_COLOR, 1))
        painter.setBrush(QBrush(self.PIN_COLOR))
        painter.drawEllipse(QPointF(0, 0), self.PIN_RADIUS, self.PIN_RADIUS)

        # BASIC level: Stop here (no label, no arrow)
        if self._detail_level == DetailLevel.BASIC:
            return

        # =======================================================================
        # FULL level: Draw label and direction arrow
        # =======================================================================
        self._draw_label(painter)
        self._draw_direction_arrow(painter)

    def _draw_label(self, painter: QPainter) -> None:
        """Draw pin name label adjacent to pin.

        Positions the label based on pin direction to avoid overlap with
        the cell body:
        - INPUT: Label on left (outside cell)
        - OUTPUT: Label on right (outside cell)
        - INOUT: Label above pin

        Args:
            painter: QPainter to draw with
        """
        # Skip if pin name is empty
        if not self._pin.name:
            return

        # Configure font and color
        painter.setPen(self._LABEL_COLOR)
        font = QFont("sans-serif", self.LABEL_FONT_SIZE)
        painter.setFont(font)

        # Position label based on pin direction
        if self._pin.direction == PinDirection.INPUT:
            # Input pins: label on left (outside cell, since pin is on left edge)
            label_x = -self.LABEL_OFFSET - self._estimate_label_width()
            label_y = 4.0  # Vertically centered (font baseline adjustment)
            painter.drawText(QPointF(label_x, label_y), self._pin.name)

        elif self._pin.direction == PinDirection.OUTPUT:
            # Output pins: label on right (outside cell, since pin is on right edge)
            label_x = self.LABEL_OFFSET
            label_y = 4.0  # Vertically centered
            painter.drawText(QPointF(label_x, label_y), self._pin.name)

        else:  # INOUT
            # Inout pins: label above pin to avoid ambiguity
            label_x = -self._estimate_label_width() / 2
            label_y = -self.LABEL_OFFSET
            painter.drawText(QPointF(label_x, label_y), self._pin.name)

    def _draw_direction_arrow(self, painter: QPainter) -> None:
        """Draw direction arrow based on pin type.

        Arrows indicate signal flow direction:
        - INPUT: Arrow pointing into cell (rightward →)
        - OUTPUT: Arrow pointing out of cell (leftward ←)
        - INOUT: Bidirectional arrows (↔)

        Args:
            painter: QPainter to draw with
        """
        painter.setPen(QPen(self.PIN_COLOR, 1))
        painter.setBrush(QBrush(self.PIN_COLOR))

        if self._pin.direction == PinDirection.INPUT:
            self._draw_input_arrow(painter)
        elif self._pin.direction == PinDirection.OUTPUT:
            self._draw_output_arrow(painter)
        else:  # INOUT
            self._draw_bidirectional_arrow(painter)

    def _draw_input_arrow(self, painter: QPainter) -> None:
        """Draw arrow pointing into cell (rightward →).

        Arrow starts from the right of the pin circle and points right,
        indicating signal flow into the cell.

        Args:
            painter: QPainter to draw with
        """
        # Arrow baseline starts after pin circle with small gap
        base_x = self.PIN_RADIUS + 2

        # Create arrow as polyline: base → tip → upper barb → tip → lower barb
        arrow = QPolygonF([
            QPointF(base_x, 0),                          # Arrow base
            QPointF(base_x + self.ARROW_SIZE, 0),        # Arrow tip
            QPointF(base_x + self.ARROW_SIZE - 3, -3),   # Upper barb
            QPointF(base_x + self.ARROW_SIZE, 0),        # Back to tip
            QPointF(base_x + self.ARROW_SIZE - 3, 3),    # Lower barb
        ])
        painter.drawPolyline(arrow)

    def _draw_output_arrow(self, painter: QPainter) -> None:
        """Draw arrow pointing out of cell (leftward ←).

        Arrow starts from the left of the pin circle and points left,
        indicating signal flow out of the cell.

        Args:
            painter: QPainter to draw with
        """
        # Arrow baseline starts before pin circle with small gap
        base_x = -self.PIN_RADIUS - 2

        # Create arrow as polyline: base → tip → upper barb → tip → lower barb
        arrow = QPolygonF([
            QPointF(base_x, 0),                          # Arrow base
            QPointF(base_x - self.ARROW_SIZE, 0),        # Arrow tip
            QPointF(base_x - self.ARROW_SIZE + 3, -3),   # Upper barb
            QPointF(base_x - self.ARROW_SIZE, 0),        # Back to tip
            QPointF(base_x - self.ARROW_SIZE + 3, 3),    # Lower barb
        ])
        painter.drawPolyline(arrow)

    def _draw_bidirectional_arrow(self, painter: QPainter) -> None:
        """Draw bidirectional arrow for INOUT pins (↔).

        Draws both input and output arrows to indicate bidirectional
        signal flow.

        Args:
            painter: QPainter to draw with
        """
        # Draw both arrows
        self._draw_input_arrow(painter)
        self._draw_output_arrow(painter)

    def _estimate_label_width(self) -> float:
        """Estimate label width for bounding rect calculation.

        Uses a rough estimate of 6 pixels per character for efficiency.
        Actual font metrics would be more accurate but slower.

        Returns:
            float: Estimated label width in pixels
        """
        # Rough estimate: approximately 6 pixels per character
        # This is conservative to ensure the bounding rect is large enough
        return len(self._pin.name) * 6

    # ==========================================================================
    # Public API Methods
    # ==========================================================================

    def get_connection_point(self) -> QPointF:
        """Return the scene coordinate for net attachment.

        The connection point is the center of the pin circle, converted to
        scene coordinates. This is critical for net routing - the router
        uses this point to determine where nets should connect.

        Returns:
            QPointF: Connection point in scene coordinates

        Note:
            Uses Qt's mapToScene() to account for:
            - Pin's position relative to parent cell
            - Parent cell's position in the scene
            - Any transformations (rotation, scaling)

        Example:
            >>> # Cell at (100, 200), pin at (10, 20) relative to cell
            >>> connection_point = pin_item.get_connection_point()
            >>> # Returns (110, 220) in scene coordinates
        """
        # Pin center is at item origin (0, 0)
        item_pos = QPointF(0, 0)

        # Convert to scene coordinates (handles full transformation chain)
        scene_pos = self.mapToScene(item_pos)

        return scene_pos

    def set_detail_level(self, level: DetailLevel) -> None:
        """Set the level of detail based on zoom.

        Changes the rendering detail level and updates visibility:
        - MINIMAL: Hides the pin (setVisible(False))
        - BASIC: Shows pin circle only
        - FULL: Shows pin circle, label, and arrow

        Args:
            level: New DetailLevel value

        Note:
            Typically called by SchematicCanvas when zoom changes (T04).
            Triggers a repaint to update the visual appearance.

        Example:
            >>> pin_item.set_detail_level(DetailLevel.FULL)  # Show all details
            >>> pin_item.set_detail_level(DetailLevel.MINIMAL)  # Hide pin
        """
        # Skip if level hasn't changed to avoid unnecessary repaints
        if self._detail_level == level:
            return

        self._detail_level = level

        # Update visibility based on level
        # MINIMAL = hidden, BASIC/FULL = visible
        self.setVisible(level != DetailLevel.MINIMAL)

        # Trigger repaint to update rendering
        self.update()

    def get_pin(self) -> Pin:
        """Return the associated domain pin entity.

        Provides access to the underlying Pin for property queries,
        such as displaying pin properties in a property panel or
        determining net connectivity.

        Returns:
            The Pin domain entity this item visualizes

        Example:
            >>> pin = pin_item.get_pin()
            >>> print(f"Pin direction: {pin.direction}")
            >>> print(f"Connected net: {pin.net_id}")
        """
        return self._pin

    def __repr__(self) -> str:
        """Return string representation for debugging.

        Returns:
            String like: PinItem(name='A', direction=INPUT, pos=(10.0, 20.0))
        """
        pos = self.pos()
        return (
            f"PinItem(name={self._pin.name!r}, "
            f"direction={self._pin.direction.name}, "
            f"pos=({pos.x()}, {pos.y()}))"
        )
