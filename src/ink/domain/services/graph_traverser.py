"""GraphTraverser protocol for domain-level graph traversal operations.

This module defines the GraphTraverser protocol, which abstracts graph
traversal operations from the underlying graph library implementation.
This enables testability and future library migration (e.g., to rustworkx).

Architecture:
    Layer: Domain Layer (Protocol Interface)
    Pattern: Dependency Inversion Principle
    Purpose: Domain defines the interface, infrastructure implements it

The protocol defines operations needed by application services:
- Connectivity queries: cells on a net, pins of a cell, net of a pin
- Fanin/fanout traversal: with configurable hop count and sequential boundaries
- Path finding: shortest path between cells

All methods return domain entities (Cell, Pin, Net), not raw graph nodes,
maintaining clean separation between domain and infrastructure layers.

Example:
    >>> from ink.domain.services import GraphTraverser
    >>> from ink.infrastructure.graph import NetworkXGraphTraverser
    >>>
    >>> # Use dependency injection with protocol
    >>> def expand_fanout(traverser: GraphTraverser, cell_id: CellId, hops: int):
    ...     return traverser.get_fanout_cells(cell_id, hops=hops)
    >>>
    >>> # Infrastructure provides implementation
    >>> traverser: GraphTraverser = NetworkXGraphTraverser(graph, design)
    >>> cells = expand_fanout(traverser, CellId("XI1"), hops=2)

See Also:
    - ink.infrastructure.graph.NetworkXGraphTraverser: NetworkX implementation
    - docs/architecture/ddd-architecture.md: DDD design patterns
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ink.domain.model import Cell, Net, Pin
    from ink.domain.value_objects.identifiers import CellId, NetId, PinId


@runtime_checkable
class GraphTraverser(Protocol):
    """Domain service protocol for graph traversal operations.

    This protocol defines the interface for graph-based connectivity queries
    used by application services (expansion, selection, search). The protocol
    enables dependency inversion: domain layer defines the interface, and
    infrastructure layer provides the implementation.

    All methods return domain entities (Cell, Pin, Net), not raw graph nodes.
    This maintains a clean separation between domain concepts and infrastructure
    implementation details.

    Key Design Decisions:
        1. Protocol (not ABC): Uses structural typing (duck typing with hints)
        2. Runtime checkable: Supports isinstance/issubclass at runtime
        3. List returns: Returns List[Entity] for simplicity (not iterators)
        4. Optional params: stop_at_sequential defaults to False
        5. None for missing: Returns None/empty list for missing entities

    Methods:
        get_connected_cells: Get all cells connected to a net
        get_cell_pins: Get all pins of a cell
        get_pin_net: Get the net connected to a pin
        get_fanout_cells: Get downstream cells with hop count
        get_fanin_cells: Get upstream cells with hop count
        get_fanout_from_pin: Get fanout from a specific pin
        get_fanin_to_pin: Get fanin to a specific pin
        find_path: Find shortest path between cells

    Example:
        >>> class MockTraverser:
        ...     def get_connected_cells(self, net_id): return []
        ...     def get_cell_pins(self, cell_id): return []
        ...     # ... other methods
        >>>
        >>> traverser: GraphTraverser = MockTraverser()  # Structural typing
    """

    def get_connected_cells(self, net_id: NetId) -> list[Cell]:
        """Get all cells connected to a net.

        Returns cells that have pins connected to the specified net.
        This includes cells with both input and output pins on the net.

        Args:
            net_id: Unique identifier of the net to query.

        Returns:
            List of Cell entities connected to the net.
            Empty list if net doesn't exist or has no connected cells.

        Example:
            >>> cells = traverser.get_connected_cells(NetId("clk"))
            >>> for cell in cells:
            ...     print(f"{cell.name} is connected to clk")
        """
        ...

    def get_cell_pins(self, cell_id: CellId) -> list[Pin]:
        """Get all pins of a cell.

        Returns pins in the order they were added to the cell.
        This includes input, output, and inout pins.

        Args:
            cell_id: Unique identifier of the cell.

        Returns:
            List of Pin entities belonging to the cell.
            Empty list if cell doesn't exist.

        Example:
            >>> pins = traverser.get_cell_pins(CellId("XFF1"))
            >>> for pin in pins:
            ...     print(f"{pin.name}: {pin.direction}")
        """
        ...

    def get_pin_net(self, pin_id: PinId) -> Net | None:
        """Get the net connected to a pin.

        Returns the net that the specified pin is connected to.
        Floating pins (not connected) return None.

        Args:
            pin_id: Unique identifier of the pin.

        Returns:
            Net entity if pin is connected, None if floating or pin not found.

        Example:
            >>> net = traverser.get_pin_net(PinId("XI1.Y"))
            >>> if net:
            ...     print(f"Pin drives {net.name}")
        """
        ...

    def get_fanout_cells(
        self,
        cell_id: CellId,
        hops: int = 1,
        stop_at_sequential: bool = False,
    ) -> list[Cell]:
        """Get fanout cells (downstream) from a cell.

        Performs breadth-first traversal from the cell's output pins,
        following signal flow through nets to receiving cells.

        The starting cell is NOT included in the results.

        Args:
            cell_id: Starting cell for fanout traversal.
            hops: Number of hops to traverse (1 = immediate fanout).
                Must be positive; 0 or negative returns empty list.
            stop_at_sequential: If True, stop traversal at sequential cells
                (flip-flops, latches). Sequential cells are included in
                results but their fanout is not expanded.

        Returns:
            List of cells reachable within specified hops.
            Empty list if cell doesn't exist or has no fanout.

        Example:
            >>> # Get immediate fanout
            >>> fanout = traverser.get_fanout_cells(CellId("XI1"), hops=1)
            >>>
            >>> # Get 2-hop fanout, stopping at flip-flops
            >>> fanout = traverser.get_fanout_cells(
            ...     CellId("XI1"),
            ...     hops=2,
            ...     stop_at_sequential=True
            ... )
        """
        ...

    def get_fanin_cells(
        self,
        cell_id: CellId,
        hops: int = 1,
        stop_at_sequential: bool = False,
    ) -> list[Cell]:
        """Get fanin cells (upstream) to a cell.

        Performs breadth-first traversal from the cell's input pins,
        following signal flow backwards through nets to driving cells.

        The starting cell is NOT included in the results.

        Args:
            cell_id: Starting cell for fanin traversal.
            hops: Number of hops to traverse (1 = immediate fanin).
                Must be positive; 0 or negative returns empty list.
            stop_at_sequential: If True, stop traversal at sequential cells
                (flip-flops, latches). Sequential cells are included in
                results but their fanin is not expanded.

        Returns:
            List of cells reachable within specified hops.
            Empty list if cell doesn't exist or has no fanin.

        Example:
            >>> # Get immediate fanin
            >>> fanin = traverser.get_fanin_cells(CellId("XI3"), hops=1)
            >>>
            >>> # Get 2-hop fanin, stopping at flip-flops
            >>> fanin = traverser.get_fanin_cells(
            ...     CellId("XI3"),
            ...     hops=2,
            ...     stop_at_sequential=True
            ... )
        """
        ...

    def get_fanout_from_pin(
        self,
        pin_id: PinId,
        hops: int = 1,
        stop_at_sequential: bool = False,
    ) -> list[Cell]:
        """Get fanout cells from a specific pin.

        More precise than cell-based fanout - starts from a specific pin
        rather than all output pins of a cell. Useful for analyzing
        individual signal paths.

        Args:
            pin_id: Starting pin for fanout traversal.
            hops: Number of hops to traverse (1 = immediate fanout).
            stop_at_sequential: If True, stop at sequential cells.

        Returns:
            List of cells reachable from this pin.
            Empty list if pin doesn't exist.

        Example:
            >>> # Fanout from specific output pin
            >>> fanout = traverser.get_fanout_from_pin(PinId("XI1.Y"), hops=1)
        """
        ...

    def get_fanin_to_pin(
        self,
        pin_id: PinId,
        hops: int = 1,
        stop_at_sequential: bool = False,
    ) -> list[Cell]:
        """Get fanin cells to a specific pin.

        More precise than cell-based fanin - targets a specific pin
        rather than all input pins of a cell. Useful for analyzing
        individual signal paths.

        Args:
            pin_id: Target pin for fanin traversal.
            hops: Number of hops to traverse (1 = immediate fanin).
            stop_at_sequential: If True, stop at sequential cells.

        Returns:
            List of cells reachable to this pin.
            Empty list if pin doesn't exist.

        Example:
            >>> # Fanin to specific input pin
            >>> fanin = traverser.get_fanin_to_pin(PinId("XI3.A"), hops=1)
        """
        ...

    def find_path(
        self,
        from_cell_id: CellId,
        to_cell_id: CellId,
        max_hops: int = 10,
    ) -> list[Cell] | None:
        """Find shortest path between two cells.

        Uses graph shortest-path algorithm to find the minimum-hop path
        between two cells. Path includes both start and end cells.

        Args:
            from_cell_id: Starting cell of the path.
            to_cell_id: Target cell of the path.
            max_hops: Maximum path length to search. If shortest path
                exceeds this limit, returns None.

        Returns:
            List of cells forming the path (including start and end),
            or None if no path exists within max_hops.

        Example:
            >>> path = traverser.find_path(
            ...     CellId("XINPUT"),
            ...     CellId("XOUTPUT"),
            ...     max_hops=20
            ... )
            >>> if path:
            ...     print(" -> ".join(cell.name for cell in path))
        """
        ...
