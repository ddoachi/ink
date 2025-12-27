"""Pin Direction File Parser.

This module provides parsing functionality for `.pindir` files, which contain
mappings from pin names to their directions (INPUT, OUTPUT, INOUT).

The `.pindir` file format is a simple whitespace-separated format:
    * Comment lines start with asterisk
    * Data lines: PIN_NAME  DIRECTION
    * Directions are case-insensitive (INPUT, input, Input all valid)
    * Pin names are case-sensitive (A and a are different pins)

Example .pindir file:
    * Standard cell pin directions
    * Format: PIN_NAME  DIRECTION

    A       INPUT
    B       INPUT
    Y       OUTPUT
    Q       OUTPUT

Usage:
    >>> from pathlib import Path
    >>> from ink.infrastructure.parsing.pindir_parser import PinDirectionParser
    >>>
    >>> parser = PinDirectionParser()
    >>> direction_map = parser.parse_file(Path("example.pindir"))
    >>> direction_map.get_direction("A")
    <PinDirection.INPUT: 'INPUT'>
    >>> direction_map.get_direction("UNKNOWN")  # Default for missing pins
    <PinDirection.INOUT: 'INOUT'>

Error Handling:
    - FileNotFoundError: Raised when the specified file doesn't exist
    - PinDirectionParseError: Raised for syntax errors, with line number context
    - Duplicate pins: Warning logged, last definition used (allows overrides)

See Also:
    - ink.domain.value_objects.pin_direction.PinDirection: The enum type for directions
    - E01-F02-T01.spec.md: Full specification for this parser
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from ink.domain.value_objects.pin_direction import PinDirection

# Number of columns expected in a valid .pindir data line: PIN_NAME DIRECTION
_EXPECTED_COLUMN_COUNT = 2


class PinDirectionParseError(Exception):
    """Exception raised when pin direction file parsing fails.

    This exception is raised for syntax errors in .pindir files, including:
    - Invalid direction values (not INPUT, OUTPUT, or INOUT)
    - Malformed lines (wrong number of columns)
    - Other parsing failures

    The error message always includes the line number where the error occurred,
    making it easy to locate and fix issues in the source file.

    Example:
        >>> raise PinDirectionParseError("Line 42: Invalid direction 'INPTU'")
        PinDirectionParseError: Line 42: Invalid direction 'INPTU'

    Attributes:
        message: Human-readable description of the parsing error
    """


@dataclass
class PinDirectionMap:
    """Mapping of pin names to their directions with default handling.

    This data structure holds the parsed content of a .pindir file,
    providing efficient lookup of pin directions by name. It also tracks
    which pins were queried but not found in the mapping, enabling
    statistics and reporting on missing pin direction data.

    The map supports:
    - O(1) lookup by pin name
    - Default value (INOUT) for unknown pins
    - Case-sensitive pin name matching
    - Tracking of missing pin accesses for statistics

    Design Decisions:
        - INOUT is used as the default direction because it's the most
          conservative assumption (allows bidirectional traversal)
        - Missing pins are tracked using a Set for O(1) insertion and
          automatic deduplication
        - The tracking field uses field(default_factory=set) to ensure
          each instance gets its own independent set

    Attributes:
        directions: Dictionary mapping pin names to PinDirection values
        _accessed_missing_pins: Set of pin names that were queried but
            not found in the directions mapping. This is internal state
            used for statistics; access via get_missing_pins() method.

    Example:
        >>> from ink.domain.value_objects.pin_direction import PinDirection
        >>> pin_map = PinDirectionMap(directions={"A": PinDirection.INPUT})
        >>> pin_map.get_direction("A")
        <PinDirection.INPUT: 'INPUT'>
        >>> pin_map.get_direction("UNKNOWN")  # Tracks as missing
        <PinDirection.INOUT: 'INOUT'>
        >>> pin_map.get_missing_pins()
        {'UNKNOWN'}
    """

    directions: dict[str, PinDirection]

    # Internal tracking of pins that were queried but not found.
    # Uses field with default_factory to ensure each instance has its own set.
    # init=False means this field is not included in the generated __init__.
    _accessed_missing_pins: set[str] = field(default_factory=set, init=False)

    def get_direction(self, pin_name: str) -> PinDirection:
        """Get direction for a pin name, with default for unknown pins.

        This method provides safe lookup with a sensible default value.
        If the pin is not found in the mapping, INOUT is returned as
        the safest assumption (allows both input and output traversal).

        Missing pins are tracked internally for statistics and reporting.
        Use get_missing_pins() to retrieve the set of all pins that were
        queried but not found.

        Args:
            pin_name: The name of the pin to look up (case-sensitive)

        Returns:
            The direction of the pin if found, otherwise PinDirection.INOUT

        Note:
            This method has a side effect: it tracks missing pins.
            Use has_pin() if you want to check existence without tracking.
        """
        if pin_name not in self.directions:
            # Track this missing pin for statistics reporting.
            # Set.add() is O(1) and automatically handles deduplication.
            self._accessed_missing_pins.add(pin_name)
            return PinDirection.INOUT

        return self.directions[pin_name]

    def has_pin(self, pin_name: str) -> bool:
        """Check if a pin name exists in the mapping.

        Use this method when you need to distinguish between:
        - Pin explicitly defined as INOUT
        - Pin not defined (defaulting to INOUT)

        Unlike get_direction(), this method does NOT track missing pins.
        This allows checking for pin existence without side effects.

        Args:
            pin_name: The name of the pin to check (case-sensitive)

        Returns:
            True if the pin is defined in the mapping, False otherwise
        """
        return pin_name in self.directions

    def get_missing_pin_stats(self) -> dict[str, int]:
        """Get statistics on missing pin direction queries.

        Provides insight into pin direction coverage and helps identify
        incomplete .pindir files. Use this after loading a design to
        understand how many pins are using default INOUT directions.

        Returns:
            Dictionary with the following statistics:
            - 'defined_pins': Number of pins with explicit direction definitions
            - 'missing_pins_accessed': Number of unique pins queried but not found
            - 'total_unique_pins': Total unique pins (defined + missing accessed)

        Example:
            >>> stats = pin_map.get_missing_pin_stats()
            >>> coverage = stats['defined_pins'] / stats['total_unique_pins'] * 100
            >>> print(f"Pin direction coverage: {coverage:.1f}%")
        """
        defined_count = len(self.directions)
        missing_count = len(self._accessed_missing_pins)

        return {
            "defined_pins": defined_count,
            "missing_pins_accessed": missing_count,
            "total_unique_pins": defined_count + missing_count,
        }

    def get_missing_pins(self) -> set[str]:
        """Get set of all pin names that were queried but not defined.

        Returns a copy of the internal tracking set to prevent external
        modification of internal state. This ensures immutability of
        the tracking data.

        Use this method to:
        - Export missing pins for manual direction assignment
        - Display warnings to users about incomplete pin direction data
        - Generate reports on pin direction coverage

        Returns:
            Set of pin names that were looked up via get_direction()
            but were not found in the directions mapping.
            Returns an empty set if no missing pins have been accessed.
        """
        # Return a copy to prevent external mutation of internal state.
        # This preserves the encapsulation of the tracking mechanism.
        return self._accessed_missing_pins.copy()


class PinDirectionParser:
    """Parser for pin direction files (.pindir format).

    This parser reads .pindir files and converts them to PinDirectionMap objects.
    It handles:
    - Comment lines (starting with *)
    - Empty and whitespace-only lines
    - Whitespace-separated PIN_NAME DIRECTION format
    - Case-insensitive direction values
    - Duplicate pin detection with warnings

    The parser follows a fail-fast approach: syntax errors are raised immediately
    with line number context, while duplicate pins generate warnings but continue
    processing.

    Attributes:
        logger: Logger instance for warnings and info messages

    Example:
        >>> parser = PinDirectionParser()
        >>> direction_map = parser.parse_file(Path("cells.pindir"))
        >>> print(f"Loaded {len(direction_map.directions)} pin directions")
    """

    def __init__(self) -> None:
        """Initialize the parser with a module-level logger."""
        self.logger = logging.getLogger(__name__)

    def parse_file(self, file_path: Path) -> PinDirectionMap:
        """Parse a .pindir file and return pin direction mapping.

        This is the main entry point for parsing. It reads the file line by line,
        skipping comments and empty lines, and builds a mapping of pin names to
        their directions.

        Args:
            file_path: Path to the .pindir file to parse

        Returns:
            PinDirectionMap containing all parsed pin directions

        Raises:
            FileNotFoundError: If the file doesn't exist at the specified path
            PinDirectionParseError: If the file contains syntax errors

        Example:
            >>> parser = PinDirectionParser()
            >>> try:
            ...     result = parser.parse_file(Path("design.pindir"))
            ...     print(f"Parsed {len(result.directions)} pins")
            ... except FileNotFoundError:
            ...     print("Pin direction file not found")
            ... except PinDirectionParseError as e:
            ...     print(f"Syntax error: {e}")
        """
        # Validate file exists before attempting to read
        if not file_path.exists():
            raise FileNotFoundError(f"Pin direction file not found: {file_path}")

        # Storage for parsed directions
        directions: dict[str, PinDirection] = {}

        # Track line number for error reporting
        line_number = 0

        try:
            # Open file with explicit UTF-8 encoding for cross-platform compatibility
            with file_path.open("r", encoding="utf-8") as f:
                for line_number, line in enumerate(f, start=1):
                    # Strip leading/trailing whitespace
                    stripped = line.strip()

                    # Skip empty lines and comment lines
                    # Comments are lines starting with * (no leading whitespace check)
                    if not stripped or stripped.startswith("*"):
                        continue

                    # Parse the data line to extract pin name and direction
                    pin_name, direction = self._parse_line(stripped, line_number)

                    # Check for duplicate pin definitions
                    # We warn but continue, using the last definition (override behavior)
                    if pin_name in directions:
                        self.logger.warning(
                            f"Duplicate pin definition '{pin_name}' at line {line_number}. "
                            f"Overwriting previous definition."
                        )

                    # Store the pin direction
                    directions[pin_name] = direction

        except PinDirectionParseError:
            # Re-raise parse errors as-is (they already have line context)
            raise
        except Exception as e:
            # Wrap unexpected errors with file context
            raise PinDirectionParseError(
                f"Failed to parse pin direction file: {file_path}"
            ) from e

        # Log successful parse with pin count
        self.logger.info(f"Parsed {len(directions)} pin directions from {file_path}")

        return PinDirectionMap(directions=directions)

    def _parse_line(self, line: str, line_number: int) -> tuple[str, PinDirection]:
        """Parse a single pin direction line.

        Extracts the pin name and direction from a whitespace-separated line.
        The expected format is: PIN_NAME DIRECTION

        Args:
            line: The stripped line content (no leading/trailing whitespace)
            line_number: Line number for error reporting

        Returns:
            Tuple of (pin_name, direction) where pin_name is the original case
            and direction is the validated PinDirection enum value

        Raises:
            PinDirectionParseError: If the line format is invalid
        """
        # Split on whitespace (handles tabs, multiple spaces, etc.)
        parts = line.split()

        # Validate we have exactly 2 columns: PIN_NAME and DIRECTION
        if len(parts) != _EXPECTED_COLUMN_COUNT:
            raise PinDirectionParseError(
                f"Line {line_number}: Expected format 'PIN_NAME DIRECTION', got: {line}"
            )

        pin_name = parts[0]
        direction_str = parts[1]

        # Validate pin name is not empty (shouldn't happen after split, but defensive)
        if not pin_name:
            raise PinDirectionParseError(
                f"Line {line_number}: Pin name cannot be empty"
            )

        # Validate and convert the direction string to enum
        direction = self._validate_direction(direction_str, line_number)

        return pin_name, direction

    def _validate_direction(self, direction_str: str, line_number: int) -> PinDirection:
        """Validate and convert direction string to PinDirection enum.

        Performs case-insensitive matching, so 'input', 'INPUT', and 'Input'
        are all valid and equivalent.

        Args:
            direction_str: The direction string from the file
            line_number: Line number for error reporting

        Returns:
            The corresponding PinDirection enum value

        Raises:
            PinDirectionParseError: If the direction value is not valid
        """
        try:
            # Case-insensitive matching by converting to uppercase before lookup
            return PinDirection[direction_str.upper()]
        except KeyError:
            # Build a helpful error message listing valid options
            valid_directions = ", ".join([d.name for d in PinDirection])
            raise PinDirectionParseError(
                f"Line {line_number}: Invalid direction '{direction_str}'. "
                f"Valid values: {valid_directions}"
            ) from None
