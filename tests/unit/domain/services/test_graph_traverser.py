"""Unit tests for GraphTraverser protocol - TDD RED phase.

These tests define the expected behavior of the GraphTraverser protocol
and verify that implementations satisfy the protocol's structural typing.

The GraphTraverser protocol defines the interface for graph traversal
operations used by application services (expansion, selection, search).

Test Coverage Goals:
- Protocol structural typing verification
- Method signature validation
- Return type expectations

Architecture:
    Layer: Domain Layer (Protocol Interface)
    Pattern: Protocol (structural typing)
    Purpose: Enables dependency inversion - domain defines interface,
             infrastructure provides implementation
"""

from typing import Protocol


class TestGraphTraverserProtocol:
    """Tests for GraphTraverser protocol definition."""

    def test_graph_traverser_can_be_imported(self) -> None:
        """GraphTraverser protocol should be importable from domain services."""
        from ink.domain.services import GraphTraverser

        # Verify it exists and is a class
        assert GraphTraverser is not None

    def test_graph_traverser_is_protocol(self) -> None:
        """GraphTraverser should be a typing.Protocol."""
        from ink.domain.services import GraphTraverser

        # Check that it's a Protocol subclass
        assert issubclass(GraphTraverser, Protocol)

    def test_graph_traverser_is_runtime_checkable(self) -> None:
        """GraphTraverser should be runtime_checkable for isinstance checks."""
        from ink.domain.services import GraphTraverser

        # Should support isinstance/issubclass at runtime
        # This requires @runtime_checkable decorator
        assert hasattr(GraphTraverser, "__protocol_attrs__") or hasattr(
            GraphTraverser, "_is_runtime_protocol"
        )


class TestGraphTraverserMethods:
    """Tests for GraphTraverser protocol method signatures."""

    def test_has_get_connected_cells_method(self) -> None:
        """GraphTraverser should define get_connected_cells method."""
        from ink.domain.services import GraphTraverser

        # Verify method exists in protocol
        assert hasattr(GraphTraverser, "get_connected_cells")

    def test_has_get_cell_pins_method(self) -> None:
        """GraphTraverser should define get_cell_pins method."""
        from ink.domain.services import GraphTraverser

        assert hasattr(GraphTraverser, "get_cell_pins")

    def test_has_get_pin_net_method(self) -> None:
        """GraphTraverser should define get_pin_net method."""
        from ink.domain.services import GraphTraverser

        assert hasattr(GraphTraverser, "get_pin_net")

    def test_has_get_fanout_cells_method(self) -> None:
        """GraphTraverser should define get_fanout_cells method."""
        from ink.domain.services import GraphTraverser

        assert hasattr(GraphTraverser, "get_fanout_cells")

    def test_has_get_fanin_cells_method(self) -> None:
        """GraphTraverser should define get_fanin_cells method."""
        from ink.domain.services import GraphTraverser

        assert hasattr(GraphTraverser, "get_fanin_cells")

    def test_has_get_fanout_from_pin_method(self) -> None:
        """GraphTraverser should define get_fanout_from_pin method."""
        from ink.domain.services import GraphTraverser

        assert hasattr(GraphTraverser, "get_fanout_from_pin")

    def test_has_get_fanin_to_pin_method(self) -> None:
        """GraphTraverser should define get_fanin_to_pin method."""
        from ink.domain.services import GraphTraverser

        assert hasattr(GraphTraverser, "get_fanin_to_pin")

    def test_has_find_path_method(self) -> None:
        """GraphTraverser should define find_path method."""
        from ink.domain.services import GraphTraverser

        assert hasattr(GraphTraverser, "find_path")
