"""CDL Parser Integration - Main parser orchestrating all components.

This module provides the CDLParser class, which integrates all parsing components
to produce a complete Design aggregate from CDL (Circuit Description Language)
files.

The parser orchestrates:
- CDLLexer: Line tokenization and classification
- SubcircuitParser: .SUBCKT/.ENDS block parsing for cell definitions
- InstanceParser: X-prefixed instance parsing with port mapping
- NetNormalizer: Net name normalization and classification

Architecture:
    The CDLParser is an infrastructure component that bridges file I/O and
    the domain layer. It reads CDL files, coordinates parsing components,
    and constructs a Design aggregate root that can be consumed by application
    services.

    Parsing is performed in two passes:
    1. First pass: Collect all subcircuit definitions (.SUBCKT/.ENDS)
    2. Second pass: Parse instances with port mapping from definitions

    This two-pass approach ensures that instances can be correctly mapped
    to their subcircuit definitions regardless of file ordering.

Usage:
    # Basic usage
    parser = CDLParser()
    design = parser.parse_file(Path("design.ckt"))

    print(f"Loaded: {design.name}")
    print(f"Instances: {design.instance_count}")
    print(f"Nets: {design.net_count}")

    # With progress callback for large files
    def on_progress(current: int, total: int) -> None:
        print(f"Parsing: {current}/{total} lines")

    design = parser.parse_file(Path("large_design.ckt"), on_progress)

    # Error handling
    try:
        design = parser.parse_file(Path("bad_design.ckt"))
    except ValueError as e:
        print(f"Parse failed: {e}")
        for error in parser.get_errors():
            print(f"  {error.severity}: {error.message}")

Performance:
    The parser is optimized to handle large netlists (100K+ cells) efficiently.
    Key optimizations:
    - Single file read with in-memory processing
    - Cached net normalization
    - Dictionary-based instance lookup
    - Progress callback every 100 lines (not every line)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ink.domain.model.design import Design
from ink.infrastructure.parsing.cdl_lexer import CDLLexer, LineType
from ink.infrastructure.parsing.instance_parser import InstanceParser
from ink.infrastructure.parsing.net_normalizer import NetNormalizer
from ink.infrastructure.parsing.subcircuit_parser import SubcircuitParser

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ink.domain.value_objects.instance import CellInstance
    from ink.domain.value_objects.net import NetInfo
    from ink.domain.value_objects.subcircuit import SubcircuitDefinition
    from ink.infrastructure.parsing.cdl_lexer import CDLToken

# Progress callback interval (call every N lines to avoid overhead)
_PROGRESS_INTERVAL = 100


@dataclass
class ParsingError:
    """Parsing error or warning with context information.

    This dataclass captures parsing issues with enough context for
    debugging and error reporting.

    Attributes:
        line_num: Line number where the error occurred (1-indexed).
                  For errors not tied to a specific line (e.g., unclosed blocks),
                  this may be -1.
        message: Human-readable description of the error or warning.
        severity: Either "error" for critical issues that may prevent parsing,
                 or "warning" for non-fatal issues that allow continued parsing.

    Example:
        >>> error = ParsingError(42, "Unknown cell type 'FOO'", "warning")
        >>> print(f"Line {error.line_num}: {error.message}")
    """

    line_num: int
    message: str
    severity: str  # "error" or "warning"


class CDLParser:
    """Main CDL parser integrating all parsing components.

    This class orchestrates the parsing of CDL files into a Design aggregate.
    It handles:
    - Two-pass parsing (subcircuits first, then instances)
    - Error collection with line numbers
    - Partial loading on recoverable errors
    - Progress reporting for large files
    - Net normalization and classification

    The parser maintains state during parsing (errors, progress callback)
    and should be reused for multiple files if desired.

    Attributes:
        _errors: List of parsing errors and warnings collected during parsing.
        _progress_callback: Optional callback for progress reporting.

    Example:
        >>> parser = CDLParser()
        >>> design = parser.parse_file(Path("design.ckt"))
        >>> if parser.get_errors():
        ...     for err in parser.get_errors():
        ...         print(f"{err.severity}: {err.message}")
    """

    def __init__(self) -> None:
        """Initialize the CDL parser.

        Creates a new parser instance with empty error list and no callback.
        The parser can be reused for multiple files - errors are cleared
        at the start of each parse_file() call.
        """
        self._errors: list[ParsingError] = []
        self._progress_callback: Callable[[int, int], None] | None = None

    def parse_file(
        self,
        file_path: Path,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> Design:
        """Parse a CDL file and return a Design aggregate.

        This is the main entry point for parsing CDL files. It performs:
        1. Tokenization via CDLLexer
        2. First pass: Subcircuit definition parsing
        3. Validation of block completeness
        4. Second pass: Instance parsing with port mapping
        5. Net collection and normalization
        6. Design aggregate construction

        Args:
            file_path: Path to the .ckt file to parse.
            progress_callback: Optional callback(current_line, total_lines)
                             called periodically during parsing. Useful for
                             showing progress in UI.

        Returns:
            Design aggregate root containing all parsed data.

        Raises:
            ValueError: If the file cannot be parsed due to critical errors
                       (e.g., unclosed blocks, invalid syntax). The error
                       message includes details about all errors encountered.
            FileNotFoundError: If the file does not exist.

        Example:
            >>> parser = CDLParser()
            >>> design = parser.parse_file(Path("design.ckt"))
            >>> print(f"Loaded {design.instance_count} instances")
        """
        # Initialize state for this parse operation
        self._progress_callback = progress_callback
        self._errors.clear()

        # Initialize parsing components
        lexer = CDLLexer(file_path)
        subcircuit_parser = SubcircuitParser()
        net_normalizer = NetNormalizer()

        # Tokenize the file (reads entire file into memory for two-pass)
        tokens = list(lexer.tokenize())
        total_lines = len(tokens)

        # =====================================================================
        # First Pass: Parse subcircuit definitions
        # =====================================================================
        # We need to know all subcircuit definitions before parsing instances
        # so we can map positional connections to named ports.
        self._parse_subcircuit_definitions(tokens, subcircuit_parser, total_lines)

        # Validate all subcircuit blocks are properly closed
        try:
            subcircuit_parser.validate_complete()
        except ValueError as e:
            self._add_error(-1, str(e), "error")

        # =====================================================================
        # Second Pass: Parse instances
        # =====================================================================
        # Now that we have all definitions, parse instances with port mapping.
        instance_parser = InstanceParser(subcircuit_parser.get_all_definitions())
        instances = self._parse_instances(tokens, instance_parser, total_lines)

        # Collect warnings from instance parser (unknown cell types, etc.)
        for warning in instance_parser.get_warnings():
            self._add_error(-1, warning, "warning")

        # =====================================================================
        # Build Design Aggregate
        # =====================================================================
        design = self._build_design(
            name=file_path.stem,
            subcircuit_defs=subcircuit_parser.get_all_definitions(),
            instances=instances,
            net_normalizer=net_normalizer,
        )

        # =====================================================================
        # Check for Critical Errors
        # =====================================================================
        if self._has_critical_errors():
            error_summary = self._format_errors()
            raise ValueError(f"Failed to parse {file_path}:\n{error_summary}")

        return design

    def _parse_subcircuit_definitions(
        self,
        tokens: list[CDLToken],
        subcircuit_parser: SubcircuitParser,
        total_lines: int,
    ) -> None:
        """First pass: Parse all .SUBCKT/.ENDS definitions.

        Processes tokens to extract subcircuit definitions. Errors are
        collected rather than raised immediately to allow partial parsing.

        Args:
            tokens: List of CDLToken objects from lexer.
            subcircuit_parser: Parser for .SUBCKT/.ENDS blocks.
            total_lines: Total number of tokens for progress reporting.
        """
        for i, token in enumerate(tokens):
            # Report progress periodically
            if self._progress_callback and i % _PROGRESS_INTERVAL == 0:
                self._progress_callback(i, total_lines)

            try:
                if token.line_type == LineType.SUBCKT:
                    subcircuit_parser.parse_subckt_line(token)
                elif token.line_type == LineType.ENDS:
                    subcircuit_parser.parse_ends_line(token)
            except ValueError as e:
                self._add_error(token.line_num, str(e), "error")

    def _parse_instances(
        self,
        tokens: list[CDLToken],
        instance_parser: InstanceParser,
        total_lines: int,
    ) -> list[CellInstance]:
        """Second pass: Parse all X-prefixed instances.

        Processes tokens to extract cell instances with port mapping.
        Errors are collected to allow partial parsing.

        Args:
            tokens: List of CDLToken objects from lexer.
            instance_parser: Parser for X-prefixed instances.
            total_lines: Total number of tokens for progress reporting.

        Returns:
            List of successfully parsed CellInstance objects.
        """
        instances: list[CellInstance] = []

        for i, token in enumerate(tokens):
            # Report progress periodically
            if self._progress_callback and i % _PROGRESS_INTERVAL == 0:
                self._progress_callback(i, total_lines)

            if token.line_type == LineType.INSTANCE:
                try:
                    instance = instance_parser.parse_instance_line(token)
                    instances.append(instance)
                except ValueError as e:
                    self._add_error(token.line_num, str(e), "error")
                    # Continue parsing (partial load)

        return instances

    def _build_design(
        self,
        name: str,
        subcircuit_defs: dict[str, SubcircuitDefinition],
        instances: list[CellInstance],
        net_normalizer: NetNormalizer,
    ) -> Design:
        """Construct Design aggregate from parsed components.

        Creates the Design aggregate root by:
        1. Building instance map (name -> CellInstance)
        2. Collecting all unique nets from instance connections
        3. Normalizing net names using NetNormalizer

        Args:
            name: Design name (typically from filename).
            subcircuit_defs: Dictionary of parsed subcircuit definitions.
            instances: List of parsed cell instances.
            net_normalizer: Normalizer for net names.

        Returns:
            Fully constructed Design aggregate.
        """
        # Collect all unique nets from instance connections
        nets: dict[str, NetInfo] = {}
        for instance in instances:
            for _port, net_name in instance.connections.items():
                if net_name not in nets:
                    # Normalize and classify the net
                    nets[net_name] = net_normalizer.normalize(net_name)

        # Build instance map
        instance_map = {inst.name: inst for inst in instances}

        # Create and return the Design aggregate
        return Design(
            name=name,
            subcircuit_defs=subcircuit_defs,
            instances=instance_map,
            nets=nets,
        )

    def _add_error(self, line_num: int, message: str, severity: str) -> None:
        """Record a parsing error or warning.

        Args:
            line_num: Line number where the error occurred (-1 if not specific).
            message: Description of the error or warning.
            severity: Either "error" or "warning".
        """
        self._errors.append(ParsingError(line_num, message, severity))

    def _has_critical_errors(self) -> bool:
        """Check if any critical (non-warning) errors occurred.

        Returns:
            True if at least one error with severity "error" exists.
        """
        return any(e.severity == "error" for e in self._errors)

    def _format_errors(self) -> str:
        """Format all errors and warnings for reporting.

        Creates a human-readable list of all parsing issues, with
        line numbers where available.

        Returns:
            Multi-line string with formatted error messages.
        """
        lines = []
        for error in self._errors:
            if error.line_num > 0:
                lines.append(f"Line {error.line_num}: {error.message}")
            else:
                lines.append(error.message)
        return "\n".join(lines)

    def get_errors(self) -> list[ParsingError]:
        """Return all parsing errors and warnings.

        The returned list includes both errors and warnings from the
        most recent parse_file() call. The list is a copy to prevent
        external modification.

        Returns:
            List of ParsingError objects from the most recent parse.
        """
        return self._errors.copy()
