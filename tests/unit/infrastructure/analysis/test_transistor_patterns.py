"""Unit tests for TransistorPatternRecognizer.

This module tests the transistor pattern recognition functionality which identifies
common circuit structures (inverters, transmission gates, NAND, NOR) from
transistor-level netlists.

Test Organization:
    1. Inverter Pattern Recognition
    2. Transmission Gate Recognition
    3. NAND Gate Recognition
    4. NOR Gate Recognition
    5. Edge Cases and Error Handling

See Also:
    - Spec E01-F04-T04 for requirements
    - TransistorPatternRecognizer implementation
"""

from ink.infrastructure.analysis.topology_analyzer import (
    TransistorInstance,
)
from ink.infrastructure.analysis.transistor_patterns import (
    RecognizedStructure,
    StructureType,
    TransistorPatternRecognizer,
)

# =============================================================================
# INVERTER PATTERN RECOGNITION
# =============================================================================


class TestInverterRecognition:
    """Tests for inverter pattern recognition in transistor netlists."""

    def test_recognizes_simple_inverter(self) -> None:
        """Complementary PMOS/NMOS pair detected as inverter.

        Pattern: PMOS (source=VDD, gate=A, drain=Y) + NMOS (source=VSS, gate=A, drain=Y)
        """
        recognizer = TransistorPatternRecognizer()

        transistors = [
            TransistorInstance("MP1", "PMOS", drain="Y", gate="A", source="VDD", bulk="VDD"),
            TransistorInstance("MN1", "NMOS", drain="Y", gate="A", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_inverters(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 1
        assert result[0].type == StructureType.INVERTER
        assert result[0].input_nodes == {"A"}
        assert result[0].output_nodes == {"Y"}
        assert set(result[0].transistors) == {"MP1", "MN1"}

    def test_inverter_signal_flow_gate_to_drain(self) -> None:
        """Signal flows from gate (input) to drain (output)."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            TransistorInstance("MP", "PMOS", drain="out", gate="in", source="VDD", bulk="VDD"),
            TransistorInstance("MN", "NMOS", drain="out", gate="in", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_inverters(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 1
        inv = result[0]
        # Input is gate, output is drain
        assert "in" in inv.input_nodes
        assert "out" in inv.output_nodes

    def test_multiple_inverters_in_subcircuit(self) -> None:
        """Multiple inverter pairs correctly identified."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # Inverter 1: A -> Y1
            TransistorInstance("MP1", "PMOS", drain="Y1", gate="A", source="VDD", bulk="VDD"),
            TransistorInstance("MN1", "NMOS", drain="Y1", gate="A", source="VSS", bulk="VSS"),
            # Inverter 2: B -> Y2
            TransistorInstance("MP2", "PMOS", drain="Y2", gate="B", source="VDD", bulk="VDD"),
            TransistorInstance("MN2", "NMOS", drain="Y2", gate="B", source="VSS", bulk="VSS"),
            # Inverter 3: Y1 -> Y3 (chained)
            TransistorInstance("MP3", "PMOS", drain="Y3", gate="Y1", source="VDD", bulk="VDD"),
            TransistorInstance("MN3", "NMOS", drain="Y3", gate="Y1", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_inverters(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 3
        # Verify all three inverters were found
        input_nodes = {frozenset(inv.input_nodes) for inv in result}
        assert frozenset({"A"}) in input_nodes
        assert frozenset({"B"}) in input_nodes
        assert frozenset({"Y1"}) in input_nodes

    def test_handles_different_vdd_names(self) -> None:
        """Works with VDD, VDDX, VCC, VPWR."""
        recognizer = TransistorPatternRecognizer()

        vdd_names = ["VDD", "VDDX", "VCC", "VPWR"]
        vss_names = ["VSS", "VSSX", "GND", "VGND"]

        for vdd, vss in zip(vdd_names, vss_names, strict=True):
            transistors = [
                TransistorInstance("MP", "PMOS", drain="Y", gate="A", source=vdd, bulk=vdd),
                TransistorInstance("MN", "NMOS", drain="Y", gate="A", source=vss, bulk=vss),
            ]

            result = recognizer.find_inverters(transistors, vdd=vdd, vss=vss)

            assert len(result) == 1, f"Failed for VDD={vdd}, VSS={vss}"

    def test_ignores_mismatched_transistor_pairs(self) -> None:
        """Transistors with different gates are not inverters."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # Different gates - not an inverter
            TransistorInstance("MP", "PMOS", drain="Y", gate="A", source="VDD", bulk="VDD"),
            TransistorInstance("MN", "NMOS", drain="Y", gate="B", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_inverters(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 0

    def test_ignores_mismatched_drain_pairs(self) -> None:
        """Transistors with different drains are not inverters."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # Different drains - not an inverter
            TransistorInstance("MP", "PMOS", drain="Y1", gate="A", source="VDD", bulk="VDD"),
            TransistorInstance("MN", "NMOS", drain="Y2", gate="A", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_inverters(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 0

    def test_ignores_pmos_not_connected_to_vdd(self) -> None:
        """PMOS source must be VDD for inverter."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # PMOS source is not VDD
            TransistorInstance("MP", "PMOS", drain="Y", gate="A", source="X", bulk="VDD"),
            TransistorInstance("MN", "NMOS", drain="Y", gate="A", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_inverters(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 0

    def test_ignores_nmos_not_connected_to_vss(self) -> None:
        """NMOS source must be VSS for inverter."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            TransistorInstance("MP", "PMOS", drain="Y", gate="A", source="VDD", bulk="VDD"),
            # NMOS source is not VSS
            TransistorInstance("MN", "NMOS", drain="Y", gate="A", source="X", bulk="VSS"),
        ]

        result = recognizer.find_inverters(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 0


# =============================================================================
# TRANSMISSION GATE RECOGNITION
# =============================================================================


class TestTransmissionGateRecognition:
    """Tests for transmission gate pattern recognition."""

    def test_recognizes_transmission_gate(self) -> None:
        """PMOS/NMOS with shared source/drain detected as TG.

        Pattern: PMOS and NMOS sharing source/drain terminals with different gates.
        """
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # TG: A <-> B, controlled by CLK/CLK_B
            TransistorInstance("MN", "NMOS", drain="A", gate="CLK", source="B", bulk="VSS"),
            TransistorInstance("MP", "PMOS", drain="A", gate="CLK_B", source="B", bulk="VDD"),
        ]

        result = recognizer.find_transmission_gates(transistors)

        assert len(result) == 1
        assert result[0].type == StructureType.TRANSMISSION_GATE
        # A and B are the signal nodes (bidirectional)
        assert result[0].input_nodes == {"A", "B"} or result[0].output_nodes == {"A", "B"}
        # CLK and CLK_B are control nodes
        assert result[0].control_nodes == {"CLK", "CLK_B"}

    def test_tgate_bidirectional_flow(self) -> None:
        """Transmission gate signal flow is bidirectional."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            TransistorInstance("MN", "NMOS", drain="node1", gate="EN", source="node2", bulk="VSS"),
            TransistorInstance(
                "MP", "PMOS", drain="node1", gate="EN_B", source="node2", bulk="VDD"
            ),
        ]

        result = recognizer.find_transmission_gates(transistors)

        assert len(result) == 1
        tg = result[0]
        # Both nodes are input AND output (bidirectional)
        signal_nodes = tg.input_nodes | tg.output_nodes
        assert "node1" in signal_nodes
        assert "node2" in signal_nodes

    def test_distinguishes_tgate_from_inverter(self) -> None:
        """TG not confused with inverter (no VDD/VSS on source/drain)."""
        recognizer = TransistorPatternRecognizer()

        # This looks like TG with VDD/VSS names as nodes
        # But we should NOT detect TG if nodes are power rails
        transistors = [
            TransistorInstance("MN", "NMOS", drain="VDD", gate="CLK", source="VSS", bulk="VSS"),
            TransistorInstance("MP", "PMOS", drain="VDD", gate="CLK_B", source="VSS", bulk="VDD"),
        ]

        # With explicit power net exclusion
        result = recognizer.find_transmission_gates(
            transistors, power_nets={"VDD", "VDDX", "VCC"}, ground_nets={"VSS", "VSSX", "GND"}
        )

        assert len(result) == 0

    def test_multiple_transmission_gates(self) -> None:
        """Multiple TGs in subcircuit are all detected."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # TG1: A <-> B
            TransistorInstance("MN1", "NMOS", drain="A", gate="CLK", source="B", bulk="VSS"),
            TransistorInstance("MP1", "PMOS", drain="A", gate="CLK_B", source="B", bulk="VDD"),
            # TG2: C <-> D
            TransistorInstance("MN2", "NMOS", drain="C", gate="EN", source="D", bulk="VSS"),
            TransistorInstance("MP2", "PMOS", drain="C", gate="EN_B", source="D", bulk="VDD"),
        ]

        result = recognizer.find_transmission_gates(transistors)

        assert len(result) == 2

    def test_tgate_with_swapped_source_drain(self) -> None:
        """TG detection works regardless of source/drain order."""
        recognizer = TransistorPatternRecognizer()

        # Source and drain are symmetric in TG
        transistors = [
            TransistorInstance("MN", "NMOS", drain="B", gate="CLK", source="A", bulk="VSS"),
            TransistorInstance("MP", "PMOS", drain="A", gate="CLK_B", source="B", bulk="VDD"),
        ]

        result = recognizer.find_transmission_gates(transistors)

        assert len(result) == 1

    def test_tgate_requires_complementary_gates(self) -> None:
        """TG requires different gate signals for PMOS and NMOS."""
        recognizer = TransistorPatternRecognizer()

        # Same gate on both - not a proper TG
        transistors = [
            TransistorInstance("MN", "NMOS", drain="A", gate="CLK", source="B", bulk="VSS"),
            TransistorInstance("MP", "PMOS", drain="A", gate="CLK", source="B", bulk="VDD"),
        ]

        result = recognizer.find_transmission_gates(transistors)

        # Still detected as TG (same gate is valid, just not complementary)
        # Some designs use inverted gate externally
        assert len(result) == 1


# =============================================================================
# NAND GATE RECOGNITION
# =============================================================================


class TestNandRecognition:
    """Tests for NAND gate pattern recognition."""

    def test_recognizes_nand2(self) -> None:
        """Parallel PMOS + series NMOS = NAND2.

        Pattern:
        - 2 PMOS in parallel: source=VDD, drains connected to output
        - 2 NMOS in series: top drain=output, bottom source=VSS
        """
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # Parallel PMOS pull-up
            TransistorInstance("MP1", "PMOS", drain="Y", gate="A", source="VDD", bulk="VDD"),
            TransistorInstance("MP2", "PMOS", drain="Y", gate="B", source="VDD", bulk="VDD"),
            # Series NMOS pull-down
            TransistorInstance("MN1", "NMOS", drain="Y", gate="A", source="n1", bulk="VSS"),
            TransistorInstance("MN2", "NMOS", drain="n1", gate="B", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_nand_gates(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 1
        assert result[0].type == StructureType.NAND
        assert result[0].input_nodes == {"A", "B"}
        assert result[0].output_nodes == {"Y"}

    def test_recognizes_nand3(self) -> None:
        """3-input NAND correctly identified."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # 3 parallel PMOS
            TransistorInstance("MP1", "PMOS", drain="Y", gate="A", source="VDD", bulk="VDD"),
            TransistorInstance("MP2", "PMOS", drain="Y", gate="B", source="VDD", bulk="VDD"),
            TransistorInstance("MP3", "PMOS", drain="Y", gate="C", source="VDD", bulk="VDD"),
            # 3 series NMOS
            TransistorInstance("MN1", "NMOS", drain="Y", gate="A", source="n1", bulk="VSS"),
            TransistorInstance("MN2", "NMOS", drain="n1", gate="B", source="n2", bulk="VSS"),
            TransistorInstance("MN3", "NMOS", drain="n2", gate="C", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_nand_gates(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 1
        assert result[0].input_nodes == {"A", "B", "C"}

    def test_nand2_signal_flow(self) -> None:
        """NAND signal flows from all inputs to output."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            TransistorInstance("MP1", "PMOS", drain="out", gate="in1", source="VDD", bulk="VDD"),
            TransistorInstance("MP2", "PMOS", drain="out", gate="in2", source="VDD", bulk="VDD"),
            TransistorInstance("MN1", "NMOS", drain="out", gate="in1", source="mid", bulk="VSS"),
            TransistorInstance("MN2", "NMOS", drain="mid", gate="in2", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_nand_gates(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 1
        nand = result[0]
        assert "in1" in nand.input_nodes
        assert "in2" in nand.input_nodes
        assert "out" in nand.output_nodes


# =============================================================================
# NOR GATE RECOGNITION
# =============================================================================


class TestNorRecognition:
    """Tests for NOR gate pattern recognition."""

    def test_recognizes_nor2(self) -> None:
        """Series PMOS + parallel NMOS = NOR2.

        Pattern:
        - 2 PMOS in series: top source=VDD, bottom drain=output
        - 2 NMOS in parallel: drains connected to output, sources=VSS
        """
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # Series PMOS pull-up
            TransistorInstance("MP1", "PMOS", drain="n1", gate="A", source="VDD", bulk="VDD"),
            TransistorInstance("MP2", "PMOS", drain="Y", gate="B", source="n1", bulk="VDD"),
            # Parallel NMOS pull-down
            TransistorInstance("MN1", "NMOS", drain="Y", gate="A", source="VSS", bulk="VSS"),
            TransistorInstance("MN2", "NMOS", drain="Y", gate="B", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_nor_gates(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 1
        assert result[0].type == StructureType.NOR
        assert result[0].input_nodes == {"A", "B"}
        assert result[0].output_nodes == {"Y"}

    def test_recognizes_nor3(self) -> None:
        """3-input NOR correctly identified."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            # 3 series PMOS
            TransistorInstance("MP1", "PMOS", drain="n1", gate="A", source="VDD", bulk="VDD"),
            TransistorInstance("MP2", "PMOS", drain="n2", gate="B", source="n1", bulk="VDD"),
            TransistorInstance("MP3", "PMOS", drain="Y", gate="C", source="n2", bulk="VDD"),
            # 3 parallel NMOS
            TransistorInstance("MN1", "NMOS", drain="Y", gate="A", source="VSS", bulk="VSS"),
            TransistorInstance("MN2", "NMOS", drain="Y", gate="B", source="VSS", bulk="VSS"),
            TransistorInstance("MN3", "NMOS", drain="Y", gate="C", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_nor_gates(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 1
        assert result[0].input_nodes == {"A", "B", "C"}

    def test_nor2_signal_flow(self) -> None:
        """NOR signal flows from all inputs to output."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            TransistorInstance("MP1", "PMOS", drain="mid", gate="in1", source="VDD", bulk="VDD"),
            TransistorInstance("MP2", "PMOS", drain="out", gate="in2", source="mid", bulk="VDD"),
            TransistorInstance("MN1", "NMOS", drain="out", gate="in1", source="VSS", bulk="VSS"),
            TransistorInstance("MN2", "NMOS", drain="out", gate="in2", source="VSS", bulk="VSS"),
        ]

        result = recognizer.find_nor_gates(transistors, vdd="VDD", vss="VSS")

        assert len(result) == 1
        nor = result[0]
        assert "in1" in nor.input_nodes
        assert "in2" in nor.input_nodes
        assert "out" in nor.output_nodes


# =============================================================================
# EDGE CASES AND ERROR HANDLING
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_transistor_list(self) -> None:
        """Empty transistor list returns empty results."""
        recognizer = TransistorPatternRecognizer()

        assert recognizer.find_inverters([], vdd="VDD", vss="VSS") == []
        assert recognizer.find_transmission_gates([]) == []
        assert recognizer.find_nand_gates([], vdd="VDD", vss="VSS") == []
        assert recognizer.find_nor_gates([], vdd="VDD", vss="VSS") == []

    def test_single_transistor(self) -> None:
        """Single transistor cannot form any pattern."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            TransistorInstance("M1", "NMOS", drain="Y", gate="A", source="VSS", bulk="VSS"),
        ]

        assert recognizer.find_inverters(transistors, vdd="VDD", vss="VSS") == []
        assert recognizer.find_transmission_gates(transistors) == []
        assert recognizer.find_nand_gates(transistors, vdd="VDD", vss="VSS") == []
        assert recognizer.find_nor_gates(transistors, vdd="VDD", vss="VSS") == []

    def test_unrelated_transistors(self) -> None:
        """Transistors with no common nodes form no patterns."""
        recognizer = TransistorPatternRecognizer()

        transistors = [
            TransistorInstance("M1", "NMOS", drain="A", gate="B", source="C", bulk="VSS"),
            TransistorInstance("M2", "PMOS", drain="X", gate="Y", source="Z", bulk="VDD"),
        ]

        assert recognizer.find_inverters(transistors, vdd="VDD", vss="VSS") == []
        assert recognizer.find_transmission_gates(transistors) == []

    def test_recognized_structure_dataclass(self) -> None:
        """RecognizedStructure dataclass works correctly."""
        structure = RecognizedStructure(
            type=StructureType.INVERTER,
            input_nodes={"A"},
            output_nodes={"Y"},
            control_nodes=set(),
            transistors=["MP1", "MN1"],
        )

        assert structure.type == StructureType.INVERTER
        assert "A" in structure.input_nodes
        assert "Y" in structure.output_nodes
        assert len(structure.transistors) == 2

    def test_structure_type_enum(self) -> None:
        """StructureType enum has expected values."""
        assert StructureType.INVERTER.value == "inverter"
        assert StructureType.TRANSMISSION_GATE.value == "tgate"
        assert StructureType.NAND.value == "nand"
        assert StructureType.NOR.value == "nor"
        assert StructureType.PASS_TRANSISTOR.value == "pass"
        assert StructureType.UNKNOWN.value == "unknown"
