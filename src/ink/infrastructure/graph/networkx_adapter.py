"""NetworkX graph builder adapter for the infrastructure layer.

This module implements the NetworkXGraphBuilder class that translates
the Design aggregate into a NetworkX MultiDiGraph for efficient
graph-based connectivity queries (fanin/fanout traversal).

Architecture:
    Layer: Infrastructure Layer
    Pattern: Adapter Pattern (adapts Domain model to NetworkX graph)
    Bounded Context: Netlist Context

The graph builder creates a heterogeneous graph where:
- Nodes represent domain entities (Cell, Pin, Net, Port)
- Edges represent relationships (containment, signal flow)

Graph Structure:
    Node Types:
        - 'cell': Gate-level cell instances
        - 'pin': Connection points on cells
        - 'net': Wires connecting pins
        - 'port': Top-level I/O interfaces

    Edge Types:
        - 'contains_pin': Cell → Pin (containment relationship)
        - 'drives': Signal flow edges between pins/ports and nets

Edge Direction Rules (Signal Flow):
    - OUTPUT Pin → Net (output pins drive nets)
    - Net → INPUT Pin (nets drive input pins)
    - INOUT Pin: treated as input (Net → Pin)
    - INPUT Port → Net (input ports drive internal nets)
    - Net → OUTPUT Port (internal nets drive output ports)
    - INOUT Port: treated as input port (Port → Net)

Design Decisions:
    1. MultiDiGraph: Supports multiple edges between same nodes (e.g., bus signals)
    2. Entity References: Each node stores reference to original domain entity
       for easy retrieval during graph traversal
    3. Typed Nodes/Edges: All nodes and edges have type attributes for filtering
    4. Builder Pattern: Allows reuse for multiple designs
    5. Future Migration: Structure designed for easy migration to rustworkx

Example:
    >>> from ink.infrastructure.graph import NetworkXGraphBuilder
    >>> from ink.domain.model import Design
    >>>
    >>> design = Design(name="inverter_chain")
    >>> # ... add cells, pins, nets, ports to design ...
    >>>
    >>> builder = NetworkXGraphBuilder()
    >>> graph = builder.build_from_design(design)
    >>>
    >>> # Access graph properties
    >>> builder.node_count()
    10
    >>> builder.cell_node_count()
    2
    >>>
    >>> # Get entity from node
    >>> cell = builder.get_node_entity(CellId("XI1"))
    >>> cell.cell_type
    'INV_X1'
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from ink.domain.model import Cell, Design, Net, Pin, Port


class NetworkXGraphBuilder:
    """Builds NetworkX MultiDiGraph from Design aggregate.

    This class translates the domain model (Design aggregate containing
    Cell, Pin, Net, Port entities) into a NetworkX graph structure
    suitable for graph-based connectivity queries.

    The builder follows the Builder pattern, allowing the same instance
    to be reused for building graphs from multiple designs. Each call
    to build_from_design() clears the previous graph.

    Attributes:
        graph: The NetworkX MultiDiGraph being constructed

    Node Attributes:
        - node_type: 'cell' | 'pin' | 'net' | 'port'
        - name: Entity name
        - entity: Reference to original domain entity
        - (Cell) cell_type: Cell type (e.g., "INV_X1")
        - (Cell) is_sequential: True for flip-flops/latches
        - (Pin) direction: PinDirection enum
        - (Pin) net_id: Connected net ID or None
        - (Net) pin_count: Number of connected pins
        - (Port) direction: PinDirection enum
        - (Port) net_id: Connected net ID or None

    Edge Attributes:
        - edge_type: 'contains_pin' | 'drives'

    Example:
        >>> builder = NetworkXGraphBuilder()
        >>> graph = builder.build_from_design(design)
        >>>
        >>> # Check graph structure
        >>> builder.node_count()
        7
        >>> builder.cell_node_count()
        1
        >>>
        >>> # Access node entity
        >>> entity = builder.get_node_entity(CellId("XI1"))
        >>> isinstance(entity, Cell)
        True
    """

    def __init__(self) -> None:
        """Initialize the builder with an empty MultiDiGraph.

        Creates an empty NetworkX MultiDiGraph ready for building.
        MultiDiGraph is used to support multiple edges between the same
        nodes (e.g., multiple connections in bus signals).
        """
        # MultiDiGraph: directed graph with parallel edges support
        # This is essential for representing multiple connections between
        # the same pair of nodes (common in bus architectures)
        # Note: type ignore needed because networkx lacks type stubs
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()  # type: ignore[no-any-unimported]

        # Store reference to current design for entity lookups
        self._design: Design | None = None

    def build_from_design(  # type: ignore[no-any-unimported]
        self, design: Design
    ) -> nx.MultiDiGraph:
        """Build graph from Design aggregate.

        Constructs a complete graph representation of the design by:
        1. Adding all entity nodes (cells, pins, nets, ports)
        2. Adding containment edges (cell → pins)
        3. Adding signal flow edges (pins ↔ nets, ports ↔ nets)

        Args:
            design: The Design aggregate to build the graph from.
                   Must contain valid domain entities (Cell, Pin, Net, Port).

        Returns:
            The constructed NetworkX MultiDiGraph. This is the same
            instance as self.graph.

        Note:
            - Calling this method clears any previously built graph
            - The design reference is stored for entity lookups
            - All entity references in nodes point to the original
              immutable domain entities

        Example:
            >>> builder = NetworkXGraphBuilder()
            >>> graph = builder.build_from_design(design)
            >>> graph.number_of_nodes()
            7
        """
        # Store design reference for potential future lookups
        self._design = design

        # Clear any previous graph data for reuse
        self.graph.clear()

        # Phase 1: Add all entity nodes
        # Order matters: nodes must exist before creating edges
        self._add_cell_nodes()
        self._add_pin_nodes()
        self._add_net_nodes()
        self._add_port_nodes()

        # Phase 2: Add edges representing relationships
        # Cell→Pin containment edges
        self._add_cell_pin_edges()

        # Signal flow edges (respecting direction semantics)
        self._add_pin_net_edges()
        self._add_port_net_edges()

        return self.graph

    # =========================================================================
    # Node Creation Methods
    # =========================================================================

    def _add_cell_nodes(self) -> None:
        """Add Cell nodes to graph.

        Creates a node for each cell in the design with attributes:
        - node_type: 'cell'
        - name: Instance name
        - cell_type: Cell type reference (e.g., "INV_X1")
        - is_sequential: True for flip-flops and latches
        - entity: Reference to original Cell entity
        """
        if self._design is None:
            return

        for cell in self._design.get_all_cells():
            self.graph.add_node(
                cell.id,
                node_type="cell",
                name=cell.name,
                cell_type=cell.cell_type,
                is_sequential=cell.is_sequential,
                entity=cell,  # Store reference for easy retrieval
            )

    def _add_pin_nodes(self) -> None:
        """Add Pin nodes to graph.

        Creates a node for each pin in the design with attributes:
        - node_type: 'pin'
        - name: Pin name (local name, e.g., "A", "Y")
        - direction: PinDirection enum (INPUT, OUTPUT, INOUT)
        - net_id: Connected net ID or None for floating pins
        - entity: Reference to original Pin entity
        """
        if self._design is None:
            return

        for pin in self._design.get_all_pins():
            self.graph.add_node(
                pin.id,
                node_type="pin",
                name=pin.name,
                direction=pin.direction,
                net_id=pin.net_id,
                entity=pin,
            )

    def _add_net_nodes(self) -> None:
        """Add Net nodes to graph.

        Creates a node for each net in the design with attributes:
        - node_type: 'net'
        - name: Net name
        - pin_count: Number of pins connected to this net
        - entity: Reference to original Net entity
        """
        if self._design is None:
            return

        for net in self._design.get_all_nets():
            self.graph.add_node(
                net.id,
                node_type="net",
                name=net.name,
                pin_count=net.pin_count(),
                entity=net,
            )

    def _add_port_nodes(self) -> None:
        """Add Port nodes to graph.

        Creates a node for each port in the design with attributes:
        - node_type: 'port'
        - name: Port name (interface name)
        - direction: PinDirection enum (INPUT, OUTPUT, INOUT)
        - net_id: Connected internal net ID or None
        - entity: Reference to original Port entity
        """
        if self._design is None:
            return

        for port in self._design.get_all_ports():
            self.graph.add_node(
                port.id,
                node_type="port",
                name=port.name,
                direction=port.direction,
                net_id=port.net_id,
                entity=port,
            )

    # =========================================================================
    # Edge Creation Methods
    # =========================================================================

    def _add_cell_pin_edges(self) -> None:
        """Add Cell→Pin edges for containment relationships.

        Creates a directed edge from each cell to each of its pins.
        This represents the containment relationship: cells contain pins.

        Edge attributes:
        - edge_type: 'contains_pin'
        """
        if self._design is None:
            return

        for cell in self._design.get_all_cells():
            for pin_id in cell.pin_ids:
                self.graph.add_edge(
                    cell.id,
                    pin_id,
                    edge_type="contains_pin",
                )

    def _add_pin_net_edges(self) -> None:
        """Add Pin↔Net edges for signal flow.

        Creates directed edges between pins and their connected nets.
        Edge direction follows signal flow semantics:

        - OUTPUT pins drive nets: Pin → Net
        - INPUT pins are driven by nets: Net → Pin
        - INOUT pins: treated as input (Net → Pin)
          Note: INOUT could have bidirectional edges, but for simplicity
          we treat them as receivers since fanin/fanout queries typically
          focus on driver relationships.

        Floating pins (net_id=None) have no pin-net edges.

        Edge attributes:
        - edge_type: 'drives'
        """
        if self._design is None:
            return

        for pin in self._design.get_all_pins():
            # Skip floating pins (not connected to any net)
            if pin.net_id is None:
                continue

            # Direction determines edge direction
            if pin.direction.is_output():
                # Output pins drive nets: Pin → Net
                # Note: is_output() returns True for OUTPUT and INOUT
                # For pure OUTPUT, this creates Pin → Net
                self.graph.add_edge(
                    pin.id,
                    pin.net_id,
                    edge_type="drives",
                )

            if pin.direction.is_input():
                # Input pins are driven by nets: Net → Pin
                # Note: is_input() returns True for INPUT and INOUT
                self.graph.add_edge(
                    pin.net_id,
                    pin.id,
                    edge_type="drives",
                )

    def _add_port_net_edges(self) -> None:
        """Add Port↔Net edges for I/O signal flow.

        Creates directed edges between ports and their connected internal nets.
        Edge direction follows I/O signal flow semantics:

        - INPUT ports drive internal nets: Port → Net
          (External signals flow into the design)
        - OUTPUT ports are driven by internal nets: Net → Port
          (Internal signals flow out of the design)
        - INOUT ports: treated as input ports (Port → Net)
          Similar to INOUT pins, we treat them as drivers for simplicity.

        Unconnected ports (net_id=None) have no port-net edges.

        Edge attributes:
        - edge_type: 'drives'
        """
        if self._design is None:
            return

        for port in self._design.get_all_ports():
            # Skip unconnected ports
            if port.net_id is None:
                continue

            if port.direction.is_input():
                # Input ports drive internal nets: Port → Net
                # This represents external signal driving internal logic
                self.graph.add_edge(
                    port.id,
                    port.net_id,
                    edge_type="drives",
                )

            if port.direction.is_output():
                # Output ports are driven by internal nets: Net → Port
                # This represents internal signal driving external interface
                self.graph.add_edge(
                    port.net_id,
                    port.id,
                    edge_type="drives",
                )

    # =========================================================================
    # Graph Access Methods
    # =========================================================================

    def get_graph(self) -> nx.MultiDiGraph:  # type: ignore[no-any-unimported]
        """Get the constructed graph.

        Returns:
            The NetworkX MultiDiGraph instance. This is the same instance
            used internally, so modifications will affect the builder state.

        Example:
            >>> builder = NetworkXGraphBuilder()
            >>> graph = builder.get_graph()
            >>> graph.number_of_nodes()
            0  # Empty before build
        """
        return self.graph

    def get_node_entity(self, node_id: str) -> Cell | Pin | Net | Port | None:
        """Get the domain entity associated with a graph node.

        Retrieves the original domain entity (Cell, Pin, Net, or Port)
        stored in the node's 'entity' attribute.

        Args:
            node_id: The node identifier (CellId, PinId, NetId, or PortId)

        Returns:
            The domain entity (Cell, Pin, Net, or Port) associated with
            the node, or None if the node doesn't exist or has no entity.

        Example:
            >>> entity = builder.get_node_entity(CellId("XI1"))
            >>> isinstance(entity, Cell)
            True
            >>> entity.cell_type
            'INV_X1'
        """
        return self.graph.nodes[node_id].get("entity")  # type: ignore[no-any-return]

    def get_node_type(self, node_id: str) -> str | None:
        """Get the type of a graph node.

        Retrieves the 'node_type' attribute which identifies whether
        the node represents a cell, pin, net, or port.

        Args:
            node_id: The node identifier

        Returns:
            The node type string ('cell', 'pin', 'net', 'port'),
            or None if the node doesn't exist or has no type.

        Example:
            >>> builder.get_node_type(CellId("XI1"))
            'cell'
            >>> builder.get_node_type(NetId("net_in"))
            'net'
        """
        return self.graph.nodes[node_id].get("node_type")  # type: ignore[no-any-return]

    # =========================================================================
    # Graph Statistics Methods
    # =========================================================================

    def node_count(self) -> int:
        """Get total number of nodes in the graph.

        Returns:
            Total count of all nodes (cells + pins + nets + ports)

        Example:
            >>> builder.build_from_design(design)
            >>> builder.node_count()
            7  # 1 cell + 2 pins + 2 nets + 2 ports
        """
        return int(self.graph.number_of_nodes())

    def edge_count(self) -> int:
        """Get total number of edges in the graph.

        Returns:
            Total count of all edges (containment + signal flow)

        Example:
            >>> builder.build_from_design(design)
            >>> builder.edge_count()
            6  # 2 cell-pin + 2 pin-net + 2 port-net
        """
        return int(self.graph.number_of_edges())

    def cell_node_count(self) -> int:
        """Get number of cell nodes in the graph.

        Counts nodes where node_type='cell'.

        Returns:
            Number of cell nodes (0 or more)

        Example:
            >>> builder.build_from_design(design)
            >>> builder.cell_node_count()
            1
        """
        return sum(
            1
            for _, data in self.graph.nodes(data=True)
            if data.get("node_type") == "cell"
        )

    def net_node_count(self) -> int:
        """Get number of net nodes in the graph.

        Counts nodes where node_type='net'.

        Returns:
            Number of net nodes (0 or more)

        Example:
            >>> builder.build_from_design(design)
            >>> builder.net_node_count()
            2
        """
        return sum(
            1
            for _, data in self.graph.nodes(data=True)
            if data.get("node_type") == "net"
        )
