"""Layout infrastructure module for Sugiyama hierarchical layout algorithm.

This module implements the layout phases of the Sugiyama algorithm for schematic
visualization:
1. Layer Assignment - Assign cells to horizontal layers (this task)
2. Crossing Minimization - Reduce edge crossings within layers
3. Coordinate Assignment - Compute final X/Y positions

Architecture:
    Layer: Infrastructure Layer
    Pattern: Algorithm implementations
    Bounded Context: Schematic Context
"""

from ink.infrastructure.layout.layer_assignment import (
    LayerAssignment,
    LayerAssignmentAlgorithm,
)

__all__ = [
    "LayerAssignment",
    "LayerAssignmentAlgorithm",
]
