"""Net entity for the domain layer.

This module defines the Net entity, which represents a wire connecting multiple pins.
Nets are the connectivity fabric of a netlist, linking outputs to inputs across cells.

Each net has:
- id: Unique identifier for the net
- name: Human-readable net name
- connected_pin_ids: Tuple of pins connected to this net

The Net entity is immutable (frozen dataclass) following DDD patterns.

Architecture:
    This entity lives in the domain layer with no external dependencies.
    It is used by the Design aggregate and graph traversal services.

Example:
    >>> from ink.domain.model.net import Net
    >>> from ink.domain.value_objects.identifiers import NetId, PinId
    >>>
    >>> # Create a net connecting multiple pins (fanout)
    >>> net = Net(
    ...     id=NetId("net_123"),
    ...     name="net_123",
    ...     connected_pin_ids=[PinId("XI1.Y"), PinId("XI2.A"), PinId("XI3.A")]
    ... )
    >>> net.is_multi_fanout()
    True
    >>> net.pin_count()
    3

Note:
    The spec mentions `connected_pin_ids: List[PinId]` with `field(default_factory=list)`,
    but for true immutability we use a tuple. Lists inside frozen dataclasses are still
    mutable (their contents can change). Using a tuple ensures complete immutability.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ink.domain.value_objects.identifiers import NetId, PinId


@dataclass(frozen=True, slots=True)
class Net:
    """Net entity representing a wire connecting multiple pins.

    Nets are the connectivity fabric of a netlist. Each net connects
    one or more pins, typically linking an output pin to one or more
    input pins (fanout). A net can also connect to ports for I/O.

    This is a frozen dataclass, meaning:
    - All fields are immutable after creation
    - Instances are hashable (can be used in sets/dicts)
    - Equality is based on all field values

    Attributes:
        id: Unique identifier for this net (e.g., "net_123", "clk").
        name: Human-readable net name, typically matching the id.
            For buses, might include index notation (e.g., "data[7]").
        connected_pin_ids: Tuple of pin IDs connected to this net.
            An empty tuple means the net has no connections (orphan).
            Stored as tuple for complete immutability.

    Example:
        >>> net = Net(
        ...     id=NetId("clk"),
        ...     name="clk",
        ...     connected_pin_ids=[PinId("XI1.CLK"), PinId("XFF1.CLK")]
        ... )
        >>> net.pin_count()
        2
        >>> net.is_multi_fanout()
        True
    """

    # Unique identifier for this net
    id: NetId

    # Human-readable net name
    name: str

    # Pin IDs connected to this net (stored as immutable tuple)
    connected_pin_ids: tuple[PinId, ...]

    def __init__(
        self,
        id: NetId,
        name: str,
        connected_pin_ids: Sequence[PinId] | None = None,
    ) -> None:
        """Initialize a Net with the given attributes.

        This custom __init__ is needed to:
        1. Convert the input sequence to an immutable tuple
        2. Handle the default case of empty pins

        Args:
            id: Unique identifier for this net.
            name: Human-readable net name.
            connected_pin_ids: Sequence of pin IDs connected to this net.
                Defaults to empty tuple if not provided.
        """
        # Use object.__setattr__ because frozen=True prevents normal assignment
        object.__setattr__(self, "id", id)
        object.__setattr__(self, "name", name)

        # Convert to tuple for immutability, or use empty tuple if None
        if connected_pin_ids is None:
            pin_tuple: tuple[PinId, ...] = ()
        else:
            pin_tuple = tuple(connected_pin_ids)
        object.__setattr__(self, "connected_pin_ids", pin_tuple)

    def is_multi_fanout(self) -> bool:
        """Check if this net has multiple connected pins (fanout > 1).

        A multi-fanout net connects more than one pin, which is typical
        for signal distribution (one output driving multiple inputs).

        This method is useful for:
        - Identifying high-fanout nets that may need buffering
        - Analyzing signal distribution in the netlist
        - Visualization decisions (showing fanout as a single wire vs. split)

        Returns:
            True if the net connects more than one pin,
            False if zero or one pin is connected.

        Example:
            >>> fanout_net = Net(id=NetId("clk"), name="clk",
            ...                  connected_pin_ids=[PinId("p1"), PinId("p2")])
            >>> fanout_net.is_multi_fanout()
            True
            >>>
            >>> single_net = Net(id=NetId("n1"), name="n1",
            ...                  connected_pin_ids=[PinId("p1")])
            >>> single_net.is_multi_fanout()
            False
        """
        return len(self.connected_pin_ids) > 1

    def pin_count(self) -> int:
        """Get the number of pins connected to this net.

        Returns the total count of connected pins, which represents
        the fanout of the net.

        Returns:
            Number of pins connected to this net (0 or more).

        Example:
            >>> net = Net(id=NetId("data"), name="data",
            ...           connected_pin_ids=[PinId("p1"), PinId("p2"), PinId("p3")])
            >>> net.pin_count()
            3
        """
        return len(self.connected_pin_ids)

    def __repr__(self) -> str:
        """Return detailed string representation for debugging.

        Returns:
            String like: Net(id='net_123', name='net_123', pins=3)
        """
        return f"Net(id={self.id!r}, name={self.name!r}, pins={len(self.connected_pin_ids)})"

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            String like: net_123 (3 pins)
        """
        return f"{self.name} ({len(self.connected_pin_ids)} pins)"
