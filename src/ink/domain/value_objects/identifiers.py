"""Identifier value objects for the domain layer.

This module defines strongly-typed identifier types using NewType to provide
compile-time type safety without runtime overhead. These identifiers are used
throughout the domain layer to uniquely identify domain entities.

The NewType approach provides several benefits:
- Type safety at static analysis time (mypy catches type errors)
- Zero runtime overhead (compiles to plain strings)
- Clear semantic distinction between different ID types
- Simple serialization (just strings)

ID Types:
    CellId: Unique identifier for cell instances (e.g., "XI1", "XFF1")
    NetId: Unique identifier for nets/wires (e.g., "net_123", "clk")
    PinId: Unique identifier for pins (e.g., "XI1.A", "XFF1.CLK")
    PortId: Unique identifier for top-level ports (e.g., "IN", "OUT[7]")

Example:
    >>> from ink.domain.value_objects.identifiers import CellId, NetId
    >>> cell_id = CellId("XI1")
    >>> net_id = NetId("net_123")
    >>> # Type checker will catch mixing different ID types:
    >>> # some_function_expecting_cell_id(net_id)  # Error!

Note:
    Validation of IDs (non-empty, format checks) is handled at the aggregate
    root level (Design), not in these types. This keeps the value objects
    simple and follows the principle of validation at system boundaries.
"""

from typing import NewType

# CellId uniquely identifies a cell instance in a design.
# Format: Instance name from CDL, e.g., "XI1", "XI_CORE/U_ALU/XI_ADD"
# Hierarchical names use '/' as separator.
CellId = NewType("CellId", str)

# NetId uniquely identifies a net (wire) in a design.
# Format: Net name from CDL, e.g., "net_123", "clk", "data[7]"
# Bus bits use '[N]' notation after normalization.
NetId = NewType("NetId", str)

# PinId uniquely identifies a pin on a cell instance.
# Format: Typically "instance_name.pin_name", e.g., "XI1.A", "XFF1.CLK"
# Can also be just pin name for ports: "A", "Y"
PinId = NewType("PinId", str)

# PortId uniquely identifies a top-level I/O port of the design.
# Format: Port name from CDL, e.g., "IN", "OUT", "DATA[31:0]"
PortId = NewType("PortId", str)

__all__ = [
    "CellId",
    "NetId",
    "PinId",
    "PortId",
]
