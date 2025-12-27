"""Pin entity for the domain layer.

This module defines the Pin entity, which represents a connection point on a cell.
Pins are the fundamental connection points in a netlist, serving as the interface
between cells and nets.

Each pin has:
- id: Unique identifier (typically "instance.pin_name" format)
- name: Pin name (e.g., "A", "Y", "CLK", "D", "Q")
- direction: INPUT, OUTPUT, or INOUT (bidirectional)
- net_id: Connected net, or None if the pin is floating

The Pin entity is immutable (frozen dataclass) following DDD value object patterns,
enabling safe caching, hashing, and functional programming patterns.

Architecture:
    This entity lives in the domain layer with no external dependencies.
    It is used by the Design aggregate and graph traversal services.

Example:
    >>> from ink.domain.model.pin import Pin
    >>> from ink.domain.value_objects.identifiers import PinId, NetId
    >>> from ink.domain.value_objects.pin_direction import PinDirection
    >>>
    >>> # Create a connected input pin
    >>> pin = Pin(
    ...     id=PinId("XI1.A"),
    ...     name="A",
    ...     direction=PinDirection.INPUT,
    ...     net_id=NetId("net_123")
    ... )
    >>> pin.is_connected()
    True
    >>>
    >>> # Create a floating (unconnected) pin
    >>> floating = Pin(
    ...     id=PinId("XI1.NC"),
    ...     name="NC",
    ...     direction=PinDirection.INPUT,
    ...     net_id=None
    ... )
    >>> floating.is_connected()
    False
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink.domain.value_objects.identifiers import NetId, PinId
    from ink.domain.value_objects.pin_direction import PinDirection


@dataclass(frozen=True, slots=True)
class Pin:
    """Pin entity representing a connection point on a cell.

    Pins are the fundamental connection points in a netlist. Each pin
    has a direction (INPUT, OUTPUT, or INOUT) and may be connected to
    a net. Floating pins (not connected) have net_id=None.

    This is a frozen dataclass, meaning:
    - All fields are immutable after creation
    - Instances are hashable (can be used in sets/dicts)
    - Equality is based on all field values

    Attributes:
        id: Unique identifier for this pin. Format is typically
            "instance_name.pin_name" (e.g., "XI1.A", "XFF1.CLK").
        name: Pin name from the cell definition (e.g., "A", "Y", "CLK").
            This is the local name within the cell, not the full path.
        direction: Pin direction indicating signal flow:
            - INPUT: Pin receives signals (e.g., gate input, FF data)
            - OUTPUT: Pin drives signals (e.g., gate output, FF Q)
            - INOUT: Bidirectional (e.g., tri-state buffer, pad)
        net_id: ID of the connected net, or None if the pin is floating.
            Floating pins are typically unused or optional pins.

    Example:
        >>> pin = Pin(
        ...     id=PinId("XI1.A"),
        ...     name="A",
        ...     direction=PinDirection.INPUT,
        ...     net_id=NetId("net_123")
        ... )
        >>> pin.name
        'A'
        >>> pin.is_connected()
        True
    """

    # Unique identifier for this pin (typically instance.pin format)
    id: PinId

    # Pin name from cell definition (local name, not full path)
    name: str

    # Signal flow direction: INPUT, OUTPUT, or INOUT
    direction: PinDirection

    # Connected net ID, or None for floating pins
    net_id: NetId | None

    def is_connected(self) -> bool:
        """Check if this pin is connected to a net.

        A pin is considered connected if its net_id is not None.
        Floating (unconnected) pins return False.

        This method is useful for:
        - Filtering out unconnected pins during graph traversal
        - Identifying potentially problematic floating pins
        - Determining which pins participate in connectivity

        Returns:
            True if the pin is connected to a net (net_id is not None),
            False if the pin is floating (net_id is None).

        Example:
            >>> connected = Pin(id=PinId("p1"), name="A",
            ...                 direction=PinDirection.INPUT,
            ...                 net_id=NetId("net1"))
            >>> connected.is_connected()
            True
            >>>
            >>> floating = Pin(id=PinId("p2"), name="NC",
            ...                direction=PinDirection.INPUT,
            ...                net_id=None)
            >>> floating.is_connected()
            False
        """
        return self.net_id is not None

    def __repr__(self) -> str:
        """Return detailed string representation for debugging.

        Returns:
            String like: Pin(id='XI1.A', name='A', direction=INPUT, net_id='net_123')
        """
        return (
            f"Pin(id={self.id!r}, name={self.name!r}, "
            f"direction={self.direction.name}, net_id={self.net_id!r})"
        )

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            String like: XI1.A (INPUT) -> net_123
            or: XI1.NC (INPUT) [floating]
        """
        if self.net_id is not None:
            return f"{self.id} ({self.direction.name}) -> {self.net_id}"
        return f"{self.id} ({self.direction.name}) [floating]"
