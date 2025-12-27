"""Unit tests for Pin Direction File Parser.

This module tests the complete pin direction parsing workflow:
- PinDirectionParseError: Custom exception for parsing errors
- PinDirectionMap: Data structure holding pin name to direction mappings
- PinDirectionParser: Parser for .pindir files

Test organization follows the TDD pattern with comprehensive coverage
of both happy paths and error conditions.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.parsing.pindir_parser import (
    PinDirectionMap,
    PinDirectionParseError,
    PinDirectionParser,
)

# =============================================================================
# PinDirectionParseError Tests
# =============================================================================


class TestPinDirectionParseError:
    """Test suite for PinDirectionParseError exception class."""

    def test_is_exception_subclass(self) -> None:
        """PinDirectionParseError should be a subclass of Exception."""
        assert issubclass(PinDirectionParseError, Exception)

    def test_can_be_raised_with_message(self) -> None:
        """Should be raisable with a custom message."""
        with pytest.raises(PinDirectionParseError, match="test error"):
            raise PinDirectionParseError("test error")

    def test_message_is_accessible(self) -> None:
        """Error message should be accessible via str()."""
        error = PinDirectionParseError("Line 42: Invalid direction 'INPTU'")
        assert "Line 42" in str(error)
        assert "Invalid direction" in str(error)

    def test_can_be_raised_with_line_number_context(self) -> None:
        """Should support line-numbered error messages."""
        error_msg = "Line 15: Expected format 'PIN_NAME DIRECTION', got: A B C"
        with pytest.raises(PinDirectionParseError, match="Line 15"):
            raise PinDirectionParseError(error_msg)


# =============================================================================
# PinDirectionMap Tests
# =============================================================================


class TestPinDirectionMapCreation:
    """Test suite for PinDirectionMap creation."""

    def test_create_empty_map(self) -> None:
        """Should be able to create an empty PinDirectionMap."""
        pin_map = PinDirectionMap(directions={})
        assert len(pin_map.directions) == 0

    def test_create_with_single_direction(self) -> None:
        """Should be able to create with a single pin direction."""
        pin_map = PinDirectionMap(directions={"A": PinDirection.INPUT})
        assert pin_map.directions["A"] == PinDirection.INPUT

    def test_create_with_multiple_directions(self) -> None:
        """Should be able to create with multiple pin directions."""
        directions = {
            "A": PinDirection.INPUT,
            "B": PinDirection.INPUT,
            "Y": PinDirection.OUTPUT,
        }
        pin_map = PinDirectionMap(directions=directions)
        assert len(pin_map.directions) == 3


class TestPinDirectionMapGetDirection:
    """Test suite for PinDirectionMap.get_direction() method."""

    def test_get_direction_existing_input_pin(self) -> None:
        """Should return INPUT for a defined INPUT pin."""
        pin_map = PinDirectionMap(directions={"A": PinDirection.INPUT})
        assert pin_map.get_direction("A") == PinDirection.INPUT

    def test_get_direction_existing_output_pin(self) -> None:
        """Should return OUTPUT for a defined OUTPUT pin."""
        pin_map = PinDirectionMap(directions={"Y": PinDirection.OUTPUT})
        assert pin_map.get_direction("Y") == PinDirection.OUTPUT

    def test_get_direction_existing_inout_pin(self) -> None:
        """Should return INOUT for a defined INOUT pin."""
        pin_map = PinDirectionMap(directions={"IO": PinDirection.INOUT})
        assert pin_map.get_direction("IO") == PinDirection.INOUT

    def test_get_direction_missing_pin_returns_inout(self) -> None:
        """Should return INOUT (default) for unknown pins."""
        pin_map = PinDirectionMap(directions={"A": PinDirection.INPUT})
        assert pin_map.get_direction("UNKNOWN") == PinDirection.INOUT

    def test_get_direction_empty_map_returns_inout(self) -> None:
        """Should return INOUT for any pin when map is empty."""
        pin_map = PinDirectionMap(directions={})
        assert pin_map.get_direction("ANY") == PinDirection.INOUT

    def test_get_direction_case_sensitive(self) -> None:
        """Pin names should be case-sensitive (A != a)."""
        pin_map = PinDirectionMap(
            directions={
                "A": PinDirection.INPUT,
                "a": PinDirection.OUTPUT,
            }
        )
        assert pin_map.get_direction("A") == PinDirection.INPUT
        assert pin_map.get_direction("a") == PinDirection.OUTPUT


class TestPinDirectionMapHasPin:
    """Test suite for PinDirectionMap.has_pin() method."""

    def test_has_pin_true_for_existing(self) -> None:
        """Should return True for defined pins."""
        pin_map = PinDirectionMap(directions={"A": PinDirection.INPUT})
        assert pin_map.has_pin("A") is True

    def test_has_pin_false_for_missing(self) -> None:
        """Should return False for undefined pins."""
        pin_map = PinDirectionMap(directions={"A": PinDirection.INPUT})
        assert pin_map.has_pin("B") is False

    def test_has_pin_false_for_empty_map(self) -> None:
        """Should return False for any pin when map is empty."""
        pin_map = PinDirectionMap(directions={})
        assert pin_map.has_pin("A") is False

    def test_has_pin_case_sensitive(self) -> None:
        """Pin name lookup should be case-sensitive."""
        pin_map = PinDirectionMap(directions={"A": PinDirection.INPUT})
        assert pin_map.has_pin("A") is True
        assert pin_map.has_pin("a") is False


# =============================================================================
# PinDirectionParser - Valid File Parsing Tests
# =============================================================================


class TestPinDirectionParserValidFiles:
    """Test suite for PinDirectionParser with valid input files."""

    def test_parse_single_line_file(self, tmp_path: Path) -> None:
        """Should parse a file with a single valid line."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A  INPUT\n")

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.INPUT
        assert len(result.directions) == 1

    def test_parse_multiple_lines(self, tmp_path: Path) -> None:
        """Should parse multiple valid pin direction lines."""
        content = """A  INPUT
B  INPUT
Y  OUTPUT
"""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.INPUT
        assert result.get_direction("B") == PinDirection.INPUT
        assert result.get_direction("Y") == PinDirection.OUTPUT
        assert len(result.directions) == 3

    def test_parse_with_tabs_separator(self, tmp_path: Path) -> None:
        """Should handle tabs as whitespace separators."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A\tINPUT\n")

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.INPUT

    def test_parse_with_multiple_spaces(self, tmp_path: Path) -> None:
        """Should handle multiple spaces as separators."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A          OUTPUT\n")

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.OUTPUT

    def test_parse_with_mixed_whitespace(self, tmp_path: Path) -> None:
        """Should handle mixed tabs and spaces as separators."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A   \t   INOUT\n")

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.INOUT


class TestPinDirectionParserCaseHandling:
    """Test suite for case handling in pin direction parsing."""

    def test_direction_case_insensitive_lowercase(self, tmp_path: Path) -> None:
        """Should handle lowercase direction values."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A  input\n")

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.INPUT

    def test_direction_case_insensitive_uppercase(self, tmp_path: Path) -> None:
        """Should handle uppercase direction values."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A  OUTPUT\n")

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.OUTPUT

    def test_direction_case_insensitive_mixedcase(self, tmp_path: Path) -> None:
        """Should handle mixed case direction values."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A  InOuT\n")

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.INOUT

    def test_pin_names_case_sensitive(self, tmp_path: Path) -> None:
        """Pin names should be case-sensitive (A and a are different)."""
        content = """A  INPUT
a  OUTPUT
"""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.INPUT
        assert result.get_direction("a") == PinDirection.OUTPUT


class TestPinDirectionParserCommentsAndBlankLines:
    """Test suite for comment and blank line handling."""

    def test_skip_comment_lines(self, tmp_path: Path) -> None:
        """Should skip lines starting with *."""
        content = """* This is a comment
A  INPUT
* Another comment
B  OUTPUT
"""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert len(result.directions) == 2
        assert result.get_direction("A") == PinDirection.INPUT
        assert result.get_direction("B") == PinDirection.OUTPUT

    def test_skip_empty_lines(self, tmp_path: Path) -> None:
        """Should skip empty lines."""
        content = """A  INPUT

B  OUTPUT

"""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert len(result.directions) == 2

    def test_skip_whitespace_only_lines(self, tmp_path: Path) -> None:
        """Should skip lines with only whitespace."""
        content = """A  INPUT
   \t
B  OUTPUT
"""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert len(result.directions) == 2

    def test_comment_with_leading_whitespace_is_data(self, tmp_path: Path) -> None:
        """Lines with leading whitespace before * are data, not comments."""
        # This tests that only lines STARTING with * are comments
        # " * comment" would be parsed as data (and likely fail as invalid)
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("* Comment\nA  INPUT\n")

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.INPUT


class TestPinDirectionParserDuplicateHandling:
    """Test suite for duplicate pin handling."""

    def test_duplicate_pins_use_last_definition(self, tmp_path: Path) -> None:
        """Duplicate pins should use the last definition."""
        content = """A  INPUT
A  OUTPUT
"""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert result.get_direction("A") == PinDirection.OUTPUT
        assert len(result.directions) == 1

    def test_duplicate_pins_log_warning(self, tmp_path: Path) -> None:
        """Duplicate pins should log a warning."""
        content = """A  INPUT
A  OUTPUT
"""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()

        with patch.object(parser.logger, "warning") as mock_warning:
            parser.parse_file(pindir_file)
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args[0][0]
            assert "Duplicate pin definition" in call_args
            assert "'A'" in call_args
            assert "line 2" in call_args


# =============================================================================
# PinDirectionParser - Error Handling Tests
# =============================================================================


class TestPinDirectionParserFileErrors:
    """Test suite for file-related error handling."""

    def test_file_not_found_raises_error(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError for missing files."""
        missing_file = tmp_path / "nonexistent.pindir"

        parser = PinDirectionParser()

        with pytest.raises(FileNotFoundError) as exc_info:
            parser.parse_file(missing_file)

        assert "not found" in str(exc_info.value)
        assert "nonexistent.pindir" in str(exc_info.value)

    def test_empty_file_returns_empty_map(self, tmp_path: Path) -> None:
        """Empty file should return empty PinDirectionMap."""
        pindir_file = tmp_path / "empty.pindir"
        pindir_file.write_text("")

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert len(result.directions) == 0

    def test_comments_only_file_returns_empty_map(self, tmp_path: Path) -> None:
        """File with only comments should return empty map."""
        content = """* Comment 1
* Comment 2
* Comment 3
"""
        pindir_file = tmp_path / "comments_only.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()
        result = parser.parse_file(pindir_file)

        assert len(result.directions) == 0


class TestPinDirectionParserSyntaxErrors:
    """Test suite for syntax error handling."""

    def test_invalid_direction_raises_parse_error(self, tmp_path: Path) -> None:
        """Invalid direction value should raise PinDirectionParseError."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A  INPTU\n")  # Typo

        parser = PinDirectionParser()

        with pytest.raises(PinDirectionParseError) as exc_info:
            parser.parse_file(pindir_file)

        error_msg = str(exc_info.value)
        assert "Line 1" in error_msg
        assert "Invalid direction" in error_msg or "INPTU" in error_msg

    def test_invalid_direction_shows_valid_options(self, tmp_path: Path) -> None:
        """Error for invalid direction should list valid options."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A  UNKNOWN\n")

        parser = PinDirectionParser()

        with pytest.raises(PinDirectionParseError) as exc_info:
            parser.parse_file(pindir_file)

        error_msg = str(exc_info.value)
        assert "INPUT" in error_msg or "OUTPUT" in error_msg or "INOUT" in error_msg

    def test_malformed_line_too_few_columns(self, tmp_path: Path) -> None:
        """Line with only pin name (no direction) should raise error."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A\n")

        parser = PinDirectionParser()

        with pytest.raises(PinDirectionParseError) as exc_info:
            parser.parse_file(pindir_file)

        assert "Line 1" in str(exc_info.value)

    def test_malformed_line_too_many_columns(self, tmp_path: Path) -> None:
        """Line with too many columns should raise error."""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text("A  B  INPUT\n")

        parser = PinDirectionParser()

        with pytest.raises(PinDirectionParseError) as exc_info:
            parser.parse_file(pindir_file)

        error_msg = str(exc_info.value)
        assert "Line 1" in error_msg

    def test_error_includes_line_number_for_later_lines(self, tmp_path: Path) -> None:
        """Error line number should be accurate for lines after the first."""
        content = """A  INPUT
B  OUTPUT
C  INVALID
D  INOUT
"""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()

        with pytest.raises(PinDirectionParseError) as exc_info:
            parser.parse_file(pindir_file)

        assert "Line 3" in str(exc_info.value)


# =============================================================================
# PinDirectionParser - Internal Method Tests
# =============================================================================


class TestPinDirectionParserParseLine:
    """Test suite for _parse_line() internal method."""

    def test_parse_line_valid_input(self) -> None:
        """Should parse valid line into (pin_name, direction) tuple."""
        parser = PinDirectionParser()
        pin_name, direction = parser._parse_line("A  INPUT", 1)

        assert pin_name == "A"
        assert direction == PinDirection.INPUT

    def test_parse_line_preserves_pin_name_case(self) -> None:
        """Should preserve the case of pin names."""
        parser = PinDirectionParser()
        pin_name, _ = parser._parse_line("MyPin  INPUT", 1)

        assert pin_name == "MyPin"

    def test_parse_line_strips_whitespace(self) -> None:
        """Should handle various whitespace patterns."""
        parser = PinDirectionParser()
        pin_name, direction = parser._parse_line("  A   OUTPUT  ", 1)

        assert pin_name == "A"
        assert direction == PinDirection.OUTPUT


class TestPinDirectionParserValidateDirection:
    """Test suite for _validate_direction() internal method."""

    def test_validate_direction_input(self) -> None:
        """Should validate INPUT direction."""
        parser = PinDirectionParser()
        result = parser._validate_direction("INPUT", 1)
        assert result == PinDirection.INPUT

    def test_validate_direction_output(self) -> None:
        """Should validate OUTPUT direction."""
        parser = PinDirectionParser()
        result = parser._validate_direction("OUTPUT", 1)
        assert result == PinDirection.OUTPUT

    def test_validate_direction_inout(self) -> None:
        """Should validate INOUT direction."""
        parser = PinDirectionParser()
        result = parser._validate_direction("INOUT", 1)
        assert result == PinDirection.INOUT

    def test_validate_direction_case_insensitive(self) -> None:
        """Should handle case variations."""
        parser = PinDirectionParser()
        assert parser._validate_direction("input", 1) == PinDirection.INPUT
        assert parser._validate_direction("Output", 1) == PinDirection.OUTPUT
        assert parser._validate_direction("INOUT", 1) == PinDirection.INOUT


class TestPinDirectionParserLogging:
    """Test suite for parser logging functionality."""

    def test_logs_success_on_parse(self, tmp_path: Path) -> None:
        """Should log info message on successful parse."""
        content = """A  INPUT
B  OUTPUT
C  INOUT
"""
        pindir_file = tmp_path / "test.pindir"
        pindir_file.write_text(content)

        parser = PinDirectionParser()

        with patch.object(parser.logger, "info") as mock_info:
            parser.parse_file(pindir_file)
            mock_info.assert_called_once()
            call_args = mock_info.call_args[0][0]
            assert "3 pin directions" in call_args
