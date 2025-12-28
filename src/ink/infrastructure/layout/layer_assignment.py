"""Layer Assignment Algorithm for Sugiyama hierarchical layout.

This module implements the layer assignment phase of the Sugiyama algorithm.
The algorithm assigns each cell to a horizontal layer based on its position
in the logical signal flow, with primary inputs in layer 0 and cells placed
according to the longest path from sources.

Architecture:
    Layer: Infrastructure Layer
    Pattern: Algorithm implementation
    Bounded Context: Schematic Context

Algorithm Overview:
    1. Detect and mark feedback edges (cycle breaking) using DFS
    2. Assign layer 0 to all source nodes (cells with no incoming edges)
    3. Use topological sort with longest-path computation
    4. Return LayerAssignment result with layer_map, reverse_edges, layer_count

Complexity:
    Time: O(V + E) where V = nodes, E = edges
    Space: O(V) for storing layer assignments

Example:
    >>> import networkx as nx
    >>> from ink.infrastructure.layout import LayerAssignmentAlgorithm
    >>>
    >>> g = nx.DiGraph()
    >>> g.add_edges_from([("IN", "A"), ("A", "B"), ("B", "OUT")])
    >>>
    >>> algo = LayerAssignmentAlgorithm()
    >>> result = algo.assign_layers(g)
    >>>
    >>> result.layer_map
    {'IN': 0, 'A': 1, 'B': 2, 'OUT': 3}
    >>> result.layer_count
    4
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import networkx as nx


@dataclass(frozen=True)
class LayerAssignment:
    """Result of layer assignment algorithm.

    This immutable data class holds the results of running the layer
    assignment algorithm on a circuit graph.

    Attributes:
        layer_map: Dictionary mapping node IDs to their assigned layer numbers.
                   Layer 0 contains source nodes (primary inputs), and layer
                   numbers increase in the direction of signal flow.
        reverse_edges: Set of edges (source, target) that were marked for
                       reversal to break cycles. These are feedback edges in
                       sequential circuits.
        layer_count: Total number of layers in the assignment. Equal to
                     max(layer_map.values()) + 1, or 0 for empty graphs.

    Example:
        >>> result = LayerAssignment(
        ...     layer_map={'IN': 0, 'A': 1, 'OUT': 2},
        ...     reverse_edges=set(),
        ...     layer_count=3,
        ... )
        >>> result.layer_map['A']
        1
    """

    layer_map: dict[str, int]
    reverse_edges: set[tuple[str, str]]
    layer_count: int


class LayerAssignmentAlgorithm:
    """Assigns cells to layers using longest-path algorithm from sources.

    This class implements the first phase of the Sugiyama layout algorithm.
    It analyzes the circuit graph to determine the logical depth of each
    cell from primary inputs, assigning cells to horizontal layers that
    reveal left-to-right signal flow.

    The algorithm handles both DAGs (directed acyclic graphs) and cyclic
    graphs. For cyclic graphs, feedback edges are detected and marked for
    temporary reversal to enable topological ordering.

    Algorithm Steps:
        1. Detect cycles and mark feedback edges using DFS
        2. Create temporary acyclic graph by reversing feedback edges
        3. Perform topological sort on acyclic graph
        4. Assign source nodes to layer 0
        5. Compute longest-path layer for each remaining node
        6. Return LayerAssignment with results

    Example:
        >>> import networkx as nx
        >>> algo = LayerAssignmentAlgorithm()
        >>> g = nx.DiGraph()
        >>> g.add_edges_from([("A", "B"), ("B", "C")])
        >>> result = algo.assign_layers(g)
        >>> result.layer_map
        {'A': 0, 'B': 1, 'C': 2}
    """

    def assign_layers(  # type: ignore[no-any-unimported]
        self,
        graph: nx.DiGraph | nx.MultiDiGraph,
    ) -> LayerAssignment:
        """Assign cells to layers using longest-path from sources.

        This is the main entry point for the layer assignment algorithm.
        It processes the input graph and returns a LayerAssignment result
        containing the layer mapping for all nodes.

        Args:
            graph: NetworkX directed graph representing the circuit.
                   Nodes represent cells/ports, edges represent signal flow.
                   Can be DiGraph or MultiDiGraph.

        Returns:
            LayerAssignment containing:
            - layer_map: Dict mapping node IDs to layer numbers
            - reverse_edges: Set of edges marked for reversal (feedback)
            - layer_count: Total number of layers

        Raises:
            No exceptions are raised. Empty graphs return empty results.

        Time Complexity:
            O(V + E) where V = number of nodes, E = number of edges

        Space Complexity:
            O(V) for storing layer assignments

        Example:
            >>> g = nx.DiGraph()
            >>> g.add_edges_from([("IN", "A"), ("A", "OUT")])
            >>> result = algo.assign_layers(g)
            >>> result.layer_map
            {'IN': 0, 'A': 1, 'OUT': 2}
        """
        # Handle empty graph case
        if graph.number_of_nodes() == 0:
            return LayerAssignment(
                layer_map={},
                reverse_edges=set(),
                layer_count=0,
            )

        # Step 1: Detect feedback edges (back edges that create cycles)
        # These edges will be temporarily reversed to create a DAG
        reverse_edges = self._find_feedback_edges(graph)

        # Step 2: Create a working DAG by conceptually reversing feedback edges
        # We don't actually modify the graph, just use a different edge set
        working_graph = self._create_acyclic_graph(graph, reverse_edges)

        # Step 3: Compute layer assignments using longest-path from sources
        # Sources are nodes with no incoming edges in the working DAG
        layer_map = self._compute_longest_path_layers(working_graph)

        # Step 4: Calculate layer count
        layer_count = max(layer_map.values()) + 1 if layer_map else 0

        return LayerAssignment(
            layer_map=layer_map,
            reverse_edges=reverse_edges,
            layer_count=layer_count,
        )

    def _find_feedback_edges(  # type: ignore[no-any-unimported]
        self,
        graph: nx.DiGraph | nx.MultiDiGraph,
    ) -> set[tuple[Any, Any]]:
        """Find feedback edges (back edges) that create cycles in the graph.

        Uses iterative Depth-First Search (DFS) to identify back edges.
        A back edge is an edge from a node to one of its ancestors in the
        DFS tree, which indicates a cycle.

        The algorithm uses three colors:
        - WHITE (0): Unvisited node
        - GRAY (1): Node currently in the DFS stack (visiting)
        - BLACK (2): Node fully processed (all descendants visited)

        A back edge is detected when we find an edge to a GRAY node
        (an ancestor in the current DFS path).

        This implementation uses an iterative approach with an explicit stack
        to avoid Python's recursion limit for deep graphs (10,000+ nodes).

        Args:
            graph: The input directed graph (may contain cycles)

        Returns:
            Set of edges (source, target) that are feedback edges.
            Removing or reversing these edges would make the graph acyclic.

        Time Complexity:
            O(V + E) - standard DFS traversal

        Example:
            For graph A -> B -> C -> A, returns {('C', 'A')} as the back edge.
        """
        # Color states for DFS
        WHITE = 0  # Unvisited
        GRAY = 1  # Currently in DFS stack
        BLACK = 2  # Fully processed

        color: dict[Any, int] = dict.fromkeys(graph.nodes(), WHITE)
        feedback_edges: set[tuple[Any, Any]] = set()

        # Run iterative DFS from all unvisited nodes
        for start_node in graph.nodes():
            if color[start_node] != WHITE:
                continue

            # Stack contains (node, iterator_over_successors, is_entering)
            # is_entering=True means we're entering the node for the first time
            # is_entering=False means we're returning from processing children
            stack: list[tuple[Any, Any, bool]] = [
                (start_node, iter(graph.successors(start_node)), True)
            ]

            while stack:
                node, successors_iter, is_entering = stack.pop()

                if is_entering:
                    # First time visiting this node
                    color[node] = GRAY
                    # Put this node back on stack to process after children
                    stack.append((node, successors_iter, False))

                    # Check all successors
                    for successor in successors_iter:
                        if color[successor] == GRAY:
                            # Back edge found - successor is ancestor
                            feedback_edges.add((node, successor))
                        elif color[successor] == WHITE:
                            # Push successor to process next
                            stack.append(
                                (
                                    successor,
                                    iter(graph.successors(successor)),
                                    True,
                                )
                            )
                        # BLACK nodes are already fully processed, skip
                else:
                    # Finished processing all children of this node
                    color[node] = BLACK

        return feedback_edges

    def _create_acyclic_graph(  # type: ignore[no-any-unimported]
        self,
        graph: nx.DiGraph | nx.MultiDiGraph,
        reverse_edges: set[tuple[Any, Any]],
    ) -> nx.DiGraph:
        """Create an acyclic version of the graph by reversing feedback edges.

        Creates a new DiGraph where the feedback edges are reversed.
        This allows topological sorting and layer assignment to proceed.

        Args:
            graph: The original graph (may contain cycles)
            reverse_edges: Set of edges to reverse

        Returns:
            A new DiGraph that is acyclic (DAG)

        Note:
            The original graph is not modified.
            We use DiGraph for the working graph even if input is MultiDiGraph,
            as we only need edge presence, not multiplicity.
        """
        # Create a new DiGraph for the working copy
        working = nx.DiGraph()

        # Add all nodes (preserving attributes)
        for node in graph.nodes():
            working.add_node(node, **dict(graph.nodes[node]))

        # Add edges, reversing the feedback edges
        for u, v in graph.edges():
            if (u, v) in reverse_edges:
                # Reverse this edge
                working.add_edge(v, u)
            else:
                # Keep edge as-is
                working.add_edge(u, v)

        return working

    def _compute_longest_path_layers(  # type: ignore[no-any-unimported]
        self,
        dag: nx.DiGraph,
    ) -> dict[Any, int]:
        """Compute layer assignments using longest-path from sources.

        Assigns each node to a layer based on the longest path from any
        source node (node with no predecessors). This ensures that:
        - Source nodes are in layer 0
        - Each node is placed at max(predecessor_layers) + 1
        - The resulting layers reveal the logical depth of each node

        Uses topological sort to process nodes in dependency order.

        Args:
            dag: Directed Acyclic Graph (must be acyclic)

        Returns:
            Dictionary mapping each node to its layer number (0-indexed)

        Algorithm:
            1. Initialize all source nodes (in_degree=0) to layer 0
            2. Process nodes in topological order
            3. For each node, layer = max(predecessor_layers) + 1

        Time Complexity:
            O(V + E) - topological sort + single pass over edges
        """
        layer_map: dict[Any, int] = {}

        # Step 1: Find all source nodes (no incoming edges)
        # These form layer 0
        for node in dag.nodes():
            if dag.in_degree(node) == 0:
                layer_map[node] = 0

        # Step 2: Process nodes in topological order
        # This ensures predecessors are processed before successors
        try:
            topo_order = list(nx.topological_sort(dag))
        except nx.NetworkXUnfeasible:
            # Should not happen since we created an acyclic graph
            # But handle gracefully - assign all remaining nodes to layer 0
            for node in dag.nodes():
                if node not in layer_map:
                    layer_map[node] = 0
            return layer_map

        # Step 3: Assign layers based on longest path from sources
        for node in topo_order:
            if node in layer_map:
                # Already assigned (source node)
                continue

            # Get all predecessors
            predecessors = list(dag.predecessors(node))

            if not predecessors:
                # No predecessors = source node (should already be handled)
                layer_map[node] = 0
            else:
                # Layer = max predecessor layer + 1 (longest path)
                max_pred_layer = max(layer_map[pred] for pred in predecessors)
                layer_map[node] = max_pred_layer + 1

        return layer_map
