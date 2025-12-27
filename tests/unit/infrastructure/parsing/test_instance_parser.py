"""Unit tests for InstanceParser.

This test module validates the InstanceParser infrastructure component, which
parses X-prefixed CDL instance lines and creates CellInstance value objects.
Tests follow TDD principles - they were written before the implementation.

Test Categories:
1. Basic Parsing - Simple instance lines with known cell types
2. Port Mapping - Positional net-to-port mapping using subcircuit definitions
3. Unknown Cell Types - Handling instances with undefined cell types
4. Connection Mismatches - Too few/many connections
5. Validation - Name format, cell type presence
6. Edge Cases - Hierarchical names, special net names, empty cases

Architecture:
    InstanceParser lives in the infrastructure layer. It depends on:
    - CDLLexer tokens (INSTANCE type)
    - SubcircuitDefinition value objects for port mapping
    - Produces CellInstance value objects

    The parser collects warnings for graceful degradation (unknown cell types,
    connection mismatches) rather than raising errors.
"""

from __future__ import annotations

import pytest

from ink.domain.value_objects.subcircuit import SubcircuitDefinition
from ink.infrastructure.parsing.cdl_lexer import CDLToken, LineType


class TestInstanceParserConstruction:
    """Tests for InstanceParser initialization."""

    def test_create_parser_with_definitions(self) -> None:
        """Test creating parser with subcircuit definitions dict.

        The parser requires a dictionary of subcircuit definitions to
        map positional nets to named ports.
        """
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {
            "INV": SubcircuitDefinition("INV", ["A", "Y", "VDD", "VSS"]),
            "NAND2": SubcircuitDefinition("NAND2", ["A1", "A2", "ZN", "VDD", "VSS"]),
        }
        parser = InstanceParser(defs)

        # Parser should be created without error
        assert parser is not None

    def test_create_parser_with_empty_definitions(self) -> None:
        """Test creating parser with empty definitions dict.

        Parser should work with empty definitions - instances will have
        generic port names and warnings will be logged.
        """
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})

        # Should work without error
        assert parser is not None


class TestInstanceParserBasicParsing:
    """Tests for basic instance line parsing."""

    def test_parse_simple_instance(self) -> None:
        """Test parsing a simple instance with known cell type.

        Given: .SUBCKT INV A Y VDD VSS and line "XI1 net1 net2 VDD VSS INV"
        When: We parse the instance line
        Then: CellInstance has correct name, cell_type, and connections
        """
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"INV": SubcircuitDefinition("INV", ["A", "Y", "VDD", "VSS"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI1 net1 net2 VDD VSS INV",
            raw="XI1 net1 net2 VDD VSS INV",
        )

        instance = parser.parse_instance_line(token)

        assert instance.name == "XI1"
        assert instance.cell_type == "INV"
        assert instance.connections == {
            "A": "net1",
            "Y": "net2",
            "VDD": "VDD",
            "VSS": "VSS",
        }

    def test_parse_instance_with_nand_cell(self) -> None:
        """Test parsing NAND2 instance with multiple inputs."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {
            "NAND2": SubcircuitDefinition("NAND2", ["A1", "A2", "ZN", "VDD", "VSS"])
        }
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=10,
            line_type=LineType.INSTANCE,
            content="XNAND_1 in1 in2 out VDD VSS NAND2",
            raw="XNAND_1 in1 in2 out VDD VSS NAND2",
        )

        instance = parser.parse_instance_line(token)

        assert instance.name == "XNAND_1"
        assert instance.cell_type == "NAND2"
        assert instance.connections["A1"] == "in1"
        assert instance.connections["A2"] == "in2"
        assert instance.connections["ZN"] == "out"

    def test_parse_instance_lowercase_x_prefix(self) -> None:
        """Test parsing instance with lowercase 'x' prefix."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"INV": SubcircuitDefinition("INV", ["A", "Y"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="xI1 net1 net2 INV",
            raw="xI1 net1 net2 INV",
        )

        instance = parser.parse_instance_line(token)

        assert instance.name == "xI1"
        assert instance.cell_type == "INV"


class TestInstanceParserHierarchicalNames:
    """Tests for hierarchical instance name parsing."""

    def test_parse_hierarchical_instance_name(self) -> None:
        """Test instance with hierarchical path using '/' separator."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"ADDER": SubcircuitDefinition("ADDER", ["A", "B", "CIN", "S", "COUT"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=20,
            line_type=LineType.INSTANCE,
            content="XI_CORE/U_ALU/XI_ADD a b cin sum cout ADDER",
            raw="XI_CORE/U_ALU/XI_ADD a b cin sum cout ADDER",
        )

        instance = parser.parse_instance_line(token)

        assert instance.name == "XI_CORE/U_ALU/XI_ADD"
        assert "/" in instance.name
        assert instance.cell_type == "ADDER"

    def test_parse_deeply_nested_hierarchy(self) -> None:
        """Test instance with deep hierarchy nesting."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"BUF": SubcircuitDefinition("BUF", ["A", "Y"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=30,
            line_type=LineType.INSTANCE,
            content="XTOP/XMID1/XMID2/XMID3/XLEAF in out BUF",
            raw="XTOP/XMID1/XMID2/XMID3/XLEAF in out BUF",
        )

        instance = parser.parse_instance_line(token)

        assert instance.name == "XTOP/XMID1/XMID2/XMID3/XLEAF"
        assert instance.name.count("/") == 4


class TestInstanceParserUnknownCellTypes:
    """Tests for handling unknown cell types."""

    def test_unknown_cell_type_warning(self) -> None:
        """Test warning logged for unknown cell type.

        When a cell type is not in the definitions dict, the parser should:
        1. Log a warning
        2. Create generic port names (port0, port1, etc.)
        3. Still create a valid CellInstance
        """
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})  # No definitions

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI1 net1 net2 UNKNOWN_CELL",
            raw="XI1 net1 net2 UNKNOWN_CELL",
        )

        instance = parser.parse_instance_line(token)

        # Instance should still be created
        assert instance.cell_type == "UNKNOWN_CELL"
        assert instance.name == "XI1"

        # Warning should be logged
        warnings = parser.get_warnings()
        assert len(warnings) > 0
        assert "UNKNOWN_CELL" in warnings[0]

    def test_unknown_cell_generic_port_names(self) -> None:
        """Test that unknown cell types get generic port names."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI1 net1 net2 net3 UNKNOWN",
            raw="XI1 net1 net2 net3 UNKNOWN",
        )

        instance = parser.parse_instance_line(token)

        # Should have generic port names: port0, port1, port2
        assert "port0" in instance.connections
        assert "port1" in instance.connections
        assert "port2" in instance.connections
        assert instance.connections["port0"] == "net1"
        assert instance.connections["port1"] == "net2"
        assert instance.connections["port2"] == "net3"

    def test_multiple_unknown_cells_accumulate_warnings(self) -> None:
        """Test that multiple unknown cell types each generate a warning."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})

        token1 = CDLToken(5, LineType.INSTANCE, "XI1 n1 CELL_A", "XI1 n1 CELL_A")
        token2 = CDLToken(6, LineType.INSTANCE, "XI2 n1 CELL_B", "XI2 n1 CELL_B")

        parser.parse_instance_line(token1)
        parser.parse_instance_line(token2)

        warnings = parser.get_warnings()
        assert len(warnings) >= 2
        assert any("CELL_A" in w for w in warnings)
        assert any("CELL_B" in w for w in warnings)


class TestInstanceParserConnectionMismatches:
    """Tests for handling connection count mismatches."""

    def test_too_few_connections_warning(self) -> None:
        """Test warning when instance has fewer nets than ports.

        Parser should map available nets and log a warning.
        """
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"INV": SubcircuitDefinition("INV", ["A", "Y", "VDD", "VSS"])}
        parser = InstanceParser(defs)

        # Only 2 nets, but INV has 4 ports
        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI1 net1 net2 INV",
            raw="XI1 net1 net2 INV",
        )

        instance = parser.parse_instance_line(token)

        # Should have partial mapping
        assert instance.connections.get("A") == "net1"
        assert instance.connections.get("Y") == "net2"

        # Warning should be logged
        warnings = parser.get_warnings()
        assert len(warnings) > 0
        # Warning should mention the instance or connection issue
        assert any("XI1" in w or "connection" in w.lower() for w in warnings)

    def test_too_many_connections_warning(self) -> None:
        """Test warning when instance has more nets than ports.

        Parser should map up to port count and log a warning.
        """
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"INV": SubcircuitDefinition("INV", ["A", "Y"])}
        parser = InstanceParser(defs)

        # 4 nets, but INV only has 2 ports
        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI1 net1 net2 net3 net4 INV",
            raw="XI1 net1 net2 net3 net4 INV",
        )

        instance = parser.parse_instance_line(token)

        # Should map first 2 nets to ports
        assert len(instance.connections) == 2
        assert instance.connections["A"] == "net1"
        assert instance.connections["Y"] == "net2"

        # Warning should be logged
        warnings = parser.get_warnings()
        assert len(warnings) > 0

    def test_exact_connection_count_no_warning(self) -> None:
        """Test that exact match doesn't generate warning."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"INV": SubcircuitDefinition("INV", ["A", "Y"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI1 net1 net2 INV",
            raw="XI1 net1 net2 INV",
        )

        parser.parse_instance_line(token)

        # No warnings for exact match
        assert len(parser.get_warnings()) == 0


class TestInstanceParserValidation:
    """Tests for instance validation during parsing."""

    def test_invalid_instance_name_prefix(self) -> None:
        """Test error when instance name doesn't start with X.

        Note: The lexer should have already classified this as INSTANCE,
        but we still validate in the parser for safety.
        """
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"INV": SubcircuitDefinition("INV", ["A", "Y"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="I1 net1 net2 INV",  # Missing X prefix
            raw="I1 net1 net2 INV",
        )

        with pytest.raises(ValueError, match="must start with 'X'"):
            parser.parse_instance_line(token)

    def test_empty_line_content_error(self) -> None:
        """Test error when instance line content is empty."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="",
            raw="",
        )

        with pytest.raises(ValueError):
            parser.parse_instance_line(token)

    def test_instance_with_only_name_error(self) -> None:
        """Test error when instance line has only the name (no cell type)."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI1",  # Only name, no cell type
            raw="XI1",
        )

        with pytest.raises(ValueError):
            parser.parse_instance_line(token)

    def test_instance_name_and_cell_type_only(self) -> None:
        """Test instance with just name and cell type (no connections).

        This is valid for cells with no ports.
        """
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI_FILLER FILL_X1",  # No nets between name and cell type
            raw="XI_FILLER FILL_X1",
        )

        instance = parser.parse_instance_line(token)

        assert instance.name == "XI_FILLER"
        assert instance.cell_type == "FILL_X1"
        # Should have warning about unknown cell type
        assert len(parser.get_warnings()) > 0


class TestInstanceParserEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_instance_with_bus_net_names(self) -> None:
        """Test parsing instance with bus notation nets like data<7>."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"MUX2": SubcircuitDefinition("MUX2", ["D0", "D1", "S", "Y"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI1 data<0> data<1> sel out<0> MUX2",
            raw="XI1 data<0> data<1> sel out<0> MUX2",
        )

        instance = parser.parse_instance_line(token)

        assert instance.connections["D0"] == "data<0>"
        assert instance.connections["D1"] == "data<1>"
        assert instance.connections["Y"] == "out<0>"

    def test_instance_with_power_ground_nets(self) -> None:
        """Test instance connected to VDD and VSS."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"INV": SubcircuitDefinition("INV", ["A", "Y", "VDD", "VSS"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI1 in out VDD VSS INV",
            raw="XI1 in out VDD VSS INV",
        )

        instance = parser.parse_instance_line(token)

        assert instance.connections["VDD"] == "VDD"
        assert instance.connections["VSS"] == "VSS"

    def test_instance_with_all_same_net(self) -> None:
        """Test instance where all ports connect to same net."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"TIE": SubcircuitDefinition("TIE", ["Z1", "Z2", "Z3"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XI_TIE VDD VDD VDD TIE",
            raw="XI_TIE VDD VDD VDD TIE",
        )

        instance = parser.parse_instance_line(token)

        # All connections to VDD is valid
        assert all(net == "VDD" for net in instance.connections.values())

    def test_single_port_instance(self) -> None:
        """Test minimal instance with single port."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"CAP": SubcircuitDefinition("CAP", ["P"])}
        parser = InstanceParser(defs)

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="XCAP1 node1 CAP",
            raw="XCAP1 node1 CAP",
        )

        instance = parser.parse_instance_line(token)

        assert len(instance.connections) == 1
        assert instance.connections["P"] == "node1"

    def test_large_instance_many_ports(self) -> None:
        """Test instance with many ports (stress test)."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        # Create a cell with 20 ports
        ports = [f"P{i}" for i in range(20)]
        defs = {"BIGCELL": SubcircuitDefinition("BIGCELL", ports)}
        parser = InstanceParser(defs)

        # Create matching nets
        nets = [f"net{i}" for i in range(20)]
        content = f"XI_BIG {' '.join(nets)} BIGCELL"

        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content=content,
            raw=content,
        )

        instance = parser.parse_instance_line(token)

        assert len(instance.connections) == 20
        for i in range(20):
            assert instance.connections[f"P{i}"] == f"net{i}"

    def test_whitespace_handling(self) -> None:
        """Test parsing with various whitespace formats."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"INV": SubcircuitDefinition("INV", ["A", "Y"])}
        parser = InstanceParser(defs)

        # Multiple spaces between tokens
        token = CDLToken(
            line_num=5,
            line_type=LineType.INSTANCE,
            content="  XI1   net1    net2    INV  ",
            raw="  XI1   net1    net2    INV  ",
        )

        instance = parser.parse_instance_line(token)

        assert instance.name == "XI1"
        assert instance.cell_type == "INV"


class TestInstanceParserWarningManagement:
    """Tests for warning collection and retrieval."""

    def test_get_warnings_returns_copy(self) -> None:
        """Test that get_warnings returns a copy, not the internal list."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})

        token = CDLToken(5, LineType.INSTANCE, "XI1 n1 UNKNOWN", "XI1 n1 UNKNOWN")
        parser.parse_instance_line(token)

        warnings1 = parser.get_warnings()
        warnings2 = parser.get_warnings()

        # Should be equal but not the same object
        assert warnings1 == warnings2

        # Modifying returned list shouldn't affect internal state
        warnings1.append("external warning")
        assert len(parser.get_warnings()) < len(warnings1)

    def test_warnings_include_line_numbers(self) -> None:
        """Test that warnings include line numbers for debugging."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})

        token = CDLToken(
            line_num=42,
            line_type=LineType.INSTANCE,
            content="XI1 n1 UNKNOWN",
            raw="XI1 n1 UNKNOWN",
        )
        parser.parse_instance_line(token)

        warnings = parser.get_warnings()
        assert any("42" in w or "line" in w.lower() for w in warnings)

    def test_clear_warnings(self) -> None:
        """Test that warnings can be cleared if such method exists."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        parser = InstanceParser({})

        token = CDLToken(5, LineType.INSTANCE, "XI1 n1 UNKNOWN", "XI1 n1 UNKNOWN")
        parser.parse_instance_line(token)

        # If clear method exists, test it
        if hasattr(parser, "clear_warnings"):
            parser.clear_warnings()
            assert len(parser.get_warnings()) == 0


class TestInstanceParserIntegration:
    """Integration tests with lexer and subcircuit parser."""

    def test_parse_multiple_instances(self) -> None:
        """Test parsing multiple instances in sequence."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {
            "INV": SubcircuitDefinition("INV", ["A", "Y"]),
            "NAND2": SubcircuitDefinition("NAND2", ["A1", "A2", "ZN"]),
        }
        parser = InstanceParser(defs)

        tokens = [
            CDLToken(5, LineType.INSTANCE, "XI1 in n1 INV", "XI1 in n1 INV"),
            CDLToken(6, LineType.INSTANCE, "XI2 n1 n2 out NAND2", "XI2 n1 n2 out NAND2"),
            CDLToken(7, LineType.INSTANCE, "XI3 out result INV", "XI3 out result INV"),
        ]

        instances = [parser.parse_instance_line(token) for token in tokens]

        assert len(instances) == 3
        assert instances[0].cell_type == "INV"
        assert instances[1].cell_type == "NAND2"
        assert instances[2].cell_type == "INV"

        # First instance output connects to second instance input
        assert instances[0].connections["Y"] == "n1"
        assert instances[1].connections["A1"] == "n1"

    def test_mixed_known_and_unknown_cells(self) -> None:
        """Test parsing mix of known and unknown cell types."""
        from ink.infrastructure.parsing.instance_parser import InstanceParser

        defs = {"INV": SubcircuitDefinition("INV", ["A", "Y"])}
        parser = InstanceParser(defs)

        tokens = [
            CDLToken(5, LineType.INSTANCE, "XI1 in n1 INV", "..."),
            CDLToken(6, LineType.INSTANCE, "XI2 n1 n2 UNKNOWN1", "..."),
            CDLToken(7, LineType.INSTANCE, "XI3 n2 out INV", "..."),
            CDLToken(8, LineType.INSTANCE, "XI4 out x UNKNOWN2", "..."),
        ]

        instances = [parser.parse_instance_line(token) for token in tokens]

        assert len(instances) == 4

        # Known cells should have named ports
        assert "A" in instances[0].connections
        assert "Y" in instances[2].connections

        # Unknown cells should have generic ports
        assert "port0" in instances[1].connections
        assert "port0" in instances[3].connections

        # Should have 2 warnings (one per unknown cell)
        warnings = parser.get_warnings()
        assert len(warnings) == 2
