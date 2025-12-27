"""Symbol Layout Calculator for pin positioning on cell symbols.

This module provides the SymbolLayoutCalculator class, which calculates pin
positions on cell symbol edges for schematic rendering. The calculator handles:
- Pin placement based on direction (INPUT=left, OUTPUT/INOUT=right)
- Even distribution of multiple pins along each edge
- Dynamic cell height adjustment for many pins
- Connection point calculation for net routing

Architecture Notes:
    - Lives in the presentation layer (part of the canvas subsystem)
    - Works with domain entities (Cell, Pin) but contains no domain logic
    - Follows the spec E02-F01-T03 requirements

Algorithm Overview:
    1. Separate pins by direction (INPUT vs OUTPUT/INOUT)
    2. Calculate available edge height (cell_height - 2 * margin)
    3. Distribute pins evenly along edges:
       - Single pin: Center of available space
       - Multiple pins: Even spacing with formula spacing = height / (count + 1)
    4. Adjust cell height if pins exceed minimum spacing requirements

Usage Example:
    >>> from ink.presentation.canvas.symbol_layout_calculator import (
    ...     SymbolLayoutCalculator
    ... )
    >>> calculator = SymbolLayoutCalculator()
    >>> layouts = calculator.calculate_pin_layouts(cell, design)
    >>> for pin_id, layout in layouts.items():
    ...     print(f"{pin_id}: {layout.side} edge at y={layout.position.y()}")

See Also:
    - Spec E02-F01-T03 for detailed requirements
    - src/ink/domain/model/cell.py for Cell domain entity
    - src/ink/domain/model/pin.py for Pin domain entity
    - src/ink/presentation/canvas/cell_item.py for CellItem graphics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF, QRectF

from ink.domain.value_objects.pin_direction import PinDirection

if TYPE_CHECKING:
    from ink.domain.model.cell import Cell
    from ink.domain.model.design import Design
    from ink.domain.model.pin import Pin


@dataclass(frozen=True, slots=True)
class PinLayout:
    """Position information for a single pin on a cell symbol.

    PinLayout is an immutable value object that stores the calculated position
    data for a pin. It provides both relative position (for placing pin graphics
    within the cell) and absolute connection point (for net routing).

    Attributes:
        pin_id: Unique identifier for the pin (e.g., "U1.A", "XFF1.CLK").
            This matches the Pin entity's id field.
        position: Position relative to the cell's origin (top-left corner).
            For left edge pins: x=0, y=calculated position
            For right edge pins: x=cell_width, y=calculated position
            Used by PinItem.setPos() to position the pin graphic.
        connection_point: Absolute scene coordinate for net routing.
            Calculated as: cell_scene_position + position
            Used by net routing algorithms to determine wire endpoints.
        side: Which edge of the cell the pin is on.
            Valid values: "left", "right", "top", "bottom"
            Currently only "left" and "right" are used (for INPUT/OUTPUT).

    Example:
        >>> layout = PinLayout(
        ...     pin_id="U1.A",
        ...     position=QPointF(0.0, 30.0),
        ...     connection_point=QPointF(100.0, 230.0),
        ...     side="left"
        ... )
        >>> layout.position.y()  # Pin is 30px from top on left edge
        30.0

    Note:
        This class is frozen (immutable) for safe sharing and caching.
        All fields are required - there are no default values.
    """

    pin_id: str
    position: QPointF
    connection_point: QPointF
    side: str


class SymbolLayoutCalculator:
    """Calculate pin positions on cell symbol edges for schematic rendering.

    SymbolLayoutCalculator takes a Cell domain entity and its Design context,
    then computes where each pin should be positioned on the cell symbol.
    The calculator follows these rules:

    - INPUT pins are placed on the left edge
    - OUTPUT and INOUT pins are placed on the right edge
    - Multiple pins on the same edge are evenly distributed
    - A single pin is centered on its edge
    - Cell height is automatically increased if pins exceed capacity

    The distribution algorithm uses the formula:
        spacing = available_height / (pin_count + 1)
        y_position = margin + (index + 1) * spacing

    This ensures pins are never at the exact edge margins and are evenly
    spaced with equal gaps between them and from the top/bottom margins.

    Class Constants:
        DEFAULT_CELL_WIDTH: Standard cell width in pixels (120.0)
        DEFAULT_CELL_HEIGHT: Standard cell height in pixels (80.0)
        MIN_PIN_SPACING: Minimum vertical spacing between pins (15.0)
        PIN_MARGIN: Top/bottom margin for pin placement (10.0)

    Attributes:
        _cell_width: Width of the cell symbol
        _cell_height: Height of the cell symbol

    Example:
        >>> calculator = SymbolLayoutCalculator()
        >>> layouts = calculator.calculate_pin_layouts(cell, design)
        >>> for pin_id, layout in layouts.items():
        ...     pin_item = PinItem(design.get_pin(pin_id))
        ...     pin_item.setPos(layout.position)

    See Also:
        - PinLayout: Value object returned by calculate_pin_layouts
        - CellItem: Graphics item that uses calculated dimensions
        - PinItem: Graphics item that uses calculated positions
    """

    # =========================================================================
    # Class Constants - Geometry Configuration
    # =========================================================================
    # These values define the default cell symbol dimensions and pin spacing.
    # They match the spec requirements in E02-F01-T03.

    DEFAULT_CELL_WIDTH: float = 120.0
    """Default cell width in pixels. Matches CellItem.DEFAULT_WIDTH."""

    DEFAULT_CELL_HEIGHT: float = 80.0
    """Default cell height in pixels. Matches CellItem.DEFAULT_HEIGHT."""

    MIN_PIN_SPACING: float = 15.0
    """Minimum vertical spacing between adjacent pins.

    If pins would be closer than this, the cell height is increased.
    15px provides readable spacing at default zoom levels.
    """

    PIN_MARGIN: float = 10.0
    """Top and bottom margin for pin placement.

    Pins are never placed within this margin from the cell edges.
    This creates visual balance and room for pin labels.
    """

    def __init__(
        self,
        cell_width: float = DEFAULT_CELL_WIDTH,
        cell_height: float = DEFAULT_CELL_HEIGHT,
    ) -> None:
        """Initialize calculator with cell dimensions.

        Args:
            cell_width: Width of the cell symbol in pixels.
                Defaults to DEFAULT_CELL_WIDTH (120.0).
            cell_height: Height of the cell symbol in pixels.
                Defaults to DEFAULT_CELL_HEIGHT (80.0).

        Example:
            >>> calc = SymbolLayoutCalculator()  # Use defaults
            >>> calc = SymbolLayoutCalculator(150.0, 100.0)  # Custom size
        """
        self._cell_width = cell_width
        self._cell_height = cell_height

    def calculate_pin_layouts(
        self,
        cell: Cell,
        design: Design,
        cell_scene_pos: QPointF | None = None,
    ) -> dict[str, PinLayout]:
        """Calculate positions for all pins on a cell.

        This is the main entry point for layout calculation. It:
        1. Retrieves Pin entities from the Design using the Cell's pin_ids
        2. Separates pins by direction (INPUT vs OUTPUT/INOUT)
        3. Distributes pins evenly along their respective edges
        4. Creates PinLayout objects with relative and absolute positions

        Args:
            cell: Domain Cell entity containing pin IDs.
                Must have valid pin_ids that exist in the design.
            design: Design aggregate containing Pin entities.
                Used to look up Pin objects by ID for direction info.
            cell_scene_pos: Position of the cell in scene coordinates.
                Used to calculate connection_point values.
                Defaults to QPointF(0, 0) if not provided.

        Returns:
            Dictionary mapping pin_id strings to PinLayout objects.
            Keys are the string representation of PinId (e.g., "U1.A").
            Empty dict if the cell has no pins.

        Example:
            >>> layouts = calculator.calculate_pin_layouts(
            ...     cell, design, QPointF(100, 200)
            ... )
            >>> layouts["U1.A"].side
            'left'
            >>> layouts["U1.Y"].position.x()
            120.0  # Right edge

        Note:
            If a pin_id in cell.pin_ids is not found in the design,
            it is silently skipped. This handles incomplete designs
            during incremental parsing.
        """
        if cell_scene_pos is None:
            cell_scene_pos = QPointF(0.0, 0.0)

        # Early return for cells with no pins
        if not cell.pin_ids:
            return {}

        # Collect pins from design and separate by direction
        # INPUT pins go on left edge, OUTPUT/INOUT pins go on right edge
        input_pins: list[Pin] = []
        output_pins: list[Pin] = []

        for pin_id in cell.pin_ids:
            pin = design.get_pin(pin_id)
            if pin is None:
                # Skip pins not found in design (incomplete data)
                continue

            # Determine edge placement based on direction
            # INPUT -> left edge, OUTPUT/INOUT -> right edge
            if pin.direction == PinDirection.INPUT:
                input_pins.append(pin)
            else:  # OUTPUT or INOUT
                output_pins.append(pin)

        # Create cell rectangle for position calculations
        cell_rect = QRectF(0, 0, self._cell_width, self._cell_height)

        # Calculate layouts for each edge
        result: dict[str, PinLayout] = {}

        # Process left edge (INPUT pins)
        left_layouts = self._distribute_pins_on_edge(
            input_pins, "left", cell_rect
        )
        for layout in left_layouts:
            # Calculate connection point in scene coordinates
            connection_point = QPointF(
                cell_scene_pos.x() + layout.position.x(),
                cell_scene_pos.y() + layout.position.y(),
            )
            # Create new layout with connection point
            result[layout.pin_id] = PinLayout(
                pin_id=layout.pin_id,
                position=layout.position,
                connection_point=connection_point,
                side=layout.side,
            )

        # Process right edge (OUTPUT and INOUT pins)
        right_layouts = self._distribute_pins_on_edge(
            output_pins, "right", cell_rect
        )
        for layout in right_layouts:
            connection_point = QPointF(
                cell_scene_pos.x() + layout.position.x(),
                cell_scene_pos.y() + layout.position.y(),
            )
            result[layout.pin_id] = PinLayout(
                pin_id=layout.pin_id,
                position=layout.position,
                connection_point=connection_point,
                side=layout.side,
            )

        return result

    def _distribute_pins_on_edge(
        self,
        pins: list[Pin],
        edge_side: str,
        cell_rect: QRectF,
    ) -> list[PinLayout]:
        """Evenly distribute pins along a cell edge.

        Calculates vertical positions for pins on the specified edge,
        spacing them evenly within the available height (accounting for
        top and bottom margins).

        Distribution Algorithm:
            - Single pin: Centered at cell_height / 2
            - Multiple pins:
                available = cell_height - 2 * margin
                spacing = available / (count + 1)
                y[i] = margin + (i + 1) * spacing

        This creates equal spacing between:
            - Top margin and first pin
            - Each pair of adjacent pins
            - Last pin and bottom margin

        Args:
            pins: List of Pin entities to distribute.
                Order is preserved in the output.
            edge_side: Which edge to place pins on.
                "left" for INPUT pins (x=0)
                "right" for OUTPUT/INOUT pins (x=cell_width)
            cell_rect: Rectangle defining cell boundaries.
                Width determines x position for right edge.
                Height determines available vertical space.

        Returns:
            List of PinLayout objects with calculated positions.
            Order matches the input pins list.

        Note:
            Connection points in returned layouts are set equal to
            positions. The caller (calculate_pin_layouts) updates
            them with scene coordinates.
        """
        if not pins:
            return []

        layouts: list[PinLayout] = []

        # Calculate vertical positions for each pin
        for i, pin in enumerate(pins):
            position = self._calculate_pin_position(
                edge_side, i, len(pins), cell_rect
            )

            # Create layout with position (connection_point = position for now)
            layout = PinLayout(
                pin_id=str(pin.id),
                position=position,
                connection_point=position,  # Updated by caller
                side=edge_side,
            )
            layouts.append(layout)

        return layouts

    def _calculate_pin_position(
        self,
        edge_side: str,
        index: int,
        total_pins: int,
        cell_rect: QRectF,
    ) -> QPointF:
        """Calculate position for a single pin on an edge.

        Uses the even distribution formula to compute the y-coordinate:
            - Single pin (total_pins=1): y = height / 2 (centered)
            - Multiple pins:
                available = height - 2 * margin
                spacing = available / (total_pins + 1)
                y = margin + (index + 1) * spacing

        Args:
            edge_side: "left" or "right" - determines x coordinate.
            index: Zero-based index of this pin among pins on the edge.
            total_pins: Total number of pins on this edge.
            cell_rect: Rectangle defining cell dimensions.

        Returns:
            QPointF with calculated (x, y) position relative to cell origin.

        Example:
            For 3 pins on left edge of 80px tall cell (margin=10):
                available = 80 - 20 = 60
                spacing = 60 / 4 = 15
                y[0] = 10 + 15 = 25
                y[1] = 10 + 30 = 40
                y[2] = 10 + 45 = 55

        Note:
            The formula ensures pins are never placed exactly at the
            margin boundary - there's always spacing on both sides.
        """
        # Calculate x based on edge side
        x_pos = 0.0 if edge_side == "left" else cell_rect.width()

        # Calculate y position
        if total_pins == 1:
            # Single pin: center vertically
            y_pos = cell_rect.height() / 2.0
        else:
            # Multiple pins: distribute evenly within available space
            # Formula explained in docstring and spec E02-F01-T03
            available_height = cell_rect.height() - (2 * self.PIN_MARGIN)
            spacing = available_height / (total_pins + 1)
            y_pos = self.PIN_MARGIN + (index + 1) * spacing

        return QPointF(x_pos, y_pos)

    def adjust_cell_height_for_pins(
        self,
        input_count: int,
        output_count: int,
    ) -> float:
        """Calculate required cell height based on pin counts.

        If either edge has too many pins to fit with MIN_PIN_SPACING,
        the cell height is increased to accommodate them. The formula:
            required = max_count * MIN_PIN_SPACING + 2 * PIN_MARGIN

        Args:
            input_count: Number of INPUT pins (left edge).
            output_count: Number of OUTPUT/INOUT pins (right edge).

        Returns:
            Cell height in pixels. Returns DEFAULT_CELL_HEIGHT if
            the default can accommodate the pins, otherwise returns
            the calculated required height.

        Example:
            >>> calc = SymbolLayoutCalculator()
            >>> calc.adjust_cell_height_for_pins(6, 6)
            80.0  # Default is sufficient
            >>> calc.adjust_cell_height_for_pins(10, 1)
            170.0  # 10 * 15 + 20 = 170

        Note:
            The calculation is based on the edge with the most pins.
            This ensures both edges have adequate spacing.
        """
        # Use the edge with more pins
        max_pin_count = max(input_count, output_count)

        # Calculate minimum required height
        # Each pin needs MIN_PIN_SPACING, plus margins at top and bottom
        required_height = (
            max_pin_count * self.MIN_PIN_SPACING + 2 * self.PIN_MARGIN
        )

        # Return default if it's sufficient, otherwise return required
        return max(self._cell_height, required_height)
