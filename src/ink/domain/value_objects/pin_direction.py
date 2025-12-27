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


class PinDirection(Enum):
    """Pin direction types for circuit elements.

    This enum represents the three possible directions a pin can have:
    - INPUT: Receives signals from other cells/ports
    - OUTPUT: Drives signals to other cells/ports
    - INOUT: Bidirectional or unknown direction (default for missing pins)

    The string values match the `.pindir` file format specification.
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
