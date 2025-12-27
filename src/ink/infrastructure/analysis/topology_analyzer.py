"""Topology analyzer protocol and data classes.

This module defines the TopologyAnalyzer protocol and associated data classes
for extracting signal flow graphs from transistor-level subcircuit definitions.

The TopologyAnalyzer protocol is the infrastructure service interface for
topology extraction. Implementations analyze transistor connections to identify
common circuit patterns (inverters, transmission gates, NAND, NOR) and extract
directed signal flow for feedback detection.

Data Classes:
    - TransistorInstance: Represents a transistor (PMOS/NMOS) with terminal connections
    - CellInstance: Represents a subcircuit instance within another subcircuit
    - SubcircuitDefinition: Parsed subcircuit from CDL with transistors and instances
    - SignalFlowGraph: Extracted signal flow with connections and identified structures

Protocol:
    - TopologyAnalyzer: Interface for topology analysis services

Architecture:
    This module follows Clean Architecture principles:
    - Protocol defined in infrastructure layer (not domain) because it's tightly
      coupled to implementation details (transistor-level analysis)
    - Data classes are plain Python with no external dependencies
    - Implementations can be swapped without affecting consumers

See Also:
    - Spec E01-F04-T04 for requirements
    - TransistorTopologyAnalyzer for main implementation
    - TopologyBasedLatchIdentifier for consumer integration
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class TransistorInstance:
    """Represents a transistor in a subcircuit.

    This dataclass captures the essential properties of a MOSFET transistor
    as found in CDL netlists. It includes the four terminal connections
    (drain, gate, source, bulk) plus metadata (name, type).

    Attributes:
        name: Instance name (e.g., "M1", "MP1", "MN2")
        type: Transistor type - "PMOS" or "NMOS"
        drain: Drain terminal net name
        gate: Gate terminal net name (control input)
        source: Source terminal net name
        bulk: Bulk/body terminal net name (substrate connection)

    Example:
        >>> tx = TransistorInstance(
        ...     name="MP1",
        ...     type="PMOS",
        ...     drain="Y",
        ...     gate="A",
        ...     source="VDD",
        ...     bulk="VDD",
        ... )
        >>> tx.gate
        'A'

    Note:
        The terminal ordering in CDL format is typically:
        Mname drain gate source bulk type

        For PMOS: source typically connects to VDD, drain to output
        For NMOS: source typically connects to VSS, drain to output
    """

    name: str
    type: str  # "PMOS" or "NMOS"
    drain: str
    gate: str
    source: str
    bulk: str


@dataclass
class CellInstance:
    """Represents a subcircuit instance within another subcircuit.

    This dataclass captures hierarchical cell instantiation, where a subcircuit
    may contain instances of other subcircuits (not just transistors).

    Attributes:
        name: Instance name (e.g., "XI1", "U1")
        cell_type: Subcircuit type being instantiated (e.g., "INV_X1", "NAND2_X1")
        connections: Mapping from pin name to net name

    Example:
        >>> cell = CellInstance(
        ...     name="XI1",
        ...     cell_type="INV_X1",
        ...     connections={"A": "net1", "Y": "net2", "VDD": "VDD", "VSS": "VSS"},
        ... )
        >>> cell.connections["A"]
        'net1'

    Note:
        For hierarchical analysis, the TopologyAnalyzer needs to know the
        input/output pin classification for each cell_type. Use
        register_cell_pinout() to provide this information.
    """

    name: str
    cell_type: str
    connections: dict[str, str]  # pin_name -> net_name


@dataclass
class SubcircuitDefinition:
    """Parsed subcircuit from CDL.

    This dataclass represents a complete subcircuit definition as parsed
    from a CDL netlist. It includes the subcircuit's ports, transistor-level
    content, and any hierarchical cell instances.

    Attributes:
        name: Subcircuit name (e.g., "DFFR_X1", "INV_X1")
        ports: External port names in order (e.g., ["D", "Q", "CLK", "VDD", "VSS"])
        transistors: List of transistor instances in this subcircuit
        instances: List of subcircuit instances (hierarchical)

    Example:
        >>> subckt = SubcircuitDefinition(
        ...     name="INV_X1",
        ...     ports=["A", "Y", "VDD", "VSS"],
        ...     transistors=[
        ...         TransistorInstance("MP", "PMOS", "Y", "A", "VDD", "VDD"),
        ...         TransistorInstance("MN", "NMOS", "Y", "A", "VSS", "VSS"),
        ...     ],
        ...     instances=[],
        ... )

    Note:
        CDL format: .SUBCKT name port1 port2 ... / contents / .ENDS
    """

    name: str
    ports: list[str]
    transistors: list[TransistorInstance]
    instances: list[CellInstance]


@dataclass
class SignalFlowGraph:
    """Extracted signal flow from a subcircuit.

    This dataclass represents the result of topology analysis. It contains
    directed connections representing signal flow through the subcircuit,
    plus metadata about identified circuit structures.

    The connections list is suitable for cycle detection to identify
    feedback loops (which indicate sequential elements).

    Attributes:
        cell_type: Name of the analyzed subcircuit
        connections: List of (from_node, to_node) directed connections
        identified_structures: Human-readable descriptions of recognized patterns

    Example:
        >>> graph = SignalFlowGraph(
        ...     cell_type="INV_X1",
        ...     connections=[("A", "Y")],
        ...     identified_structures=["inverter@{'A'}->{'Y'}"],
        ... )

    Note:
        Connections represent signal flow, not physical wires:
        - Inverter: gate -> drain (input to output)
        - Transmission gate: bidirectional (both directions added)
        - NAND/NOR: all inputs -> output

        The connections list can be passed directly to
        TopologyBasedLatchIdentifier.register_subcircuit_topology()
        for feedback loop detection.
    """

    cell_type: str
    connections: list[tuple[str, str]]  # [(from_node, to_node), ...]
    identified_structures: list[str]  # Human-readable pattern descriptions


class TopologyAnalyzer(Protocol):
    """Infrastructure service protocol for extracting signal flow from subcircuits.

    This protocol defines the interface for topology analysis services. The
    primary implementation (TransistorTopologyAnalyzer) analyzes transistor-level
    subcircuit definitions to extract signal flow graphs.

    The extracted signal flow can be used for:
    - Feedback loop detection (identifying sequential elements)
    - Cell classification (combinational vs sequential)
    - Signal propagation analysis

    Methods:
        analyze: Extract signal flow from a subcircuit definition
        register_cell_pinout: Register pin directions for hierarchical analysis

    Example:
        >>> analyzer = TransistorTopologyAnalyzer()
        >>> analyzer.register_cell_pinout("INV_X1", {"A"}, {"Y"})
        >>> result = analyzer.analyze(subcircuit)
        >>> print(result.connections)
        [('A', 'Y')]

    See Also:
        - TransistorTopologyAnalyzer for main implementation
        - TransistorPatternRecognizer for pattern detection
    """

    def analyze(self, subcircuit: SubcircuitDefinition) -> SignalFlowGraph:
        """Extract signal flow graph from subcircuit definition.

        Analyzes the transistor-level structure of a subcircuit to identify
        common circuit patterns and extract directed signal flow connections.

        The analysis includes:
        1. Pattern recognition (inverters, transmission gates, NAND, NOR)
        2. Hierarchical instance analysis (using registered pinouts)
        3. Signal flow extraction (directed connections)

        Args:
            subcircuit: Parsed subcircuit with transistors and instances

        Returns:
            SignalFlowGraph with directed connections for cycle detection

        Example:
            >>> subckt = SubcircuitDefinition(
            ...     name="INV_X1",
            ...     ports=["A", "Y", "VDD", "VSS"],
            ...     transistors=[
            ...         TransistorInstance("MP", "PMOS", "Y", "A", "VDD", "VDD"),
            ...         TransistorInstance("MN", "NMOS", "Y", "A", "VSS", "VSS"),
            ...     ],
            ...     instances=[],
            ... )
            >>> result = analyzer.analyze(subckt)
            >>> ("A", "Y") in result.connections
            True
        """
        ...

    def register_cell_pinout(
        self, cell_type: str, input_pins: set[str], output_pins: set[str]
    ) -> None:
        """Register pin directions for a known cell type.

        Required for hierarchical analysis. When a subcircuit contains
        instances of other subcircuits, the analyzer needs to know which
        pins are inputs and which are outputs to determine signal flow.

        Args:
            cell_type: Cell type name (e.g., "INV_X1", case-insensitive)
            input_pins: Set of input pin names (e.g., {"A"})
            output_pins: Set of output pin names (e.g., {"Y"})

        Example:
            >>> analyzer.register_cell_pinout("INV_X1", {"A"}, {"Y"})
            >>> analyzer.register_cell_pinout("NAND2_X1", {"A", "B"}, {"Y"})

        Note:
            - Cell type lookup is case-insensitive
            - Power pins (VDD, VSS) should not be included
            - Bidirectional pins should be in both sets
        """
        ...
