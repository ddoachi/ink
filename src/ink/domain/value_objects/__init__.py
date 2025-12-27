"""Value objects for the domain layer.

Value objects are immutable objects that represent concepts in the domain
without identity. They are defined by their attributes rather than by a
unique identifier.

This module exports:
- Identifier types (CellId, NetId, PinId, PortId) for strong typing
- Geometry types (Point, LineSegment, NetGeometry) for net routing
- PinDirection enum for signal flow direction
- Parsing-related value objects (CellInstance, NetInfo, SubcircuitDefinition)
"""

# Geometry value objects (for net routing representation)
from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

# Identifier types (NewType wrappers for compile-time type safety)
from ink.domain.value_objects.identifiers import CellId, NetId, PinId, PortId

# Parsing-related value objects (used by CDL parser)
from ink.domain.value_objects.instance import CellInstance
from ink.domain.value_objects.net import NetInfo, NetType

# Pin direction enum with helper methods
from ink.domain.value_objects.pin_direction import PinDirection
from ink.domain.value_objects.subcircuit import SubcircuitDefinition

__all__ = [
    "CellId",
    "CellInstance",
    "LineSegment",
    "NetGeometry",
    "NetId",
    "NetInfo",
    "NetType",
    "PinDirection",
    "PinId",
    "Point",
    "PortId",
    "SubcircuitDefinition",
]
