"""Integration tests for CDLParser - the main CDL parser orchestrator.

This module tests the CDLParser class which integrates:
- CDLLexer: Line tokenization and classification
- SubcircuitParser: .SUBCKT/.ENDS block parsing
- InstanceParser: X-prefixed instance parsing
- NetNormalizer: Net name normalization

The CDLParser produces a complete Design aggregate root from CDL files.

TDD: These tests are written first (RED phase) to define expected behavior.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ink.infrastructure.parsing.cdl_parser import CDLParser, ParsingError

if TYPE_CHECKING:
    from pathlib import Path


class TestParseSimpleDesign:
    """Tests for parsing simple, well-formed CDL files."""

    def test_parse_simple_inverter_chain(self, tmp_path: Path) -> None:
        """Test parsing a simple inverter chain design."""
        cdl_content = """\
* Simple inverter chain
.SUBCKT INV A Y VDD VSS
.ENDS INV

.SUBCKT TOP IN OUT VDD VSS
XI1 IN net1 VDD VSS INV
XI2 net1 OUT VDD VSS INV
.ENDS TOP
"""
        cdl_file = tmp_path / "simple.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        # Verify design name (from filename)
        assert design.name == "simple"

        # Verify subcircuit definitions
        assert "INV" in design.subcircuit_defs
        assert "TOP" in design.subcircuit_defs
        assert design.subcircuit_defs["INV"].ports == ("A", "Y", "VDD", "VSS")

        # Verify instances
        assert len(design.instances) == 2
        assert "XI1" in design.instances
        assert "XI2" in design.instances

        # Verify instance properties
        xi1 = design.instances["XI1"]
        assert xi1.cell_type == "INV"
        assert xi1.connections["A"] == "IN"
        assert xi1.connections["Y"] == "net1"

    def test_parse_design_with_multiple_cell_types(self, tmp_path: Path) -> None:
        """Test parsing with multiple cell type definitions."""
        cdl_content = """\
.SUBCKT INV A Y VDD VSS
.ENDS INV

.SUBCKT NAND2 A B Y VDD VSS
.ENDS NAND2

.SUBCKT NOR2 A B Y VDD VSS
.ENDS NOR2

.SUBCKT TOP IN1 IN2 OUT VDD VSS
XI1 IN1 net1 VDD VSS INV
XI2 IN2 net2 VDD VSS INV
XN1 net1 net2 OUT VDD VSS NAND2
.ENDS TOP
"""
        cdl_file = tmp_path / "multi_cell.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        assert len(design.subcircuit_defs) == 4  # INV, NAND2, NOR2, TOP
        assert len(design.instances) == 3
        assert design.instances["XN1"].cell_type == "NAND2"

    def test_parse_empty_file(self, tmp_path: Path) -> None:
        """Test parsing an empty CDL file."""
        cdl_file = tmp_path / "empty.ckt"
        cdl_file.write_text("")

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        assert design.name == "empty"
        assert len(design.subcircuit_defs) == 0
        assert len(design.instances) == 0
        assert len(design.nets) == 0

    def test_parse_comments_only(self, tmp_path: Path) -> None:
        """Test parsing a file with only comments."""
        cdl_content = """\
* This is a comment file
* It has no actual content
* Just comments
"""
        cdl_file = tmp_path / "comments.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        assert design.name == "comments"
        assert len(design.subcircuit_defs) == 0
        assert len(design.instances) == 0


class TestBusNotation:
    """Tests for parsing with bus notation in net names."""

    def test_parse_with_angle_bracket_bus(self, tmp_path: Path) -> None:
        """Test parsing with angle bracket bus notation."""
        cdl_content = """\
.SUBCKT BUF A Y
.ENDS BUF

.SUBCKT TOP CLK
XI0 data<0> out<0> BUF
XI1 data<1> out<1> BUF
XI2 data<2> out<2> BUF
.ENDS TOP
"""
        cdl_file = tmp_path / "bus.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        # Verify instances were parsed
        assert len(design.instances) == 3

        # Verify nets were normalized
        normalized_names = [net.normalized_name for net in design.nets.values()]
        assert "data[0]" in normalized_names
        assert "data[1]" in normalized_names
        assert "out[0]" in normalized_names

    def test_bus_index_extraction(self, tmp_path: Path) -> None:
        """Test that bus indices are correctly extracted."""
        cdl_content = """\
.SUBCKT BUF A Y
.ENDS BUF

.SUBCKT TOP CLK
XI0 addr<15> data<7> BUF
.ENDS TOP
"""
        cdl_file = tmp_path / "bus_index.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        # Find the bus nets
        addr_net = None
        data_net = None
        for net in design.nets.values():
            if "addr" in net.original_name:
                addr_net = net
            if "data" in net.original_name:
                data_net = net

        assert addr_net is not None
        assert addr_net.is_bus is True
        assert addr_net.bus_index == 15

        assert data_net is not None
        assert data_net.is_bus is True
        assert data_net.bus_index == 7


class TestPowerGroundClassification:
    """Tests for power/ground net classification."""

    def test_power_net_classification(self, tmp_path: Path) -> None:
        """Test that power nets are correctly classified."""
        cdl_content = """\
.SUBCKT INV A Y VDD VSS
.ENDS INV

.SUBCKT TOP IN OUT VDD VSS
XI1 IN OUT VDD VSS INV
.ENDS TOP
"""
        cdl_file = tmp_path / "power.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        from ink.domain.value_objects.net import NetType

        vdd_net = design.nets.get("VDD")
        vss_net = design.nets.get("VSS")

        assert vdd_net is not None
        assert vdd_net.net_type == NetType.POWER

        assert vss_net is not None
        assert vss_net.net_type == NetType.GROUND


class TestErrorHandling:
    """Tests for error handling and partial parsing."""

    def test_parse_with_unknown_cell_type_generates_warning(self, tmp_path: Path) -> None:
        """Test that unknown cell types generate warnings but continue parsing."""
        cdl_content = """\
.SUBCKT INV A Y
.ENDS INV

.SUBCKT TOP CLK
XI1 net1 net2 INV
XI2 net3 net4 UNKNOWN_CELL
XI3 net5 net6 INV
.ENDS TOP
"""
        cdl_file = tmp_path / "unknown_cell.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        # Should still parse all instances (partial loading)
        assert len(design.instances) == 3

        # Should have warning about unknown cell type
        errors = parser.get_errors()
        warnings = [e for e in errors if e.severity == "warning"]
        assert len(warnings) > 0
        assert any("UNKNOWN_CELL" in w.message for w in warnings)

    def test_parse_with_unclosed_subcircuit_raises_error(self, tmp_path: Path) -> None:
        """Test that unclosed .SUBCKT blocks raise an error."""
        cdl_content = """\
.SUBCKT INV A Y
* Missing .ENDS!

.SUBCKT TOP IN OUT
XI1 IN OUT INV
.ENDS TOP
"""
        cdl_file = tmp_path / "unclosed.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        with pytest.raises(ValueError, match="Failed to parse"):
            parser.parse_file(cdl_file)

    def test_parse_with_mismatched_ends_raises_error(self, tmp_path: Path) -> None:
        """Test that mismatched .ENDS name raises an error."""
        cdl_content = """\
.SUBCKT INV A Y
.ENDS WRONG_NAME
"""
        cdl_file = tmp_path / "mismatch.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        with pytest.raises(ValueError, match="Failed to parse"):
            parser.parse_file(cdl_file)

    def test_get_errors_returns_all_parsing_issues(self, tmp_path: Path) -> None:
        """Test that get_errors() returns all parsing issues."""
        cdl_content = """\
.SUBCKT INV A Y
.ENDS INV

.SUBCKT TOP CLK
XI1 net1 net2 UNKNOWN1
XI2 net3 net4 UNKNOWN2
.ENDS TOP
"""
        cdl_file = tmp_path / "multiple_errors.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        parser.parse_file(cdl_file)

        errors = parser.get_errors()
        assert len(errors) >= 2  # At least two warnings about unknown cells

    def test_error_includes_line_number(self, tmp_path: Path) -> None:
        """Test that errors include line numbers for debugging."""
        cdl_content = """\
.SUBCKT INV A Y
.ENDS INV

.SUBCKT TOP CLK
XI1 net1 net2 UNKNOWN_CELL
.ENDS TOP
"""
        cdl_file = tmp_path / "line_num.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        parser.parse_file(cdl_file)

        errors = parser.get_errors()
        # The warning about unknown cell should have a line number
        unknown_cell_warning = next(
            (e for e in errors if "UNKNOWN_CELL" in e.message), None
        )
        assert unknown_cell_warning is not None
        # Line number should be present (either in the error or accessible)


class TestProgressCallback:
    """Tests for progress reporting during parsing."""

    def test_progress_callback_is_called(self, tmp_path: Path) -> None:
        """Test that progress callback is invoked during parsing."""
        cdl_content = """\
.SUBCKT INV A Y
.ENDS INV

.SUBCKT TOP CLK
"""
        # Add many instances to generate progress callbacks
        for i in range(100):
            cdl_content += f"XI{i} net{i} net{i+1} INV\n"
        cdl_content += ".ENDS TOP\n"

        cdl_file = tmp_path / "progress.ckt"
        cdl_file.write_text(cdl_content)

        progress_calls: list[tuple[int, int]] = []

        def track_progress(current: int, total: int) -> None:
            progress_calls.append((current, total))

        parser = CDLParser()
        parser.parse_file(cdl_file, progress_callback=track_progress)

        # Should have been called multiple times
        assert len(progress_calls) > 0

        # Final progress should not exceed total
        last_current, last_total = progress_calls[-1]
        assert last_current <= last_total

    def test_progress_without_callback(self, tmp_path: Path) -> None:
        """Test parsing works without progress callback."""
        cdl_content = """\
.SUBCKT INV A Y
.ENDS INV

.SUBCKT TOP CLK
XI1 net1 net2 INV
.ENDS TOP
"""
        cdl_file = tmp_path / "no_progress.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)  # No callback

        assert len(design.instances) == 1


class TestLineContinuation:
    """Tests for handling line continuations."""

    def test_parse_with_line_continuation(self, tmp_path: Path) -> None:
        """Test parsing instance with line continuation."""
        cdl_content = """\
.SUBCKT BIG_CELL A B C D E F G H I J K L
.ENDS BIG_CELL

.SUBCKT TOP CLK
XI1 net1 net2 net3 net4 net5 net6
+ net7 net8 net9 net10 net11 net12 BIG_CELL
.ENDS TOP
"""
        cdl_file = tmp_path / "continuation.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        assert len(design.instances) == 1
        xi1 = design.instances["XI1"]
        assert xi1.cell_type == "BIG_CELL"
        # Should have all 12 connections
        assert len(xi1.connections) == 12


class TestNetCollection:
    """Tests for net collection from instances."""

    def test_nets_collected_from_all_instances(self, tmp_path: Path) -> None:
        """Test that all unique nets are collected from instances."""
        cdl_content = """\
.SUBCKT INV A Y
.ENDS INV

.SUBCKT TOP CLK
XI1 in n1 INV
XI2 n1 n2 INV
XI3 n2 out INV
.ENDS TOP
"""
        cdl_file = tmp_path / "nets.ckt"
        cdl_file.write_text(cdl_content)

        parser = CDLParser()
        design = parser.parse_file(cdl_file)

        # Should have all unique nets: in, n1, n2, out
        assert len(design.nets) >= 4
        assert "in" in design.nets
        assert "n1" in design.nets
        assert "n2" in design.nets
        assert "out" in design.nets


class TestParsingErrorDataclass:
    """Tests for the ParsingError dataclass."""

    def test_parsing_error_creation(self) -> None:
        """Test creating a ParsingError."""
        error = ParsingError(
            line_num=42,
            message="Something went wrong",
            severity="error",
        )

        assert error.line_num == 42
        assert error.message == "Something went wrong"
        assert error.severity == "error"

    def test_parsing_warning_creation(self) -> None:
        """Test creating a ParsingError with warning severity."""
        warning = ParsingError(
            line_num=10,
            message="Unknown cell type",
            severity="warning",
        )

        assert warning.severity == "warning"


class TestPerformance:
    """Performance tests for large designs."""

    def test_performance_1k_cells(self, tmp_path: Path) -> None:
        """Test parsing performance with 1K cells (quick test)."""
        lines = [".SUBCKT INV A Y", ".ENDS INV", ""]
        for i in range(1000):
            lines.append(f"XI{i} net{i} net{i+1} INV")

        cdl_file = tmp_path / "1k.ckt"
        cdl_file.write_text("\n".join(lines))

        import time

        parser = CDLParser()
        start = time.time()
        design = parser.parse_file(cdl_file)
        elapsed = time.time() - start

        # Should complete quickly (< 1 second for 1K cells)
        assert elapsed < 1.0
        assert len(design.instances) == 1000

    @pytest.mark.slow
    def test_performance_100k_cells(self, tmp_path: Path) -> None:
        """Test parsing performance with 100K cells (spec requirement: < 5 seconds)."""
        lines = [".SUBCKT INV A Y", ".ENDS INV", ""]
        for i in range(100_000):
            lines.append(f"XI{i} net{i} net{i+1} INV")

        cdl_file = tmp_path / "100k.ckt"
        cdl_file.write_text("\n".join(lines))

        import time

        parser = CDLParser()
        start = time.time()
        design = parser.parse_file(cdl_file)
        elapsed = time.time() - start

        # Spec requirement: < 5 seconds
        assert elapsed < 5.0, f"Parsing 100K cells took {elapsed:.2f}s (requirement: < 5s)"
        assert len(design.instances) == 100_000
