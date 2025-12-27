"""Domain services module.

This module contains domain service interfaces (protocols) that define
the contracts for core business logic operations. These interfaces are
implemented by the infrastructure layer.

Domain services follow the Protocol pattern from Python's typing module,
enabling structural typing (duck typing with type hints) and easy testing
through mock implementations.

Available Protocols:
    GraphTraverser: Protocol for graph-based connectivity queries
    PinDirectionService: Query interface for pin direction lookups
    LatchIdentifier: Protocol for sequential element detection

See Also:
    - ink.infrastructure.services: Infrastructure implementations
    - ink.infrastructure.graph: Graph traversal implementations
    - docs/architecture/ddd-architecture.md: DDD design patterns
"""

from ink.domain.services.graph_traverser import GraphTraverser
from ink.domain.services.latch_identifier import (
    DetectionStrategy,
    LatchIdentifier,
    SequentialDetectionResult,
)
from ink.domain.services.pin_direction_service import PinDirectionService

__all__ = [
    "DetectionStrategy",
    "GraphTraverser",
    "LatchIdentifier",
    "PinDirectionService",
    "SequentialDetectionResult",
]
