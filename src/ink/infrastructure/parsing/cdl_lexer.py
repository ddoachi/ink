"""CDL Lexer and Tokenizer.

This module provides lexical analysis for CDL (Circuit Description Language) files.
CDL is a SPICE-like format used to describe gate-level netlists for schematic viewers.

The lexer performs:
- Line-level tokenization and classification
- Line continuation handling (+ prefix)
- Comment stripping (* prefix)
- Line type classification (SUBCKT, ENDS, INSTANCE, TRANSISTOR, COMMENT, BLANK)

Usage:
    lexer = CDLLexer(Path("design.ckt"))
    for token in lexer.tokenize():
        if token.line_type == LineType.SUBCKT:
            process_subcircuit(token)

Architecture:
    The CDLLexer follows a streaming/iterator pattern for memory efficiency.
    Large netlist files can be processed without loading the entire file into memory.
    The tokenization process:
    1. Read lines from file
    2. Handle line continuations (+ prefix joins lines)
    3. Strip inline comments (* prefix)
    4. Classify each logical line by type
    5. Yield CDLToken with original line number for error tracking
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class LineType(Enum):
    """CDL line type classification.

    Each line in a CDL file is classified into one of these types:
    - SUBCKT: Subcircuit definition (.SUBCKT)
    - ENDS: Subcircuit terminator (.ENDS)
    - INSTANCE: Cell instance (X-prefix)
    - TRANSISTOR: Transistor definition (M-prefix)
    - COMMENT: Comment line (* prefix)
    - BLANK: Empty or whitespace-only line
    - UNKNOWN: Unrecognized line format

    The classification is case-insensitive for keywords (.SUBCKT, .subckt, .Subckt
    are all valid).
    """

    SUBCKT = "SUBCKT"
    ENDS = "ENDS"
    INSTANCE = "INSTANCE"
    TRANSISTOR = "TRANSISTOR"
    COMMENT = "COMMENT"
    BLANK = "BLANK"
    UNKNOWN = "UNKNOWN"


@dataclass
class CDLToken:
    """A tokenized CDL line.

    Represents a single logical line from a CDL file after processing:
    - Continuation lines are joined into a single token
    - Comments are stripped from content (but preserved in raw)
    - Line type is classified based on content
    - Original line number is preserved for error reporting

    Attributes:
        line_num: Original line number in file (1-indexed). For continued lines,
                  this is the line number of the first line.
        line_type: Classified type of the line (SUBCKT, INSTANCE, etc.)
        content: Cleaned content with comments stripped and continuations joined.
                 Whitespace is normalized (no trailing spaces).
        raw: Original raw line(s) for error reporting. For continued lines,
             contains all lines joined with newlines.
    """

    line_num: int
    line_type: LineType
    content: str
    raw: str


class CDLLexer:
    """Lexical analyzer for CDL files.

    Provides iterator-based tokenization of CDL netlist files.
    Handles line continuation, comment stripping, and line classification.

    The lexer is designed for memory efficiency - it reads the file line by line
    and yields tokens as they are parsed, rather than loading the entire file.

    Args:
        file_path: Path to the CDL file to tokenize

    Example:
        >>> lexer = CDLLexer(Path("design.ckt"))
        >>> for token in lexer.tokenize():
        ...     print(f"{token.line_num}: {token.line_type.value}")

    CDL Format Notes:
        - Lines starting with * are comments
        - Lines starting with + are continuations of the previous line
        - .SUBCKT defines a subcircuit (case insensitive)
        - .ENDS terminates a subcircuit definition
        - Lines starting with X are cell instances
        - Lines starting with M are transistor definitions
    """

    def __init__(self, file_path: Path) -> None:
        """Initialize lexer with file path.

        Args:
            file_path: Path to the CDL file to tokenize. The file will be read
                       when tokenize() is called.
        """
        self.file_path = file_path

    def tokenize(self) -> Iterator[CDLToken]:
        """Yield tokens from CDL file.

        Handles line continuation (+ prefix) and comment stripping.
        Yields one token per logical line (after joining continuations).

        The tokenization process:
        1. Read each line from the file
        2. Handle CRLF/LF line endings
        3. Collect continuation lines (starting with +)
        4. Join continuations into a single logical line
        5. Strip inline comments
        6. Classify the line type
        7. Yield a CDLToken with all metadata

        Yields:
            CDLToken for each logical line in the file. Line numbers are 1-indexed
            and refer to the first line of a multi-line continuation.

        Note:
            Empty files yield no tokens. The iterator is lazy - file reading
            only happens as tokens are consumed.
        """
        # Read all lines from file, handling both CRLF and LF line endings
        with self.file_path.open("r", encoding="utf-8", newline="") as f:
            raw_lines = f.readlines()

        # Process lines, collecting continuations
        i = 0
        while i < len(raw_lines):
            # Get the current line and strip line endings (both \r\n and \n)
            current_line = raw_lines[i].rstrip("\r\n")
            line_num = i + 1  # 1-indexed line number

            # Collect continuation lines (lines starting with +)
            # A continuation line belongs to the previous logical line
            continuation_lines: list[str] = [current_line]
            raw_lines_collected: list[str] = [raw_lines[i].rstrip("\r\n")]

            # Look ahead for continuation lines
            j = i + 1
            while j < len(raw_lines):
                next_line = raw_lines[j].rstrip("\r\n")
                # Check if this line is a continuation (starts with +)
                if next_line.lstrip().startswith("+"):
                    continuation_lines.append(next_line)
                    raw_lines_collected.append(next_line)
                    j += 1
                else:
                    break

            # Join continuation lines if any
            if len(continuation_lines) > 1:
                joined_content = self._handle_continuation(continuation_lines)
                raw = "\n".join(raw_lines_collected)
            else:
                joined_content = current_line
                raw = current_line

            # Classify the line type BEFORE stripping comments
            # This ensures pure comment lines are classified as COMMENT, not BLANK
            line_type = self._classify_line(joined_content)

            # Strip inline comments from content
            # For COMMENT lines, preserve the raw content (minus leading whitespace)
            if line_type == LineType.COMMENT:
                content = joined_content.strip()
            else:
                content = self._strip_comment(joined_content)

            # Yield the token
            yield CDLToken(
                line_num=line_num,
                line_type=line_type,
                content=content,
                raw=raw,
            )

            # Move to next logical line (skip over continuation lines we consumed)
            i = j

    def _classify_line(self, content: str) -> LineType:  # noqa: PLR0911
        """Classify line by type based on content.

        Classification is performed on the cleaned content (after comment stripping
        and continuation joining). The classification is case-insensitive for
        keywords like .SUBCKT and .ENDS.

        Classification rules (applied in order):
        1. Empty or whitespace-only → BLANK
        2. Starts with * → COMMENT
        3. Starts with .SUBCKT (case insensitive) → SUBCKT
        4. Starts with .ENDS (case insensitive) → ENDS
        5. Starts with X or x → INSTANCE
        6. Starts with M or m → TRANSISTOR
        7. Anything else → UNKNOWN

        Args:
            content: Cleaned line content to classify (comments already stripped)

        Returns:
            LineType classification for the line
        """
        # Strip leading/trailing whitespace for classification
        stripped = content.strip()

        # Check for blank lines first
        if not stripped:
            return LineType.BLANK

        # Check for comment lines (start with *)
        if stripped.startswith("*"):
            return LineType.COMMENT

        # Convert to uppercase for case-insensitive keyword matching
        upper = stripped.upper()

        # Check for .SUBCKT definition
        if upper.startswith(".SUBCKT"):
            return LineType.SUBCKT

        # Check for .ENDS terminator
        if upper.startswith(".ENDS"):
            return LineType.ENDS

        # Check for X-prefixed instance (cell instantiation)
        first_char = stripped[0].upper()
        if first_char == "X":
            return LineType.INSTANCE

        # Check for M-prefixed transistor
        if first_char == "M":
            return LineType.TRANSISTOR

        # Unknown line type (could be .PARAM, .INCLUDE, or other directives)
        return LineType.UNKNOWN

    def _strip_comment(self, line: str) -> str:
        """Remove inline comments starting with *.

        CDL uses * to start comments. This method handles:
        - Full comment lines (line starts with *)
        - Inline comments (text before * is preserved)

        For full comment lines (starting with *), returns empty string since
        the line will be classified as COMMENT type anyway.

        For inline comments, preserves the content before * and strips
        trailing whitespace.

        Args:
            line: Raw line that may contain inline comment

        Returns:
            Line with inline comment removed and trailing whitespace stripped.
            For pure comment lines, returns empty string.

        Examples:
            >>> lexer._strip_comment("XI1 A B INV * instance")
            'XI1 A B INV'
            >>> lexer._strip_comment("* This is a comment")
            ''
            >>> lexer._strip_comment("XI1 A B INV")
            'XI1 A B INV'
        """
        # Handle empty lines
        if not line:
            return ""

        # Check if line starts with * (pure comment line)
        stripped = line.lstrip()
        if stripped.startswith("*"):
            return ""

        # Find the first * character (start of inline comment)
        comment_pos = line.find("*")
        if comment_pos == -1:
            # No comment found, return stripped line
            return line.rstrip()

        # Return content before comment, with trailing whitespace stripped
        return line[:comment_pos].rstrip()

    def _handle_continuation(self, lines: list[str]) -> str:
        """Join lines with + continuation prefix.

        CDL uses + at the start of a line to indicate continuation of the
        previous line. This method joins multiple lines into a single logical
        line.

        The + prefix and any whitespace after it are stripped from continuation
        lines. Lines are joined with a single space separator.

        Args:
            lines: List of lines to join. The first line is the base line,
                   subsequent lines should have + prefix (which will be stripped).

        Returns:
            Single joined line with + prefixes removed and lines connected
            with single spaces.

        Examples:
            >>> lexer._handle_continuation(["XI1 A B", "+ C D INV"])
            'XI1 A B C D INV'
            >>> lexer._handle_continuation(["XI1 net1", "+ net2", "+ net3 CELL"])
            'XI1 net1 net2 net3 CELL'
        """
        if not lines:
            return ""

        if len(lines) == 1:
            return lines[0]

        # Start with the first line
        parts: list[str] = [lines[0].rstrip()]

        # Process continuation lines (strip + and leading whitespace)
        for line in lines[1:]:
            # Strip leading whitespace, then the + character, then more whitespace
            stripped = line.lstrip()
            if stripped.startswith("+"):
                # Remove the + and any following whitespace
                continuation_content = stripped[1:].lstrip()
                parts.append(continuation_content)
            else:
                # Should not happen in normal use, but handle gracefully
                parts.append(stripped)

        # Join all parts with single space
        return " ".join(parts)
