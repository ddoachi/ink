"""Graph infrastructure module for NetworkX graph building and traversal.

This module provides the infrastructure layer implementation for building
and manipulating NetworkX graphs from the domain model entities.

Classes:
    NetworkXGraphBuilder: Builds NetworkX MultiDiGraph from Design aggregate
    NetworkXGraphTraverser: Implements GraphTraverser protocol for queries

Example:
    >>> from ink.infrastructure.graph import NetworkXGraphBuilder, NetworkXGraphTraverser
    >>> from ink.domain.model import Design
    >>>
    >>> design = Design(name="my_design")
    >>> # ... add entities to design ...
    >>> builder = NetworkXGraphBuilder()
    >>> graph = builder.build_from_design(design)
    >>> traverser = NetworkXGraphTraverser(graph, design)
    >>>
    >>> # Query fanout
    >>> fanout = traverser.get_fanout_cells(CellId("XI1"), hops=2)
"""

from ink.infrastructure.graph.networkx_adapter import NetworkXGraphBuilder
from ink.infrastructure.graph.networkx_traverser import NetworkXGraphTraverser

__all__ = [
    "NetworkXGraphBuilder",
    "NetworkXGraphTraverser",
]
