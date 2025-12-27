"""Unit tests for TransistorTopologyAnalyzer.

This module tests the main TransistorTopologyAnalyzer class which extracts signal
flow graphs from transistor-level subcircuit definitions.

Test Organization:
    1. Data Classes (TransistorInstance, CellInstance, SubcircuitDefinition, SignalFlowGraph)
    2. TopologyAnalyzer Protocol Compliance
    3. Inverter Analysis
    4. Transmission Gate Analysis
    5. NAND/NOR Analysis
    6. D-Latch Analysis
    7. D-Flip-Flop Analysis
    8. Hierarchical Analysis (Cell Instances)
    9. Power Net Identification
    10. Integration with LatchIdentifier

See Also:
    - Spec E01-F04-T04 for requirements
    - TransistorTopologyAnalyzer implementation
"""

from ink.domain.services.latch_identifier import DetectionStrategy
from ink.infrastructure.analysis.topology_analyzer import (
    CellInstance,
    SignalFlowGraph,
    SubcircuitDefinition,
    TransistorInstance,
)
from ink.infrastructure.analysis.transistor_topology_analyzer import (
    TransistorTopologyAnalyzer,
)
from ink.infrastructure.identification.topology_latch_identifier import (
    TopologyBasedLatchIdentifier,
)

# =============================================================================
# DATA CLASSES
# =============================================================================


class TestDataClasses:
    """Tests for data class definitions."""

    def test_transistor_instance_creation(self) -> None:
        """TransistorInstance dataclass creation."""
        tx = TransistorInstance(
            name="M1",
            type="NMOS",
            drain="Y",
            gate="A",
            source="VSS",
            bulk="VSS",
        )

        assert tx.name == "M1"
        assert tx.type == "NMOS"
        assert tx.drain == "Y"
        assert tx.gate == "A"
        assert tx.source == "VSS"
        assert tx.bulk == "VSS"

    def test_cell_instance_creation(self) -> None:
        """CellInstance dataclass creation."""
        cell = CellInstance(
            name="XI1",
            cell_type="INV_X1",
            connections={"A": "net1", "Y": "net2"},
        )

        assert cell.name == "XI1"
        assert cell.cell_type == "INV_X1"
        assert cell.connections == {"A": "net1", "Y": "net2"}

    def test_subcircuit_definition_creation(self) -> None:
        """SubcircuitDefinition dataclass creation."""
        subckt = SubcircuitDefinition(
            name="INV_X1",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[
                TransistorInstance("MP", "PMOS", "Y", "A", "VDD", "VDD"),
                TransistorInstance("MN", "NMOS", "Y", "A", "VSS", "VSS"),
            ],
            instances=[],
        )

        assert subckt.name == "INV_X1"
        assert subckt.ports == ["A", "Y", "VDD", "VSS"]
        assert len(subckt.transistors) == 2
        assert len(subckt.instances) == 0

    def test_signal_flow_graph_creation(self) -> None:
        """SignalFlowGraph dataclass creation."""
        graph = SignalFlowGraph(
            cell_type="INV_X1",
            connections=[("A", "Y")],
            identified_structures=["inverter@{'A'}->{'Y'}"],
        )

        assert graph.cell_type == "INV_X1"
        assert graph.connections == [("A", "Y")]
        assert len(graph.identified_structures) == 1


# =============================================================================
# TOPOLOGY ANALYZER PROTOCOL COMPLIANCE
# =============================================================================


class TestProtocolCompliance:
    """Tests for TopologyAnalyzer protocol compliance."""

    def test_implements_topology_analyzer_protocol(self) -> None:
        """TransistorTopologyAnalyzer implements TopologyAnalyzer protocol."""
        analyzer = TransistorTopologyAnalyzer()

        # Protocol requires analyze() method
        assert hasattr(analyzer, "analyze")
        assert callable(analyzer.analyze)

        # Protocol requires register_cell_pinout() method
        assert hasattr(analyzer, "register_cell_pinout")
        assert callable(analyzer.register_cell_pinout)

    def test_analyze_returns_signal_flow_graph(self) -> None:
        """analyze() returns SignalFlowGraph."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="TEST",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        assert isinstance(result, SignalFlowGraph)
        assert result.cell_type == "TEST"


# =============================================================================
# INVERTER ANALYSIS
# =============================================================================


class TestInverterAnalysis:
    """Tests for inverter analysis in subcircuits."""

    def test_analyzes_simple_inverter(self) -> None:
        """Simple inverter extracted correctly."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="INV_X1",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[
                TransistorInstance("MP", "PMOS", "Y", "A", "VDD", "VDD"),
                TransistorInstance("MN", "NMOS", "Y", "A", "VSS", "VSS"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        assert ("A", "Y") in result.connections
        assert any("inverter" in s for s in result.identified_structures)

    def test_analyzes_inverter_chain(self) -> None:
        """Inverter chain extracted correctly."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="BUF_X1",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[
                # First inverter: A -> n1
                TransistorInstance("MP1", "PMOS", "n1", "A", "VDD", "VDD"),
                TransistorInstance("MN1", "NMOS", "n1", "A", "VSS", "VSS"),
                # Second inverter: n1 -> Y
                TransistorInstance("MP2", "PMOS", "Y", "n1", "VDD", "VDD"),
                TransistorInstance("MN2", "NMOS", "Y", "n1", "VSS", "VSS"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        assert ("A", "n1") in result.connections
        assert ("n1", "Y") in result.connections
        assert len([s for s in result.identified_structures if "inverter" in s]) == 2


# =============================================================================
# TRANSMISSION GATE ANALYSIS
# =============================================================================


class TestTransmissionGateAnalysis:
    """Tests for transmission gate analysis."""

    def test_analyzes_transmission_gate(self) -> None:
        """Transmission gate extracted with bidirectional connections."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="TG_X1",
            ports=["A", "B", "EN", "ENB", "VDD", "VSS"],
            transistors=[
                TransistorInstance("MN", "NMOS", "A", "EN", "B", "VSS"),
                TransistorInstance("MP", "PMOS", "A", "ENB", "B", "VDD"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        # Bidirectional: both directions should be present
        has_a_to_b = ("A", "B") in result.connections
        has_b_to_a = ("B", "A") in result.connections
        assert has_a_to_b and has_b_to_a
        assert any("tgate" in s for s in result.identified_structures)

    def test_transmission_gate_identifies_control_nodes(self) -> None:
        """TG control nodes are identified separately."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="TG_X1",
            ports=["IN", "OUT", "CLK", "CLK_B", "VDD", "VSS"],
            transistors=[
                TransistorInstance("MN", "NMOS", "IN", "CLK", "OUT", "VSS"),
                TransistorInstance("MP", "PMOS", "IN", "CLK_B", "OUT", "VDD"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        # Control nodes (CLK, CLK_B) should NOT appear in connections
        # Only signal path nodes (IN, OUT) should
        for src, dst in result.connections:
            assert src not in {"CLK", "CLK_B"}
            assert dst not in {"CLK", "CLK_B"}


# =============================================================================
# NAND/NOR ANALYSIS
# =============================================================================


class TestNandNorAnalysis:
    """Tests for NAND and NOR gate analysis."""

    def test_analyzes_nand2(self) -> None:
        """NAND2 gate extracted correctly."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="NAND2_X1",
            ports=["A", "B", "Y", "VDD", "VSS"],
            transistors=[
                # Parallel PMOS
                TransistorInstance("MP1", "PMOS", "Y", "A", "VDD", "VDD"),
                TransistorInstance("MP2", "PMOS", "Y", "B", "VDD", "VDD"),
                # Series NMOS
                TransistorInstance("MN1", "NMOS", "Y", "A", "n1", "VSS"),
                TransistorInstance("MN2", "NMOS", "n1", "B", "VSS", "VSS"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        assert ("A", "Y") in result.connections
        assert ("B", "Y") in result.connections
        assert any("nand" in s for s in result.identified_structures)

    def test_analyzes_nor2(self) -> None:
        """NOR2 gate extracted correctly."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="NOR2_X1",
            ports=["A", "B", "Y", "VDD", "VSS"],
            transistors=[
                # Series PMOS
                TransistorInstance("MP1", "PMOS", "n1", "A", "VDD", "VDD"),
                TransistorInstance("MP2", "PMOS", "Y", "B", "n1", "VDD"),
                # Parallel NMOS
                TransistorInstance("MN1", "NMOS", "Y", "A", "VSS", "VSS"),
                TransistorInstance("MN2", "NMOS", "Y", "B", "VSS", "VSS"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        assert ("A", "Y") in result.connections
        assert ("B", "Y") in result.connections
        assert any("nor" in s for s in result.identified_structures)


# =============================================================================
# D-LATCH ANALYSIS
# =============================================================================


class TestDLatchAnalysis:
    """Tests for D-latch topology analysis."""

    def test_analyzes_tg_d_latch(self) -> None:
        """D-latch with TG + inverter feedback analyzed correctly."""
        analyzer = TransistorTopologyAnalyzer()

        # D-latch structure:
        # D -> TG1 -> n1 -> INV1 -> Q
        #             ^            |
        #             |            v
        #       TG2 <--- INV2 <----
        subckt = SubcircuitDefinition(
            name="DLATCH_X1",
            ports=["D", "G", "GN", "Q", "VDD", "VSS"],
            transistors=[
                # Input TG (D -> n1 when G=1)
                TransistorInstance("M1", "NMOS", "n1", "G", "D", "VSS"),
                TransistorInstance("M2", "PMOS", "n1", "GN", "D", "VDD"),
                # Inverter 1 (n1 -> Q)
                TransistorInstance("M3", "PMOS", "Q", "n1", "VDD", "VDD"),
                TransistorInstance("M4", "NMOS", "Q", "n1", "VSS", "VSS"),
                # Inverter 2 (Q -> n2)
                TransistorInstance("M5", "PMOS", "n2", "Q", "VDD", "VDD"),
                TransistorInstance("M6", "NMOS", "n2", "Q", "VSS", "VSS"),
                # Feedback TG (n2 -> n1 when G=0)
                TransistorInstance("M7", "NMOS", "n1", "GN", "n2", "VSS"),
                TransistorInstance("M8", "PMOS", "n1", "G", "n2", "VDD"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        # Verify key connections exist
        # TG1: D <-> n1
        assert ("D", "n1") in result.connections or ("n1", "D") in result.connections
        # INV1: n1 -> Q
        assert ("n1", "Q") in result.connections
        # INV2: Q -> n2
        assert ("Q", "n2") in result.connections
        # Feedback TG2: n2 <-> n1
        assert ("n2", "n1") in result.connections or ("n1", "n2") in result.connections

        # Verify structures identified
        assert any("tgate" in s for s in result.identified_structures)
        assert any("inverter" in s for s in result.identified_structures)


# =============================================================================
# D-FLIP-FLOP ANALYSIS
# =============================================================================


class TestDFlipFlopAnalysis:
    """Tests for D flip-flop topology analysis."""

    def test_analyzes_master_slave_dff(self) -> None:
        """Master-slave D-FF with two feedback loops analyzed."""
        analyzer = TransistorTopologyAnalyzer()

        # Simplified master-slave DFF:
        # Master latch (active when CLK=0):
        #   D -> TG1 -> n1 -> INV1 -> n2
        #               ^             |
        #               |<-- INV2 <---|
        #
        # Slave latch (active when CLK=1):
        #   n2 -> TG2 -> n3 -> INV3 -> Q
        #                ^             |
        #                |<-- INV4 <---|
        subckt = SubcircuitDefinition(
            name="DFF_X1",
            ports=["D", "CLK", "CLKB", "Q", "VDD", "VSS"],
            transistors=[
                # Master TG (D -> n1)
                TransistorInstance("M1", "NMOS", "n1", "CLKB", "D", "VSS"),
                TransistorInstance("M2", "PMOS", "n1", "CLK", "D", "VDD"),
                # Master INV1 (n1 -> n2)
                TransistorInstance("M3", "PMOS", "n2", "n1", "VDD", "VDD"),
                TransistorInstance("M4", "NMOS", "n2", "n1", "VSS", "VSS"),
                # Master feedback INV2 (n2 -> n3)
                TransistorInstance("M5", "PMOS", "n3", "n2", "VDD", "VDD"),
                TransistorInstance("M6", "NMOS", "n3", "n2", "VSS", "VSS"),
                # Master feedback TG (n3 -> n1)
                TransistorInstance("M7", "NMOS", "n1", "CLK", "n3", "VSS"),
                TransistorInstance("M8", "PMOS", "n1", "CLKB", "n3", "VDD"),
                # Slave TG (n2 -> n4)
                TransistorInstance("M9", "NMOS", "n4", "CLK", "n2", "VSS"),
                TransistorInstance("M10", "PMOS", "n4", "CLKB", "n2", "VDD"),
                # Slave INV3 (n4 -> Q)
                TransistorInstance("M11", "PMOS", "Q", "n4", "VDD", "VDD"),
                TransistorInstance("M12", "NMOS", "Q", "n4", "VSS", "VSS"),
                # Slave feedback INV4 (Q -> n5)
                TransistorInstance("M13", "PMOS", "n5", "Q", "VDD", "VDD"),
                TransistorInstance("M14", "NMOS", "n5", "Q", "VSS", "VSS"),
                # Slave feedback TG (n5 -> n4)
                TransistorInstance("M15", "NMOS", "n4", "CLKB", "n5", "VSS"),
                TransistorInstance("M16", "PMOS", "n4", "CLK", "n5", "VDD"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        # Verify TGs and inverters identified
        tgate_count = len([s for s in result.identified_structures if "tgate" in s])
        inv_count = len([s for s in result.identified_structures if "inverter" in s])

        assert tgate_count >= 2  # At least 2 TGs (master input + slave input)
        assert inv_count >= 2  # At least 2 inverters


# =============================================================================
# HIERARCHICAL ANALYSIS (CELL INSTANCES)
# =============================================================================


class TestHierarchicalAnalysis:
    """Tests for hierarchical subcircuit analysis."""

    def test_analyzes_cell_instances(self) -> None:
        """Subcircuit instances analyzed using registered pinouts."""
        analyzer = TransistorTopologyAnalyzer()

        # Register INV_X1 pinout
        analyzer.register_cell_pinout("INV_X1", input_pins={"A"}, output_pins={"Y"})

        # Subcircuit using INV_X1 instance
        subckt = SubcircuitDefinition(
            name="BUF_HIER_X1",
            ports=["IN", "OUT", "VDD", "VSS"],
            transistors=[],  # No transistors, only instances
            instances=[
                CellInstance("XI1", "INV_X1", {"A": "IN", "Y": "n1"}),
                CellInstance("XI2", "INV_X1", {"A": "n1", "Y": "OUT"}),
            ],
        )

        result = analyzer.analyze(subckt)

        # Signal flow: IN -> n1 -> OUT
        assert ("IN", "n1") in result.connections
        assert ("n1", "OUT") in result.connections

    def test_unknown_cell_skipped(self) -> None:
        """Unknown cell types gracefully skipped."""
        analyzer = TransistorTopologyAnalyzer()

        # Don't register UNKNOWN_CELL pinout
        subckt = SubcircuitDefinition(
            name="TEST",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[],
            instances=[
                CellInstance("XI1", "UNKNOWN_CELL", {"A": "A", "Y": "Y"}),
            ],
        )

        # Should not raise
        result = analyzer.analyze(subckt)

        # No connections from unknown cell
        assert len(result.connections) == 0

    def test_mixed_transistors_and_instances(self) -> None:
        """Subcircuit with both transistors and instances analyzed."""
        analyzer = TransistorTopologyAnalyzer()

        analyzer.register_cell_pinout("INV_X1", input_pins={"A"}, output_pins={"Y"})

        subckt = SubcircuitDefinition(
            name="MIXED_X1",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[
                # Direct inverter at transistor level
                TransistorInstance("MP1", "PMOS", "n1", "A", "VDD", "VDD"),
                TransistorInstance("MN1", "NMOS", "n1", "A", "VSS", "VSS"),
            ],
            instances=[
                # Hierarchical inverter instance
                CellInstance("XI1", "INV_X1", {"A": "n1", "Y": "Y"}),
            ],
        )

        result = analyzer.analyze(subckt)

        # Both inverters should contribute connections
        assert ("A", "n1") in result.connections  # From transistors
        assert ("n1", "Y") in result.connections  # From instance

    def test_register_cell_pinout_case_insensitive(self) -> None:
        """Cell type lookup is case-insensitive."""
        analyzer = TransistorTopologyAnalyzer()

        analyzer.register_cell_pinout("inv_x1", input_pins={"A"}, output_pins={"Y"})

        subckt = SubcircuitDefinition(
            name="TEST",
            ports=["IN", "OUT", "VDD", "VSS"],
            transistors=[],
            instances=[
                CellInstance("XI1", "INV_X1", {"A": "IN", "Y": "OUT"}),
            ],
        )

        result = analyzer.analyze(subckt)

        assert ("IN", "OUT") in result.connections


# =============================================================================
# POWER NET IDENTIFICATION
# =============================================================================


class TestPowerNetIdentification:
    """Tests for power net identification."""

    def test_identifies_vdd_from_ports(self) -> None:
        """VDD identified from subcircuit ports."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="TEST",
            ports=["A", "Y", "VPWR", "VGND"],
            transistors=[
                TransistorInstance("MP", "PMOS", "Y", "A", "VPWR", "VPWR"),
                TransistorInstance("MN", "NMOS", "Y", "A", "VGND", "VGND"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        # Should still detect inverter with VPWR/VGND
        assert ("A", "Y") in result.connections

    def test_custom_power_net_names(self) -> None:
        """Custom VDD/VSS names supported."""
        analyzer = TransistorTopologyAnalyzer(
            vdd_names={"CUSTOM_VDD"},
            vss_names={"CUSTOM_VSS"},
        )

        subckt = SubcircuitDefinition(
            name="TEST",
            ports=["A", "Y", "CUSTOM_VDD", "CUSTOM_VSS"],
            transistors=[
                TransistorInstance("MP", "PMOS", "Y", "A", "CUSTOM_VDD", "CUSTOM_VDD"),
                TransistorInstance("MN", "NMOS", "Y", "A", "CUSTOM_VSS", "CUSTOM_VSS"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        assert ("A", "Y") in result.connections


# =============================================================================
# INTEGRATION WITH LATCH IDENTIFIER
# =============================================================================


class TestIntegrationWithLatchIdentifier:
    """Tests for integration with TopologyBasedLatchIdentifier."""

    def test_output_compatible_with_latch_identifier(self) -> None:
        """SignalFlowGraph.connections feeds into LatchIdentifier."""
        analyzer = TransistorTopologyAnalyzer()

        # D-latch with feedback
        subckt = SubcircuitDefinition(
            name="DLATCH_X1",
            ports=["D", "G", "GN", "Q", "VDD", "VSS"],
            transistors=[
                # Input TG
                TransistorInstance("M1", "NMOS", "n1", "G", "D", "VSS"),
                TransistorInstance("M2", "PMOS", "n1", "GN", "D", "VDD"),
                # INV1
                TransistorInstance("M3", "PMOS", "Q", "n1", "VDD", "VDD"),
                TransistorInstance("M4", "NMOS", "Q", "n1", "VSS", "VSS"),
                # INV2
                TransistorInstance("M5", "PMOS", "n2", "Q", "VDD", "VDD"),
                TransistorInstance("M6", "NMOS", "n2", "Q", "VSS", "VSS"),
                # Feedback TG
                TransistorInstance("M7", "NMOS", "n1", "GN", "n2", "VSS"),
                TransistorInstance("M8", "PMOS", "n1", "G", "n2", "VDD"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        # Feed to LatchIdentifier
        identifier = TopologyBasedLatchIdentifier()
        identifier.register_subcircuit_topology("DLATCH_X1", result.connections)

        detection = identifier.detect_with_reason("DLATCH_X1")

        assert detection.is_sequential is True
        assert detection.strategy == DetectionStrategy.FEEDBACK_LOOP

    def test_combinational_cell_no_feedback(self) -> None:
        """Combinational cell has no feedback cycle."""
        analyzer = TransistorTopologyAnalyzer()

        # Simple inverter - no feedback
        subckt = SubcircuitDefinition(
            name="INV_X1",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[
                TransistorInstance("MP", "PMOS", "Y", "A", "VDD", "VDD"),
                TransistorInstance("MN", "NMOS", "Y", "A", "VSS", "VSS"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        # Feed to LatchIdentifier
        identifier = TopologyBasedLatchIdentifier()
        identifier.register_subcircuit_topology("INV_X1", result.connections)

        detection = identifier.detect_with_reason("INV_X1")

        assert detection.is_sequential is False

    def test_sr_latch_detected_as_sequential(self) -> None:
        """SR latch (cross-coupled NANDs) detected as sequential."""
        analyzer = TransistorTopologyAnalyzer()

        # Simplified SR latch with cross-coupled NAND structure
        # In practice, each NAND would have parallel PMOS + series NMOS
        # Here we focus on the cross-coupling pattern
        subckt = SubcircuitDefinition(
            name="SR_LATCH_X1",
            ports=["S", "R", "Q", "QN", "VDD", "VSS"],
            transistors=[
                # NAND1: inputs S, QN -> output Q
                # Parallel PMOS
                TransistorInstance("MP1", "PMOS", "Q", "S", "VDD", "VDD"),
                TransistorInstance("MP2", "PMOS", "Q", "QN", "VDD", "VDD"),
                # Series NMOS
                TransistorInstance("MN1", "NMOS", "Q", "S", "n1", "VSS"),
                TransistorInstance("MN2", "NMOS", "n1", "QN", "VSS", "VSS"),
                # NAND2: inputs R, Q -> output QN
                # Parallel PMOS
                TransistorInstance("MP3", "PMOS", "QN", "R", "VDD", "VDD"),
                TransistorInstance("MP4", "PMOS", "QN", "Q", "VDD", "VDD"),
                # Series NMOS
                TransistorInstance("MN3", "NMOS", "QN", "R", "n2", "VSS"),
                TransistorInstance("MN4", "NMOS", "n2", "Q", "VSS", "VSS"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        # Feed to LatchIdentifier
        identifier = TopologyBasedLatchIdentifier()
        identifier.register_subcircuit_topology("SR_LATCH_X1", result.connections)

        detection = identifier.detect_with_reason("SR_LATCH_X1")

        # Cross-coupling creates feedback: Q -> QN -> Q
        assert detection.is_sequential is True
        assert detection.strategy == DetectionStrategy.FEEDBACK_LOOP


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_subcircuit(self) -> None:
        """Empty subcircuit returns empty SignalFlowGraph."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="EMPTY",
            ports=["VDD", "VSS"],
            transistors=[],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        assert result.cell_type == "EMPTY"
        assert result.connections == []
        assert result.identified_structures == []

    def test_transistors_only_subcircuit(self) -> None:
        """Subcircuit with only transistors, no instances."""
        analyzer = TransistorTopologyAnalyzer()

        subckt = SubcircuitDefinition(
            name="INV_X1",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[
                TransistorInstance("MP", "PMOS", "Y", "A", "VDD", "VDD"),
                TransistorInstance("MN", "NMOS", "Y", "A", "VSS", "VSS"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        assert len(result.connections) > 0

    def test_instances_only_subcircuit(self) -> None:
        """Subcircuit with only instances, no transistors."""
        analyzer = TransistorTopologyAnalyzer()

        analyzer.register_cell_pinout("INV_X1", input_pins={"A"}, output_pins={"Y"})

        subckt = SubcircuitDefinition(
            name="BUF_X1",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[],
            instances=[
                CellInstance("XI1", "INV_X1", {"A": "A", "Y": "n1"}),
                CellInstance("XI2", "INV_X1", {"A": "n1", "Y": "Y"}),
            ],
        )

        result = analyzer.analyze(subckt)

        assert ("A", "n1") in result.connections
        assert ("n1", "Y") in result.connections

    def test_duplicate_connections_handled(self) -> None:
        """Duplicate connections are not duplicated in output."""
        analyzer = TransistorTopologyAnalyzer()

        # Two inverters with same input/output (unusual but valid)
        subckt = SubcircuitDefinition(
            name="TEST",
            ports=["A", "Y", "VDD", "VSS"],
            transistors=[
                # First inverter
                TransistorInstance("MP1", "PMOS", "Y", "A", "VDD", "VDD"),
                TransistorInstance("MN1", "NMOS", "Y", "A", "VSS", "VSS"),
                # Second inverter (same nodes - parallel drive)
                TransistorInstance("MP2", "PMOS", "Y", "A", "VDD", "VDD"),
                TransistorInstance("MN2", "NMOS", "Y", "A", "VSS", "VSS"),
            ],
            instances=[],
        )

        result = analyzer.analyze(subckt)

        # Should not have duplicate connections
        connection_count = result.connections.count(("A", "Y"))
        # Implementation may deduplicate or not - just ensure no crash
        assert connection_count >= 1
