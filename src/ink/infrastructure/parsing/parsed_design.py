"""ParsedDesign - Infrastructure representation of parsed CDL data.

This module defines the ParsedDesign class, which is the output of the CDL parser.
It represents the raw parsed data before transformation into domain entities.

Architecture:
    ParsedDesign is an infrastructure-layer data structure that holds:
    - Subcircuit definitions (cell type port lists)
    - Cell instances (instantiations with connections)
    - Net information (normalized names and classifications)
    - Top-level ports

    This is SEPARATE from the domain-layer Design aggregate, which manages
    domain entities (Cell, Pin, Net, Port). The application layer will
    transform ParsedDesign into the domain Design aggregate.

Layer Separation:
    Infrastructure (ParsedDesign) → Application (Builder) → Domain (Design)

    ParsedDesign uses value objects:
    - CellInstance: Instance name, cell type, connections dict
    - NetInfo: Original/normalized names, type classification
    - SubcircuitDefinition: Cell type name and port list

    Domain Design uses entities:
    - Cell: With CellId, is_sequential, pin_ids
    - Pin: With PinId, direction, net_id
    - Net: With NetId, connected_pin_ids
    - Port: With PortId, direction, net_id

Usage:
    # Parser creates ParsedDesign
    parsed = parser.parse_file(path)

    # Application layer transforms to domain Design
    design = DesignBuilder.build(parsed, latch_config)

Note:
    The old Design class was moved to this file to maintain backwards
    compatibility with the CDL parser. The domain-layer Design aggregate
    is now in src/ink/domain/model/design.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink.domain.value_objects.instance import CellInstance
    from ink.domain.value_objects.net import NetInfo, NetType
    from ink.domain.value_objects.subcircuit import SubcircuitDefinition


@dataclass
class ParsedDesign:
    """Infrastructure representation of parsed CDL data.

    This class holds the raw output of CDL parsing before transformation
    into domain entities. It contains:
    - Subcircuit definitions (cell type interfaces)
    - Cell instances (instantiations with net connections)
    - Net information (normalized names and types)
    - Top-level port names

    This is NOT the domain aggregate - it's infrastructure data that will
    be transformed into the domain Design by a builder/factory in the
    application layer.

    Attributes:
        name: Design name, typically derived from the CDL filename.
        subcircuit_defs: Dict mapping cell type names to SubcircuitDefinition.
        instances: Dict mapping instance names to CellInstance.
        nets: Dict mapping net names to NetInfo.
        top_level_ports: List of top-level port names.

    Example:
        >>> parsed = ParsedDesign(name="inverter_chain")
        >>> parsed.add_instance(CellInstance("XI1", "INV", {"A": "in", "Y": "out"}))
        >>> print(parsed.instance_count)
        1
    """

    # Design name (from filename or explicit)
    name: str

    # Cell type definitions: cell_type_name -> SubcircuitDefinition
    subcircuit_defs: dict[str, SubcircuitDefinition] = field(default_factory=dict)

    # Cell instances: instance_name -> CellInstance
    instances: dict[str, CellInstance] = field(default_factory=dict)

    # Net information: net_name -> NetInfo
    nets: dict[str, NetInfo] = field(default_factory=dict)

    # Top-level I/O ports of the design
    top_level_ports: list[str] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # Instance Management
    # -------------------------------------------------------------------------

    def add_instance(self, instance: CellInstance) -> None:
        """Add a cell instance to the parsed design.

        Validates that the instance name is unique before adding.

        Args:
            instance: The CellInstance to add.

        Raises:
            ValueError: If an instance with the same name already exists.
        """
        if instance.name in self.instances:
            raise ValueError(f"Duplicate instance name: {instance.name}")
        self.instances[instance.name] = instance

    def get_instance(self, name: str) -> CellInstance | None:
        """Retrieve a cell instance by name.

        Args:
            name: The exact instance name to look up.

        Returns:
            The CellInstance if found, None otherwise.
        """
        return self.instances.get(name)

    def get_instances_by_type(self, cell_type: str) -> list[CellInstance]:
        """Find all instances of a specific cell type.

        Args:
            cell_type: The cell type name to filter by.

        Returns:
            List of matching CellInstance objects.
        """
        return [inst for inst in self.instances.values() if inst.cell_type == cell_type]

    # -------------------------------------------------------------------------
    # Net Management
    # -------------------------------------------------------------------------

    def add_net(self, name: str, net_info: NetInfo) -> None:
        """Add a net to the parsed design.

        Unlike instances, duplicate net names are allowed (overwrites existing).

        Args:
            name: The net name (key for lookup).
            net_info: The NetInfo object with normalization and classification.
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

        Args:
            net_type: The NetType enum value to filter by.

        Returns:
            List of matching NetInfo objects.
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
        """Get the total number of cell instances."""
        return len(self.instances)

    @property
    def net_count(self) -> int:
        """Get the total number of unique nets."""
        return len(self.nets)

    @property
    def subcircuit_count(self) -> int:
        """Get the total number of subcircuit definitions."""
        return len(self.subcircuit_defs)

    # -------------------------------------------------------------------------
    # String Representation
    # -------------------------------------------------------------------------

    def __repr__(self) -> str:
        """Return detailed string for debugging."""
        return (
            f"ParsedDesign(name={self.name!r}, "
            f"subcircuits={self.subcircuit_count}, "
            f"instances={self.instance_count}, "
            f"nets={self.net_count})"
        )

    def __str__(self) -> str:
        """Return human-readable summary."""
        return (
            f"ParsedDesign: {self.name}\n"
            f"  Subcircuits: {self.subcircuit_count}\n"
            f"  Instances: {self.instance_count}\n"
            f"  Nets: {self.net_count}\n"
            f"  Ports: {len(self.top_level_ports)}"
        )
