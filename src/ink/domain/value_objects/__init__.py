"""Value objects for the domain layer.

Value objects are immutable objects that represent concepts in the domain
without identity. They are defined by their attributes rather than by a
unique identifier.
"""

from ink.domain.value_objects.net import NetInfo, NetType

__all__ = ["NetInfo", "NetType"]
