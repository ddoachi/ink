"""Transistor topology analyzer implementation.

This module provides the TransistorTopologyAnalyzer class, which implements
the TopologyAnalyzer protocol for extracting signal flow graphs from
transistor-level subcircuit definitions.

The analyzer recognizes common circuit patterns (inverters, transmission gates,
NAND, NOR) and extracts directed signal flow connections that can be used for
feedback loop detection to identify sequential elements.

Pipeline Integration:
    CDL Parser (E01-F02) -> TransistorTopologyAnalyzer -> LatchIdentifier (E01-F04-T02)

    SubcircuitDefinition -> SignalFlowGraph.connections -> register_subcircuit_topology()

See Also:
    - Spec E01-F04-T04 for requirements
    - TopologyAnalyzer protocol
    - TransistorPatternRecognizer for pattern detection
    - TopologyBasedLatchIdentifier for integration
"""

from __future__ import annotations

from ink.infrastructure.analysis.topology_analyzer import (
    CellInstance,
    SignalFlowGraph,
    SubcircuitDefinition,
)
from ink.infrastructure.analysis.transistor_patterns import (
    RecognizedStructure,
    TransistorPatternRecognizer,
)

# Number of signal nodes expected for a valid transmission gate
_TG_SIGNAL_NODE_COUNT = 2

# Default power supply net names recognized across different PDKs
DEFAULT_VDD_NAMES = {"VDD", "VDDX", "VCC", "VPWR"}
DEFAULT_VSS_NAMES = {"VSS", "VSSX", "GND", "VGND"}


class TransistorTopologyAnalyzer:
    """Extracts signal flow graph from transistor-level subcircuits.

    This class implements the TopologyAnalyzer protocol. It analyzes transistor
    connections to identify common circuit patterns and extract directed signal
    flow for feedback detection.

    Analysis Pipeline:
        1. Identify power/ground nets from subcircuit ports
        2. Find inverters (complementary PMOS/NMOS pairs)
        3. Find transmission gates (PMOS/NMOS with shared terminals)
        4. Find NAND/NOR gates (parallel/series transistor networks)
        5. Analyze hierarchical cell instances (using registered pinouts)
        6. Combine all connections into SignalFlowGraph

    Attributes:
        _vdd_names: Set of recognized power supply net names
        _vss_names: Set of recognized ground net names
        _cell_pinouts: Registered cell type pinout information
        _pattern_recognizer: TransistorPatternRecognizer instance

    Example:
        >>> analyzer = TransistorTopologyAnalyzer()
        >>> analyzer.register_cell_pinout("INV_X1", {"A"}, {"Y"})
        >>>
        >>> subckt = SubcircuitDefinition(
        ...     name="BUF_X1",
        ...     ports=["A", "Y", "VDD", "VSS"],
        ...     transistors=[...],
        ...     instances=[],
        ... )
        >>> result = analyzer.analyze(subckt)
        >>> print(result.connections)

    See Also:
        - TopologyAnalyzer protocol
        - TransistorPatternRecognizer for pattern detection
    """

    def __init__(
        self,
        vdd_names: set[str] | None = None,
        vss_names: set[str] | None = None,
    ) -> None:
        """Initialize analyzer.

        Args:
            vdd_names: Power supply net names to recognize.
                       Default: {"VDD", "VDDX", "VCC", "VPWR"}
            vss_names: Ground net names to recognize.
                       Default: {"VSS", "VSSX", "GND", "VGND"}
        """
        self._vdd_names = vdd_names or set(DEFAULT_VDD_NAMES)
        self._vss_names = vss_names or set(DEFAULT_VSS_NAMES)

        # Cell pinout registry: cell_type (uppercase) -> (input_pins, output_pins)
        self._cell_pinouts: dict[str, tuple[set[str], set[str]]] = {}

        # Pattern recognizer instance
        self._pattern_recognizer = TransistorPatternRecognizer()

    def analyze(self, subcircuit: SubcircuitDefinition) -> SignalFlowGraph:
        """Extract signal flow from subcircuit.

        Analyzes the subcircuit's transistors and instances to identify
        circuit patterns and extract directed signal flow connections.

        The analysis pipeline:
        1. Identify VDD/VSS from subcircuit ports
        2. Find inverters -> add gate-to-drain connections
        3. Find transmission gates -> add bidirectional connections
        4. Find NAND/NOR gates -> add input-to-output connections
        5. Analyze hierarchical instances -> add instance connections
        6. Return combined SignalFlowGraph

        Args:
            subcircuit: Parsed subcircuit with transistors and instances

        Returns:
            SignalFlowGraph with directed connections for cycle detection
        """
        connections: list[tuple[str, str]] = []
        structures: list[str] = []

        # Step 0: Identify power/ground nets from ports
        vdd, vss = self._identify_power_nets(subcircuit)

        # Step 1: Find and process inverters
        inverters = self._pattern_recognizer.find_inverters(subcircuit.transistors, vdd, vss)
        self._process_inverters(inverters, connections, structures)

        # Step 2: Find and process transmission gates
        tgates = self._pattern_recognizer.find_transmission_gates(
            subcircuit.transistors,
            power_nets=self._vdd_names,
            ground_nets=self._vss_names,
        )
        self._process_transmission_gates(tgates, connections, structures)

        # Step 3: Find and process NAND gates
        nands = self._pattern_recognizer.find_nand_gates(subcircuit.transistors, vdd, vss)
        self._process_nand_nor(nands, connections, structures, "nand")

        # Step 4: Find and process NOR gates
        nors = self._pattern_recognizer.find_nor_gates(subcircuit.transistors, vdd, vss)
        self._process_nand_nor(nors, connections, structures, "nor")

        # Step 5: Handle hierarchical cell instances
        for instance in subcircuit.instances:
            inst_connections = self._analyze_instance(instance)
            connections.extend(inst_connections)

        return SignalFlowGraph(
            cell_type=subcircuit.name,
            connections=connections,
            identified_structures=structures,
        )

    def register_cell_pinout(
        self, cell_type: str, input_pins: set[str], output_pins: set[str]
    ) -> None:
        """Register known cell pinout for hierarchical analysis.

        When analyzing subcircuits that contain instances of other cells,
        the analyzer needs to know the pin directions to determine signal flow.

        Args:
            cell_type: Cell type name (case-insensitive)
            input_pins: Set of input pin names
            output_pins: Set of output pin names

        Note:
            - Cell type is stored uppercase for case-insensitive lookup
            - Power pins (VDD, VSS) should not be included
        """
        self._cell_pinouts[cell_type.upper()] = (input_pins, output_pins)

    def _identify_power_nets(self, subcircuit: SubcircuitDefinition) -> tuple[str, str]:
        """Identify VDD and VSS nets in subcircuit.

        Searches the subcircuit's ports for known power supply and ground
        net names. Returns the first match found for each.

        Args:
            subcircuit: Subcircuit definition to analyze

        Returns:
            Tuple of (vdd_net_name, vss_net_name)
            Defaults to ("VDD", "VSS") if not found in ports
        """
        vdd = next(
            (p for p in subcircuit.ports if p.upper() in self._vdd_names),
            "VDD",
        )
        vss = next(
            (p for p in subcircuit.ports if p.upper() in self._vss_names),
            "VSS",
        )
        return vdd, vss

    def _process_inverters(
        self,
        inverters: list[RecognizedStructure],
        connections: list[tuple[str, str]],
        structures: list[str],
    ) -> None:
        """Process recognized inverters into signal flow connections.

        For each inverter, adds a directed connection from input (gate)
        to output (drain).

        Args:
            inverters: List of recognized inverter structures
            connections: Output list to append connections to
            structures: Output list to append structure descriptions
        """
        for inv in inverters:
            # Add directed connections: input -> output
            for inp in inv.input_nodes:
                for out in inv.output_nodes:
                    connections.append((inp, out))

            # Record structure for documentation
            structures.append(f"inverter@{inv.input_nodes}->{inv.output_nodes}")

    def _process_transmission_gates(
        self,
        tgates: list[RecognizedStructure],
        connections: list[tuple[str, str]],
        structures: list[str],
    ) -> None:
        """Process recognized transmission gates into signal flow connections.

        Transmission gates are bidirectional, so both directions are added.
        Control nodes (clock signals) are excluded from signal path.

        Args:
            tgates: List of recognized transmission gate structures
            connections: Output list to append connections to
            structures: Output list to append structure descriptions
        """
        for tg in tgates:
            # Get signal nodes (exclude control nodes)
            signal_nodes = list(tg.input_nodes | tg.output_nodes)

            # Bidirectional: add both directions
            if len(signal_nodes) == _TG_SIGNAL_NODE_COUNT:
                connections.append((signal_nodes[0], signal_nodes[1]))
                connections.append((signal_nodes[1], signal_nodes[0]))

            # Record structure
            structures.append(f"tgate@{signal_nodes}")

    def _process_nand_nor(
        self,
        gates: list[RecognizedStructure],
        connections: list[tuple[str, str]],
        structures: list[str],
        gate_type: str,
    ) -> None:
        """Process recognized NAND/NOR gates into signal flow connections.

        For each gate, adds directed connections from all inputs to output.

        Args:
            gates: List of recognized gate structures
            connections: Output list to append connections to
            structures: Output list to append structure descriptions
            gate_type: "nand" or "nor" for structure description
        """
        for gate in gates:
            # Add directed connections: each input -> output
            for inp in gate.input_nodes:
                for out in gate.output_nodes:
                    connections.append((inp, out))

            # Record structure
            structures.append(f"{gate_type}@{gate.input_nodes}->{gate.output_nodes}")

    def _analyze_instance(self, instance: CellInstance) -> list[tuple[str, str]]:
        """Extract connections from a subcircuit instance.

        Uses registered cell pinouts to determine signal flow through
        hierarchical cell instances.

        Args:
            instance: Cell instance to analyze

        Returns:
            List of (input_net, output_net) connections through the instance
        """
        cell_key = instance.cell_type.upper()
        if cell_key not in self._cell_pinouts:
            # Unknown cell - skip without error
            return []

        input_pins, output_pins = self._cell_pinouts[cell_key]
        connections: list[tuple[str, str]] = []

        # Get nets connected to input/output pins
        input_nets = [instance.connections[p] for p in input_pins if p in instance.connections]
        output_nets = [instance.connections[p] for p in output_pins if p in instance.connections]

        # Add directed connections: each input net -> each output net
        for inp in input_nets:
            for out in output_nets:
                connections.append((inp, out))

        return connections
