"""Pin Direction Service Protocol.

This module defines the domain service interface (Protocol) for querying
pin directions. The interface provides a clean API for the application layer
to query pin directions without depending on infrastructure details.

Design Decisions:
    - Protocol over ABC: Enables structural typing and easier testing
    - Default to INOUT: Safest assumption for unknown pins (allows traversal)
    - Case-sensitive: Matches real netlist pin name semantics
    - Separate has_pin(): Distinguishes "not found" from "explicitly INOUT"

Usage:
    The PinDirectionService protocol is implemented by infrastructure services
    and used by application services for graph construction and rendering.

    >>> from ink.domain.services.pin_direction_service import PinDirectionService
    >>> from ink.domain.value_objects.pin_direction import PinDirection
    >>>
    >>> def create_pin(name: str, service: PinDirectionService) -> dict:
    ...     direction = service.get_direction(name)
    ...     return {"name": name, "direction": direction}

See Also:
    - E01-F02-T02.spec.md: Full specification for this service
    - ink.infrastructure.services.pin_direction_service_impl: Implementation
    - ink.domain.value_objects.pin_direction: PinDirection enum
"""

from typing import Protocol

from ink.domain.value_objects.pin_direction import PinDirection


class PinDirectionService(Protocol):
    """Domain service protocol for querying pin directions.

    This protocol defines the contract for pin direction lookup services.
    Pin directions are applied globally by pin name - a pin named "A" has
    the same direction (e.g., INPUT) for all cells that have an "A" pin.

    The service provides:
    - O(1) lookup for pin directions by name
    - Default INOUT behavior for unknown pins
    - Explicit existence checking via has_pin()
    - Bulk retrieval via get_all_pins()

    Implementation Notes:
        Implementations MUST:
        - Return INOUT for unknown pins (not raise exceptions)
        - Perform case-sensitive pin name matching
        - Return copies from get_all_pins() to prevent mutation

        Implementations SHOULD:
        - Provide O(1) lookup performance
        - Log debug messages for unknown pin lookups

    Example:
        >>> class MockPinDirectionService:
        ...     def get_direction(self, pin_name: str) -> PinDirection:
        ...         return {"A": PinDirection.INPUT}.get(pin_name, PinDirection.INOUT)
        ...     def has_pin(self, pin_name: str) -> bool:
        ...         return pin_name in {"A"}
        ...     def get_all_pins(self) -> dict[str, PinDirection]:
        ...         return {"A": PinDirection.INPUT}
    """

    def get_direction(self, pin_name: str) -> PinDirection:
        """Get direction for a pin name.

        Looks up the direction mapping for the given pin name. If the pin
        is not found in the mapping, returns INOUT as the safe default.
        This default allows graph traversal in both directions for unknown pins.

        Args:
            pin_name: Name of the pin to look up. Pin names are case-sensitive,
                     so "CLK" and "clk" are treated as different pins.

        Returns:
            PinDirection for the pin:
            - The mapped direction if pin is found
            - PinDirection.INOUT if pin is not found (default)

        Example:
            >>> direction = service.get_direction("A")
            >>> if direction == PinDirection.INPUT:
            ...     print("Pin A is an input")
        """
        ...

    def has_pin(self, pin_name: str) -> bool:
        """Check if pin name exists in the direction mapping.

        Use this method to distinguish between:
        - Pin explicitly defined as INOUT in the mapping
        - Pin not defined at all (defaulting to INOUT)

        This distinction is useful for validation, debugging, and
        understanding which pins have explicit direction assignments.

        Args:
            pin_name: Name of the pin to check. Pin names are case-sensitive.

        Returns:
            True if the pin is defined in the mapping, False otherwise

        Example:
            >>> if service.has_pin("A"):
            ...     print(f"A is defined as {service.get_direction('A')}")
            ... else:
            ...     print("A is not defined, using default INOUT")
        """
        ...

    def get_all_pins(self) -> dict[str, PinDirection]:
        """Get all pin name to direction mappings.

        Returns a copy of the complete pin direction mapping. The returned
        dictionary can be safely modified without affecting the service's
        internal state.

        This method is useful for:
        - Debugging and logging
        - UI display of all available pins
        - Bulk operations on pin directions

        Returns:
            Dictionary mapping pin names (str) to their directions (PinDirection).
            Returns an empty dict if no pins are defined.

        Note:
            The returned dictionary is a copy. Modifications will not affect
            the service's internal state.

        Example:
            >>> all_pins = service.get_all_pins()
            >>> print(f"Loaded {len(all_pins)} pin directions")
            >>> for name, direction in all_pins.items():
            ...     print(f"  {name}: {direction}")
        """
        ...
