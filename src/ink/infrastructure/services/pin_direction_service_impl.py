"""Pin Direction Service Implementation.

This module provides the infrastructure implementation of the PinDirectionService
protocol. It wraps a PinDirectionMap (from the parser) and provides a clean API
for querying pin directions.

Architecture:
    This implementation follows the Clean Architecture pattern:
    - Domain layer defines the PinDirectionService protocol (interface)
    - Infrastructure layer provides this implementation (concrete class)
    - Application layer uses the protocol (depends on abstraction)

Performance Characteristics:
    - get_direction(): O(1) dictionary lookup
    - has_pin(): O(1) dictionary lookup
    - get_all_pins(): O(n) copy where n = number of pins
    - get_pin_count(): O(1)
    - get_pins_by_direction(): O(n) filter where n = number of pins

Design Decisions:
    - Dataclass for simple initialization and immutability
    - Optional logger injection for testing
    - Debug logging for unknown pins (not warnings, to avoid log spam)
    - Returns copies from get_all_pins() to prevent external mutation

Usage:
    >>> from pathlib import Path
    >>> from ink.infrastructure.parsing.pindir_parser import PinDirectionParser
    >>> from ink.infrastructure.services.pin_direction_service_impl import (
    ...     PinDirectionServiceImpl,
    ... )
    >>>
    >>> # Parse pin direction file
    >>> parser = PinDirectionParser()
    >>> direction_map = parser.parse_file(Path("example.pindir"))
    >>>
    >>> # Create service
    >>> service = PinDirectionServiceImpl(_direction_map=direction_map)
    >>>
    >>> # Query directions
    >>> direction = service.get_direction("A")
    >>> print(f"Pin A is {direction}")

See Also:
    - E01-F02-T02.spec.md: Full specification
    - ink.domain.services.pin_direction_service: Service protocol
    - ink.infrastructure.parsing.pindir_parser: Parser and PinDirectionMap
"""

import logging
from dataclasses import dataclass, field

from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.parsing.pindir_parser import PinDirectionMap


@dataclass
class PinDirectionServiceImpl:
    """Implementation of PinDirectionService using parsed pin direction data.

    This class provides O(1) lookup for pin directions using an in-memory
    dictionary (PinDirectionMap). It implements the PinDirectionService
    protocol from the domain layer.

    The service is designed to be immutable after creation - the underlying
    direction map should not be modified. All public methods that return
    collections return copies to prevent external mutation.

    Attributes:
        _direction_map: The parsed pin direction mapping. This is the source
                       of truth for all pin direction lookups.
        _logger: Logger instance for debug messages. If not provided, a
                module-level logger is created automatically.

    Example:
        >>> from ink.infrastructure.parsing.pindir_parser import PinDirectionMap
        >>> from ink.domain.value_objects.pin_direction import PinDirection
        >>>
        >>> # Create service with inline map
        >>> direction_map = PinDirectionMap(directions={
        ...     "A": PinDirection.INPUT,
        ...     "Y": PinDirection.OUTPUT,
        ... })
        >>> service = PinDirectionServiceImpl(_direction_map=direction_map)
        >>>
        >>> # Use the service
        >>> print(service.get_direction("A"))  # PinDirection.INPUT
        >>> print(service.has_pin("A"))  # True
        >>> print(service.get_pin_count())  # 2
    """

    # The underlying pin direction mapping from the parser.
    # Uses underscore prefix to indicate it's internal/private.
    _direction_map: PinDirectionMap

    # Optional logger for debug messages.
    # Uses field with default_factory to avoid mutable default argument.
    _logger: logging.Logger | None = field(default=None)

    def __post_init__(self) -> None:
        """Initialize the logger if not provided.

        This method is called automatically after __init__ by the dataclass
        mechanism. It sets up a default logger if one wasn't injected,
        enabling debug logging for unknown pin lookups.
        """
        if self._logger is None:
            # Use module-level logger for consistent logging configuration
            self._logger = logging.getLogger(__name__)

    def get_direction(self, pin_name: str) -> PinDirection:
        """Get direction for a pin name.

        Looks up the pin direction in the underlying map. If the pin is not
        found, returns INOUT as the safe default and logs a debug message.

        The default INOUT behavior is intentional:
        - INOUT allows graph traversal in both directions (fanin and fanout)
        - This is safer than failing or assuming INPUT/OUTPUT
        - Debug logging helps identify missing pin definitions during development

        Args:
            pin_name: Name of the pin to look up. Pin names are case-sensitive,
                     meaning "CLK" and "clk" are treated as different pins.

        Returns:
            PinDirection for the pin:
            - The mapped direction if pin is found in the map
            - PinDirection.INOUT if pin is not found (default behavior)

        Example:
            >>> service.get_direction("A")  # Returns INPUT if A is defined as INPUT
            >>> service.get_direction("UNKNOWN")  # Returns INOUT (default)
        """
        # Delegate to the underlying map for the actual lookup
        direction = self._direction_map.get_direction(pin_name)

        # Log debug message for unknown pins to help with troubleshooting.
        # We check has_pin() to distinguish "not found" from "explicitly INOUT".
        if not self.has_pin(pin_name):
            # Assert is for type checker - logger is always set after __post_init__
            assert self._logger is not None
            self._logger.debug(
                f"Pin '{pin_name}' not found in direction mapping. "
                f"Defaulting to INOUT."
            )

        return direction

    def has_pin(self, pin_name: str) -> bool:
        """Check if pin name exists in the direction mapping.

        This method provides explicit existence checking, which is important
        for distinguishing between:
        - Pin explicitly defined as INOUT (has_pin returns True)
        - Pin not defined, defaulting to INOUT (has_pin returns False)

        Use this method when you need to know if a pin was explicitly
        configured vs. relying on the default behavior.

        Args:
            pin_name: Name of the pin to check. Pin names are case-sensitive.

        Returns:
            True if the pin is defined in the mapping, False otherwise

        Example:
            >>> service.has_pin("A")  # True if A is in the mapping
            >>> service.has_pin("UNKNOWN")  # False if not in mapping
        """
        return self._direction_map.has_pin(pin_name)

    def get_all_pins(self) -> dict[str, PinDirection]:
        """Get all pin name to direction mappings.

        Returns a complete copy of the internal pin direction mapping.
        The copy ensures that external code cannot modify the service's
        internal state, preserving immutability.

        This method is useful for:
        - Debugging: Print all available pin directions
        - UI: Display pin direction configuration
        - Validation: Check completeness of pin direction definitions

        Returns:
            Dictionary mapping pin names to their directions.
            Returns an empty dict if no pins are defined.
            This is a copy - modifications won't affect the service.

        Performance:
            O(n) where n is the number of pins, due to dictionary copy.
            For typical pin direction files (100-1000 pins), this is
            negligible (<1ms).

        Example:
            >>> all_pins = service.get_all_pins()
            >>> for name, direction in all_pins.items():
            ...     print(f"{name}: {direction}")
        """
        # Return a copy to prevent external mutation of internal state.
        # This preserves the immutability guarantee of the service.
        return self._direction_map.directions.copy()

    def get_pin_count(self) -> int:
        """Get total number of pins with defined directions.

        Returns the count of pins that have explicit direction assignments
        in the mapping. Pins not in the mapping (which default to INOUT)
        are not counted.

        This method is useful for:
        - Logging: Report number of loaded pin directions
        - Validation: Verify expected number of pins were loaded
        - Monitoring: Track pin direction coverage

        Returns:
            Number of pins with defined directions (>= 0)

        Performance:
            O(1) - uses len() on the internal dictionary.

        Example:
            >>> count = service.get_pin_count()
            >>> print(f"Loaded {count} pin directions")
        """
        return len(self._direction_map.directions)

    def get_pins_by_direction(self, direction: PinDirection) -> list[str]:
        """Get all pin names with a specific direction.

        Filters the pin mapping to return only pins with the specified
        direction. This is useful for operations that need to work with
        pins of a specific type (e.g., all inputs, all outputs).

        Args:
            direction: The direction to filter by (INPUT, OUTPUT, or INOUT)

        Returns:
            List of pin names with the specified direction.
            Returns an empty list if no pins match.
            The order of pins in the list is not guaranteed.

        Performance:
            O(n) where n is the total number of pins, as we must check
            each pin's direction.

        Example:
            >>> input_pins = service.get_pins_by_direction(PinDirection.INPUT)
            >>> print(f"Found {len(input_pins)} input pins: {input_pins}")
            >>>
            >>> output_pins = service.get_pins_by_direction(PinDirection.OUTPUT)
            >>> for pin in output_pins:
            ...     print(f"Output: {pin}")
        """
        # Use list comprehension for clear, Pythonic filtering.
        # This iterates through all pins and collects those matching the direction.
        return [
            pin_name
            for pin_name, pin_dir in self._direction_map.directions.items()
            if pin_dir == direction
        ]
