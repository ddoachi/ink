"""Port entity for the domain layer.

This module defines the Port entity, which represents a top-level I/O interface
of a design. Ports are the external connection points that define how the design
communicates with the outside world.

Each port has:
- id: Unique identifier for the port
- name: Port name as it appears in the interface
- direction: INPUT, OUTPUT, or INOUT
- net_id: Connected internal net, or None if unconnected

The Port entity is immutable (frozen dataclass) following DDD patterns.

Architecture:
    This entity lives in the domain layer with no external dependencies.
    It is used by the Design aggregate to represent the top-level interface.

Example:
    >>> from ink.domain.model.port import Port
    >>> from ink.domain.value_objects.identifiers import PortId, NetId
    >>> from ink.domain.value_objects.pin_direction import PinDirection
    >>>
    >>> # Create an input port
    >>> clk_port = Port(
    ...     id=PortId("CLK"),
    ...     name="CLK",
    ...     direction=PinDirection.INPUT,
    ...     net_id=NetId("clk_internal")
    ... )
    >>> clk_port.is_input_port()
    True
    >>> clk_port.is_output_port()
    False
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink.domain.value_objects.identifiers import NetId, PortId
    from ink.domain.value_objects.pin_direction import PinDirection


@dataclass(frozen=True, slots=True)
class Port:
    """Port entity representing a top-level I/O of the design.

    Ports define the external interface of a design. Each port has a
    direction indicating whether it's an input, output, or bidirectional
    signal. Ports connect to internal nets to route signals within the design.

    This is a frozen dataclass, meaning:
    - All fields are immutable after creation
    - Instances are hashable (can be used in sets/dicts)
    - Equality is based on all field values

    Attributes:
        id: Unique identifier for this port (e.g., "CLK", "DATA[7]").
        name: Port name as it appears in the design interface.
            For buses, might include index notation (e.g., "DATA[7]").
        direction: Port direction indicating signal flow:
            - INPUT: External signal into the design
            - OUTPUT: Internal signal out of the design
            - INOUT: Bidirectional (e.g., GPIO, pad interface)
        net_id: ID of the internal net connected to this port, or None
            if the port is not connected internally (unusual but possible).

    Example:
        >>> port = Port(
        ...     id=PortId("OUT"),
        ...     name="OUT",
        ...     direction=PinDirection.OUTPUT,
        ...     net_id=NetId("output_net")
        ... )
        >>> port.is_output_port()
        True
    """

    # Unique identifier for this port
    id: PortId

    # Port name as it appears in the interface
    name: str

    # Signal flow direction: INPUT, OUTPUT, or INOUT
    direction: PinDirection

    # Connected internal net ID, or None if not connected
    net_id: NetId | None

    def is_input_port(self) -> bool:
        """Check if this port is an input to the design.

        Returns True for INPUT and INOUT ports, as both can receive
        external signals. This delegates to the PinDirection.is_input()
        method for consistent behavior.

        This method is useful for:
        - Identifying input ports for stimulus application
        - Finding ports that can receive external signals
        - Filtering ports by direction

        Returns:
            True if this port can receive signals (INPUT or INOUT),
            False if this is a pure OUTPUT port.

        Example:
            >>> input_port = Port(id=PortId("IN"), name="IN",
            ...                   direction=PinDirection.INPUT, net_id=None)
            >>> input_port.is_input_port()
            True
            >>>
            >>> output_port = Port(id=PortId("OUT"), name="OUT",
            ...                    direction=PinDirection.OUTPUT, net_id=None)
            >>> output_port.is_input_port()
            False
        """
        return self.direction.is_input()

    def is_output_port(self) -> bool:
        """Check if this port is an output from the design.

        Returns True for OUTPUT and INOUT ports, as both can drive
        external signals. This delegates to the PinDirection.is_output()
        method for consistent behavior.

        This method is useful for:
        - Identifying output ports for signal observation
        - Finding ports that can drive external signals
        - Filtering ports by direction

        Returns:
            True if this port can drive signals (OUTPUT or INOUT),
            False if this is a pure INPUT port.

        Example:
            >>> output_port = Port(id=PortId("OUT"), name="OUT",
            ...                    direction=PinDirection.OUTPUT, net_id=None)
            >>> output_port.is_output_port()
            True
            >>>
            >>> input_port = Port(id=PortId("IN"), name="IN",
            ...                   direction=PinDirection.INPUT, net_id=None)
            >>> input_port.is_output_port()
            False
        """
        return self.direction.is_output()

    def __repr__(self) -> str:
        """Return detailed string representation for debugging.

        Returns:
            String like: Port(id='CLK', name='CLK', direction=INPUT, net_id='clk_net')
        """
        return (
            f"Port(id={self.id!r}, name={self.name!r}, "
            f"direction={self.direction.name}, net_id={self.net_id!r})"
        )

    def __str__(self) -> str:
        """Return human-readable string representation.

        Returns:
            String like: CLK (INPUT) -> clk_net
            or: CLK (INPUT) [not connected]
        """
        if self.net_id is not None:
            return f"{self.name} ({self.direction.name}) -> {self.net_id}"
        return f"{self.name} ({self.direction.name}) [not connected]"
