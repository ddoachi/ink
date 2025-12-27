"""Instance parser for CDL X-prefixed cell instantiations.

This module provides parsing functionality for X-prefixed instance lines in CDL
(Circuit Description Language) files. It works with tokens produced by the
CDLLexer and SubcircuitDefinition objects to create CellInstance value objects.

The parser handles:
- Parsing instance lines to extract name, nets, and cell type
- Mapping positional net lists to named ports using subcircuit definitions
- Graceful handling of unknown cell types (warning, not error)
- Connection count mismatches (warning, partial mapping)
- Validation of instance name format (X-prefix)

Usage:
    # After parsing subcircuit definitions
    instance_parser = InstanceParser(subcircuit_defs)

    for token in lexer.tokenize():
        if token.line_type == LineType.INSTANCE:
            instance = instance_parser.parse_instance_line(token)
            design.add_instance(instance)

    # Check for warnings
    for warning in instance_parser.get_warnings():
        logger.warning(warning)

Architecture:
    The InstanceParser is an infrastructure component that bridges:
    - CDLLexer (produces INSTANCE tokens)
    - SubcircuitDefinition (provides port lists for mapping)
    - CellInstance (domain value object output)

    The parser follows a "graceful degradation" pattern:
    - Unknown cell types: Create instance with generic port names + warning
    - Connection mismatches: Map available connections + warning
    - Invalid format: Raise ValueError (unrecoverable)

CDL Instance Line Format:
    X<instance_name> net1 net2 ... netN cell_type

Example:
        XI1 input output VDD VSS INV

    The instance name is always first (X-prefixed).
    The cell type is always last.
    Everything in between is the positional net list.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ink.domain.value_objects.instance import CellInstance

if TYPE_CHECKING:
    from ink.domain.value_objects.subcircuit import SubcircuitDefinition
    from ink.infrastructure.parsing.cdl_lexer import CDLToken

# Minimum parts in an instance line: [instance_name, cell_type]
_MIN_INSTANCE_PARTS = 2


class InstanceParser:
    """Parser for X-prefixed cell instances in CDL files.

    Maintains parsing state including a list of accumulated warnings.
    The parser uses subcircuit definitions to map positional net lists
    to named port connections.

    Attributes:
        _subcircuit_defs: Dictionary mapping cell type names to SubcircuitDefinition
        _warnings: List of accumulated warning messages

    Example:
        >>> defs = {"INV": SubcircuitDefinition("INV", ["A", "Y", "VDD", "VSS"])}
        >>> parser = InstanceParser(defs)
        >>> token = CDLToken(5, LineType.INSTANCE, "XI1 n1 n2 VDD VSS INV", "...")
        >>> instance = parser.parse_instance_line(token)
        >>> instance.name
        'XI1'
        >>> instance.connections
        {'A': 'n1', 'Y': 'n2', 'VDD': 'VDD', 'VSS': 'VSS'}
    """

    def __init__(self, subcircuit_defs: dict[str, SubcircuitDefinition]) -> None:
        """Initialize the parser with subcircuit definitions.

        The definitions are used to map positional net lists to named ports.
        If a cell type is not in the definitions, a warning is logged and
        generic port names (port0, port1, etc.) are used.

        Args:
            subcircuit_defs: Dictionary mapping cell type names to
                            SubcircuitDefinition objects. Can be empty.
        """
        # Store reference to subcircuit definitions for port lookups.
        # The dictionary maps cell_type -> SubcircuitDefinition.
        self._subcircuit_defs = subcircuit_defs

        # Accumulated warnings for non-fatal parsing issues.
        # Includes unknown cell types, connection count mismatches, etc.
        self._warnings: list[str] = []

    def parse_instance_line(self, token: CDLToken) -> CellInstance:
        """Parse an instance line and create a CellInstance.

        Extracts the instance name, net list, and cell type from the token.
        Uses subcircuit definitions to map nets to named ports.

        Format: X<instance_name> net1 net2 ... netN cell_type

        Processing steps:
        1. Split content on whitespace
        2. Validate minimum parts (name + cell_type)
        3. Extract instance_name (first token)
        4. Extract cell_type (last token)
        5. Extract net_list (everything in between)
        6. Map nets to ports using subcircuit definition
        7. Create and return CellInstance

        Args:
            token: A CDLToken with line_type INSTANCE containing the instance line.
                   The content field should have comments stripped and
                   continuations joined.

        Returns:
            A CellInstance value object with parsed data.

        Raises:
            ValueError: If the line format is invalid (empty, missing parts,
                       invalid instance name format).

        Example:
            >>> token = CDLToken(5, LineType.INSTANCE, "XI1 n1 n2 INV", "...")
            >>> instance = parser.parse_instance_line(token)
            >>> instance.name, instance.cell_type
            ('XI1', 'INV')
        """
        # Strip leading/trailing whitespace and split on whitespace
        content = token.content.strip()

        # Check for empty content
        if not content:
            raise ValueError(f"Empty instance line at line {token.line_num}")

        # Split into tokens
        parts = content.split()

        # Validate minimum parts: instance_name + cell_type
        if len(parts) < _MIN_INSTANCE_PARTS:
            raise ValueError(
                f"Invalid instance format at line {token.line_num}: "
                f"expected 'X<name> [nets...] cell_type', got '{content}'"
            )

        # Extract components:
        # - First token is always the instance name (X-prefixed)
        # - Last token is always the cell type
        # - Everything in between is the positional net list
        instance_name = parts[0]
        cell_type = parts[-1]
        net_list = parts[1:-1]  # May be empty for cells with no ports

        # Map nets to ports using subcircuit definition
        connections = self._map_connections(net_list, cell_type, instance_name, token.line_num)

        # Create CellInstance (validates name format internally)
        # ValueError from CellInstance.__init__ will propagate with validation errors
        return CellInstance(
            name=instance_name,
            cell_type=cell_type,
            connections=connections,
        )

    def _map_connections(
        self,
        nets: list[str],
        cell_type: str,
        instance_name: str,
        line_num: int,
    ) -> dict[str, str]:
        """Map positional net list to port names.

        Uses the subcircuit definition for the cell type to determine
        port names. If the cell type is unknown, generates generic port
        names (port0, port1, etc.).

        Connection count mismatches are handled gracefully:
        - Too few nets: Map available, remaining ports unmapped
        - Too many nets: Map up to port count, ignore extras

        Args:
            nets: Ordered list of net names from instance line
            cell_type: Cell type name to look up in definitions
            instance_name: Instance name for warning messages
            line_num: Line number for warning messages

        Returns:
            Dictionary mapping port_name -> net_name
        """
        # Look up subcircuit definition for this cell type
        definition = self._subcircuit_defs.get(cell_type)

        if definition is None:
            # Unknown cell type - create generic port names and warn
            self._warnings.append(
                f"Line {line_num}: Unknown cell type '{cell_type}' "
                f"for instance '{instance_name}'"
            )
            # Generate generic port names: port0, port1, etc.
            return {f"port{i}": net for i, net in enumerate(nets)}

        # Get port list from definition
        ports = definition.ports

        # Validate connection count and log warning if mismatch
        self._validate_connection_count(
            net_count=len(nets),
            port_count=len(ports),
            instance_name=instance_name,
            line_num=line_num,
        )

        # Map nets to ports positionally
        # We pre-slice to ensure equal lengths, so strict=True is safe
        if len(nets) < len(ports):
            # Too few nets - map what we have
            return dict(zip(ports[: len(nets)], nets, strict=True))
        elif len(nets) > len(ports):
            # Too many nets - truncate to port count
            return dict(zip(ports, nets[: len(ports)], strict=True))
        else:
            # Exact match
            return dict(zip(ports, nets, strict=True))

    def _validate_connection_count(
        self,
        net_count: int,
        port_count: int,
        instance_name: str,
        line_num: int,
    ) -> None:
        """Validate net/port count match and log warning if mismatch.

        This is a validation helper that compares the number of nets
        provided in the instance line with the number of ports defined
        in the subcircuit definition.

        Args:
            net_count: Number of nets provided in instance line
            port_count: Number of ports defined in subcircuit
            instance_name: Instance name for warning message
            line_num: Line number for warning message
        """
        if net_count < port_count:
            self._warnings.append(
                f"Line {line_num}: Instance '{instance_name}' has too few connections: "
                f"expected {port_count}, got {net_count}"
            )
        elif net_count > port_count:
            self._warnings.append(
                f"Line {line_num}: Instance '{instance_name}' has too many connections: "
                f"expected {port_count}, got {net_count}"
            )
        # If counts match, no warning needed

    def get_warnings(self) -> list[str]:
        """Return a copy of accumulated parsing warnings.

        Warnings include:
        - Unknown cell types (not in subcircuit definitions)
        - Connection count mismatches (too few or too many nets)

        Returns a copy to prevent external modification of internal state.

        Returns:
            List of warning message strings. Empty if no warnings.

        Example:
            >>> for warning in parser.get_warnings():
            ...     print(f"Warning: {warning}")
        """
        return self._warnings.copy()

    def clear_warnings(self) -> None:
        """Clear all accumulated warnings.

        Useful for batch processing where warnings should be collected
        per-batch rather than across the entire session.
        """
        self._warnings.clear()
