"""Cell entity for the domain layer.

This module defines the Cell entity, which represents a gate-level cell instance
in a netlist. Cells are the fundamental building blocks of digital circuits,
including combinational gates (AND, OR, INV) and sequential elements (DFF, LATCH).

Each cell has:
- id: Unique identifier for the cell instance
- name: Instance name as it appears in the design
- cell_type: Reference to the cell type definition (e.g., "INV_X1", "DFF_X1")
- pin_ids: Tuple of pins on this cell
- is_sequential: Flag indicating if this is a flip-flop or latch

The Cell entity is immutable (frozen dataclass) following DDD patterns.

Architecture:
    This entity lives in the domain layer with no external dependencies.
    It is used by the Design aggregate and graph traversal services.

Example:
    >>> from ink.domain.model.cell import Cell
    >>> from ink.domain.value_objects.identifiers import CellId, PinId
    >>>
    >>> # Create a combinational cell (inverter)
    >>> inv = Cell(
    ...     id=CellId("XI1"),
    ...     name="XI1",
    ...     cell_type="INV_X1",
    ...     pin_ids=[PinId("XI1.A"), PinId("XI1.Y")],
    ...     is_sequential=False
    ... )
    >>> inv.is_latch()
    False
    >>>
    >>> # Create a sequential cell (flip-flop)
    >>> ff = Cell(
    ...     id=CellId("XFF1"),
    ...     name="XFF1",
    ...     cell_type="DFF_X1",
    ...     pin_ids=[PinId("XFF1.D"), PinId("XFF1.CLK"), PinId("XFF1.Q")],
    ...     is_sequential=True
    ... )
    >>> ff.is_latch()
    True
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ink.domain.value_objects.identifiers import CellId, PinId


@dataclass(frozen=True, slots=True)
class Cell:
    """Cell entity representing a gate-level cell instance.

    Cells are the fundamental building blocks of digital circuits. Each cell
    is an instance of a cell type (e.g., INV_X1, NAND2_X2) with specific pin
    connections. Cells can be combinational (no memory) or sequential
    (flip-flops, latches) which affects exploration behavior.

    This is a frozen dataclass, meaning:
    - All fields are immutable after creation
    - Instances are hashable (can be used in sets/dicts)
    - Equality is based on all field values

    Attributes:
        id: Unique identifier for this cell instance (e.g., "XI1", "XFF1").
            Format follows CDL conventions, typically starting with 'X'.
        name: Instance name as it appears in the design, typically same as id.
            For hierarchical instances: "XI_CORE/U_ALU/XI_ADD"
        cell_type: Reference to the cell type definition (e.g., "INV_X1").
            Must match a SubcircuitDefinition in the Design aggregate.
        pin_ids: Tuple of pin IDs for pins on this cell.
            An empty tuple means the cell has no pins (unusual but valid).
            Stored as tuple for complete immutability.
        is_sequential: True if this is a sequential element (flip-flop, latch).
            Sequential cells are used as expansion boundaries in schematic
            exploration to prevent traversing through clock domains.

    Example:
        >>> cell = Cell(
        ...     id=CellId("XI1"),
        ...     name="XI1",
        ...     cell_type="INV_X1",
        ...     pin_ids=[PinId("XI1.A"), PinId("XI1.Y")]
        ... )
        >>> cell.cell_type
        'INV_X1'
        >>> cell.is_latch()
        False
    """

    # Unique identifier for this cell instance
    id: CellId

    # Instance name as it appears in the design
    name: str

    # Reference to cell type definition (subcircuit name)
    cell_type: str

    # Pin IDs on this cell (stored as immutable tuple)
    pin_ids: tuple[PinId, ...]

    # True for sequential elements (flip-flops, latches)
    is_sequential: bool

    def __init__(
        self,
        id: CellId,
        name: str,
        cell_type: str,
        pin_ids: Sequence[PinId] | None = None,
        is_sequential: bool = False,
    ) -> None:
        """Initialize a Cell with the given attributes.

        This custom __init__ is needed to:
        1. Convert the input sequence to an immutable tuple
        2. Handle default values for optional parameters

        Args:
            id: Unique identifier for this cell instance.
            name: Instance name as it appears in the design.
            cell_type: Reference to the cell type definition.
            pin_ids: Sequence of pin IDs on this cell.
                Defaults to empty tuple if not provided.
            is_sequential: True for flip-flops and latches.
                Defaults to False (combinational).
        """
        # Use object.__setattr__ because frozen=True prevents normal assignment
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "cell_type", cell_type)

        # Convert to tuple for immutability, or use empty tuple if None
        if pin_ids is None:
            pin_tuple: tuple[PinId, ...] = ()
        else:
            pin_tuple = tuple(pin_ids)
        object.__setattr__(self, "pin_ids", pin_tuple)

        object.__setattr__(self, "is_sequential", is_sequential)

    def is_latch(self) -> bool:
        """Check if this cell is a sequential element (flip-flop or latch).

        Sequential cells are important for schematic exploration as they
        represent timing boundaries. Expansion typically stops at sequential
        elements to prevent traversing entire clock domains at once.

        This method is an alias for checking is_sequential, provided for
        semantic clarity in the domain language ("is this cell a latch?").

        Returns:
            True if this cell is a sequential element (is_sequential=True),
            False if this is a combinational cell.

        Example:
            >>> ff = Cell(id=CellId("XFF1"), name="XFF1",
            ...           cell_type="DFF_X1", is_sequential=True)
            >>> ff.is_latch()
            True
            >>>
            >>> inv = Cell(id=CellId("XI1"), name="XI1",
            ...            cell_type="INV_X1", is_sequential=False)
            >>> inv.is_latch()
            False
        """
        return self.is_sequential

    def __repr__(self) -> str:
        """Return detailed string representation for debugging.

        Returns:
            String like: Cell(id='XI1', name='XI1', type='INV_X1', pins=2, seq=False)
        """
        return (
            f"Cell(id={self.id!r}, name={self.name!r}, "
            f"type={self.cell_type!r}, pins={len(self.pin_ids)}, "
            f"seq={self.is_sequential})"
        )

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            String like: XI1 (INV_X1)
            or: XFF1 (DFF_X1) [sequential]
        """
        base = f"{self.name} ({self.cell_type})"
        if self.is_sequential:
            return f"{base} [sequential]"
        return base
