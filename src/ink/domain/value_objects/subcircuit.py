"""Subcircuit definition value object.

This module defines the SubcircuitDefinition value object, which represents a cell type
definition parsed from CDL .SUBCKT blocks. It is an immutable data structure following
Domain-Driven Design principles.

A subcircuit definition contains:
- name: The cell type name (e.g., "INV_X1", "NAND2")
- ports: Ordered list of port names defining the interface (e.g., ["A", "Y", "VDD", "VSS"])

The value object enforces invariants:
- Name must not be empty
- Ports list must have at least one port
- Port names must be unique

Usage:
    # Creating a subcircuit definition
    defn = SubcircuitDefinition(name="INV", ports=["A", "Y", "VDD", "VSS"])

    # Accessing properties
    print(defn.name)   # "INV"
    print(defn.ports)  # ("A", "Y", "VDD", "VSS")

    # Value objects are immutable
    defn.name = "NEW"  # Raises AttributeError

Architecture:
    This value object lives in the domain layer and has no external dependencies.
    It is used by infrastructure parsers to return parsed data and by domain services
    for cell type lookups.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class SubcircuitDefinition:
    """Immutable subcircuit definition from CDL.

    Represents a cell type definition parsed from a .SUBCKT block in CDL format.
    This is a value object - it has no identity and is defined entirely by its
    attribute values.

    Attributes:
        name: Cell type name exactly as specified in CDL (case-sensitive).
              Examples: "INV", "NAND2_X1", "my_custom_cell"
        ports: Ordered tuple of port names defining the cell interface.
               The order is significant as it matches positional connections
               in instance definitions. Stored as tuple for immutability.

    Examples:
        >>> defn = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        >>> defn.name
        'INV'
        >>> defn.ports
        ('A', 'Y')

    Raises:
        ValueError: If name is empty, ports is empty, or ports has duplicates.
    """

    name: str
    ports: tuple[str, ...]

    def __init__(self, name: str, ports: Sequence[str]) -> None:
        """Initialize a SubcircuitDefinition with validation.

        This custom __init__ is needed because:
        1. We accept a Sequence for ports but store it as a tuple
        2. We need to validate invariants before storing

        Args:
            name: The cell type name. Must not be empty.
            ports: Ordered sequence of port names. Must have at least one port
                   and all names must be unique.

        Raises:
            ValueError: If name is empty, ports is empty, or ports has duplicates.
        """
        # Validate name is not empty
        if not name:
            raise ValueError("Subcircuit name cannot be empty")

        # Convert ports to tuple for immutability
        ports_tuple = tuple(ports)

        # Validate at least one port exists
        if not ports_tuple:
            raise ValueError(f"Subcircuit {name} must have at least one port")

        # Check for duplicate port names
        seen: set[str] = set()
        duplicates: list[str] = []
        for port in ports_tuple:
            if port in seen and port not in duplicates:
                duplicates.append(port)
            seen.add(port)

        if duplicates:
            raise ValueError(f"Subcircuit {name} has duplicate port names: {', '.join(duplicates)}")

        # Use object.__setattr__ because frozen=True prevents normal assignment
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "ports", ports_tuple)

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging.

        Returns:
            String like: SubcircuitDefinition(name='INV', ports=('A', 'Y'))
        """
        return f"SubcircuitDefinition(name={self.name!r}, ports={self.ports!r})"

    def __str__(self) -> str:
        """Return a human-readable string representation.

        Returns:
            String like: INV(A, Y, VDD, VSS)
        """
        return f"{self.name}({', '.join(self.ports)})"
