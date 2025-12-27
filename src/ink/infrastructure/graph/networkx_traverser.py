"""NetworkX-based implementation of GraphTraverser protocol.

This module provides the NetworkXGraphTraverser class, which implements
the GraphTraverser protocol using NetworkX as the underlying graph library.

Architecture:
    Layer: Infrastructure Layer
    Pattern: Adapter Pattern (adapts NetworkX to domain service interface)
    Implements: GraphTraverser protocol from domain layer

The traverser operates on a NetworkX MultiDiGraph built by NetworkXGraphBuilder
and uses the Design aggregate to resolve graph node IDs to domain entities.

Key Design Decisions:
    1. BFS Traversal: Uses breadth-first search for hop-counted queries
    2. Visited Tracking: Prevents infinite loops in cyclic graphs
    3. Entity Resolution: Converts graph node IDs to domain entities
    4. Sequential Boundaries: Respects is_sequential flag for expansion limits
    5. Edge Direction: Follows pin direction semantics (OUTPUT→Net, Net→INPUT)

Performance Characteristics:
    - get_connected_cells: O(k) where k = pins on net
    - get_cell_pins: O(k) where k = pins on cell
    - get_fanout/fanin: O(n) where n = cells visited
    - find_path: O(V + E) using NetworkX shortest_path

Example:
    >>> from ink.infrastructure.graph import NetworkXGraphBuilder, NetworkXGraphTraverser
    >>>
    >>> builder = NetworkXGraphBuilder()
    >>> graph = builder.build_from_design(design)
    >>> traverser = NetworkXGraphTraverser(graph, design)
    >>>
    >>> # Get 2-hop fanout from a cell
    >>> fanout = traverser.get_fanout_cells(
    ...     CellId("XI1"),
    ...     hops=2,
    ...     stop_at_sequential=True
    ... )

See Also:
    - ink.domain.services.GraphTraverser: Protocol definition
    - ink.infrastructure.graph.NetworkXGraphBuilder: Graph construction
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

from ink.domain.value_objects.identifiers import CellId, NetId, PinId

if TYPE_CHECKING:
    from ink.domain.model import Cell, Design, Net, Pin


class NetworkXGraphTraverser:
    """NetworkX-based implementation of GraphTraverser protocol.

    This class adapts NetworkX graph operations to the domain service
    interface defined by the GraphTraverser protocol. It performs graph
    traversals and returns domain entities (Cell, Pin, Net).

    The traverser requires:
    - A NetworkX MultiDiGraph built by NetworkXGraphBuilder
    - The Design aggregate for entity resolution (ID → Entity)

    Attributes:
        graph: The NetworkX MultiDiGraph to traverse
        design: The Design aggregate for entity lookups

    Implementation Notes:
        - Uses BFS (breadth-first search) for fanin/fanout traversal
        - Tracks visited cells to prevent cycles
        - Resolves graph node IDs to domain entities via Design aggregate
        - Respects pin direction for signal flow traversal
        - Handles sequential boundaries by checking Cell.is_sequential

    Example:
        >>> builder = NetworkXGraphBuilder()
        >>> graph = builder.build_from_design(design)
        >>> traverser = NetworkXGraphTraverser(graph, design)
        >>>
        >>> cells = traverser.get_connected_cells(NetId("clk"))
        >>> for cell in cells:
        ...     print(cell.name)
    """

    def __init__(  # type: ignore[no-any-unimported]
        self,
        graph: nx.MultiDiGraph,
        design: Design,
    ) -> None:
        """Initialize the traverser with graph and design.

        Args:
            graph: NetworkX MultiDiGraph built by NetworkXGraphBuilder.
                   Must have node_type and entity attributes on nodes.
            design: Design aggregate for resolving entity IDs to entities.
                   Used for lookups when entity attribute is missing.
        """
        self.graph = graph
        self.design = design

    # =========================================================================
    # Basic Connectivity Queries
    # =========================================================================

    def get_connected_cells(self, net_id: NetId) -> list[Cell]:
        """Get all cells connected to a net via pins.

        Finds all cells that have pins connected to the specified net.
        This includes cells with both input and output pins on the net.

        Algorithm:
            1. Find all edges from/to net_id with edge_type='drives'
            2. For each connected pin, find the parent cell
            3. Return unique cells (deduplicated by cell ID)

        Args:
            net_id: The net to find connected cells for.

        Returns:
            List of Cell entities connected to the net.
            Empty list if net doesn't exist or has no connections.
        """
        # Check if net exists in graph
        if net_id not in self.graph:
            return []

        cells: list[Cell] = []
        seen_cell_ids: set[CellId] = set()

        # Get pins connected to this net via "drives" edges
        # Net → Pin edges (net drives input pins)
        for _, pin_id, edge_data in self.graph.out_edges(net_id, data=True):
            if edge_data.get("edge_type") == "drives":
                self._add_cells_for_pin(pin_id, cells, seen_cell_ids)

        # Pin → Net edges (output pins drive net)
        for pin_id, _, edge_data in self.graph.in_edges(net_id, data=True):
            if edge_data.get("edge_type") == "drives":
                self._add_cells_for_pin(pin_id, cells, seen_cell_ids)

        return cells

    def _add_cells_for_pin(
        self,
        pin_id: str,
        cells: list[Cell],
        seen_cell_ids: set[CellId],
    ) -> None:
        """Add cells containing a pin to the results list.

        Helper method that finds cells containing a pin and adds them
        to the result list, avoiding duplicates.

        Args:
            pin_id: The pin ID to find parent cells for.
            cells: The result list to append cells to.
            seen_cell_ids: Set of already-seen cell IDs for deduplication.
        """
        # Find cells that contain this pin (Cell → Pin edges)
        for cell_id, _, edge_data in self.graph.in_edges(pin_id, data=True):
            if edge_data.get("edge_type") == "contains_pin":
                typed_cell_id = CellId(str(cell_id))
                if typed_cell_id not in seen_cell_ids:
                    cell = self.design.get_cell(typed_cell_id)
                    if cell:
                        cells.append(cell)
                        seen_cell_ids.add(typed_cell_id)

    def get_cell_pins(self, cell_id: CellId) -> list[Pin]:
        """Get all pins of a cell.

        Finds all pins that belong to the specified cell by following
        Cell → Pin containment edges in the graph.

        Args:
            cell_id: The cell to get pins for.

        Returns:
            List of Pin entities belonging to the cell.
            Empty list if cell doesn't exist.
        """
        # Check if cell exists in graph
        if cell_id not in self.graph:
            return []

        pins: list[Pin] = []

        # Cell → Pin edges (containment)
        for _, pin_id, edge_data in self.graph.out_edges(cell_id, data=True):
            if edge_data.get("edge_type") == "contains_pin":
                pin = self.design.get_pin(PinId(str(pin_id)))
                if pin:
                    pins.append(pin)

        return pins

    def get_pin_net(self, pin_id: PinId) -> Net | None:
        """Get the net connected to a pin.

        Looks up the pin in the Design aggregate and returns its
        connected net, if any.

        Args:
            pin_id: The pin to find the connected net for.

        Returns:
            Net entity if pin is connected, None if floating or not found.
        """
        pin = self.design.get_pin(pin_id)
        if not pin or not pin.net_id:
            return None
        return self.design.get_net(pin.net_id)

    # =========================================================================
    # Fanout Traversal
    # =========================================================================

    def get_fanout_cells(
        self,
        cell_id: CellId,
        hops: int = 1,
        stop_at_sequential: bool = False,
    ) -> list[Cell]:
        """Get fanout cells (downstream) from a cell.

        Performs BFS traversal from the cell's output pins, following
        signal flow through nets to receiving cells.

        Args:
            cell_id: Starting cell for fanout traversal.
            hops: Number of hops to traverse.
            stop_at_sequential: If True, don't expand past sequential cells.

        Returns:
            List of cells reachable within specified hops.
        """
        return self._traverse_cells(
            cell_id,
            hops,
            stop_at_sequential,
            is_fanout=True,
        )

    # =========================================================================
    # Fanin Traversal
    # =========================================================================

    def get_fanin_cells(
        self,
        cell_id: CellId,
        hops: int = 1,
        stop_at_sequential: bool = False,
    ) -> list[Cell]:
        """Get fanin cells (upstream) to a cell.

        Performs BFS traversal from the cell's input pins, following
        signal flow backwards through nets to driving cells.

        Args:
            cell_id: Starting cell for fanin traversal.
            hops: Number of hops to traverse.
            stop_at_sequential: If True, don't expand past sequential cells.

        Returns:
            List of cells reachable within specified hops.
        """
        return self._traverse_cells(
            cell_id,
            hops,
            stop_at_sequential,
            is_fanout=False,
        )

    def _traverse_cells(
        self,
        cell_id: CellId,
        hops: int,
        stop_at_sequential: bool,
        is_fanout: bool,
    ) -> list[Cell]:
        """Common BFS traversal logic for fanin/fanout.

        Args:
            cell_id: Starting cell for traversal.
            hops: Number of hops to traverse.
            stop_at_sequential: If True, don't expand past sequential cells.
            is_fanout: True for fanout (follow output pins), False for fanin.

        Returns:
            List of cells reachable within specified hops.
        """
        # Handle edge cases
        if hops <= 0 or cell_id not in self.graph:
            return []

        visited_cells: set[CellId] = set()
        current_level: set[CellId] = {cell_id}

        for _ in range(hops):
            if not current_level:
                break

            next_level: set[CellId] = set()

            for current_cell_id in current_level:
                visited_cells.add(current_cell_id)
                self._expand_cell(
                    current_cell_id,
                    visited_cells,
                    next_level,
                    stop_at_sequential,
                    is_fanout,
                )

            current_level = next_level

        # Add any remaining cells in current_level to visited
        visited_cells.update(current_level)

        # Convert to list, excluding starting cell
        return self._visited_to_cells(visited_cells, cell_id)

    def _expand_cell(
        self,
        current_cell_id: CellId,
        visited_cells: set[CellId],
        next_level: set[CellId],
        stop_at_sequential: bool,
        is_fanout: bool,
    ) -> None:
        """Expand a single cell during BFS traversal.

        Args:
            current_cell_id: Cell to expand.
            visited_cells: Set of already visited cells.
            next_level: Set to add discovered cells to.
            stop_at_sequential: If True, don't expand past sequential cells.
            is_fanout: True for fanout, False for fanin.
        """
        pins = self.get_cell_pins(current_cell_id)
        for pin in pins:
            # Filter by direction: fanout uses output, fanin uses input
            if is_fanout and not pin.direction.is_output():
                continue
            if not is_fanout and not pin.direction.is_input():
                continue

            # Skip floating pins
            if not pin.net_id:
                continue

            # Get cells connected to this net
            connected_cells = self.get_connected_cells(pin.net_id)
            self._add_connected_cells(
                connected_cells,
                current_cell_id,
                visited_cells,
                next_level,
                stop_at_sequential,
            )

    def _add_connected_cells(
        self,
        connected_cells: list[Cell],
        current_cell_id: CellId,
        visited_cells: set[CellId],
        next_level: set[CellId],
        stop_at_sequential: bool,
    ) -> None:
        """Add connected cells to traversal sets.

        Args:
            connected_cells: Cells connected via net.
            current_cell_id: Current cell being expanded.
            visited_cells: Set of already visited cells.
            next_level: Set to add discovered cells to.
            stop_at_sequential: If True, don't expand past sequential cells.
        """
        for connected_cell in connected_cells:
            # Skip self and already visited
            if connected_cell.id == current_cell_id:
                continue
            if connected_cell.id in visited_cells:
                continue

            # Sequential boundary: add to visited but not next_level
            if stop_at_sequential and connected_cell.is_sequential:
                visited_cells.add(connected_cell.id)
                continue

            next_level.add(connected_cell.id)

    def _visited_to_cells(
        self,
        visited_cells: set[CellId],
        starting_cell_id: CellId,
    ) -> list[Cell]:
        """Convert visited cell IDs to Cell entities, excluding starting cell.

        Args:
            visited_cells: Set of visited cell IDs.
            starting_cell_id: Cell to exclude from results.

        Returns:
            List of Cell entities.
        """
        result: list[Cell] = []
        for visited_cell_id in visited_cells:
            if visited_cell_id == starting_cell_id:
                continue  # Exclude starting cell
            cell = self.design.get_cell(visited_cell_id)
            if cell:
                result.append(cell)

        return result

    # =========================================================================
    # Pin-Level Traversal
    # =========================================================================

    def get_fanout_from_pin(
        self,
        pin_id: PinId,
        hops: int = 1,
        stop_at_sequential: bool = False,
    ) -> list[Cell]:
        """Get fanout cells from a specific pin.

        For MVP, delegates to cell-based fanout from the pin's parent cell.
        A more precise implementation could start traversal from just this pin.

        Args:
            pin_id: Starting pin for fanout traversal.
            hops: Number of hops to traverse.
            stop_at_sequential: If True, stop at sequential cells.

        Returns:
            List of cells reachable from this pin.
        """
        # Get the cell containing this pin
        cell_ids = self._get_cells_for_pin(pin_id)
        if not cell_ids:
            return []

        # For MVP, delegate to cell-based fanout
        return self.get_fanout_cells(cell_ids[0], hops, stop_at_sequential)

    def get_fanin_to_pin(
        self,
        pin_id: PinId,
        hops: int = 1,
        stop_at_sequential: bool = False,
    ) -> list[Cell]:
        """Get fanin cells to a specific pin.

        For MVP, delegates to cell-based fanin to the pin's parent cell.
        A more precise implementation could target just this pin.

        Args:
            pin_id: Target pin for fanin traversal.
            hops: Number of hops to traverse.
            stop_at_sequential: If True, stop at sequential cells.

        Returns:
            List of cells reachable to this pin.
        """
        # Get the cell containing this pin
        cell_ids = self._get_cells_for_pin(pin_id)
        if not cell_ids:
            return []

        # For MVP, delegate to cell-based fanin
        return self.get_fanin_cells(cell_ids[0], hops, stop_at_sequential)

    def _get_cells_for_pin(self, pin_id: PinId) -> list[CellId]:
        """Get cells that contain a pin.

        Helper method to find the parent cell of a pin by following
        Cell → Pin containment edges backwards.

        Args:
            pin_id: The pin to find parent cells for.

        Returns:
            List of CellIds containing this pin (usually just one).
        """
        # Check if pin exists in graph
        if pin_id not in self.graph:
            return []

        cell_ids: list[CellId] = []
        # Find cells that contain this pin (Cell → Pin edges)
        for cell_id, _, edge_data in self.graph.in_edges(pin_id, data=True):
            if edge_data.get("edge_type") == "contains_pin":
                cell_ids.append(CellId(str(cell_id)))
        return cell_ids

    # =========================================================================
    # Path Finding
    # =========================================================================

    def find_path(
        self,
        from_cell_id: CellId,
        to_cell_id: CellId,
        max_hops: int = 10,
    ) -> list[Cell] | None:
        """Find shortest path between two cells.

        Uses NetworkX shortest_path algorithm to find the minimum-hop
        path between two cells. The path is filtered to include only
        Cell nodes (not Pin or Net nodes).

        Algorithm:
            1. Use nx.shortest_path to find path through graph
            2. Filter path to extract only Cell nodes
            3. Check if path length exceeds max_hops
            4. Return Cell entities or None

        Args:
            from_cell_id: Starting cell of the path.
            to_cell_id: Target cell of the path.
            max_hops: Maximum path length to accept.

        Returns:
            List of cells forming the path, or None if no valid path.
        """
        # Check if cells exist in graph
        if from_cell_id not in self.graph or to_cell_id not in self.graph:
            return None

        try:
            # Use NetworkX shortest path on undirected view
            # (paths can go both ways through cells)
            undirected = self.graph.to_undirected()
            raw_path = nx.shortest_path(
                undirected,
                source=from_cell_id,
                target=to_cell_id,
            )

            # Filter to Cell nodes only
            cell_path: list[Cell] = []
            for node_id in raw_path:
                node_data = self.graph.nodes.get(node_id, {})
                if node_data.get("node_type") == "cell":
                    cell = self.design.get_cell(CellId(str(node_id)))
                    if cell:
                        cell_path.append(cell)

            # Check if path exceeds max_hops
            # Path length in hops = number of cells - 1
            if len(cell_path) - 1 > max_hops:
                return None

            return cell_path if cell_path else None

        except nx.NetworkXNoPath:
            return None
        except nx.NodeNotFound:
            return None
