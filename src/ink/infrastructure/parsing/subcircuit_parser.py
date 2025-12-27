"""Subcircuit definition parser for CDL files.

This module provides parsing functionality for .SUBCKT/.ENDS blocks in CDL
(Circuit Description Language) files. It works with tokens produced by the
CDLLexer to build SubcircuitDefinition value objects.

The parser handles:
- Parsing .SUBCKT header lines to extract cell name and port list
- Tracking nesting with a stack for proper block matching
- Parsing .ENDS lines with validation against the nesting stack
- Storing parsed definitions for later retrieval

Usage:
    # In CDLParser main loop
    subckt_parser = SubcircuitParser()

    for token in lexer.tokenize():
        if token.line_type == LineType.SUBCKT:
            definition = subckt_parser.parse_subckt_line(token)
        elif token.line_type == LineType.ENDS:
            closed_name = subckt_parser.parse_ends_line(token)

    # After parsing, validate all blocks are closed
    subckt_parser.validate_complete()

    # Retrieve definitions for instance parsing
    inv_def = subckt_parser.get_definition("INV")

Architecture:
    The SubcircuitParser is an infrastructure component that bridges:
    - CDLLexer (produces tokens)
    - SubcircuitDefinition (domain value object)
    - Future Instance Parser (consumes definitions for port mapping)

    It maintains state during parsing (stack, definitions dict) but produces
    immutable SubcircuitDefinition value objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ink.domain.value_objects.subcircuit import SubcircuitDefinition

if TYPE_CHECKING:
    from ink.infrastructure.parsing.cdl_lexer import CDLToken

# Minimum number of parts in a .SUBCKT line: [".SUBCKT", "name"]
_MIN_SUBCKT_PARTS = 2


class SubcircuitParser:
    """Parser for .SUBCKT/.ENDS blocks in CDL files.

    Maintains parsing state including:
    - A dictionary of parsed SubcircuitDefinition objects keyed by name
    - A nesting stack to track open blocks for proper matching

    The parser enforces:
    - Valid .SUBCKT format (name + at least one port)
    - No duplicate port names within a subcircuit
    - Proper matching of .SUBCKT/.ENDS pairs
    - Error reporting with line numbers

    Attributes:
        _definitions: Dictionary mapping cell type names to SubcircuitDefinition
        _stack: Stack of open subcircuit names for nesting tracking

    Example:
        >>> parser = SubcircuitParser()
        >>> token = CDLToken(1, LineType.SUBCKT, ".SUBCKT INV A Y", "...")
        >>> defn = parser.parse_subckt_line(token)
        >>> defn.name
        'INV'
        >>> parser.current_subcircuit()
        'INV'
    """

    def __init__(self) -> None:
        """Initialize the parser with empty state.

        Creates an empty definitions dictionary and an empty nesting stack.
        The parser is ready to process tokens immediately after construction.
        """
        # Dictionary to store parsed subcircuit definitions by name.
        # If a subcircuit is defined multiple times, the later definition wins.
        self._definitions: dict[str, SubcircuitDefinition] = {}

        # Stack to track nesting of .SUBCKT blocks.
        # Each .SUBCKT pushes its name; each .ENDS pops it.
        # Used to validate proper matching and enable current_subcircuit().
        self._stack: list[str] = []

    def parse_subckt_line(self, token: CDLToken) -> SubcircuitDefinition:
        """Parse a .SUBCKT header line and create a SubcircuitDefinition.

        Extracts the cell name and port list from the token content.
        Expected format: .SUBCKT cell_name port1 port2 ... portN

        The parsed definition is:
        1. Validated (name not empty, ports exist, no duplicate ports)
        2. Stored in the definitions dictionary
        3. Pushed onto the nesting stack

        Args:
            token: A CDLToken with line_type SUBCKT containing the .SUBCKT line.
                   The content field should have comments stripped and
                   continuations joined.

        Returns:
            A SubcircuitDefinition value object with the extracted name and ports.

        Raises:
            ValueError: If the line format is invalid (missing name/ports),
                       or if port names are duplicated. The error includes
                       the line number for debugging.

        Example:
            >>> token = CDLToken(1, LineType.SUBCKT, ".SUBCKT INV A Y", "...")
            >>> defn = parser.parse_subckt_line(token)
            >>> defn.name, defn.ports
            ('INV', ('A', 'Y'))
        """
        # Get the content and strip leading/trailing whitespace
        content = token.content.strip()

        # Split on whitespace to get tokens
        # Format: .SUBCKT cell_name port1 port2 ... portN
        parts = content.split()

        # Validate we have at least .SUBCKT and a cell name
        if len(parts) < _MIN_SUBCKT_PARTS:
            raise ValueError(
                f"Invalid .SUBCKT format at line {token.line_num}: "
                f"expected '.SUBCKT name ports...', got '{content}'"
            )

        # Extract cell name (second token, after .SUBCKT)
        cell_name = parts[1]

        # Extract ports (everything after the cell name)
        ports = parts[2:]

        # Validate we have at least one port
        if not ports:
            raise ValueError(
                f"Subcircuit {cell_name} at line {token.line_num} must have at least one port"
            )

        # Create the SubcircuitDefinition (validates internally for duplicates)
        try:
            definition = SubcircuitDefinition(name=cell_name, ports=ports)
        except ValueError as e:
            # Re-raise with line number context
            raise ValueError(f"Error at line {token.line_num}: {e}") from e

        # Store in definitions dictionary (last definition wins if duplicate)
        self._definitions[cell_name] = definition

        # Push onto nesting stack
        self._stack.append(cell_name)

        return definition

    def parse_ends_line(self, token: CDLToken) -> str:
        """Parse a .ENDS line and validate matching with the nesting stack.

        Expected format: .ENDS [cell_name]
        If cell_name is provided, it must match the top of the nesting stack.
        If cell_name is omitted, the most recently opened block is closed.

        Args:
            token: A CDLToken with line_type ENDS containing the .ENDS line.

        Returns:
            The name of the closed subcircuit (always matches what was opened).

        Raises:
            ValueError: If there's no matching .SUBCKT (stack empty),
                       or if the provided name doesn't match the stack top.
                       The error includes the line number for debugging.

        Example:
            >>> # After opening .SUBCKT INV
            >>> ends_token = CDLToken(10, LineType.ENDS, ".ENDS INV", "...")
            >>> closed = parser.parse_ends_line(ends_token)
            >>> closed
            'INV'
        """
        # Check that we have an open subcircuit to close
        if not self._stack:
            raise ValueError(f".ENDS at line {token.line_num} without matching .SUBCKT")

        # Parse the .ENDS line to get optional name
        content = token.content.strip()
        parts = content.split()

        # Determine the expected name (top of stack)
        expected_name = self._stack[-1]

        # If a name is provided, validate it matches
        if len(parts) > 1:
            provided_name = parts[1]
            if provided_name != expected_name:
                raise ValueError(
                    f".ENDS name mismatch at line {token.line_num}: "
                    f"expected '{expected_name}', got '{provided_name}'"
                )

        # Pop the stack and return the closed name
        return self._stack.pop()

    def get_definition(self, cell_type: str) -> SubcircuitDefinition | None:
        """Retrieve a parsed subcircuit definition by name.

        Args:
            cell_type: The exact cell type name to look up (case-sensitive).

        Returns:
            The SubcircuitDefinition if found, None otherwise.

        Example:
            >>> defn = parser.get_definition("INV")
            >>> if defn:
            ...     print(f"INV has ports: {defn.ports}")
        """
        return self._definitions.get(cell_type)

    def get_all_definitions(self) -> dict[str, SubcircuitDefinition]:
        """Return all parsed subcircuit definitions.

        Returns:
            A dictionary mapping cell type names to SubcircuitDefinition objects.
            The dictionary is a copy to prevent external modification.

        Example:
            >>> all_defs = parser.get_all_definitions()
            >>> for name, defn in all_defs.items():
            ...     print(f"{name}: {len(defn.ports)} ports")
        """
        return dict(self._definitions)

    def validate_complete(self) -> None:
        """Validate that all .SUBCKT blocks have been closed.

        Should be called after processing all tokens to ensure proper
        block nesting. If any blocks are unclosed, raises an error with
        the names of all unclosed blocks.

        Raises:
            ValueError: If one or more .SUBCKT blocks remain unclosed.
                       The error lists all unclosed block names.

        Example:
            >>> parser.validate_complete()  # Raises if blocks unclosed
        """
        if self._stack:
            unclosed = ", ".join(self._stack)
            raise ValueError(f"Unclosed .SUBCKT blocks: {unclosed}")

    def current_subcircuit(self) -> str | None:
        """Return the name of the currently open (innermost) subcircuit.

        Useful for determining context during parsing - e.g., which
        subcircuit an instance belongs to.

        Returns:
            The name of the innermost open subcircuit, or None if not
            currently inside any subcircuit definition.

        Example:
            >>> # After .SUBCKT OUTER ... .SUBCKT INNER
            >>> parser.current_subcircuit()
            'INNER'
        """
        if not self._stack:
            return None
        return self._stack[-1]
