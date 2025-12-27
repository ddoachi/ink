"""Transistor pattern recognition for common circuit structures.

This module provides the TransistorPatternRecognizer class which identifies
common transistor patterns in subcircuit definitions:
- Inverters (complementary PMOS/NMOS pairs)
- Transmission gates (PMOS/NMOS with shared source/drain)
- NAND gates (parallel PMOS + series NMOS)
- NOR gates (series PMOS + parallel NMOS)

Pattern Recognition Strategy:
    1. Group transistors by type (PMOS/NMOS)
    2. For each pattern, find transistor pairs/groups that match criteria
    3. Extract input/output/control nodes from matched transistors
    4. Return recognized structures with metadata

See Also:
    - Spec E01-F04-T04 for requirements
    - TransistorTopologyAnalyzer for integration
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ink.infrastructure.analysis.topology_analyzer import TransistorInstance

# Minimum number of transistors required to form multi-input gates
MIN_GATE_INPUTS = 2


class StructureType(Enum):
    """Types of recognized transistor structures.

    Each structure type represents a common circuit pattern that can be
    identified from transistor-level netlist analysis.

    Attributes:
        INVERTER: Complementary PMOS/NMOS pair with shared gate and drain
        TRANSMISSION_GATE: PMOS/NMOS with shared source/drain, bidirectional
        NAND: Parallel PMOS + series NMOS pull-down
        NOR: Series PMOS + parallel NMOS pull-down
        PASS_TRANSISTOR: Single transistor pass gate
        UNKNOWN: Unrecognized pattern
    """

    INVERTER = "inverter"
    TRANSMISSION_GATE = "tgate"
    NAND = "nand"
    NOR = "nor"
    PASS_TRANSISTOR = "pass"
    UNKNOWN = "unknown"


@dataclass
class RecognizedStructure:
    """A recognized transistor pattern.

    This dataclass captures the result of pattern recognition, including
    the structure type and the nodes involved.

    Attributes:
        type: The type of structure recognized
        input_nodes: Set of input signal node names
        output_nodes: Set of output signal node names
        control_nodes: Set of control node names (e.g., clock for TG)
        transistors: List of transistor names involved in this structure

    Example:
        >>> structure = RecognizedStructure(
        ...     type=StructureType.INVERTER,
        ...     input_nodes={"A"},
        ...     output_nodes={"Y"},
        ...     control_nodes=set(),
        ...     transistors=["MP1", "MN1"],
        ... )
    """

    type: StructureType
    input_nodes: set[str]
    output_nodes: set[str]
    control_nodes: set[str]
    transistors: list[str]


class TransistorPatternRecognizer:
    """Recognizes common transistor patterns in subcircuit definitions.

    This class provides methods to identify standard circuit structures
    from lists of transistor instances. Each method searches for a specific
    pattern and returns a list of recognized structures.

    Pattern Detection:
        - find_inverters: PMOS/NMOS pairs with VDD/VSS sources, shared gate/drain
        - find_transmission_gates: PMOS/NMOS with shared source/drain terminals
        - find_nand_gates: Parallel PMOS + series NMOS networks
        - find_nor_gates: Series PMOS + parallel NMOS networks

    Example:
        >>> recognizer = TransistorPatternRecognizer()
        >>> transistors = [
        ...     TransistorInstance("MP", "PMOS", "Y", "A", "VDD", "VDD"),
        ...     TransistorInstance("MN", "NMOS", "Y", "A", "VSS", "VSS"),
        ... ]
        >>> inverters = recognizer.find_inverters(transistors, "VDD", "VSS")
        >>> len(inverters)
        1
        >>> inverters[0].input_nodes
        {'A'}

    See Also:
        - TransistorTopologyAnalyzer for integration
    """

    def find_inverters(
        self, transistors: list[TransistorInstance], vdd: str, vss: str
    ) -> list[RecognizedStructure]:
        """Find complementary PMOS/NMOS pairs forming inverters.

        An inverter is formed when:
        - PMOS: source connects to VDD, gate is input, drain is output
        - NMOS: source connects to VSS, gate is input, drain is output
        - Both transistors share the same gate (input) and drain (output)

        Args:
            transistors: List of transistor instances to analyze
            vdd: Power supply net name (e.g., "VDD")
            vss: Ground net name (e.g., "VSS")

        Returns:
            List of RecognizedStructure for each inverter found

        Example:
            Pattern:
                     VDD
                      |
                 [PMOS] source=VDD, gate=A, drain=Y
                      |
               A -----+-----> Y
                      |
                 [NMOS] source=VSS, gate=A, drain=Y
                      |
                     VSS
        """
        if not transistors:
            return []

        # Separate PMOS and NMOS transistors
        pmos_list = [t for t in transistors if t.type.upper() == "PMOS"]
        nmos_list = [t for t in transistors if t.type.upper() == "NMOS"]

        # Find PMOS with source=VDD and NMOS with source=VSS
        # that share the same gate and drain
        pmos_vdd = [p for p in pmos_list if p.source == vdd]
        nmos_vss = [n for n in nmos_list if n.source == vss]

        inverters: list[RecognizedStructure] = []
        used_pmos: set[str] = set()
        used_nmos: set[str] = set()

        for p in pmos_vdd:
            if p.name in used_pmos:
                continue
            for n in nmos_vss:
                if n.name in used_nmos:
                    continue
                # Check if gate and drain match (forming an inverter)
                if p.gate == n.gate and p.drain == n.drain:
                    inverters.append(
                        RecognizedStructure(
                            type=StructureType.INVERTER,
                            input_nodes={p.gate},
                            output_nodes={p.drain},
                            control_nodes=set(),
                            transistors=[p.name, n.name],
                        )
                    )
                    used_pmos.add(p.name)
                    used_nmos.add(n.name)
                    break

        return inverters

    def find_transmission_gates(
        self,
        transistors: list[TransistorInstance],
        power_nets: set[str] | None = None,
        ground_nets: set[str] | None = None,
    ) -> list[RecognizedStructure]:
        """Find PMOS/NMOS pairs forming transmission gates.

        A transmission gate is formed when:
        - PMOS and NMOS share the same source/drain pair (order may differ)
        - Gates are different (complementary clock signals)
        - Neither source nor drain connects to power/ground

        Args:
            transistors: List of transistor instances to analyze
            power_nets: Set of power net names to exclude (e.g., {"VDD", "VPWR"})
            ground_nets: Set of ground net names to exclude (e.g., {"VSS", "VGND"})

        Returns:
            List of RecognizedStructure for each transmission gate found

        Example:
            Pattern:
                      CLK
                       |
                  [NMOS] gate=CLK, source=A, drain=B
               A ------+------ B   (bidirectional)
                  [PMOS] gate=CLK_B, source=A, drain=B
                       |
                     CLK_B
        """
        if not transistors:
            return []

        power_nets = power_nets or {"VDD", "VDDX", "VCC", "VPWR"}
        ground_nets = ground_nets or {"VSS", "VSSX", "GND", "VGND"}
        excluded_nets = power_nets | ground_nets

        pmos_list = [t for t in transistors if t.type.upper() == "PMOS"]
        nmos_list = [t for t in transistors if t.type.upper() == "NMOS"]

        tgates: list[RecognizedStructure] = []
        used_pmos: set[str] = set()
        used_nmos: set[str] = set()

        for n in nmos_list:
            if n.name in used_nmos:
                continue
            # Skip if connected to power rails
            n_terminals = {n.source, n.drain}
            if n_terminals & excluded_nets:
                continue

            for p in pmos_list:
                if p.name in used_pmos:
                    continue
                # Skip if connected to power rails
                p_terminals = {p.source, p.drain}
                if p_terminals & excluded_nets:
                    continue

                # Check if they share the same source/drain pair
                # (order may be swapped between PMOS and NMOS)
                if n_terminals == p_terminals:
                    # Found a transmission gate
                    signal_nodes = n_terminals
                    control_nodes = {n.gate, p.gate}

                    tgates.append(
                        RecognizedStructure(
                            type=StructureType.TRANSMISSION_GATE,
                            input_nodes=signal_nodes,
                            output_nodes=signal_nodes,  # Bidirectional
                            control_nodes=control_nodes,
                            transistors=[n.name, p.name],
                        )
                    )
                    used_nmos.add(n.name)
                    used_pmos.add(p.name)
                    break

        return tgates

    def find_nand_gates(
        self, transistors: list[TransistorInstance], vdd: str, vss: str
    ) -> list[RecognizedStructure]:
        """Find NAND gate structures.

        A NAND gate is formed by:
        - Parallel PMOS pull-up network: multiple PMOS with source=VDD, drains connected
        - Series NMOS pull-down network: NMOS chain from output to VSS

        This implementation detects N-input NANDs by looking for:
        - N PMOS with source=VDD, same drain, different gates
        - N NMOS in series: chain from output to VSS

        Args:
            transistors: List of transistor instances to analyze
            vdd: Power supply net name
            vss: Ground net name

        Returns:
            List of RecognizedStructure for each NAND gate found
        """
        if not transistors:
            return []

        pmos_list = [t for t in transistors if t.type.upper() == "PMOS"]
        nmos_list = [t for t in transistors if t.type.upper() == "NMOS"]

        # Find parallel PMOS: source=VDD, same drain
        pmos_vdd = [p for p in pmos_list if p.source == vdd]

        # Group PMOS by drain (output node)
        pmos_by_drain: dict[str, list[TransistorInstance]] = {}
        for p in pmos_vdd:
            if p.drain not in pmos_by_drain:
                pmos_by_drain[p.drain] = []
            pmos_by_drain[p.drain].append(p)

        nands: list[RecognizedStructure] = []

        # For each potential output node with multiple parallel PMOS
        for output_node, parallel_pmos in pmos_by_drain.items():
            if len(parallel_pmos) < MIN_GATE_INPUTS:
                continue

            # Get the gate signals from PMOS (these are NAND inputs)
            pmos_gates = {p.gate for p in parallel_pmos}
            expected_inputs = len(pmos_gates)

            # Find series NMOS chain from output to VSS
            # Trace chain starting from output_node to VSS
            chain = self._find_nmos_series_chain(nmos_list, output_node, vss)

            if len(chain) == expected_inputs:
                # Found a complete series chain
                nmos_gates = {n.gate for n in chain}

                # Verify gates match between PMOS and NMOS networks
                if pmos_gates == nmos_gates:
                    all_transistors = [p.name for p in parallel_pmos]
                    all_transistors.extend(n.name for n in chain)

                    nands.append(
                        RecognizedStructure(
                            type=StructureType.NAND,
                            input_nodes=pmos_gates,
                            output_nodes={output_node},
                            control_nodes=set(),
                            transistors=all_transistors,
                        )
                    )

        return nands

    def _find_nmos_series_chain(
        self,
        nmos_list: list[TransistorInstance],
        start_node: str,
        end_node: str,
    ) -> list[TransistorInstance]:
        """Find a series chain of NMOS from start_node to end_node.

        Traces through NMOS transistors following drain->source connections.

        Args:
            nmos_list: List of NMOS transistors to search
            start_node: Starting node (typically output of gate)
            end_node: Ending node (typically VSS)

        Returns:
            List of transistors in the chain (ordered from start to end)
        """
        chain: list[TransistorInstance] = []
        current_node = start_node
        used: set[str] = set()

        while current_node != end_node:
            # Find NMOS with drain=current_node
            found = None
            for n in nmos_list:
                if n.name not in used and n.drain == current_node:
                    found = n
                    break

            if found is None:
                break  # Chain broken

            chain.append(found)
            used.add(found.name)
            current_node = found.source

        return chain

    def find_nor_gates(
        self, transistors: list[TransistorInstance], vdd: str, vss: str
    ) -> list[RecognizedStructure]:
        """Find NOR gate structures.

        A NOR gate is formed by:
        - Series PMOS pull-up network: PMOS chain from VDD to output
        - Parallel NMOS pull-down network: multiple NMOS with source=VSS, drains connected

        This implementation detects N-input NORs by looking for:
        - N PMOS in series: chain from VDD to output
        - N NMOS with source=VSS, same drain, different gates

        Args:
            transistors: List of transistor instances to analyze
            vdd: Power supply net name
            vss: Ground net name

        Returns:
            List of RecognizedStructure for each NOR gate found
        """
        if not transistors:
            return []

        pmos_list = [t for t in transistors if t.type.upper() == "PMOS"]
        nmos_list = [t for t in transistors if t.type.upper() == "NMOS"]

        # Find parallel NMOS: source=VSS, same drain
        nmos_vss = [n for n in nmos_list if n.source == vss]

        # Group NMOS by drain (output node)
        nmos_by_drain: dict[str, list[TransistorInstance]] = {}
        for n in nmos_vss:
            if n.drain not in nmos_by_drain:
                nmos_by_drain[n.drain] = []
            nmos_by_drain[n.drain].append(n)

        nors: list[RecognizedStructure] = []

        # For each potential output node with multiple parallel NMOS
        for output_node, parallel_nmos in nmos_by_drain.items():
            if len(parallel_nmos) < MIN_GATE_INPUTS:
                continue

            # Get the gate signals from NMOS (these are NOR inputs)
            nmos_gates = {n.gate for n in parallel_nmos}
            expected_inputs = len(nmos_gates)

            # Find series PMOS chain from VDD to output
            # Trace chain starting from VDD to output_node
            chain = self._find_pmos_series_chain(pmos_list, vdd, output_node)

            if len(chain) == expected_inputs:
                # Found a complete series chain
                pmos_gates = {p.gate for p in chain}

                # Verify gates match between PMOS and NMOS networks
                if pmos_gates == nmos_gates:
                    all_transistors = [n.name for n in parallel_nmos]
                    all_transistors.extend(p.name for p in chain)

                    nors.append(
                        RecognizedStructure(
                            type=StructureType.NOR,
                            input_nodes=nmos_gates,
                            output_nodes={output_node},
                            control_nodes=set(),
                            transistors=all_transistors,
                        )
                    )

        return nors

    def _find_pmos_series_chain(
        self,
        pmos_list: list[TransistorInstance],
        start_node: str,
        end_node: str,
    ) -> list[TransistorInstance]:
        """Find a series chain of PMOS from start_node to end_node.

        Traces through PMOS transistors following source->drain connections.

        Args:
            pmos_list: List of PMOS transistors to search
            start_node: Starting node (typically VDD)
            end_node: Ending node (typically output of gate)

        Returns:
            List of transistors in the chain (ordered from start to end)
        """
        chain: list[TransistorInstance] = []
        current_node = start_node
        used: set[str] = set()

        while current_node != end_node:
            # Find PMOS with source=current_node
            found = None
            for p in pmos_list:
                if p.name not in used and p.source == current_node:
                    found = p
                    break

            if found is None:
                break  # Chain broken

            chain.append(found)
            used.add(found.name)
            current_node = found.drain

        return chain
