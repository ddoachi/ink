"""Graph infrastructure module for NetworkX graph building and traversal.

This module provides the infrastructure layer implementation for building
and manipulating NetworkX graphs from the domain model entities.

Classes:
    NetworkXGraphBuilder: Builds NetworkX MultiDiGraph from Design aggregate

Example:
    >>> from ink.infrastructure.graph import NetworkXGraphBuilder
    >>> from ink.domain.model import Design
    >>>
    >>> design = Design(name="my_design")
    >>> # ... add entities to design ...
    >>> builder = NetworkXGraphBuilder()
    >>> graph = builder.build_from_design(design)
"""

from ink.infrastructure.graph.networkx_adapter import NetworkXGraphBuilder

__all__ = [
    "NetworkXGraphBuilder",
]
