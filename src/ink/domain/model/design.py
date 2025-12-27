"""Design aggregate root for the domain layer.

This module defines the Design class, which serves as the aggregate root for
managing all domain entities in a netlist: Cell, Pin, Net, and Port.

Following Domain-Driven Design (DDD) principles, the Design aggregate:
- Acts as the single entry point for all netlist data operations
- Manages entity collections with O(1) lookup by ID and name
- Enforces domain invariants (no duplicate IDs/names, valid references)
- Provides validation for referential integrity

Architecture:
    The Design class lives in the domain layer with no external dependencies
    outside the domain. It is created by infrastructure parsers and consumed
    by application services for graph building and schematic rendering.

    Layer: Domain Layer (Pure)
    Bounded Context: Netlist Context
    Pattern: Aggregate Root

Key Design Decisions:
    1. Mutable Aggregate: Design is mutable to support incremental construction
       during parsing. Entities themselves are immutable (frozen dataclasses).

    2. Dual Index Strategy:
       - Primary storage: Dict[EntityId, Entity] for O(1) ID lookup
       - Secondary index: Dict[str, EntityId] for O(1) name lookup
       - Indexes updated atomically on add operations

    3. Hybrid Validation:
       - Eager: Duplicate detection on add_*() methods (fail fast)
       - Lazy: Referential integrity via validate() method (after construction)

    4. Immutable Views: Collection accessors return list copies to prevent
       accidental modification of internal state.

Example:
    >>> from ink.domain.model.design import Design
    >>> from ink.domain.model.cell import Cell
    >>> from ink.domain.value_objects.identifiers import CellId
    >>>
    >>> # Create a design and add entities
    >>> design = Design(name="top_module")
    >>> cell = Cell(id=CellId("XI1"), name="XI1", cell_type="INV_X1")
    >>> design.add_cell(cell)
    >>>
    >>> # Query the design
    >>> design.cell_count()
    1
    >>> design.get_cell_by_name("XI1")
    Cell(id='XI1', name='XI1', type='INV_X1', pins=0, seq=False)
    >>>
    >>> # Validate referential integrity
    >>> errors = design.validate()
    >>> if not errors:
    ...     print("Design is valid")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink.domain.model.cell import Cell
    from ink.domain.model.net import Net
    from ink.domain.model.pin import Pin
    from ink.domain.model.port import Port
    from ink.domain.value_objects.identifiers import CellId, NetId, PinId, PortId


@dataclass
class Design:
    """Aggregate root managing all netlist entities.

    Design is the central entry point for all netlist operations. It manages
    collections of cells, nets, pins, and ports, enforcing consistency rules
    and providing efficient lookup operations.

    The aggregate maintains two levels of indexing:
    - Primary: Entity ID → Entity (for O(1) lookup by typed ID)
    - Secondary: Name → Entity ID (for O(1) lookup by name string)

    This dual indexing allows efficient access patterns commonly used in
    schematic exploration: looking up cells by instance name, nets by
    signal name, or ports by interface name.

    Attributes:
        name: Design or subcircuit name (e.g., "top_module", "inverter_chain")

    Private Attributes:
        _cells: Primary storage for cells indexed by CellId
        _nets: Primary storage for nets indexed by NetId
        _pins: Primary storage for pins indexed by PinId
        _ports: Primary storage for ports indexed by PortId
        _cell_name_index: Secondary index for cell name → CellId lookup
        _net_name_index: Secondary index for net name → NetId lookup
        _port_name_index: Secondary index for port name → PortId lookup

    Note:
        Pins do not have a name index because pin names are only unique
        within a cell (e.g., many cells have an "A" pin). Pin lookup is
        done by full PinId (e.g., "XI1.A") or via the cell.

    Example:
        >>> design = Design(name="inverter")
        >>> design.add_cell(Cell(id=CellId("XI1"), name="XI1", cell_type="INV"))
        >>> design.cell_count()
        1
        >>> design.get_cell_by_name("XI1")
        Cell(...)
    """

    # Design name (from filename or explicit)
    name: str

    # =========================================================================
    # Primary Storage: Entity ID → Entity (O(1) lookup by ID)
    # =========================================================================

    # Cell instances indexed by CellId
    _cells: dict[CellId, Cell] = field(default_factory=dict, repr=False)

    # Nets indexed by NetId
    _nets: dict[NetId, Net] = field(default_factory=dict, repr=False)

    # Pins indexed by PinId
    _pins: dict[PinId, Pin] = field(default_factory=dict, repr=False)

    # Ports indexed by PortId
    _ports: dict[PortId, Port] = field(default_factory=dict, repr=False)

    # =========================================================================
    # Secondary Indexes: Name → Entity ID (O(1) lookup by name)
    # =========================================================================

    # Cell name → CellId (cell instance names are globally unique)
    _cell_name_index: dict[str, CellId] = field(default_factory=dict, repr=False)

    # Net name → NetId (net names are globally unique)
    _net_name_index: dict[str, NetId] = field(default_factory=dict, repr=False)

    # Port name → PortId (port names are globally unique)
    _port_name_index: dict[str, PortId] = field(default_factory=dict, repr=False)

    # Note: No pin name index - pin names only unique within cell context
    # (e.g., many cells have "A" pin). Access pins via cell + pin_id.

    # =========================================================================
    # Cell Management
    # =========================================================================

    def add_cell(self, cell: Cell) -> None:
        """Add a cell to the design.

        Validates that both the cell ID and name are unique before adding.
        Updates both primary storage and name index atomically.

        This method performs eager validation to fail fast on duplicates,
        preventing corrupt state in the aggregate.

        Args:
            cell: The Cell entity to add. Both cell.id and cell.name must
                  be unique within this design.

        Raises:
            ValueError: If a cell with the same ID already exists.
            ValueError: If a cell with the same name already exists.

        Example:
            >>> design = Design(name="test")
            >>> cell = Cell(id=CellId("XI1"), name="XI1", cell_type="INV_X1")
            >>> design.add_cell(cell)
            >>> design.cell_count()
            1

        Note:
            ID uniqueness is checked first, then name uniqueness. If both
            are violated, only the ID error is raised.
        """
        # Eager validation: check for duplicate ID first
        if cell.id in self._cells:
            raise ValueError(f"Cell with id {cell.id} already exists")

        # Check for duplicate name in the index
        if cell.name in self._cell_name_index:
            raise ValueError(f"Cell with name {cell.name} already exists")

        # Add to primary storage and update name index atomically
        self._cells[cell.id] = cell
        self._cell_name_index[cell.name] = cell.id

    def get_cell(self, cell_id: CellId) -> Cell | None:
        """Get cell by ID with O(1) lookup.

        Args:
            cell_id: The unique identifier of the cell to retrieve.

        Returns:
            The Cell entity if found, None otherwise.

        Example:
            >>> cell = design.get_cell(CellId("XI1"))
            >>> if cell:
            ...     print(f"Found: {cell.cell_type}")
        """
        return self._cells.get(cell_id)

    def get_cell_by_name(self, name: str) -> Cell | None:
        """Get cell by instance name with O(1) lookup via index.

        Uses the secondary name index for fast lookup, then retrieves
        the entity from primary storage.

        Args:
            name: The instance name of the cell (e.g., "XI1", "XFF1").

        Returns:
            The Cell entity if found, None otherwise.

        Example:
            >>> cell = design.get_cell_by_name("XI1")
            >>> if cell:
            ...     print(f"Cell type: {cell.cell_type}")
        """
        cell_id = self._cell_name_index.get(name)
        return self._cells.get(cell_id) if cell_id else None

    def get_all_cells(self) -> list[Cell]:
        """Get all cells in the design.

        Returns a copy of the cell list to prevent modification of
        internal storage. The caller can safely modify the returned list.

        Returns:
            List of all Cell entities. Empty list if no cells exist.

        Example:
            >>> cells = design.get_all_cells()
            >>> for cell in cells:
            ...     print(cell.name)
        """
        return list(self._cells.values())

    def cell_count(self) -> int:
        """Get total number of cells in the design.

        Returns:
            Number of cells (0 or more).
        """
        return len(self._cells)

    def sequential_cell_count(self) -> int:
        """Get number of sequential cells (flip-flops, latches).

        Counts cells where is_sequential is True. Sequential cells are
        important for schematic exploration as expansion boundaries.

        Returns:
            Number of sequential cells (0 or more).

        Example:
            >>> design.sequential_cell_count()
            5  # 5 flip-flops or latches in the design
        """
        return sum(1 for cell in self._cells.values() if cell.is_sequential)

    # =========================================================================
    # Net Management
    # =========================================================================

    def add_net(self, net: Net) -> None:
        """Add a net to the design.

        Validates that both the net ID and name are unique before adding.
        Updates both primary storage and name index atomically.

        Args:
            net: The Net entity to add. Both net.id and net.name must
                 be unique within this design.

        Raises:
            ValueError: If a net with the same ID already exists.
            ValueError: If a net with the same name already exists.

        Example:
            >>> design = Design(name="test")
            >>> net = Net(id=NetId("clk"), name="clk")
            >>> design.add_net(net)
        """
        # Eager validation: check for duplicate ID
        if net.id in self._nets:
            raise ValueError(f"Net with id {net.id} already exists")

        # Check for duplicate name
        if net.name in self._net_name_index:
            raise ValueError(f"Net with name {net.name} already exists")

        # Add to storage and index
        self._nets[net.id] = net
        self._net_name_index[net.name] = net.id

    def get_net(self, net_id: NetId) -> Net | None:
        """Get net by ID with O(1) lookup.

        Args:
            net_id: The unique identifier of the net to retrieve.

        Returns:
            The Net entity if found, None otherwise.
        """
        return self._nets.get(net_id)

    def get_net_by_name(self, name: str) -> Net | None:
        """Get net by name with O(1) lookup via index.

        Args:
            name: The net name (e.g., "clk", "data[7]").

        Returns:
            The Net entity if found, None otherwise.
        """
        net_id = self._net_name_index.get(name)
        return self._nets.get(net_id) if net_id else None

    def get_all_nets(self) -> list[Net]:
        """Get all nets in the design.

        Returns a copy of the net list to prevent modification of
        internal storage.

        Returns:
            List of all Net entities. Empty list if no nets exist.
        """
        return list(self._nets.values())

    def net_count(self) -> int:
        """Get total number of nets in the design.

        Returns:
            Number of nets (0 or more).
        """
        return len(self._nets)

    # =========================================================================
    # Pin Management
    # =========================================================================

    def add_pin(self, pin: Pin) -> None:
        """Add a pin to the design.

        Validates that the pin ID is unique before adding. Pins do not
        have a name index because pin names are only unique within their
        parent cell (e.g., many cells have an "A" pin).

        Args:
            pin: The Pin entity to add. pin.id must be unique within
                 this design.

        Raises:
            ValueError: If a pin with the same ID already exists.

        Example:
            >>> pin = Pin(id=PinId("XI1.A"), name="A", direction=PinDirection.INPUT)
            >>> design.add_pin(pin)
        """
        # Check for duplicate ID only (no name index for pins)
        if pin.id in self._pins:
            raise ValueError(f"Pin with id {pin.id} already exists")

        self._pins[pin.id] = pin

    def get_pin(self, pin_id: PinId) -> Pin | None:
        """Get pin by ID with O(1) lookup.

        Args:
            pin_id: The unique identifier of the pin (e.g., "XI1.A").

        Returns:
            The Pin entity if found, None otherwise.
        """
        return self._pins.get(pin_id)

    def get_all_pins(self) -> list[Pin]:
        """Get all pins in the design.

        Returns a copy of the pin list to prevent modification of
        internal storage.

        Returns:
            List of all Pin entities. Empty list if no pins exist.
        """
        return list(self._pins.values())

    def pin_count(self) -> int:
        """Get total number of pins in the design.

        Returns:
            Number of pins (0 or more).
        """
        return len(self._pins)

    # =========================================================================
    # Port Management
    # =========================================================================

    def add_port(self, port: Port) -> None:
        """Add a port to the design.

        Validates that both the port ID and name are unique before adding.
        Updates both primary storage and name index atomically.

        Args:
            port: The Port entity to add. Both port.id and port.name must
                  be unique within this design.

        Raises:
            ValueError: If a port with the same ID already exists.
            ValueError: If a port with the same name already exists.

        Example:
            >>> port = Port(id=PortId("IN"), name="IN", direction=PinDirection.INPUT)
            >>> design.add_port(port)
        """
        # Eager validation
        if port.id in self._ports:
            raise ValueError(f"Port with id {port.id} already exists")

        if port.name in self._port_name_index:
            raise ValueError(f"Port with name {port.name} already exists")

        # Add to storage and index
        self._ports[port.id] = port
        self._port_name_index[port.name] = port.id

    def get_port(self, port_id: PortId) -> Port | None:
        """Get port by ID with O(1) lookup.

        Args:
            port_id: The unique identifier of the port.

        Returns:
            The Port entity if found, None otherwise.
        """
        return self._ports.get(port_id)

    def get_port_by_name(self, name: str) -> Port | None:
        """Get port by name with O(1) lookup via index.

        Args:
            name: The port name (e.g., "IN", "OUT", "DATA[7]").

        Returns:
            The Port entity if found, None otherwise.
        """
        port_id = self._port_name_index.get(name)
        return self._ports.get(port_id) if port_id else None

    def get_all_ports(self) -> list[Port]:
        """Get all ports in the design.

        Returns a copy of the port list to prevent modification of
        internal storage.

        Returns:
            List of all Port entities. Empty list if no ports exist.
        """
        return list(self._ports.values())

    def port_count(self) -> int:
        """Get total number of ports in the design.

        Returns:
            Number of ports (0 or more).
        """
        return len(self._ports)

    # =========================================================================
    # Validation
    # =========================================================================

    def validate(self) -> list[str]:
        """Validate design referential integrity.

        Performs lazy validation of all cross-entity references. This should
        be called after the design is fully constructed (e.g., after parsing)
        to ensure all references are valid.

        Validation Checks:
            1. Pin → Net: Each pin's net_id (if set) must reference an existing net
            2. Cell → Pin: Each cell's pin_ids must reference existing pins
            3. Net → Pin: Each net's connected_pin_ids must reference existing pins
            4. Port → Net: Each port's net_id (if set) must reference an existing net

        Returns:
            List of error messages. Empty list if design is valid.

        Example:
            >>> errors = design.validate()
            >>> if errors:
            ...     for error in errors:
            ...         print(f"Error: {error}")
            ... else:
            ...     print("Design is valid")
        """
        errors: list[str] = []

        # Check pin → net references
        for pin in self._pins.values():
            if pin.net_id is not None and pin.net_id not in self._nets:
                errors.append(
                    f"Pin {pin.id} references non-existent net {pin.net_id}"
                )

        # Check cell → pin references
        for cell in self._cells.values():
            for pin_id in cell.pin_ids:
                if pin_id not in self._pins:
                    errors.append(
                        f"Cell {cell.id} references non-existent pin {pin_id}"
                    )

        # Check net → pin references
        for net in self._nets.values():
            for pin_id in net.connected_pin_ids:
                if pin_id not in self._pins:
                    errors.append(
                        f"Net {net.id} references non-existent pin {pin_id}"
                    )

        # Check port → net references
        for port in self._ports.values():
            if port.net_id is not None and port.net_id not in self._nets:
                errors.append(
                    f"Port {port.id} references non-existent net {port.net_id}"
                )

        return errors

    # =========================================================================
    # String Representation
    # =========================================================================

    def __repr__(self) -> str:
        """Return detailed string representation for debugging.

        Returns:
            String showing design name and entity counts.

        Example:
            >>> repr(design)
            "Design(name='top', cells=100, nets=150, pins=400, ports=10)"
        """
        return (
            f"Design(name={self.name!r}, "
            f"cells={self.cell_count()}, "
            f"nets={self.net_count()}, "
            f"pins={self.pin_count()}, "
            f"ports={self.port_count()})"
        )

    def __str__(self) -> str:
        """Return human-readable summary of the design.

        Returns:
            Multi-line summary with design statistics.
        """
        return (
            f"Design: {self.name}\n"
            f"  Cells: {self.cell_count()} ({self.sequential_cell_count()} sequential)\n"
            f"  Nets: {self.net_count()}\n"
            f"  Pins: {self.pin_count()}\n"
            f"  Ports: {self.port_count()}"
        )
