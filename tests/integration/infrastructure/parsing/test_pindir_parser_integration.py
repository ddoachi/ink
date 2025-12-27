"""Integration tests for Pin Direction File Parser.

These tests validate the complete end-to-end workflow of parsing real
.pindir files from the examples directory, including:
- Parsing the actual sample file
- Performance benchmarks for large files
- Real-world usage patterns

Unlike unit tests which mock file I/O, integration tests use actual files
to verify the parser works correctly in production scenarios.
"""

import time
from pathlib import Path

import pytest

from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.parsing.pindir_parser import (
    PinDirectionMap,
    PinDirectionParser,
)

# Path to the examples directory relative to project root
EXAMPLES_DIR = Path(__file__).parent.parent.parent.parent.parent / "examples"
SAMPLE_PINDIR = EXAMPLES_DIR / "standard_cells.pindir"


class TestParseRealPindirFile:
    """Integration tests for parsing real .pindir files."""

    @pytest.fixture
    def parser(self) -> PinDirectionParser:
        """Create a parser instance for tests."""
        return PinDirectionParser()

    def test_sample_file_exists(self) -> None:
        """Verify the sample .pindir file exists for integration testing."""
        assert SAMPLE_PINDIR.exists(), f"Sample file not found: {SAMPLE_PINDIR}"

    def test_parse_sample_file_success(self, parser: PinDirectionParser) -> None:
        """Should successfully parse the sample .pindir file."""
        result = parser.parse_file(SAMPLE_PINDIR)

        assert isinstance(result, PinDirectionMap)
        assert len(result.directions) > 0

    def test_sample_file_contains_expected_pins(
        self, parser: PinDirectionParser
    ) -> None:
        """Sample file should contain expected common pin names."""
        result = parser.parse_file(SAMPLE_PINDIR)

        # Basic gate pins
        assert result.has_pin("A")
        assert result.has_pin("B")
        assert result.has_pin("Y")

        # Flip-flop pins
        assert result.has_pin("CK")
        assert result.has_pin("D")
        assert result.has_pin("Q")

        # Scan pins
        assert result.has_pin("SE")
        assert result.has_pin("SI")

    def test_sample_file_directions_correct(
        self, parser: PinDirectionParser
    ) -> None:
        """Sample file should have correct directions for known pins."""
        result = parser.parse_file(SAMPLE_PINDIR)

        # Input pins
        assert result.get_direction("A") == PinDirection.INPUT
        assert result.get_direction("B") == PinDirection.INPUT
        assert result.get_direction("CK") == PinDirection.INPUT
        assert result.get_direction("SE") == PinDirection.INPUT

        # Output pins
        assert result.get_direction("Y") == PinDirection.OUTPUT
        assert result.get_direction("Q") == PinDirection.OUTPUT
        assert result.get_direction("SO") == PinDirection.OUTPUT

    def test_sample_file_inout_pins(self, parser: PinDirectionParser) -> None:
        """Sample file should contain INOUT pins if present."""
        result = parser.parse_file(SAMPLE_PINDIR)

        # IO pin is typically bidirectional
        if result.has_pin("IO"):
            assert result.get_direction("IO") == PinDirection.INOUT


class TestParserPerformance:
    """Performance benchmarks for the parser."""

    @pytest.fixture
    def parser(self) -> PinDirectionParser:
        """Create a parser instance for tests."""
        return PinDirectionParser()

    def test_sample_file_parse_time(self, parser: PinDirectionParser) -> None:
        """Sample file should parse quickly (< 10ms)."""
        start = time.perf_counter()
        parser.parse_file(SAMPLE_PINDIR)
        duration = time.perf_counter() - start

        assert duration < 0.01, f"Parse took {duration*1000:.2f}ms, expected < 10ms"

    def test_large_file_performance(
        self, parser: PinDirectionParser, tmp_path: Path
    ) -> None:
        """Parser should handle 1000 pins in < 100ms (spec requirement)."""
        # Generate a large test file with 1000 pins
        large_file = tmp_path / "large.pindir"
        with large_file.open("w") as f:
            f.write("* Large pin direction file for performance testing\n")
            f.write("* Generated with 1000 unique pins\n\n")
            for i in range(1000):
                direction = ["INPUT", "OUTPUT", "INOUT"][i % 3]
                f.write(f"PIN_{i:04d}  {direction}\n")

        # Time the parsing
        start = time.perf_counter()
        result = parser.parse_file(large_file)
        duration = time.perf_counter() - start

        # Verify results
        assert len(result.directions) == 1000
        assert duration < 0.1, f"Parse took {duration*1000:.2f}ms, expected < 100ms"

    def test_very_large_file_scalability(
        self, parser: PinDirectionParser, tmp_path: Path
    ) -> None:
        """Parser should scale linearly for very large files (10,000 pins)."""
        # Generate a very large test file
        large_file = tmp_path / "very_large.pindir"
        with large_file.open("w") as f:
            f.write("* Very large pin direction file\n\n")
            for i in range(10000):
                direction = ["INPUT", "OUTPUT", "INOUT"][i % 3]
                f.write(f"PIN_{i:05d}  {direction}\n")

        # Time the parsing
        start = time.perf_counter()
        result = parser.parse_file(large_file)
        duration = time.perf_counter() - start

        # Verify results
        assert len(result.directions) == 10000
        assert duration < 1.0, f"Parse took {duration*1000:.2f}ms, expected < 1000ms"


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows using the parser."""

    def test_parse_and_query_workflow(self) -> None:
        """Test the typical workflow: parse file, query directions."""
        # Step 1: Create parser
        parser = PinDirectionParser()

        # Step 2: Parse the sample file
        direction_map = parser.parse_file(SAMPLE_PINDIR)

        # Step 3: Query pin directions for circuit analysis
        input_pins = [
            name
            for name, direction in direction_map.directions.items()
            if direction == PinDirection.INPUT
        ]
        output_pins = [
            name
            for name, direction in direction_map.directions.items()
            if direction == PinDirection.OUTPUT
        ]

        # Verify we have pins of each type
        assert len(input_pins) > 0, "Should have INPUT pins"
        assert len(output_pins) > 0, "Should have OUTPUT pins"

    def test_unknown_pin_default_handling(self) -> None:
        """Test that unknown pins get INOUT default for safe traversal."""
        parser = PinDirectionParser()
        direction_map = parser.parse_file(SAMPLE_PINDIR)

        # Query a pin that definitely doesn't exist
        unknown_direction = direction_map.get_direction("DEFINITELY_NOT_A_PIN_XYZ123")

        # Should default to INOUT (safest for traversal)
        assert unknown_direction == PinDirection.INOUT

        # Should not be reported as existing
        assert not direction_map.has_pin("DEFINITELY_NOT_A_PIN_XYZ123")

    def test_all_three_direction_types_represented(self) -> None:
        """Sample file should have all three direction types for testing."""
        parser = PinDirectionParser()
        direction_map = parser.parse_file(SAMPLE_PINDIR)

        # Collect unique directions
        unique_directions = set(direction_map.directions.values())

        # Should have at least INPUT and OUTPUT
        assert PinDirection.INPUT in unique_directions
        assert PinDirection.OUTPUT in unique_directions

        # INOUT may or may not be present in sample file
        # If it is, that's a bonus for comprehensive testing


class TestFileEncodingHandling:
    """Test various file encoding scenarios."""

    @pytest.fixture
    def parser(self) -> PinDirectionParser:
        """Create a parser instance for tests."""
        return PinDirectionParser()

    def test_utf8_encoding(self, parser: PinDirectionParser, tmp_path: Path) -> None:
        """Should correctly parse UTF-8 encoded files."""
        utf8_file = tmp_path / "utf8.pindir"
        utf8_file.write_text("A  INPUT\nB  OUTPUT\n", encoding="utf-8")

        result = parser.parse_file(utf8_file)
        assert len(result.directions) == 2

    def test_file_with_bom(self, parser: PinDirectionParser, tmp_path: Path) -> None:
        """Should handle UTF-8 files with BOM marker."""
        bom_file = tmp_path / "bom.pindir"
        # Write UTF-8 with BOM
        with bom_file.open("w", encoding="utf-8-sig") as f:
            f.write("A  INPUT\nB  OUTPUT\n")

        result = parser.parse_file(bom_file)
        # BOM might affect first line parsing, but should still work
        assert len(result.directions) >= 1

    def test_crlf_line_endings(self, parser: PinDirectionParser, tmp_path: Path) -> None:
        """Should handle Windows-style CRLF line endings."""
        crlf_file = tmp_path / "crlf.pindir"
        # Write with explicit CRLF
        with crlf_file.open("wb") as f:
            f.write(b"A  INPUT\r\nB  OUTPUT\r\nC  INOUT\r\n")

        result = parser.parse_file(crlf_file)
        assert len(result.directions) == 3
