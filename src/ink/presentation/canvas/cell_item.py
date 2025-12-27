"""CellItem graphics item for cell symbol rendering.

This module provides the CellItem class, a custom QGraphicsItem subclass that
renders cell symbols (gate-level instances) in the schematic canvas. CellItem
is the visual representation of a Cell domain entity.

Architecture Notes:
    - CellItem lives in the presentation layer
    - It wraps a Cell domain entity but contains no domain logic
    - All rendering, interaction, and visual state logic is encapsulated here
    - Follows Qt's QGraphicsItem pattern for scene-based graphics

Visual Specifications:
    - Cell body: Rounded rectangle (5px corner radius)
    - Default size: 120x80 pixels
    - Combinational cells: 2px border, light gray fill (#F0F0F0)
    - Sequential cells: 3px border, white fill (#FFFFFF)
    - Cell name: Centered, sans-serif 10pt, black text
    - Selection: Blue border (#2196F3), subtle highlight
    - Hover: Slightly darker border

Performance Considerations:
    - Uses Qt's caching mechanism (CacheMode.DeviceCoordinateCache)
    - Efficient bounding rect calculation (accounts for border width)
    - Shape method provides accurate selection hit detection

See Also:
    - Spec E02-F01-T01 for detailed requirements
    - src/ink/domain/model/cell.py for Cell domain entity
    - Qt documentation for QGraphicsItem

Example:
    >>> from ink.domain.model.cell import Cell
    >>> from ink.domain.value_objects.identifiers import CellId
    >>> from ink.presentation.canvas.cell_item import CellItem
    >>>
    >>> # Create domain cell
    >>> cell = Cell(id=CellId("U1"), name="U1", cell_type="AND2_X1")
    >>>
    >>> # Create graphics item
    >>> cell_item = CellItem(cell)
    >>> cell_item.set_position(100.0, 200.0)
    >>>
    >>> # Add to scene
    >>> scene.addItem(cell_item)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QStyle,
    QStyleOptionGraphicsItem,
    QWidget,
)

if TYPE_CHECKING:
    from ink.domain.model.cell import Cell


class CellItem(QGraphicsItem):
    """QGraphicsItem representing a cell symbol in the schematic canvas.

    CellItem renders gate-level cell instances as rectangular symbols with
    rounded corners. It displays the cell instance name centered within
    the symbol and provides visual distinction for sequential elements
    (flip-flops, latches) through thicker borders.

    The item supports:
    - Selection highlighting (blue border when selected)
    - Hover state visual feedback (darker border on hover)
    - Efficient caching for smooth rendering performance
    - Accurate shape-based selection detection

    Class Constants:
        DEFAULT_WIDTH: Standard cell width in pixels (120.0)
        DEFAULT_HEIGHT: Standard cell height in pixels (80.0)
        CORNER_RADIUS: Rounded corner radius in pixels (5.0)
        BORDER_WIDTH: Combinational cell border width (2.0)
        SEQUENTIAL_BORDER_WIDTH: Sequential cell border width (3.0)

    Attributes:
        _cell: The domain Cell entity this item represents

    Args:
        cell: Domain Cell entity to visualize
        parent: Optional parent QGraphicsItem for grouping

    Example:
        >>> cell = Cell(id=CellId("U1"), name="U1", cell_type="AND2_X1")
        >>> item = CellItem(cell)
        >>> item.set_position(100, 200)
        >>> scene.addItem(item)
    """

    # ==========================================================================
    # Class Constants - Geometry
    # ==========================================================================
    # These values define the default cell symbol dimensions.
    # They match the spec requirements in E02-F01-T01.

    DEFAULT_WIDTH: float = 120.0
    """Standard cell width in pixels. Chosen for readable text at default zoom."""

    DEFAULT_HEIGHT: float = 80.0
    """Standard cell height in pixels. Provides good aspect ratio for labels."""

    CORNER_RADIUS: float = 5.0
    """Corner radius for rounded rectangle. Subtle rounding for modern look."""

    BORDER_WIDTH: float = 2.0
    """Border width for combinational cells. Standard visibility."""

    SEQUENTIAL_BORDER_WIDTH: float = 3.0
    """Border width for sequential cells. Thicker for visual distinction."""

    # ==========================================================================
    # Class Constants - Colors
    # ==========================================================================
    # Color palette follows material design principles for clarity.

    _FILL_COLOR_COMBINATIONAL = QColor("#F0F0F0")
    """Light gray fill for combinational cells (non-sequential)."""

    _FILL_COLOR_SEQUENTIAL = QColor("#FFFFFF")
    """White fill for sequential cells (flip-flops, latches)."""

    _BORDER_COLOR_NORMAL = QColor("#333333")
    """Dark gray border for normal state."""

    _BORDER_COLOR_SELECTED = QColor("#2196F3")
    """Material Design blue for selected state."""

    _BORDER_COLOR_HOVER = QColor("#555555")
    """Slightly lighter dark gray for hover state."""

    _TEXT_COLOR = QColor("#000000")
    """Black text color for cell name."""

    _SELECTED_FILL_TINT = QColor(33, 150, 243, 30)
    """Semi-transparent blue tint for selected cells."""

    def __init__(self, cell: Cell, parent: QGraphicsItem | None = None) -> None:
        """Initialize cell graphics item.

        Sets up the item with the provided Cell domain entity, configures
        Qt flags for selection and hover support, and enables caching
        for efficient rendering.

        Args:
            cell: Domain cell entity containing instance data
            parent: Optional parent QGraphicsItem for grouping
        """
        super().__init__(parent)

        # Store reference to domain entity for property queries
        # This allows the presentation layer to access cell data
        # without duplicating it
        self._cell = cell

        # Track hover state for visual feedback
        # Qt doesn't provide direct hover state query, so we track it
        self._is_hovered = False

        # Configure Qt item flags
        self._setup_flags()

        # Enable caching for efficient rendering
        # DeviceCoordinateCache provides best balance of quality and speed
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    def _setup_flags(self) -> None:
        """Configure QGraphicsItem flags for interaction support.

        Enables:
        - Selection: Users can click to select cells
        - Hover events: Visual feedback on mouse hover
        - Geometry change notifications: For position tracking
        """
        # Enable selection - required for click-to-select behavior
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        # Enable hover events - required for hover visual feedback
        self.setAcceptHoverEvents(True)

        # Enable geometry change notifications - for position change handling
        self.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True
        )

    # ==========================================================================
    # QGraphicsItem Required Methods
    # ==========================================================================

    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle for collision detection and rendering.

        The bounding rect must encompass all painted areas including borders.
        It's slightly larger than the cell body to account for the pen width,
        ensuring proper collision detection and scene updates.

        Returns:
            QRectF: Rectangle encompassing the entire painted area

        Note:
            Qt uses this rect for:
            - Collision detection (item at point queries)
            - Scene update optimization (dirty region tracking)
            - View culling (items outside view aren't painted)
        """
        # Determine border width based on cell type
        border_width = (
            self.SEQUENTIAL_BORDER_WIDTH
            if self._cell.is_sequential
            else self.BORDER_WIDTH
        )

        # Pen is centered on the path, so half extends outward
        # Add a small margin (1px) for anti-aliasing
        margin = border_width / 2.0 + 1.0

        # Return rect that includes all painted content
        return QRectF(
            -margin,
            -margin,
            self.DEFAULT_WIDTH + 2 * margin,
            self.DEFAULT_HEIGHT + 2 * margin,
        )

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        _widget: QWidget | None = None,
    ) -> None:
        """Render the cell symbol.

        Draws the cell as a rounded rectangle with:
        - Fill color based on cell type (combinational vs sequential)
        - Border color based on state (normal, selected, hover)
        - Cell instance name centered within the symbol

        Args:
            painter: QPainter configured for rendering
            option: Style options including selection state
            widget: Target widget (may be None for off-screen rendering)

        Note:
            This method is called by Qt's graphics view framework whenever
            the item needs repainting. Keep it efficient as it may be called
            frequently during animations or scrolling.
        """
        # =======================================================================
        # Determine Visual State
        # =======================================================================
        # Note: PySide6 type stubs incorrectly omit 'state' attribute from
        # QStyleOptionGraphicsItem (it's inherited from QStyleOption at runtime)
        is_selected = bool(option.state & QStyle.StateFlag.State_Selected)  # type: ignore[attr-defined]
        is_sequential = self._cell.is_sequential

        # =======================================================================
        # Configure Pen (Border)
        # =======================================================================
        # Border width differs for sequential vs combinational cells
        border_width = (
            self.SEQUENTIAL_BORDER_WIDTH if is_sequential else self.BORDER_WIDTH
        )

        # Border color depends on interaction state (priority: selected > hover > normal)
        if is_selected:
            border_color = self._BORDER_COLOR_SELECTED
        elif self._is_hovered:
            border_color = self._BORDER_COLOR_HOVER
        else:
            border_color = self._BORDER_COLOR_NORMAL

        pen = QPen(border_color, border_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # =======================================================================
        # Configure Brush (Fill)
        # =======================================================================
        # Sequential cells have white fill, combinational have light gray
        fill_color = (
            self._FILL_COLOR_SEQUENTIAL if is_sequential else self._FILL_COLOR_COMBINATIONAL
        )
        painter.setBrush(QBrush(fill_color))

        # =======================================================================
        # Draw Cell Body (Rounded Rectangle)
        # =======================================================================
        body_rect = QRectF(0, 0, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
        painter.drawRoundedRect(body_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

        # =======================================================================
        # Draw Selection Highlight (Optional)
        # =======================================================================
        if is_selected:
            # Add subtle blue tint overlay for selected cells
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self._SELECTED_FILL_TINT))
            painter.drawRoundedRect(body_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

        # =======================================================================
        # Draw Cell Name Label
        # =======================================================================
        self._draw_cell_name(painter, body_rect)

    def _draw_cell_name(self, painter: QPainter, rect: QRectF) -> None:
        """Draw the cell instance name centered within the cell body.

        Args:
            painter: QPainter to draw with
            rect: Rectangle bounds for text centering

        Note:
            Long names are elided (truncated with "...") if they exceed
            the available width. This prevents text overflow while maintaining
            readability.
        """
        # Configure font - 10pt sans-serif as per spec
        font = QFont()
        font.setPointSize(10)
        font.setFamily("sans-serif")
        painter.setFont(font)

        # Set text color to black
        painter.setPen(QPen(self._TEXT_COLOR))

        # Get cell name from domain entity
        cell_name = self._cell.name

        # Calculate text width to check if elision is needed
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(cell_name)

        # Padding for text area (leave some margin from edges)
        text_padding = 8.0
        available_width = rect.width() - 2 * text_padding

        # Elide text if it's too long
        if text_width > available_width:
            cell_name = font_metrics.elidedText(
                cell_name,
                Qt.TextElideMode.ElideMiddle,
                int(available_width),
            )

        # Draw text centered in the cell body
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            cell_name,
        )

    def shape(self) -> QPainterPath:
        """Return the shape path for accurate selection detection.

        The shape determines which area responds to mouse clicks and
        collision queries. Using a rounded rectangle shape matches
        the visual appearance for intuitive selection behavior.

        Returns:
            QPainterPath: Path representing the clickable/selectable area

        Note:
            Qt uses shape() for hit testing. A precise shape ensures users
            can click exactly on the visible cell area. Without this override,
            Qt would use the boundingRect, which includes border margins.
        """
        path = QPainterPath()
        # Create rounded rectangle path matching the cell body
        path.addRoundedRect(
            QRectF(0, 0, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT),
            self.CORNER_RADIUS,
            self.CORNER_RADIUS,
        )
        return path

    # ==========================================================================
    # Hover Event Handlers
    # ==========================================================================

    def hoverEnterEvent(self, _event: object) -> None:
        """Handle mouse entering the item area.

        Sets hover state and triggers repaint for visual feedback.

        Args:
            _event: Qt hover event (unused but required by signature)
        """
        self._is_hovered = True
        self.update()  # Trigger repaint to show hover visual

    def hoverLeaveEvent(self, _event: object) -> None:
        """Handle mouse leaving the item area.

        Clears hover state and triggers repaint to remove visual feedback.

        Args:
            _event: Qt hover event (unused but required by signature)
        """
        self._is_hovered = False
        self.update()  # Trigger repaint to remove hover visual

    # ==========================================================================
    # Item State Change Handler
    # ==========================================================================

    def itemChange(
        self,
        change: QGraphicsItem.GraphicsItemChange,
        value: object,
    ) -> object:
        """Handle item state changes (selection, position, etc.).

        This method is called by Qt whenever an item property changes.
        Currently handles:
        - Selection state changes: Could emit signals for property panels
        - Position changes: Could update connected nets (future)

        Args:
            change: Type of change (ItemSelectedChange, ItemPositionChange, etc.)
            value: New value for the changed property

        Returns:
            The value to use (may be modified from input)
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            # Selection is changing - trigger update for visual feedback
            self.update()
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # Position is changing - future: update connected net routes
            pass

        return super().itemChange(change, value)

    # ==========================================================================
    # Public API Methods
    # ==========================================================================

    def set_position(self, x: float, y: float) -> None:
        """Set the cell position in scene coordinates.

        Convenience method that wraps setPos for a cleaner API.
        Position is the top-left corner of the cell body.

        Args:
            x: X coordinate in scene units
            y: Y coordinate in scene units

        Example:
            >>> cell_item.set_position(100.0, 200.0)
        """
        self.setPos(QPointF(x, y))

    def get_cell(self) -> Cell:
        """Return the associated domain cell entity.

        Provides access to the underlying Cell for property queries,
        such as displaying cell properties in a property panel.

        Returns:
            The Cell domain entity this item visualizes

        Example:
            >>> cell = cell_item.get_cell()
            >>> print(f"Cell type: {cell.cell_type}")
        """
        return self._cell

    def __repr__(self) -> str:
        """Return string representation for debugging.

        Returns:
            String like: CellItem(name='U1', type='AND2_X1', pos=(100.0, 200.0))
        """
        pos = self.pos()
        return (
            f"CellItem(name={self._cell.name!r}, type={self._cell.cell_type!r}, "
            f"pos=({pos.x()}, {pos.y()}))"
        )
