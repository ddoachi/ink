"""Value objects for the domain layer.

Value objects are immutable objects that represent concepts in the domain
without identity. They are defined by their attributes rather than by a
unique identifier.

This module exports:
- Identifier types (CellId, NetId, PinId, PortId) for strong typing
- PinDirection enum for signal flow direction
- Parsing-related value objects (CellInstance, NetInfo, SubcircuitDefinition)
"""

# Identifier types (NewType wrappers for compile-time type safety)
from ink.domain.value_objects.identifiers import CellId, NetId, PinId, PortId

# Parsing-related value objects (used by CDL parser)
from ink.domain.value_objects.instance import CellInstance
from ink.domain.value_objects.net import NetInfo, NetType

# Pin direction enum with helper methods
from ink.domain.value_objects.pin_direction import PinDirection
from ink.domain.value_objects.subcircuit import SubcircuitDefinition

__all__ = [
    # Identifiers
    "CellId",
    # Parsing value objects
    "CellInstance",
    "NetId",
    "NetInfo",
    "NetType",
    # Enums
    "PinDirection",
    "PinId",
    "PortId",
    "SubcircuitDefinition",
]
