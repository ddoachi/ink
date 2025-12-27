"""Unit tests for CDL Lexer and Tokenizer.

This module contains comprehensive tests for the CDLLexer class following TDD principles.
Tests cover:
- LineType enum values and classification
- CDLToken dataclass structure and immutability
- Line classification (_classify_line)
- Comment stripping (_strip_comment)
- Line continuation handling (_handle_continuation)
- Full tokenization (tokenize)
- Edge cases (empty files, CRLF, multiple continuations, etc.)
"""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from ink.infrastructure.parsing.cdl_lexer import CDLLexer, CDLToken, LineType


class TestLineType:
    """Tests for LineType enumeration."""

    def test_linetype_has_subckt(self) -> None:
        """LineType should have SUBCKT variant for .SUBCKT lines."""
        assert LineType.SUBCKT.value == "SUBCKT"

    def test_linetype_has_ends(self) -> None:
        """LineType should have ENDS variant for .ENDS lines."""
        assert LineType.ENDS.value == "ENDS"

    def test_linetype_has_instance(self) -> None:
        """LineType should have INSTANCE variant for X-prefixed lines."""
        assert LineType.INSTANCE.value == "INSTANCE"

    def test_linetype_has_transistor(self) -> None:
        """LineType should have TRANSISTOR variant for M-prefixed lines."""
        assert LineType.TRANSISTOR.value == "TRANSISTOR"

    def test_linetype_has_comment(self) -> None:
        """LineType should have COMMENT variant for * lines."""
        assert LineType.COMMENT.value == "COMMENT"

    def test_linetype_has_blank(self) -> None:
        """LineType should have BLANK variant for empty lines."""
        assert LineType.BLANK.value == "BLANK"

    def test_linetype_has_unknown(self) -> None:
        """LineType should have UNKNOWN variant for unrecognized lines."""
        assert LineType.UNKNOWN.value == "UNKNOWN"

    def test_linetype_all_variants(self) -> None:
        """All expected LineType variants should exist."""
        expected_variants = {
            "SUBCKT", "ENDS", "INSTANCE", "TRANSISTOR", "COMMENT", "BLANK", "UNKNOWN"
        }
        actual_variants = {lt.value for lt in LineType}
        assert actual_variants == expected_variants


class TestCDLToken:
    """Tests for CDLToken dataclass."""

    def test_token_has_line_num(self) -> None:
        """CDLToken should store the original line number (1-indexed)."""
        token = CDLToken(
            line_num=5, line_type=LineType.INSTANCE, content="XI1 A B INV", raw="XI1 A B INV"
        )
        assert token.line_num == 5

    def test_token_has_line_type(self) -> None:
        """CDLToken should store the classified line type."""
        token = CDLToken(
            line_num=1, line_type=LineType.SUBCKT, content=".SUBCKT INV A Y",
            raw=".SUBCKT INV A Y"
        )
        assert token.line_type == LineType.SUBCKT

    def test_token_has_content(self) -> None:
        """CDLToken should store cleaned content (comments stripped)."""
        token = CDLToken(
            line_num=1, line_type=LineType.INSTANCE, content="XI1 A Y INV",
            raw="XI1 A Y INV * comment"
        )
        assert token.content == "XI1 A Y INV"

    def test_token_has_raw(self) -> None:
        """CDLToken should store the original raw line."""
        raw_line = "XI1 A Y INV * comment"
        token = CDLToken(
            line_num=1, line_type=LineType.INSTANCE, content="XI1 A Y INV", raw=raw_line
        )
        assert token.raw == raw_line

    def test_token_is_dataclass(self) -> None:
        """CDLToken should be a dataclass with proper field access."""
        token = CDLToken(line_num=10, line_type=LineType.COMMENT, content="* test", raw="* test")
        # Dataclass provides __eq__ and __repr__
        token2 = CDLToken(line_num=10, line_type=LineType.COMMENT, content="* test", raw="* test")
        assert token == token2


class TestClassifyLine:
    """Tests for _classify_line method."""

    @pytest.fixture
    def lexer(self, tmp_path: Path) -> CDLLexer:
        """Create a CDLLexer with a dummy file path."""
        dummy_file = tmp_path / "dummy.ckt"
        dummy_file.touch()
        return CDLLexer(dummy_file)

    def test_classify_subckt_uppercase(self, lexer: CDLLexer) -> None:
        """Classify .SUBCKT line (uppercase)."""
        assert lexer._classify_line(".SUBCKT INV A Y") == LineType.SUBCKT

    def test_classify_subckt_lowercase(self, lexer: CDLLexer) -> None:
        """Classify .subckt line (lowercase)."""
        assert lexer._classify_line(".subckt INV A Y") == LineType.SUBCKT

    def test_classify_subckt_mixed_case(self, lexer: CDLLexer) -> None:
        """Classify .Subckt line (mixed case)."""
        assert lexer._classify_line(".Subckt INV A Y") == LineType.SUBCKT

    def test_classify_ends_uppercase(self, lexer: CDLLexer) -> None:
        """Classify .ENDS line (uppercase)."""
        assert lexer._classify_line(".ENDS INV") == LineType.ENDS

    def test_classify_ends_lowercase(self, lexer: CDLLexer) -> None:
        """Classify .ends line (lowercase)."""
        assert lexer._classify_line(".ends") == LineType.ENDS

    def test_classify_ends_with_name(self, lexer: CDLLexer) -> None:
        """Classify .ENDS with subcircuit name."""
        assert lexer._classify_line(".ENDS my_subcircuit") == LineType.ENDS

    def test_classify_instance_x_uppercase(self, lexer: CDLLexer) -> None:
        """Classify X-prefixed instance (uppercase)."""
        assert lexer._classify_line("XI1 net1 net2 INV") == LineType.INSTANCE

    def test_classify_instance_x_lowercase(self, lexer: CDLLexer) -> None:
        """Classify x-prefixed instance (lowercase)."""
        assert lexer._classify_line("xI1 net1 net2 INV") == LineType.INSTANCE

    def test_classify_transistor_m_uppercase(self, lexer: CDLLexer) -> None:
        """Classify M-prefixed transistor (uppercase)."""
        assert lexer._classify_line("M1 drain gate source bulk nmos") == LineType.TRANSISTOR

    def test_classify_transistor_m_lowercase(self, lexer: CDLLexer) -> None:
        """Classify m-prefixed transistor (lowercase)."""
        assert lexer._classify_line("m1 drain gate source bulk pmos") == LineType.TRANSISTOR

    def test_classify_comment_star(self, lexer: CDLLexer) -> None:
        """Classify * comment line."""
        assert lexer._classify_line("* This is a comment") == LineType.COMMENT

    def test_classify_blank_empty(self, lexer: CDLLexer) -> None:
        """Classify empty string as BLANK."""
        assert lexer._classify_line("") == LineType.BLANK

    def test_classify_blank_whitespace_only(self, lexer: CDLLexer) -> None:
        """Classify whitespace-only line as BLANK."""
        assert lexer._classify_line("   \t  ") == LineType.BLANK

    def test_classify_unknown(self, lexer: CDLLexer) -> None:
        """Classify unrecognized line as UNKNOWN."""
        assert lexer._classify_line("SOMETHING_ELSE param=value") == LineType.UNKNOWN

    def test_classify_instance_with_spaces(self, lexer: CDLLexer) -> None:
        """Classify instance with leading spaces (after stripping)."""
        # After content normalization, leading spaces should be handled
        assert lexer._classify_line("  XI1 A B INV") == LineType.INSTANCE


class TestStripComment:
    """Tests for _strip_comment method."""

    @pytest.fixture
    def lexer(self, tmp_path: Path) -> CDLLexer:
        """Create a CDLLexer with a dummy file path."""
        dummy_file = tmp_path / "dummy.ckt"
        dummy_file.touch()
        return CDLLexer(dummy_file)

    def test_strip_no_comment(self, lexer: CDLLexer) -> None:
        """Line without comment should be unchanged."""
        assert lexer._strip_comment("XI1 A Y INV") == "XI1 A Y INV"

    def test_strip_inline_comment(self, lexer: CDLLexer) -> None:
        """Strip inline comment starting with *."""
        assert lexer._strip_comment("XI1 A Y INV * instance comment") == "XI1 A Y INV"

    def test_strip_inline_comment_preserves_content(self, lexer: CDLLexer) -> None:
        """Content before * should be preserved without trailing whitespace."""
        result = lexer._strip_comment(".SUBCKT INV A Y VDD VSS  * subcircuit definition")
        assert result == ".SUBCKT INV A Y VDD VSS"

    def test_strip_comment_at_start(self, lexer: CDLLexer) -> None:
        """Pure comment line (starts with *) should return empty or minimal."""
        result = lexer._strip_comment("* This is a comment line")
        # For pure comment lines, the content could be empty or the original
        # Based on spec, we just strip inline comments from content lines
        # Pure comment lines are classified as COMMENT type
        assert result == ""

    def test_strip_multiple_asterisks(self, lexer: CDLLexer) -> None:
        """Only the first * starts a comment."""
        result = lexer._strip_comment("XI1 A B C * first * second")
        assert result == "XI1 A B C"

    def test_strip_trailing_whitespace(self, lexer: CDLLexer) -> None:
        """Trailing whitespace before comment should be stripped."""
        result = lexer._strip_comment("XI1 A B INV    * comment")
        assert result == "XI1 A B INV"

    def test_strip_empty_line(self, lexer: CDLLexer) -> None:
        """Empty line should remain empty."""
        assert lexer._strip_comment("") == ""


class TestHandleContinuation:
    """Tests for _handle_continuation method."""

    @pytest.fixture
    def lexer(self, tmp_path: Path) -> CDLLexer:
        """Create a CDLLexer with a dummy file path."""
        dummy_file = tmp_path / "dummy.ckt"
        dummy_file.touch()
        return CDLLexer(dummy_file)

    def test_single_line_no_continuation(self, lexer: CDLLexer) -> None:
        """Single line without continuation returns as-is."""
        lines = ["XI1 net1 net2 INV"]
        assert lexer._handle_continuation(lines) == "XI1 net1 net2 INV"

    def test_two_line_continuation(self, lexer: CDLLexer) -> None:
        """Two lines with + continuation."""
        lines = ["XI1 net1 net2", "+ net3 net4 INV"]
        result = lexer._handle_continuation(lines)
        assert result == "XI1 net1 net2 net3 net4 INV"

    def test_multiple_continuation_lines(self, lexer: CDLLexer) -> None:
        """Multiple continuation lines joined correctly."""
        lines = [
            "XI1 A1 A2 A3",
            "+ A4 A5 A6",
            "+ A7 A8 INV",
        ]
        result = lexer._handle_continuation(lines)
        assert result == "XI1 A1 A2 A3 A4 A5 A6 A7 A8 INV"

    def test_continuation_strips_plus_prefix(self, lexer: CDLLexer) -> None:
        """+ prefix should be removed from continuation lines."""
        lines = ["XI1 A B", "+C D INV"]
        result = lexer._handle_continuation(lines)
        # The + and any following space should be stripped
        assert "+" not in result
        assert result == "XI1 A B C D INV"

    def test_continuation_with_spaces_after_plus(self, lexer: CDLLexer) -> None:
        """Spaces after + should be handled correctly."""
        lines = ["XI1 A B", "+   C D INV"]
        result = lexer._handle_continuation(lines)
        assert result == "XI1 A B C D INV"

    def test_ten_continuation_lines(self, lexer: CDLLexer) -> None:
        """Handle 10+ continuation lines (edge case from spec)."""
        lines = ["XI1 net0"]
        for i in range(1, 11):
            lines.append(f"+ net{i}")
        lines.append("+ CELL")
        result = lexer._handle_continuation(lines)
        assert result == "XI1 net0 net1 net2 net3 net4 net5 net6 net7 net8 net9 net10 CELL"


class TestTokenize:
    """Tests for tokenize method."""

    def _create_temp_cdl(self, content: str) -> Path:
        """Create a temporary CDL file with given content."""
        import os
        fd, path_str = tempfile.mkstemp(suffix=".ckt")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return Path(path_str)

    def test_tokenize_returns_iterator(self, tmp_path: Path) -> None:
        """tokenize() should return an iterator."""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(".SUBCKT INV A Y\n.ENDS INV\n")
        lexer = CDLLexer(cdl_file)
        result = lexer.tokenize()
        assert isinstance(result, Iterator)

    def test_tokenize_empty_file(self, tmp_path: Path) -> None:
        """Empty file should yield no tokens."""
        cdl_file = tmp_path / "empty.ckt"
        cdl_file.write_text("")
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert tokens == []

    def test_tokenize_single_subckt(self, tmp_path: Path) -> None:
        """Tokenize single .SUBCKT line."""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(".SUBCKT INV A Y VDD VSS\n")
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert len(tokens) == 1
        assert tokens[0].line_type == LineType.SUBCKT
        assert tokens[0].line_num == 1
        assert ".SUBCKT INV A Y VDD VSS" in tokens[0].content

    def test_tokenize_subckt_ends_pair(self, tmp_path: Path) -> None:
        """Tokenize .SUBCKT/.ENDS pair."""
        cdl_content = """.SUBCKT INV A Y
.ENDS INV
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert len(tokens) == 2
        assert tokens[0].line_type == LineType.SUBCKT
        assert tokens[1].line_type == LineType.ENDS

    def test_tokenize_with_instances(self, tmp_path: Path) -> None:
        """Tokenize file with instances."""
        cdl_content = """.SUBCKT TOP IN OUT
XI1 IN n1 INV
XI2 n1 OUT INV
.ENDS TOP
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert len(tokens) == 4
        assert tokens[0].line_type == LineType.SUBCKT
        assert tokens[1].line_type == LineType.INSTANCE
        assert tokens[2].line_type == LineType.INSTANCE
        assert tokens[3].line_type == LineType.ENDS

    def test_tokenize_skips_comments(self, tmp_path: Path) -> None:
        """Comment lines should be classified as COMMENT, not skipped."""
        cdl_content = """* Header comment
.SUBCKT INV A Y
* Internal comment
XI1 A Y CELL
.ENDS INV
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        # All lines are tokenized including comments
        line_types = [t.line_type for t in tokens]
        assert LineType.COMMENT in line_types
        assert line_types.count(LineType.COMMENT) == 2

    def test_tokenize_skips_blank_lines(self, tmp_path: Path) -> None:
        """Blank lines should be classified as BLANK."""
        cdl_content = """.SUBCKT INV A Y

XI1 A Y CELL

.ENDS INV
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        line_types = [t.line_type for t in tokens]
        assert LineType.BLANK in line_types

    def test_tokenize_handles_continuation(self, tmp_path: Path) -> None:
        """Lines with + continuation should be joined."""
        cdl_content = """XI1 net1 net2
+ net3 net4 INV
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        # Continuation should result in single token
        assert len(tokens) == 1
        assert tokens[0].line_type == LineType.INSTANCE
        assert "net1" in tokens[0].content
        assert "net4" in tokens[0].content
        assert "+" not in tokens[0].content

    def test_tokenize_preserves_line_numbers(self, tmp_path: Path) -> None:
        """Line numbers should track original file position."""
        cdl_content = """* Comment
.SUBCKT INV A Y
XI1 A Y CELL
.ENDS INV
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert tokens[0].line_num == 1  # Comment
        assert tokens[1].line_num == 2  # SUBCKT
        assert tokens[2].line_num == 3  # Instance
        assert tokens[3].line_num == 4  # ENDS

    def test_tokenize_continuation_line_number(self, tmp_path: Path) -> None:
        """Continuation should preserve first line's number."""
        cdl_content = """* Comment
XI1 net1 net2
+ net3 net4 INV
.ENDS
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        # Find the instance token
        instance_token = next(t for t in tokens if t.line_type == LineType.INSTANCE)
        # Line number should be the first line of the continuation (line 2)
        assert instance_token.line_num == 2

    def test_tokenize_strips_inline_comments(self, tmp_path: Path) -> None:
        """Inline comments should be stripped from content."""
        cdl_content = """XI1 A Y INV * this is an instance
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert len(tokens) == 1
        assert "* this is" not in tokens[0].content
        assert tokens[0].content.strip() == "XI1 A Y INV"

    def test_tokenize_preserves_raw(self, tmp_path: Path) -> None:
        """Raw field should contain original line(s)."""
        cdl_content = """XI1 A Y INV * comment
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert "* comment" in tokens[0].raw

    def test_tokenize_transistor_lines(self, tmp_path: Path) -> None:
        """M-prefixed transistor lines should be classified as TRANSISTOR."""
        cdl_content = """M1 drain gate source bulk nmos w=1u l=0.18u
m2 drain gate source bulk pmos w=2u l=0.18u
"""
        cdl_file = tmp_path / "test.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert all(t.line_type == LineType.TRANSISTOR for t in tokens)


class TestEdgeCases:
    """Edge case tests for CDLLexer."""

    def test_file_with_only_comments(self, tmp_path: Path) -> None:
        """File with only comments should produce COMMENT tokens."""
        cdl_content = """* Comment 1
* Comment 2
* Comment 3
"""
        cdl_file = tmp_path / "comments.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert len(tokens) == 3
        assert all(t.line_type == LineType.COMMENT for t in tokens)

    def test_multiple_consecutive_blank_lines(self, tmp_path: Path) -> None:
        """Multiple consecutive blank lines are all tokenized."""
        cdl_content = """.SUBCKT INV A Y



XI1 A Y CELL
.ENDS
"""
        cdl_file = tmp_path / "blanks.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        blank_count = sum(1 for t in tokens if t.line_type == LineType.BLANK)
        assert blank_count == 3

    def test_crlf_line_endings(self, tmp_path: Path) -> None:
        """CRLF (Windows) line endings should be handled."""
        cdl_content = ".SUBCKT INV A Y\r\nXI1 A Y CELL\r\n.ENDS\r\n"
        cdl_file = tmp_path / "crlf.ckt"
        cdl_file.write_bytes(cdl_content.encode())
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        # Should still parse correctly
        assert len(tokens) == 3
        assert tokens[0].line_type == LineType.SUBCKT
        # Content should not contain \r
        assert "\r" not in tokens[0].content

    def test_lf_line_endings(self, tmp_path: Path) -> None:
        """LF (Unix) line endings should be handled."""
        cdl_content = ".SUBCKT INV A Y\nXI1 A Y CELL\n.ENDS\n"
        cdl_file = tmp_path / "lf.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert len(tokens) == 3

    def test_very_long_continued_line(self, tmp_path: Path) -> None:
        """Very long line with many continuations (>10) should be handled."""
        lines = ["XI1 n0 n1"]
        for i in range(2, 15):
            lines.append(f"+ n{i}")
        lines.append("+ BIGCELL")
        cdl_content = "\n".join(lines) + "\n"
        cdl_file = tmp_path / "long.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert len(tokens) == 1
        assert tokens[0].line_type == LineType.INSTANCE
        assert "n14" in tokens[0].content
        assert "BIGCELL" in tokens[0].content

    def test_whitespace_only_lines(self, tmp_path: Path) -> None:
        """Lines with only whitespace (tabs, spaces) are BLANK."""
        cdl_content = ".SUBCKT INV A Y\n   \t   \n.ENDS\n"
        cdl_file = tmp_path / "ws.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert tokens[1].line_type == LineType.BLANK

    def test_comment_at_end_of_instance(self, tmp_path: Path) -> None:
        """Comment at end of instance line is stripped."""
        cdl_content = "XI1 A B C INV * instance of inverter\n"
        cdl_file = tmp_path / "inst.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert len(tokens) == 1
        assert tokens[0].line_type == LineType.INSTANCE
        assert "* instance" not in tokens[0].content
        assert tokens[0].content.strip() == "XI1 A B C INV"

    def test_no_trailing_newline(self, tmp_path: Path) -> None:
        """File without trailing newline should be handled."""
        cdl_content = ".SUBCKT INV A Y\n.ENDS"  # No trailing newline
        cdl_file = tmp_path / "no_nl.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        assert len(tokens) == 2
        assert tokens[1].line_type == LineType.ENDS

    def test_continuation_after_subckt(self, tmp_path: Path) -> None:
        """SUBCKT with continuation line."""
        cdl_content = """.SUBCKT BIGCELL A B C D E
+ F G H I J
XI1 A B CELL
.ENDS
"""
        cdl_file = tmp_path / "subckt_cont.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        # SUBCKT + continuation = 1 token, instance = 1 token, ENDS = 1 token
        assert len(tokens) == 3
        assert tokens[0].line_type == LineType.SUBCKT
        assert "J" in tokens[0].content  # From continuation

    def test_unknown_line_type(self, tmp_path: Path) -> None:
        """Unrecognized lines should be UNKNOWN."""
        cdl_content = """.SUBCKT INV A Y
.PARAM x=1
.ENDS
"""
        cdl_file = tmp_path / "unknown.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())
        param_token = tokens[1]
        assert param_token.line_type == LineType.UNKNOWN
        assert ".PARAM" in param_token.content


class TestSampleCDLFile:
    """Test tokenization with a realistic CDL file structure."""

    def test_tokenize_sample_file(self, tmp_path: Path) -> None:
        """Tokenize a sample CDL file similar to PRD Appendix A."""
        cdl_content = """* Sample CDL Netlist
* Generated for testing

.SUBCKT INV A Y VDD VSS
* Simple inverter
M1 Y A VDD VDD pmos w=2u l=0.18u
M2 Y A VSS VSS nmos w=1u l=0.18u
.ENDS INV

.SUBCKT NAND2 A B Y VDD VSS
M1 Y A VDD VDD pmos w=2u l=0.18u
M2 Y B VDD VDD pmos w=2u l=0.18u
M3 Y A n1 VSS nmos w=1u l=0.18u
M4 n1 B VSS VSS nmos w=1u l=0.18u
.ENDS NAND2

.SUBCKT TOP IN1 IN2 OUT VDD VSS
XI1 IN1 n1 VDD VSS INV
XI2 IN2 n2 VDD VSS INV
XNAND n1 n2 OUT VDD
+ VSS NAND2 * NAND gate instance
.ENDS TOP
"""
        cdl_file = tmp_path / "sample.ckt"
        cdl_file.write_text(cdl_content)
        lexer = CDLLexer(cdl_file)
        tokens = list(lexer.tokenize())

        # Count by type
        subckt_count = sum(1 for t in tokens if t.line_type == LineType.SUBCKT)
        ends_count = sum(1 for t in tokens if t.line_type == LineType.ENDS)
        instance_count = sum(1 for t in tokens if t.line_type == LineType.INSTANCE)
        transistor_count = sum(1 for t in tokens if t.line_type == LineType.TRANSISTOR)
        comment_count = sum(1 for t in tokens if t.line_type == LineType.COMMENT)

        assert subckt_count == 3  # INV, NAND2, TOP
        assert ends_count == 3
        assert instance_count == 3  # XI1, XI2, XNAND (with continuation)
        assert transistor_count == 6  # M1-M4 in NAND2, M1-M2 in INV
        assert comment_count >= 3  # Header comments + internal comments

        # Verify XNAND instance has continuation properly joined
        xnand_token = next(
            t for t in tokens if t.line_type == LineType.INSTANCE and "XNAND" in t.content
        )
        assert "VSS" in xnand_token.content
        assert "NAND2" in xnand_token.content
        # Comment should be stripped from content
        assert "* NAND gate" not in xnand_token.content
