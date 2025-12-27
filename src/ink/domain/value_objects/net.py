"""Net-related value objects for the domain layer.

This module defines immutable value objects used to represent net information
in a normalized, consistent format. These are pure domain objects with no
external dependencies.

Net names in CDL netlists can have various formats:
- Bus notation: data<7>, addr<15:0>
- Power nets: VDD, VDDA, VCC, VPWR
- Ground nets: VSS, GND, VGND
- Trailing markers: VDD!, net1?
- Signal nets: clk, data_valid, reset_n

The NetInfo value object captures the normalized form along with classification
metadata to enable consistent connectivity matching and special net handling.
"""

from dataclasses import dataclass
from enum import Enum


class NetType(Enum):
    """Classification of net types in a CDL netlist.

    Nets are classified into categories to enable special handling:
    - SIGNAL: Normal signal nets (most common)
    - POWER: Power supply nets (VDD, VCC, etc.) - often filtered from display
    - GROUND: Ground reference nets (VSS, GND, etc.) - often filtered from display

    Example:
        >>> net_type = NetType.POWER
        >>> net_type.value
        'power'
    """

    SIGNAL = "signal"  # Normal signal net (data, clock, control)
    POWER = "power"  # Power supply (VDD, VDDA, VCC, VPWR, etc.)
    GROUND = "ground"  # Ground reference (VSS, VSSA, GND, VGND, etc.)


@dataclass(frozen=True)
class NetInfo:
    """Immutable value object representing normalized net information.

    This dataclass captures both the original and normalized forms of a net name,
    along with classification metadata. Being frozen (immutable), it can be safely
    cached and used as dictionary keys or set members.

    Attributes:
        original_name: The raw net name exactly as it appears in the CDL file.
            Example: "data<7>", "VDD!", "addr_15"
        normalized_name: The standardized form after processing.
            Example: "data[7]", "VDD", "addr_15"
            - Bus notation <N> is converted to [N]
            - Trailing special characters (!, ?) are stripped
        net_type: Classification as SIGNAL, POWER, or GROUND.
            Determined by pattern matching against known power/ground net names.
        is_bus: True if this net is part of a bus (has bit index).
            Example: data<7> is a bus bit, clk is not.
        bus_index: The bit index if is_bus is True, None otherwise.
            Example: For "data<7>", bus_index is 7.

    Example:
        >>> info = NetInfo(
        ...     original_name="data<7>",
        ...     normalized_name="data[7]",
        ...     net_type=NetType.SIGNAL,
        ...     is_bus=True,
        ...     bus_index=7
        ... )
        >>> info.normalized_name
        'data[7]'
        >>> info.is_bus
        True
    """

    original_name: str  # Original net name from CDL (e.g., "data<7>", "VDD!")
    normalized_name: str  # Normalized name for matching (e.g., "data[7]", "VDD")
    net_type: NetType  # Classified type (SIGNAL, POWER, or GROUND)
    is_bus: bool  # True if this is a bus bit (has index)
    bus_index: int | None = None  # Index if bus bit, None otherwise
