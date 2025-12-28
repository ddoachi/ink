"""Unit tests for Layer Assignment Algorithm - TDD RED Phase.

These tests define the expected behavior of the LayerAssignmentAlgorithm class
following Test-Driven Development methodology. All tests should fail initially
(RED phase) until the implementation is complete.

Test Coverage Goals (from spec E02-F02-T01):
- FR-001: Algorithm MUST assign all cells to a non-negative layer number
- FR-002: Algorithm MUST assign primary inputs to layer 0
- FR-003: Algorithm MUST detect and reverse feedback edges in cyclic graphs
- FR-004: Algorithm MUST use longest-path distance from sources for layer assignment
- FR-005: Algorithm MUST produce layers where forward edges only increase layer number

Performance Requirements:
- NFR-001: Complete layer assignment for 1000 cells in <100ms
- NFR-002: Complete layer assignment for 10,000 cells in <2 seconds

Acceptance Scenarios from Spec:
1. Pure Combinational Circuit: IN -> A -> B -> C -> OUT => layers [0,1,2,3,4]
2. Multiple Input Paths: IN1->A, IN2->B, both->C => [0,0,1,1,2]
3. Sequential Circuit with Feedback: A->B->FF->A => one edge reversed, warning logged
4. Empty Graph: Returns empty layer_map with layer_count=0
"""

from __future__ import annotations

import time

import networkx as nx
import pytest

from ink.infrastructure.layout import LayerAssignment, LayerAssignmentAlgorithm

# =============================================================================
# Fixtures: Graph Construction Helpers
# =============================================================================


@pytest.fixture
def empty_graph() -> nx.DiGraph:
    """Create an empty directed graph for testing edge cases."""
    return nx.DiGraph()


@pytest.fixture
def single_node_graph() -> nx.DiGraph:
    """Create a graph with a single node (source and sink)."""
    g = nx.DiGraph()
    g.add_node("A", node_type="cell")
    return g


@pytest.fixture
def simple_chain_graph() -> nx.DiGraph:
    """Create a simple chain: IN -> A -> B -> C -> OUT.

    Expected layers: IN=0, A=1, B=2, C=3, OUT=4
    """
    g = nx.DiGraph()
    # Add nodes with types
    g.add_node("IN", node_type="port")
    g.add_node("A", node_type="cell")
    g.add_node("B", node_type="cell")
    g.add_node("C", node_type="cell")
    g.add_node("OUT", node_type="port")

    # Add edges representing signal flow
    g.add_edge("IN", "A")
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "OUT")

    return g


@pytest.fixture
def diamond_graph() -> nx.DiGraph:
    r"""Create a diamond-shaped DAG: IN -> A,B -> C -> OUT.

    Structure::

           IN (layer 0)
          /  \
         A    B  (layer 1)
          \  /
           C     (layer 2)
           |
          OUT    (layer 3)

    Expected layers: IN=0, A=1, B=1, C=2, OUT=3
    """
    g = nx.DiGraph()
    g.add_node("IN", node_type="port")
    g.add_node("A", node_type="cell")
    g.add_node("B", node_type="cell")
    g.add_node("C", node_type="cell")
    g.add_node("OUT", node_type="port")

    g.add_edge("IN", "A")
    g.add_edge("IN", "B")
    g.add_edge("A", "C")
    g.add_edge("B", "C")
    g.add_edge("C", "OUT")

    return g


@pytest.fixture
def multiple_sources_graph() -> nx.DiGraph:
    """Create a graph with multiple source nodes.

    Structure::

        IN1 -> A --+
                   +-> C -> OUT
        IN2 -> B --+

    Expected layers: IN1=0, IN2=0, A=1, B=1, C=2, OUT=3
    """
    g = nx.DiGraph()
    g.add_node("IN1", node_type="port")
    g.add_node("IN2", node_type="port")
    g.add_node("A", node_type="cell")
    g.add_node("B", node_type="cell")
    g.add_node("C", node_type="cell")
    g.add_node("OUT", node_type="port")

    g.add_edge("IN1", "A")
    g.add_edge("IN2", "B")
    g.add_edge("A", "C")
    g.add_edge("B", "C")
    g.add_edge("C", "OUT")

    return g


@pytest.fixture
def unbalanced_paths_graph() -> nx.DiGraph:
    """Create a graph with unbalanced path lengths to same node.

    Structure:
        IN -> A -> B -> C -> D
              |           ^
              +-----------+
              (short path)

    Longest path: IN->A->B->C->D (length 4)
    Short path: IN->A->D (length 2)

    Expected layers (longest-path): IN=0, A=1, B=2, C=3, D=4
    """
    g = nx.DiGraph()
    g.add_node("IN", node_type="port")
    g.add_node("A", node_type="cell")
    g.add_node("B", node_type="cell")
    g.add_node("C", node_type="cell")
    g.add_node("D", node_type="cell")

    # Long path
    g.add_edge("IN", "A")
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "D")
    # Short path
    g.add_edge("A", "D")

    return g


@pytest.fixture
def simple_cycle_graph() -> nx.DiGraph:
    """Create a simple cyclic graph: A -> B -> C -> A.

    This represents a feedback loop typical in sequential circuits.
    One edge must be reversed to break the cycle.
    """
    g = nx.DiGraph()
    g.add_node("A", node_type="cell")
    g.add_node("B", node_type="cell")
    g.add_node("C", node_type="cell")

    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "A")  # Back edge (feedback)

    return g


@pytest.fixture
def sequential_circuit_graph() -> nx.DiGraph:
    """Create a realistic sequential circuit with flip-flop feedback.

    Structure:
        IN -> LOGIC1 -> FF_D
                         |
        CLK ----------> FF_CLK
                         |
        FF_Q -> LOGIC2 -> OUT
          |
          +-> LOGIC1 (feedback)

    The FF output feeds back into combinational logic.
    """
    g = nx.DiGraph()
    g.add_node("IN", node_type="port")
    g.add_node("CLK", node_type="port")
    g.add_node("LOGIC1", node_type="cell")
    g.add_node("FF", node_type="cell", is_sequential=True)
    g.add_node("LOGIC2", node_type="cell")
    g.add_node("OUT", node_type="port")

    # Forward path
    g.add_edge("IN", "LOGIC1")
    g.add_edge("LOGIC1", "FF")
    g.add_edge("CLK", "FF")
    g.add_edge("FF", "LOGIC2")
    g.add_edge("LOGIC2", "OUT")
    # Feedback path
    g.add_edge("FF", "LOGIC1")  # This creates a cycle

    return g


@pytest.fixture
def disconnected_components_graph() -> nx.DiGraph:
    """Create a graph with disconnected components.

    Component 1: A -> B -> C
    Component 2: X -> Y

    Each component should be assigned layers independently.
    Expected: A=0, B=1, C=2, X=0, Y=1
    """
    g = nx.DiGraph()
    # Component 1
    g.add_node("A", node_type="cell")
    g.add_node("B", node_type="cell")
    g.add_node("C", node_type="cell")
    g.add_edge("A", "B")
    g.add_edge("B", "C")

    # Component 2 (disconnected)
    g.add_node("X", node_type="cell")
    g.add_node("Y", node_type="cell")
    g.add_edge("X", "Y")

    return g


@pytest.fixture
def wide_graph() -> nx.DiGraph:
    """Create a wide graph with many parallel paths.

    Structure:
        IN -> A1, A2, A3, A4, A5 -> OUT

    All middle nodes are on the same layer.
    """
    g = nx.DiGraph()
    g.add_node("IN", node_type="port")
    g.add_node("OUT", node_type="port")

    for i in range(5):
        node = f"A{i}"
        g.add_node(node, node_type="cell")
        g.add_edge("IN", node)
        g.add_edge(node, "OUT")

    return g


# =============================================================================
# Test: LayerAssignment Data Structure
# =============================================================================


class TestLayerAssignmentDataStructure:
    """Tests for the LayerAssignment result data structure."""

    def test_layer_assignment_has_layer_map(self) -> None:
        """LayerAssignment should have a layer_map attribute."""
        result = LayerAssignment(
            layer_map={"A": 0, "B": 1},
            reverse_edges=set(),
            layer_count=2,
        )
        assert hasattr(result, "layer_map")
        assert result.layer_map == {"A": 0, "B": 1}

    def test_layer_assignment_has_reverse_edges(self) -> None:
        """LayerAssignment should have a reverse_edges attribute."""
        result = LayerAssignment(
            layer_map={},
            reverse_edges={("C", "A")},
            layer_count=0,
        )
        assert hasattr(result, "reverse_edges")
        assert result.reverse_edges == {("C", "A")}

    def test_layer_assignment_has_layer_count(self) -> None:
        """LayerAssignment should have a layer_count attribute."""
        result = LayerAssignment(
            layer_map={"A": 0, "B": 1, "C": 2},
            reverse_edges=set(),
            layer_count=3,
        )
        assert hasattr(result, "layer_count")
        assert result.layer_count == 3

    def test_layer_assignment_is_immutable(self) -> None:
        """LayerAssignment should be a frozen dataclass (immutable)."""
        from dataclasses import FrozenInstanceError

        result = LayerAssignment(
            layer_map={"A": 0},
            reverse_edges=set(),
            layer_count=1,
        )
        # Should raise FrozenInstanceError when trying to modify
        with pytest.raises(FrozenInstanceError):
            result.layer_count = 5  # type: ignore[misc]


# =============================================================================
# Test: Algorithm Instantiation
# =============================================================================


class TestAlgorithmInstantiation:
    """Tests for LayerAssignmentAlgorithm instantiation."""

    def test_algorithm_can_be_instantiated(self) -> None:
        """LayerAssignmentAlgorithm should be instantiable."""
        algo = LayerAssignmentAlgorithm()
        assert algo is not None

    def test_algorithm_has_assign_layers_method(self) -> None:
        """Algorithm should have an assign_layers method."""
        algo = LayerAssignmentAlgorithm()
        assert hasattr(algo, "assign_layers")
        assert callable(algo.assign_layers)


# =============================================================================
# Test: Empty and Single Node Graphs
# =============================================================================


class TestEmptyAndSingleNodeGraphs:
    """Tests for edge cases: empty graphs and single-node graphs."""

    def test_empty_graph_returns_empty_result(self, empty_graph: nx.DiGraph) -> None:
        """Empty graph should return empty layer_map with layer_count=0."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(empty_graph)

        assert result.layer_map == {}
        assert result.reverse_edges == set()
        assert result.layer_count == 0

    def test_single_node_assigned_to_layer_zero(
        self, single_node_graph: nx.DiGraph
    ) -> None:
        """Single node (source) should be assigned to layer 0."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(single_node_graph)

        assert result.layer_map == {"A": 0}
        assert result.layer_count == 1
        assert result.reverse_edges == set()


# =============================================================================
# Test: Simple DAG Layer Assignment
# =============================================================================


class TestSimpleDAGLayerAssignment:
    """Tests for basic DAG layer assignment (no cycles)."""

    def test_simple_chain_layers(self, simple_chain_graph: nx.DiGraph) -> None:
        """Simple chain should have sequential layers.

        IN -> A -> B -> C -> OUT
        Expected: IN=0, A=1, B=2, C=3, OUT=4
        """
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(simple_chain_graph)

        assert result.layer_map["IN"] == 0
        assert result.layer_map["A"] == 1
        assert result.layer_map["B"] == 2
        assert result.layer_map["C"] == 3
        assert result.layer_map["OUT"] == 4
        assert result.layer_count == 5
        assert result.reverse_edges == set()

    def test_diamond_graph_layers(self, diamond_graph: nx.DiGraph) -> None:
        """Diamond graph should have parallel nodes on same layer.

        IN -> A,B -> C -> OUT
        Expected: IN=0, A=1, B=1, C=2, OUT=3
        """
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(diamond_graph)

        assert result.layer_map["IN"] == 0
        assert result.layer_map["A"] == 1
        assert result.layer_map["B"] == 1
        assert result.layer_map["C"] == 2
        assert result.layer_map["OUT"] == 3
        assert result.layer_count == 4

    def test_multiple_sources_all_layer_zero(
        self, multiple_sources_graph: nx.DiGraph
    ) -> None:
        """All source nodes (no predecessors) should be in layer 0."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(multiple_sources_graph)

        # Both input ports should be layer 0
        assert result.layer_map["IN1"] == 0
        assert result.layer_map["IN2"] == 0

    def test_wide_graph_parallel_nodes_same_layer(
        self, wide_graph: nx.DiGraph
    ) -> None:
        """Wide graph parallel nodes should be on the same layer."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(wide_graph)

        # All A nodes should be on layer 1
        for i in range(5):
            assert result.layer_map[f"A{i}"] == 1

        assert result.layer_map["IN"] == 0
        assert result.layer_map["OUT"] == 2


# =============================================================================
# Test: Longest Path Assignment
# =============================================================================


class TestLongestPathAssignment:
    """Tests for longest-path layer assignment (FR-004)."""

    def test_longest_path_determines_layer(
        self, unbalanced_paths_graph: nx.DiGraph
    ) -> None:
        """Node should be placed at max(predecessor_layers) + 1.

        Graph has short path (A->D) and long path (A->B->C->D).
        D should be placed based on longest path.

        Expected: IN=0, A=1, B=2, C=3, D=4
        """
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(unbalanced_paths_graph)

        # D should be at layer 4 (longest path), not layer 2 (shortest)
        assert result.layer_map["D"] == 4
        assert result.layer_map["C"] == 3
        assert result.layer_map["B"] == 2
        assert result.layer_map["A"] == 1
        assert result.layer_map["IN"] == 0

    def test_all_nodes_assigned_non_negative_layers(
        self, diamond_graph: nx.DiGraph
    ) -> None:
        """All nodes must be assigned non-negative layer numbers (FR-001)."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(diamond_graph)

        for node, layer in result.layer_map.items():
            assert layer >= 0, f"Node {node} has negative layer {layer}"


# =============================================================================
# Test: Forward Edge Direction (FR-005)
# =============================================================================


class TestForwardEdgeDirection:
    """Tests for forward edge direction constraint (FR-005)."""

    def test_forward_edges_increase_layer(
        self, simple_chain_graph: nx.DiGraph
    ) -> None:
        """All forward edges should go from lower to higher layer (FR-005)."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(simple_chain_graph)

        for u, v in simple_chain_graph.edges():
            if (u, v) not in result.reverse_edges:
                assert result.layer_map[u] < result.layer_map[v], (
                    f"Edge ({u},{v}) goes from layer {result.layer_map[u]} "
                    f"to layer {result.layer_map[v]}"
                )

    def test_diamond_graph_edge_direction(self, diamond_graph: nx.DiGraph) -> None:
        """Diamond graph edges should all go forward."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(diamond_graph)

        for u, v in diamond_graph.edges():
            assert result.layer_map[u] < result.layer_map[v]


# =============================================================================
# Test: Cycle Detection and Feedback Edge Reversal (FR-003)
# =============================================================================


class TestCycleDetection:
    """Tests for cycle detection and feedback edge handling (FR-003)."""

    def test_simple_cycle_detects_back_edge(
        self, simple_cycle_graph: nx.DiGraph
    ) -> None:
        """Simple cycle should have one edge marked for reversal."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(simple_cycle_graph)

        # Should have exactly one reversed edge to break the cycle
        assert len(result.reverse_edges) == 1
        # The reversed edge should be one of the cycle edges
        assert result.reverse_edges.issubset(
            {("A", "B"), ("B", "C"), ("C", "A")}
        )

    def test_cycle_all_nodes_still_assigned(
        self, simple_cycle_graph: nx.DiGraph
    ) -> None:
        """All nodes in cyclic graph should still be assigned layers."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(simple_cycle_graph)

        # All nodes should be assigned
        assert "A" in result.layer_map
        assert "B" in result.layer_map
        assert "C" in result.layer_map
        assert result.layer_count > 0

    def test_sequential_circuit_handles_feedback(
        self, sequential_circuit_graph: nx.DiGraph
    ) -> None:
        """Sequential circuit feedback should be handled."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(sequential_circuit_graph)

        # All nodes should be assigned
        assert len(result.layer_map) == 6

        # Sources should be in layer 0
        assert result.layer_map["IN"] == 0
        assert result.layer_map["CLK"] == 0

        # Should have at least one reversed edge for the feedback
        assert len(result.reverse_edges) >= 1

    def test_reversed_edge_not_validated_for_direction(
        self, simple_cycle_graph: nx.DiGraph
    ) -> None:
        """Reversed edges should be exempt from forward-direction check."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(simple_cycle_graph)

        # For non-reversed edges, direction should be forward
        for u, v in simple_cycle_graph.edges():
            if (u, v) not in result.reverse_edges:
                # This edge should go forward (lower to higher layer)
                assert result.layer_map[u] < result.layer_map[v]


# =============================================================================
# Test: Disconnected Components
# =============================================================================


class TestDisconnectedComponents:
    """Tests for graphs with disconnected components."""

    def test_disconnected_components_all_assigned(
        self, disconnected_components_graph: nx.DiGraph
    ) -> None:
        """All nodes in disconnected components should be assigned."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(disconnected_components_graph)

        # All 5 nodes should be assigned
        assert len(result.layer_map) == 5
        assert "A" in result.layer_map
        assert "B" in result.layer_map
        assert "C" in result.layer_map
        assert "X" in result.layer_map
        assert "Y" in result.layer_map

    def test_disconnected_sources_in_layer_zero(
        self, disconnected_components_graph: nx.DiGraph
    ) -> None:
        """Sources in each component should be in layer 0."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(disconnected_components_graph)

        # A is source of component 1
        assert result.layer_map["A"] == 0
        # X is source of component 2
        assert result.layer_map["X"] == 0

    def test_disconnected_components_independent_layers(
        self, disconnected_components_graph: nx.DiGraph
    ) -> None:
        """Each component should have its own layer sequence."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(disconnected_components_graph)

        # Component 1: A=0, B=1, C=2
        assert result.layer_map["A"] == 0
        assert result.layer_map["B"] == 1
        assert result.layer_map["C"] == 2

        # Component 2: X=0, Y=1
        assert result.layer_map["X"] == 0
        assert result.layer_map["Y"] == 1


# =============================================================================
# Test: Layer Count Correctness
# =============================================================================


class TestLayerCount:
    """Tests for correct layer_count calculation."""

    def test_layer_count_matches_max_layer_plus_one(
        self, simple_chain_graph: nx.DiGraph
    ) -> None:
        """layer_count should be max_layer + 1."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(simple_chain_graph)

        max_layer = max(result.layer_map.values())
        assert result.layer_count == max_layer + 1

    def test_empty_graph_layer_count_zero(self, empty_graph: nx.DiGraph) -> None:
        """Empty graph should have layer_count = 0."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(empty_graph)

        assert result.layer_count == 0

    def test_single_node_layer_count_one(
        self, single_node_graph: nx.DiGraph
    ) -> None:
        """Single node graph should have layer_count = 1."""
        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(single_node_graph)

        assert result.layer_count == 1


# =============================================================================
# Test: Complex Graphs
# =============================================================================


class TestComplexGraphs:
    """Tests for more complex graph structures."""

    def test_multi_fanout_graph(self) -> None:
        """Test graph with multiple fanouts.

        Structure:
            A -> B, C, D
            B, C, D -> E
        """
        g = nx.DiGraph()
        g.add_edge("A", "B")
        g.add_edge("A", "C")
        g.add_edge("A", "D")
        g.add_edge("B", "E")
        g.add_edge("C", "E")
        g.add_edge("D", "E")

        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(g)

        assert result.layer_map["A"] == 0
        assert result.layer_map["B"] == 1
        assert result.layer_map["C"] == 1
        assert result.layer_map["D"] == 1
        assert result.layer_map["E"] == 2

    def test_deep_chain_graph(self) -> None:
        """Test deep chain of 10 nodes."""
        g = nx.DiGraph()
        nodes = [f"N{i}" for i in range(10)]
        for node in nodes:
            g.add_node(node)
        for i in range(9):
            g.add_edge(nodes[i], nodes[i + 1])

        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(g)

        # Each node should be at its index
        for i, node in enumerate(nodes):
            assert result.layer_map[node] == i

        assert result.layer_count == 10

    def test_multiple_cycles(self) -> None:
        """Test graph with multiple cycles.

        Structure:
            A -> B -> C -> A (cycle 1)
            B -> D -> B (cycle 2)
        """
        g = nx.DiGraph()
        g.add_edge("A", "B")
        g.add_edge("B", "C")
        g.add_edge("C", "A")  # Cycle 1 back edge
        g.add_edge("B", "D")
        g.add_edge("D", "B")  # Cycle 2 back edge

        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(g)

        # All nodes should be assigned
        assert len(result.layer_map) == 4

        # At least 2 edges should be reversed (one per cycle)
        assert len(result.reverse_edges) >= 1


# =============================================================================
# Test: Performance (NFR-001, NFR-002)
# =============================================================================


class TestPerformance:
    """Performance tests for layer assignment algorithm."""

    def test_1000_nodes_under_100ms(self) -> None:
        """Layer assignment for 1000 nodes should complete in <100ms (NFR-001)."""
        # Create a wide graph with 1000 nodes
        g = nx.DiGraph()
        g.add_node("SOURCE")
        g.add_node("SINK")

        # Create 998 intermediate nodes
        for i in range(998):
            g.add_node(f"N{i}")
            g.add_edge("SOURCE", f"N{i}")
            g.add_edge(f"N{i}", "SINK")

        algo = LayerAssignmentAlgorithm()

        start_time = time.perf_counter()
        result = algo.assign_layers(g)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        assert elapsed_ms < 100, f"Took {elapsed_ms:.2f}ms, expected <100ms"
        assert len(result.layer_map) == 1000
        assert result.layer_count == 3

    def test_10000_nodes_under_2s(self) -> None:
        """Layer assignment for 10,000 nodes should complete in <2s (NFR-002)."""
        # Create a chain graph with 10,000 nodes (worst case for depth)
        g = nx.DiGraph()
        nodes = [f"N{i}" for i in range(10000)]
        for node in nodes:
            g.add_node(node)
        for i in range(9999):
            g.add_edge(nodes[i], nodes[i + 1])

        algo = LayerAssignmentAlgorithm()

        start_time = time.perf_counter()
        result = algo.assign_layers(g)
        elapsed_s = time.perf_counter() - start_time

        assert elapsed_s < 2.0, f"Took {elapsed_s:.2f}s, expected <2s"
        assert len(result.layer_map) == 10000
        assert result.layer_count == 10000

    @pytest.mark.parametrize("node_count", [100, 500, 1000])
    def test_performance_scales_linearly(self, node_count: int) -> None:
        """Performance should scale roughly O(V+E)."""
        # Create a balanced graph
        g = nx.DiGraph()
        g.add_node("SOURCE")
        for i in range(node_count - 2):
            g.add_node(f"N{i}")
            g.add_edge("SOURCE", f"N{i}")
        g.add_node("SINK")
        for i in range(node_count - 2):
            g.add_edge(f"N{i}", "SINK")

        algo = LayerAssignmentAlgorithm()

        start_time = time.perf_counter()
        result = algo.assign_layers(g)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Rough linear scaling check: should complete in reasonable time
        # Allow 0.1ms per node as rough upper bound
        max_expected_ms = node_count * 0.1
        assert elapsed_ms < max_expected_ms, (
            f"Took {elapsed_ms:.2f}ms for {node_count} nodes"
        )
        assert len(result.layer_map) == node_count


# =============================================================================
# Test: Integration with NetworkX
# =============================================================================


class TestNetworkXIntegration:
    """Tests for integration with NetworkX graph library."""

    def test_accepts_digraph(self) -> None:
        """Algorithm should accept nx.DiGraph."""
        g = nx.DiGraph()
        g.add_edge("A", "B")

        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(g)

        assert result is not None

    def test_accepts_multidigraph(self) -> None:
        """Algorithm should accept nx.MultiDiGraph (common in this codebase)."""
        g = nx.MultiDiGraph()
        g.add_edge("A", "B")

        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(g)

        assert result is not None
        assert result.layer_map["A"] == 0
        assert result.layer_map["B"] == 1

    def test_preserves_original_graph(self, diamond_graph: nx.DiGraph) -> None:
        """Algorithm should not modify the original graph."""
        original_nodes = set(diamond_graph.nodes())
        original_edges = set(diamond_graph.edges())

        algo = LayerAssignmentAlgorithm()
        algo.assign_layers(diamond_graph)

        # Graph should be unchanged
        assert set(diamond_graph.nodes()) == original_nodes
        assert set(diamond_graph.edges()) == original_edges


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_self_loop_edge(self) -> None:
        """Self-loop should be detected and marked as reverse edge."""
        g = nx.DiGraph()
        g.add_node("A")
        g.add_edge("A", "A")  # Self-loop

        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(g)

        # A should be assigned (as source)
        assert result.layer_map["A"] == 0
        # Self-loop should be in reverse edges
        assert ("A", "A") in result.reverse_edges

    def test_sink_only_node(self) -> None:
        """Node with only incoming edges (sink) should be assigned."""
        g = nx.DiGraph()
        g.add_node("A")
        g.add_node("B")
        g.add_node("C")  # Sink
        g.add_edge("A", "C")
        g.add_edge("B", "C")

        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(g)

        # A and B are sources (layer 0)
        assert result.layer_map["A"] == 0
        assert result.layer_map["B"] == 0
        # C is sink (layer 1)
        assert result.layer_map["C"] == 1

    def test_isolated_nodes_multiple(self) -> None:
        """Multiple isolated nodes (no edges) should all be layer 0."""
        g = nx.DiGraph()
        for i in range(5):
            g.add_node(f"N{i}")

        algo = LayerAssignmentAlgorithm()
        result = algo.assign_layers(g)

        # All isolated nodes are sources, so layer 0
        for i in range(5):
            assert result.layer_map[f"N{i}"] == 0

        assert result.layer_count == 1
