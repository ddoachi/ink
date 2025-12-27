"""Unit tests for SubcircuitParser.

This module tests the infrastructure layer parser for .SUBCKT/.ENDS blocks
from CDL files. The parser:
- Extracts cell names and port lists from .SUBCKT lines
- Tracks nesting with a stack for proper block matching
- Validates .ENDS lines match their opening .SUBCKT
- Stores parsed SubcircuitDefinition value objects

Tests cover:
- Parsing .SUBCKT header lines
- Parsing .ENDS lines (with and without name)
- Nesting support (stack management)
- Error handling (unmatched blocks, invalid format)
- Edge cases (special characters, many ports)
"""

from __future__ import annotations

import pytest

from ink.domain.value_objects.subcircuit import SubcircuitDefinition
from ink.infrastructure.parsing.cdl_lexer import CDLToken, LineType
from ink.infrastructure.parsing.subcircuit_parser import SubcircuitParser


class TestSubcircuitParserCreation:
    """Tests for SubcircuitParser initialization."""

    def test_parser_initializes_empty(self) -> None:
        """Parser should initialize with no definitions."""
        parser = SubcircuitParser()
        assert parser.get_definition("INV") is None

    def test_parser_has_empty_stack(self) -> None:
        """Parser should start with an empty nesting stack."""
        parser = SubcircuitParser()
        # validate_complete should pass when stack is empty
        parser.validate_complete()  # Should not raise


class TestParseSubcktLine:
    """Tests for parsing .SUBCKT header lines."""

    def test_parse_simple_subcircuit(self) -> None:
        """Parse basic .SUBCKT line with name and ports."""
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV A Y VDD VSS",
            raw=".SUBCKT INV A Y VDD VSS",
        )
        parser = SubcircuitParser()
        defn = parser.parse_subckt_line(token)

        assert defn.name == "INV"
        assert defn.ports == ("A", "Y", "VDD", "VSS")

    def test_parse_subcircuit_with_single_port(self) -> None:
        """Parse .SUBCKT with only one port."""
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT GROUND VSS",
            raw=".SUBCKT GROUND VSS",
        )
        parser = SubcircuitParser()
        defn = parser.parse_subckt_line(token)

        assert defn.name == "GROUND"
        assert defn.ports == ("VSS",)

    def test_parse_subcircuit_with_many_ports(self) -> None:
        """Parse .SUBCKT with many ports (20+)."""
        ports = " ".join([f"P{i}" for i in range(25)])
        content = f".SUBCKT BIG_CELL {ports}"
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=content,
            raw=content,
        )
        parser = SubcircuitParser()
        defn = parser.parse_subckt_line(token)

        assert defn.name == "BIG_CELL"
        assert len(defn.ports) == 25

    def test_parse_lowercase_subckt(self) -> None:
        """Parse .subckt (lowercase) header."""
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".subckt inv a y vdd vss",
            raw=".subckt inv a y vdd vss",
        )
        parser = SubcircuitParser()
        defn = parser.parse_subckt_line(token)

        assert defn.name == "inv"
        assert defn.ports == ("a", "y", "vdd", "vss")

    def test_parse_mixed_case_subckt(self) -> None:
        """Parse .Subckt (mixed case) header."""
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".Subckt Inverter_X1 A Y",
            raw=".Subckt Inverter_X1 A Y",
        )
        parser = SubcircuitParser()
        defn = parser.parse_subckt_line(token)

        assert defn.name == "Inverter_X1"

    def test_parse_stores_definition(self) -> None:
        """Parsed definition should be retrievable via get_definition."""
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV A Y",
            raw=".SUBCKT INV A Y",
        )
        parser = SubcircuitParser()
        parser.parse_subckt_line(token)

        retrieved = parser.get_definition("INV")
        assert retrieved is not None
        assert retrieved.name == "INV"
        assert retrieved.ports == ("A", "Y")

    def test_parse_pushes_to_stack(self) -> None:
        """Parsing .SUBCKT should push name onto stack."""
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV A Y",
            raw=".SUBCKT INV A Y",
        )
        parser = SubcircuitParser()
        parser.parse_subckt_line(token)

        # Stack should not be empty
        with pytest.raises(ValueError, match="Unclosed"):
            parser.validate_complete()

    def test_parse_with_extra_whitespace(self) -> None:
        """Parse .SUBCKT with multiple spaces between tokens."""
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT   INV    A   Y   VDD   VSS",
            raw=".SUBCKT   INV    A   Y   VDD   VSS",
        )
        parser = SubcircuitParser()
        defn = parser.parse_subckt_line(token)

        assert defn.name == "INV"
        assert defn.ports == ("A", "Y", "VDD", "VSS")

    def test_parse_with_leading_whitespace(self) -> None:
        """Parse .SUBCKT with leading whitespace."""
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content="   .SUBCKT INV A Y",
            raw="   .SUBCKT INV A Y",
        )
        parser = SubcircuitParser()
        defn = parser.parse_subckt_line(token)

        assert defn.name == "INV"


class TestParseSubcktLineErrors:
    """Tests for error handling when parsing .SUBCKT lines."""

    def test_error_missing_cell_name(self) -> None:
        """Error when .SUBCKT has no cell name."""
        token = CDLToken(
            line_num=5,
            line_type=LineType.SUBCKT,
            content=".SUBCKT",
            raw=".SUBCKT",
        )
        parser = SubcircuitParser()
        with pytest.raises(ValueError, match="Invalid .SUBCKT"):
            parser.parse_subckt_line(token)

    def test_error_no_ports(self) -> None:
        """Error when .SUBCKT has name but no ports."""
        token = CDLToken(
            line_num=5,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV",
            raw=".SUBCKT INV",
        )
        parser = SubcircuitParser()
        with pytest.raises(ValueError, match="at least one port"):
            parser.parse_subckt_line(token)

    def test_error_duplicate_ports(self) -> None:
        """Error when .SUBCKT has duplicate port names."""
        token = CDLToken(
            line_num=5,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV A Y A",
            raw=".SUBCKT INV A Y A",
        )
        parser = SubcircuitParser()
        with pytest.raises(ValueError, match="duplicate"):
            parser.parse_subckt_line(token)

    def test_error_includes_line_number(self) -> None:
        """Error message should include line number for debugging."""
        token = CDLToken(
            line_num=42,
            line_type=LineType.SUBCKT,
            content=".SUBCKT",
            raw=".SUBCKT",
        )
        parser = SubcircuitParser()
        with pytest.raises(ValueError) as exc_info:
            parser.parse_subckt_line(token)
        assert "42" in str(exc_info.value) or "line" in str(exc_info.value).lower()


class TestParseEndsLine:
    """Tests for parsing .ENDS lines."""

    def test_parse_ends_with_name(self) -> None:
        """Parse .ENDS with explicit cell name."""
        # First, open a subcircuit
        subckt_token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV A Y",
            raw=".SUBCKT INV A Y",
        )
        ends_token = CDLToken(
            line_num=10,
            line_type=LineType.ENDS,
            content=".ENDS INV",
            raw=".ENDS INV",
        )
        parser = SubcircuitParser()
        parser.parse_subckt_line(subckt_token)
        closed_name = parser.parse_ends_line(ends_token)

        assert closed_name == "INV"

    def test_parse_ends_without_name(self) -> None:
        """Parse .ENDS without cell name (closes most recent)."""
        subckt_token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV A Y",
            raw=".SUBCKT INV A Y",
        )
        ends_token = CDLToken(
            line_num=10,
            line_type=LineType.ENDS,
            content=".ENDS",
            raw=".ENDS",
        )
        parser = SubcircuitParser()
        parser.parse_subckt_line(subckt_token)
        closed_name = parser.parse_ends_line(ends_token)

        assert closed_name == "INV"

    def test_parse_ends_pops_stack(self) -> None:
        """Parsing .ENDS should pop the stack."""
        subckt_token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV A Y",
            raw=".SUBCKT INV A Y",
        )
        ends_token = CDLToken(
            line_num=10,
            line_type=LineType.ENDS,
            content=".ENDS",
            raw=".ENDS",
        )
        parser = SubcircuitParser()
        parser.parse_subckt_line(subckt_token)
        parser.parse_ends_line(ends_token)

        # Stack should be empty now
        parser.validate_complete()  # Should not raise

    def test_parse_ends_lowercase(self) -> None:
        """Parse .ends (lowercase)."""
        subckt_token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV A Y",
            raw=".SUBCKT INV A Y",
        )
        ends_token = CDLToken(
            line_num=10,
            line_type=LineType.ENDS,
            content=".ends",
            raw=".ends",
        )
        parser = SubcircuitParser()
        parser.parse_subckt_line(subckt_token)
        closed_name = parser.parse_ends_line(ends_token)

        assert closed_name == "INV"


class TestParseEndsLineErrors:
    """Tests for error handling when parsing .ENDS lines."""

    def test_error_ends_without_subckt(self) -> None:
        """Error when .ENDS appears without matching .SUBCKT."""
        token = CDLToken(
            line_num=5,
            line_type=LineType.ENDS,
            content=".ENDS INV",
            raw=".ENDS INV",
        )
        parser = SubcircuitParser()
        with pytest.raises(ValueError, match="without matching .SUBCKT"):
            parser.parse_ends_line(token)

    def test_error_ends_wrong_name(self) -> None:
        """Error when .ENDS name doesn't match the stack top."""
        subckt_token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT INV A Y",
            raw=".SUBCKT INV A Y",
        )
        ends_token = CDLToken(
            line_num=10,
            line_type=LineType.ENDS,
            content=".ENDS BUF",  # Wrong name!
            raw=".ENDS BUF",
        )
        parser = SubcircuitParser()
        parser.parse_subckt_line(subckt_token)

        with pytest.raises(ValueError, match="mismatch"):
            parser.parse_ends_line(ends_token)

    def test_error_includes_line_number(self) -> None:
        """Error message should include line number."""
        token = CDLToken(
            line_num=99,
            line_type=LineType.ENDS,
            content=".ENDS",
            raw=".ENDS",
        )
        parser = SubcircuitParser()
        with pytest.raises(ValueError) as exc_info:
            parser.parse_ends_line(token)
        assert "99" in str(exc_info.value) or "line" in str(exc_info.value).lower()


class TestNestedSubcircuits:
    """Tests for nested .SUBCKT blocks."""

    def test_nested_subcircuits(self) -> None:
        """Handle nested .SUBCKT blocks correctly."""
        parser = SubcircuitParser()

        # Open outer subcircuit
        outer_subckt = CDLToken(1, LineType.SUBCKT, ".SUBCKT OUTER A B", ".SUBCKT OUTER A B")
        parser.parse_subckt_line(outer_subckt)

        # Open inner subcircuit
        inner_subckt = CDLToken(5, LineType.SUBCKT, ".SUBCKT INNER X Y", ".SUBCKT INNER X Y")
        parser.parse_subckt_line(inner_subckt)

        # Close inner subcircuit
        inner_ends = CDLToken(10, LineType.ENDS, ".ENDS INNER", ".ENDS INNER")
        closed = parser.parse_ends_line(inner_ends)
        assert closed == "INNER"

        # Close outer subcircuit
        outer_ends = CDLToken(15, LineType.ENDS, ".ENDS OUTER", ".ENDS OUTER")
        closed = parser.parse_ends_line(outer_ends)
        assert closed == "OUTER"

        # Stack should be empty
        parser.validate_complete()

    def test_nested_ends_without_name_closes_innermost(self) -> None:
        """Nested .ENDS without name closes the innermost block."""
        parser = SubcircuitParser()

        outer_subckt = CDLToken(1, LineType.SUBCKT, ".SUBCKT OUTER A B", "")
        parser.parse_subckt_line(outer_subckt)

        inner_subckt = CDLToken(5, LineType.SUBCKT, ".SUBCKT INNER X Y", "")
        parser.parse_subckt_line(inner_subckt)

        # .ENDS without name should close INNER
        ends = CDLToken(10, LineType.ENDS, ".ENDS", ".ENDS")
        closed = parser.parse_ends_line(ends)
        assert closed == "INNER"

        # OUTER should still be open
        with pytest.raises(ValueError, match="Unclosed"):
            parser.validate_complete()

    def test_multiple_sequential_subcircuits(self) -> None:
        """Handle multiple sequential (non-nested) subcircuits."""
        parser = SubcircuitParser()

        # First subcircuit
        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT INV A Y", ""))
        parser.parse_ends_line(CDLToken(5, LineType.ENDS, ".ENDS INV", ""))

        # Second subcircuit
        parser.parse_subckt_line(CDLToken(10, LineType.SUBCKT, ".SUBCKT BUF A Y", ""))
        parser.parse_ends_line(CDLToken(15, LineType.ENDS, ".ENDS BUF", ""))

        # Third subcircuit
        parser.parse_subckt_line(CDLToken(20, LineType.SUBCKT, ".SUBCKT NAND A B Y", ""))
        parser.parse_ends_line(CDLToken(25, LineType.ENDS, ".ENDS", ""))

        # All should be closed
        parser.validate_complete()

        # All definitions should be retrievable
        assert parser.get_definition("INV") is not None
        assert parser.get_definition("BUF") is not None
        assert parser.get_definition("NAND") is not None


class TestValidateComplete:
    """Tests for validate_complete method."""

    def test_validate_complete_empty_stack(self) -> None:
        """validate_complete should pass when stack is empty."""
        parser = SubcircuitParser()
        parser.validate_complete()  # Should not raise

    def test_validate_complete_one_unclosed(self) -> None:
        """validate_complete should fail with one unclosed block."""
        parser = SubcircuitParser()
        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT INV A Y", ""))

        with pytest.raises(ValueError, match="Unclosed") as exc_info:
            parser.validate_complete()
        assert "INV" in str(exc_info.value)

    def test_validate_complete_multiple_unclosed(self) -> None:
        """validate_complete should list all unclosed blocks."""
        parser = SubcircuitParser()
        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT OUTER A B", ""))
        parser.parse_subckt_line(CDLToken(5, LineType.SUBCKT, ".SUBCKT INNER X Y", ""))

        with pytest.raises(ValueError, match="Unclosed") as exc_info:
            parser.validate_complete()
        error_msg = str(exc_info.value)
        assert "OUTER" in error_msg
        assert "INNER" in error_msg


class TestGetDefinition:
    """Tests for get_definition method."""

    def test_get_existing_definition(self) -> None:
        """Retrieve an existing definition."""
        parser = SubcircuitParser()
        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT INV A Y", ""))
        parser.parse_ends_line(CDLToken(5, LineType.ENDS, ".ENDS", ""))

        defn = parser.get_definition("INV")
        assert defn is not None
        assert isinstance(defn, SubcircuitDefinition)
        assert defn.name == "INV"

    def test_get_nonexistent_definition(self) -> None:
        """Return None for nonexistent definition."""
        parser = SubcircuitParser()
        assert parser.get_definition("DOES_NOT_EXIST") is None

    def test_get_all_definitions(self) -> None:
        """get_all_definitions should return all parsed definitions."""
        parser = SubcircuitParser()

        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT INV A Y", ""))
        parser.parse_ends_line(CDLToken(5, LineType.ENDS, ".ENDS", ""))

        parser.parse_subckt_line(CDLToken(10, LineType.SUBCKT, ".SUBCKT BUF A Y", ""))
        parser.parse_ends_line(CDLToken(15, LineType.ENDS, ".ENDS", ""))

        all_defs = parser.get_all_definitions()
        assert len(all_defs) == 2
        assert "INV" in all_defs
        assert "BUF" in all_defs


class TestEdgeCases:
    """Tests for edge cases in SubcircuitParser."""

    def test_port_names_with_special_chars(self) -> None:
        """Port names with special characters are handled."""
        token = CDLToken(
            line_num=1,
            line_type=LineType.SUBCKT,
            content=".SUBCKT CELL VDD! VSS! A<0> A<1>",
            raw=".SUBCKT CELL VDD! VSS! A<0> A<1>",
        )
        parser = SubcircuitParser()
        defn = parser.parse_subckt_line(token)

        assert "VDD!" in defn.ports
        assert "A<0>" in defn.ports

    def test_cell_name_case_sensitivity(self) -> None:
        """Cell names should be case-sensitive."""
        parser = SubcircuitParser()

        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT inv a y", ""))
        parser.parse_ends_line(CDLToken(5, LineType.ENDS, ".ENDS", ""))

        parser.parse_subckt_line(CDLToken(10, LineType.SUBCKT, ".SUBCKT INV A Y", ""))
        parser.parse_ends_line(CDLToken(15, LineType.ENDS, ".ENDS", ""))

        # Should have two different definitions
        inv_lower = parser.get_definition("inv")
        inv_upper = parser.get_definition("INV")

        assert inv_lower is not None
        assert inv_upper is not None
        assert inv_lower != inv_upper

    def test_duplicate_definition_replaces(self) -> None:
        """Second definition with same name replaces the first."""
        parser = SubcircuitParser()

        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT INV A Y", ""))
        parser.parse_ends_line(CDLToken(5, LineType.ENDS, ".ENDS", ""))

        parser.parse_subckt_line(CDLToken(10, LineType.SUBCKT, ".SUBCKT INV X Z W", ""))
        parser.parse_ends_line(CDLToken(15, LineType.ENDS, ".ENDS", ""))

        # Second definition should be stored
        defn = parser.get_definition("INV")
        assert defn is not None
        assert defn.ports == ("X", "Z", "W")

    def test_very_long_port_list(self) -> None:
        """Handle subcircuit with 100+ ports."""
        ports = " ".join([f"P{i}" for i in range(120)])
        content = f".SUBCKT HUGE {ports}"
        token = CDLToken(1, LineType.SUBCKT, content, content)

        parser = SubcircuitParser()
        defn = parser.parse_subckt_line(token)

        assert len(defn.ports) == 120


class TestCurrentSubcircuit:
    """Tests for current_subcircuit method."""

    def test_current_subcircuit_when_empty(self) -> None:
        """Return None when not inside any subcircuit."""
        parser = SubcircuitParser()
        assert parser.current_subcircuit() is None

    def test_current_subcircuit_after_open(self) -> None:
        """Return current subcircuit name when inside a block."""
        parser = SubcircuitParser()
        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT INV A Y", ""))

        assert parser.current_subcircuit() == "INV"

    def test_current_subcircuit_after_nested(self) -> None:
        """Return innermost subcircuit name when nested."""
        parser = SubcircuitParser()
        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT OUTER A B", ""))
        parser.parse_subckt_line(CDLToken(5, LineType.SUBCKT, ".SUBCKT INNER X Y", ""))

        assert parser.current_subcircuit() == "INNER"

    def test_current_subcircuit_after_close(self) -> None:
        """Return outer subcircuit after closing inner."""
        parser = SubcircuitParser()
        parser.parse_subckt_line(CDLToken(1, LineType.SUBCKT, ".SUBCKT OUTER A B", ""))
        parser.parse_subckt_line(CDLToken(5, LineType.SUBCKT, ".SUBCKT INNER X Y", ""))
        parser.parse_ends_line(CDLToken(10, LineType.ENDS, ".ENDS", ""))

        assert parser.current_subcircuit() == "OUTER"
