"""PinDirection enum value object.

This module defines the PinDirection enum which represents the three possible
directions a pin can have in a circuit netlist:

- INPUT: Pin receives signals (e.g., gate inputs, flip-flop data)
- OUTPUT: Pin drives signals (e.g., gate outputs, flip-flop Q)
- INOUT: Bidirectional or unknown direction (e.g., tri-state buffers)

The enum is a core value object used throughout the pin direction handling
workflow, from parsing `.pindir` files to graph traversal for fanin/fanout.

Example:
    >>> from ink.domain.value_objects.pin_direction import PinDirection
    >>> direction = PinDirection.INPUT
    >>> str(direction)
    'INPUT'
    >>> PinDirection["OUTPUT"]
    <PinDirection.OUTPUT: 'OUTPUT'>
"""

from enum import Enum


class PinDirection(str, Enum):
    """Pin direction types for circuit elements.

    This enum represents the three possible directions a pin can have:
    - INPUT: Receives signals from other cells/ports
    - OUTPUT: Drives signals to other cells/ports
    - INOUT: Bidirectional or unknown direction (default for missing pins)

    The string values match the `.pindir` file format specification.
    Inherits from str for natural string serialization and comparison.

    Example:
        >>> direction = PinDirection.INPUT
        >>> direction.is_input()
        True
        >>> direction.is_output()
        False
        >>> PinDirection.INOUT.is_input()  # INOUT can receive
        True
        >>> PinDirection.INOUT.is_output()  # INOUT can drive
        True
    """

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    INOUT = "INOUT"  # Bidirectional or unknown

    def __str__(self) -> str:
        """Return the string representation of the direction.

        Returns:
            The direction value as a string (e.g., 'INPUT', 'OUTPUT', 'INOUT')
        """
        return self.value

    def is_input(self) -> bool:
        """Check if this direction can receive signals.

        Returns True for INPUT and INOUT directions, as both can receive
        signals from other cells or ports. This is useful for determining
        fanin traversal targets.

        Returns:
            True if this direction is INPUT or INOUT, False otherwise.

        Example:
            >>> PinDirection.INPUT.is_input()
            True
            >>> PinDirection.INOUT.is_input()
            True
            >>> PinDirection.OUTPUT.is_input()
            False
        """
        return self in (PinDirection.INPUT, PinDirection.INOUT)

    def is_output(self) -> bool:
        """Check if this direction can drive signals.

        Returns True for OUTPUT and INOUT directions, as both can drive
        signals to other cells or ports. This is useful for determining
        fanout traversal targets.

        Returns:
            True if this direction is OUTPUT or INOUT, False otherwise.

        Example:
            >>> PinDirection.OUTPUT.is_output()
            True
            >>> PinDirection.INOUT.is_output()
            True
            >>> PinDirection.INPUT.is_output()
            False
        """
        return self in (PinDirection.OUTPUT, PinDirection.INOUT)
