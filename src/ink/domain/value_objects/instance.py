"""Cell instance value object for CDL parsing.

This module defines the CellInstance value object, which represents a cell
instantiation parsed from X-prefixed lines in CDL files. It is an immutable
data structure following Domain-Driven Design principles.

A cell instance contains:
- name: The instance name (e.g., "XI1", "XI_CORE/U_ALU/XI_ADD")
- cell_type: The cell type reference (e.g., "INV", "NAND2_X1")
- connections: Port-to-net mapping (e.g., {"A": "net1", "Y": "net2"})

The value object enforces invariants:
- Name must not be empty
- Name must start with 'X' (case-insensitive)
- Cell type must not be empty
- Connections dict is immutable (MappingProxyType)

Usage:
    # Creating a cell instance
    instance = CellInstance(
        name="XI1",
        cell_type="INV",
        connections={"A": "net1", "Y": "net2", "VDD": "VDD", "VSS": "VSS"}
    )

    # Accessing properties
    print(instance.name)        # "XI1"
    print(instance.cell_type)   # "INV"
    print(instance.connections) # {"A": "net1", "Y": "net2", ...}

    # Value objects are immutable
    instance.name = "NEW"       # Raises AttributeError

Architecture:
    This value object lives in the domain layer and has no external dependencies.
    It is created by the InstanceParser (infrastructure) and used by domain
    services for graph building and schematic visualization.

CDL Format Reference:
    Instance lines in CDL follow the format:
        X<instance_name> net1 net2 ... netN cell_type

Example:
        XI1 input output VDD VSS INV

    The instance name MUST start with 'X' (or 'x') per SPICE convention.
    This distinguishes instances from other elements like transistors (M),
    resistors (R), capacitors (C), etc.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class CellInstance:
    """Immutable cell instance from CDL X-prefixed lines.

    Represents a cell instantiation parsed from a CDL file. This is a value
    object - it has no identity and is defined entirely by its attribute values.

    Attributes:
        name: Instance name exactly as specified in CDL (case-preserved).
              Must start with 'X' or 'x' per SPICE convention.
              May contain hierarchy separators ('/') for nested instances.
              Examples: "XI1", "xI1", "XI_CORE/U_ALU/XI_ADD"
        cell_type: Cell type reference exactly as specified in CDL (case-preserved).
                   References a subcircuit definition.
                   Examples: "INV", "NAND2_X1", "my_custom_cell"
        connections: Immutable mapping of port names to net names.
                     Created from positional net list using subcircuit definition.
                     Wrapped in MappingProxyType for immutability.

    Examples:
        >>> instance = CellInstance(
        ...     name="XI1",
        ...     cell_type="INV",
        ...     connections={"A": "net1", "Y": "net2"}
        ... )
        >>> instance.name
        'XI1'
        >>> instance.connections["A"]
        'net1'

    Raises:
        ValueError: If name is empty, doesn't start with 'X', or cell_type is empty.
    """

    # Instance name must start with X (SPICE convention for subcircuit instances)
    name: str

    # Cell type reference (must exist as a subcircuit definition)
    cell_type: str

    # Port-to-net mapping (immutable after creation)
    connections: MappingProxyType[str, str]

    def __init__(
        self,
        name: str,
        cell_type: str,
        connections: Mapping[str, str],
    ) -> None:
        """Initialize a CellInstance with validation.

        This custom __init__ is needed because:
        1. We need to validate invariants before storing
        2. We wrap connections dict in MappingProxyType for immutability
        3. frozen=True prevents normal assignment, so we use object.__setattr__

        Args:
            name: The instance name. Must not be empty and must start with 'X' or 'x'.
            cell_type: The cell type reference. Must not be empty.
            connections: Mapping of port names to net names. Will be copied and
                        made immutable via MappingProxyType.

        Raises:
            ValueError: If name is empty, doesn't start with 'X', or cell_type is empty.
        """
        # Validate name is not empty
        if not name:
            raise ValueError("Instance name cannot be empty")

        # Validate name starts with X (case-insensitive)
        # SPICE convention: X prefix indicates subcircuit instance
        if not name[0].upper() == "X":
            raise ValueError(
                f"Instance name {name!r} must start with 'X' "
                "(SPICE convention for subcircuit instances)"
            )

        # Validate cell_type is not empty
        if not cell_type:
            raise ValueError(f"Instance {name!r} missing cell type")

        # Create an immutable copy of connections using MappingProxyType
        # This ensures the connections dict cannot be modified after creation,
        # maintaining the value object's immutability guarantee
        frozen_connections = MappingProxyType(dict(connections))

        # Use object.__setattr__ because frozen=True prevents normal assignment
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "cell_type", cell_type)
        object.__setattr__(self, "connections", frozen_connections)

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging.

        Returns:
            String like: CellInstance(name='XI1', cell_type='INV', connections={...})
        """
        # Convert MappingProxyType back to dict for cleaner repr
        conn_dict = dict(self.connections)
        return (
            f"CellInstance(name={self.name!r}, "
            f"cell_type={self.cell_type!r}, "
            f"connections={conn_dict!r})"
        )

    def __str__(self) -> str:
        """Return a human-readable string representation.

        Mimics the CDL format for familiarity.

        Returns:
            String like: XI1 (INV): A=net1, Y=net2
        """
        if not self.connections:
            return f"{self.name} ({self.cell_type})"

        # Format connections as "port=net" pairs
        conn_str = ", ".join(
            f"{port}={net}" for port, net in self.connections.items()
        )
        return f"{self.name} ({self.cell_type}): {conn_str}"

    def __hash__(self) -> int:
        """Return hash based on all attributes for set/dict usage.

        The hash includes name, cell_type, and connections to ensure
        that two instances with identical data have the same hash.

        Note: connections is a MappingProxyType, which is not directly hashable.
        We convert it to a frozenset of items for hashing.
        """
        # Convert connections to hashable frozenset
        conn_items = frozenset(self.connections.items())
        return hash((self.name, self.cell_type, conn_items))

    def __eq__(self, other: object) -> bool:
        """Check equality based on all attributes.

        Two CellInstance objects are equal if they have the same
        name, cell_type, and connections.

        Args:
            other: Object to compare against

        Returns:
            True if other is a CellInstance with identical attributes
        """
        if not isinstance(other, CellInstance):
            return NotImplemented
        return (
            self.name == other.name
            and self.cell_type == other.cell_type
            and dict(self.connections) == dict(other.connections)
        )
