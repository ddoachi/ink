"""Design aggregate root for circuit representation.

This module defines the Design class, which is the root aggregate for a circuit
design parsed from CDL files. Following Domain-Driven Design principles, the
Design aggregate encapsulates:

- Subcircuit definitions (cell types with port lists)
- Cell instances (instantiations of cell types with connections)
- Nets (connectivity information with normalization and classification)
- Top-level ports (I/O interface of the design)

The Design aggregate provides a consistent interface for querying and
manipulating the circuit structure, with all modifications going through
well-defined methods to maintain invariants.

Architecture:
    The Design class lives in the domain layer and has no external dependencies
    outside the domain. It is created by infrastructure parsers (CDLParser) and
    consumed by application services for graph building, schematic rendering,
    and navigation.

Usage:
    # Creating a design (typically done by CDLParser)
    design = Design(
        name="top_module",
        subcircuit_defs={"INV": inv_def, "NAND2": nand_def},
        instances={"XI1": instance1, "XI2": instance2},
        nets={"clk": clk_net, "VDD": vdd_net},
        top_level_ports=["IN", "OUT", "VDD", "VSS"],
    )

    # Querying the design
    inv_instances = design.get_instances_by_type("INV")
    power_nets = design.get_nets_by_type(NetType.POWER)

    # Modifying the design
    design.add_instance(new_instance)
    design.add_net("new_net", new_net_info)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink.domain.value_objects.instance import CellInstance
    from ink.domain.value_objects.net import NetInfo, NetType
    from ink.domain.value_objects.subcircuit import SubcircuitDefinition


@dataclass
class Design:
    """Root aggregate for a circuit design.

    The Design aggregate is the central data structure for representing a
    parsed CDL netlist. It contains all the information needed for schematic
    visualization, navigation, and analysis.

    This class is mutable (not frozen) to support incremental construction
    during parsing and modification during design exploration.

    Attributes:
        name: The design name, typically derived from the CDL filename.
              Example: "top_module", "test_design"
        subcircuit_defs: Dictionary mapping cell type names to their
                        SubcircuitDefinition objects. These define the
                        interface (ports) of each cell type.
        instances: Dictionary mapping instance names to CellInstance objects.
                   Each instance represents a cell instantiation in the design.
        nets: Dictionary mapping net names to NetInfo objects.
              Contains normalized net information including type classification.
        top_level_ports: List of top-level port names for the design.
                        These define the I/O interface of the entire design.

    Example:
        >>> design = Design(name="inverter_chain")
        >>> design.add_instance(CellInstance("XI1", "INV", {"A": "in", "Y": "out"}))
        >>> print(design.instance_count)
        1
    """

    # Design name (from filename or explicit)
    name: str

    # Cell type definitions: cell_type_name -> SubcircuitDefinition
    # Stores the port interface for each cell type used in the design
    subcircuit_defs: dict[str, SubcircuitDefinition] = field(default_factory=dict)

    # Cell instances: instance_name -> CellInstance
    # All instantiated cells in the design with their connections
    instances: dict[str, CellInstance] = field(default_factory=dict)

    # Net information: net_name -> NetInfo
    # All unique nets with normalization and classification
    nets: dict[str, NetInfo] = field(default_factory=dict)

    # Top-level I/O ports of the design
    top_level_ports: list[str] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # Instance Management
    # -------------------------------------------------------------------------

    def add_instance(self, instance: CellInstance) -> None:
        """Add a cell instance to the design.

        Validates that the instance name is unique before adding. This ensures
        the design maintains consistent state with no duplicate instances.

        Args:
            instance: The CellInstance to add to the design. The instance name
                     must not already exist in the design.

        Raises:
            ValueError: If an instance with the same name already exists.

        Example:
            >>> design = Design(name="test")
            >>> design.add_instance(CellInstance("XI1", "INV", {"A": "n1", "Y": "n2"}))
            >>> "XI1" in design.instances
            True
        """
        if instance.name in self.instances:
            raise ValueError(f"Duplicate instance name: {instance.name}")
        self.instances[instance.name] = instance

    def get_instance(self, name: str) -> CellInstance | None:
        """Retrieve a cell instance by name.

        Args:
            name: The exact instance name to look up (case-sensitive).

        Returns:
            The CellInstance if found, None otherwise.

        Example:
            >>> inst = design.get_instance("XI1")
            >>> if inst:
            ...     print(f"Cell type: {inst.cell_type}")
        """
        return self.instances.get(name)

    def get_instances_by_type(self, cell_type: str) -> list[CellInstance]:
        """Find all instances of a specific cell type.

        Useful for analyzing usage of specific cell types, such as finding
        all flip-flops or all inverters in a design.

        Args:
            cell_type: The cell type name to filter by (case-sensitive).

        Returns:
            List of CellInstance objects matching the cell type.
            Empty list if no matches found.

        Example:
            >>> inverters = design.get_instances_by_type("INV")
            >>> print(f"Found {len(inverters)} inverters")
        """
        return [
            inst for inst in self.instances.values() if inst.cell_type == cell_type
        ]

    # -------------------------------------------------------------------------
    # Net Management
    # -------------------------------------------------------------------------

    def add_net(self, name: str, net_info: NetInfo) -> None:
        """Add a net to the design.

        Unlike instances, duplicate net names are allowed (overwrites existing).
        This supports updating net information during parsing.

        Args:
            name: The net name (key for lookup).
            net_info: The NetInfo object with normalization and classification.

        Example:
            >>> design.add_net("clk", NetInfo("clk", "clk", NetType.SIGNAL, False))
        """
        self.nets[name] = net_info

    def get_net(self, name: str) -> NetInfo | None:
        """Retrieve net information by name.

        Args:
            name: The net name to look up.

        Returns:
            The NetInfo if found, None otherwise.
        """
        return self.nets.get(name)

    def get_nets_by_type(self, net_type: NetType) -> list[NetInfo]:
        """Find all nets of a specific type.

        Useful for filtering power/ground nets from display or finding
        all signal nets for analysis.

        Args:
            net_type: The NetType enum value to filter by.

        Returns:
            List of NetInfo objects matching the net type.
            Empty list if no matches found.

        Example:
            >>> from ink.domain.value_objects.net import NetType
            >>> power_nets = design.get_nets_by_type(NetType.POWER)
        """
        return [net for net in self.nets.values() if net.net_type == net_type]

    # -------------------------------------------------------------------------
    # Subcircuit Management
    # -------------------------------------------------------------------------

    def get_subcircuit_def(self, cell_type: str) -> SubcircuitDefinition | None:
        """Retrieve a subcircuit definition by cell type name.

        Args:
            cell_type: The cell type name to look up.

        Returns:
            The SubcircuitDefinition if found, None otherwise.
        """
        return self.subcircuit_defs.get(cell_type)

    # -------------------------------------------------------------------------
    # Statistics Properties
    # -------------------------------------------------------------------------

    @property
    def instance_count(self) -> int:
        """Get the total number of cell instances in the design."""
        return len(self.instances)

    @property
    def net_count(self) -> int:
        """Get the total number of unique nets in the design."""
        return len(self.nets)

    @property
    def subcircuit_count(self) -> int:
        """Get the total number of subcircuit definitions."""
        return len(self.subcircuit_defs)

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return detailed string for debugging.

        Returns:
            String with class name and key attributes.
        """
        return (
            f"Design(name={self.name!r}, "
            f"subcircuits={self.subcircuit_count}, "
            f"instances={self.instance_count}, "
            f"nets={self.net_count})"
        )

    def __str__(self) -> str:
        """Return human-readable summary of the design.

        Returns:
            Multi-line summary with design statistics.
        """
        return (
            f"Design: {self.name}\n"
            f"  Subcircuits: {self.subcircuit_count}\n"
            f"  Instances: {self.instance_count}\n"
            f"  Nets: {self.net_count}\n"
            f"  Ports: {len(self.top_level_ports)}"
        )
