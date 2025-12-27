"""Unit tests for PinDirectionServiceImpl.

This module contains comprehensive unit tests for the pin direction lookup service,
following the TDD approach (Red-Green-Refactor). Tests cover:

1. Core functionality:
   - get_direction() for known and unknown pins
   - has_pin() for existence checks
   - get_all_pins() for retrieving all mappings

2. Extended functionality:
   - get_pin_count() for statistics
   - get_pins_by_direction() for filtering

3. Edge cases:
   - Empty direction map
   - Large direction map (1000+ pins)
   - Case-sensitivity of pin names
   - Default INOUT behavior

4. Performance requirements:
   - O(1) lookup for get_direction() and has_pin()
   - Immutability of returned data

Test Structure:
    - TestPinDirectionServiceGetDirection: Tests for get_direction()
    - TestPinDirectionServiceHasPin: Tests for has_pin()
    - TestPinDirectionServiceGetAllPins: Tests for get_all_pins()
    - TestPinDirectionServiceGetPinCount: Tests for get_pin_count()
    - TestPinDirectionServiceGetPinsByDirection: Tests for get_pins_by_direction()
    - TestPinDirectionServiceEdgeCases: Edge case tests
    - TestPinDirectionServiceLogging: Logging behavior tests

See Also:
    - E01-F02-T02.spec.md: Full specification
    - ink.domain.services.pin_direction_service: Service protocol
    - ink.infrastructure.services.pin_direction_service_impl: Implementation
"""

import logging
from unittest.mock import MagicMock

import pytest

from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.parsing.pindir_parser import PinDirectionMap
from ink.infrastructure.services.pin_direction_service_impl import (
    PinDirectionServiceImpl,
)

# =============================================================================
# Fixtures: Reusable test data and service instances
# =============================================================================


@pytest.fixture
def sample_direction_map() -> PinDirectionMap:
    """Create a sample PinDirectionMap for testing.

    Contains a typical set of pin directions found in standard cell libraries:
    - A, B: INPUT pins (common gate inputs)
    - Y, Z: OUTPUT pins (common gate outputs)
    - CLK: INPUT pin (clock signal)
    - Q, QN: OUTPUT pins (flip-flop outputs)
    - D: INPUT pin (flip-flop data)
    - EN: INOUT pin (enable, can be input or bidirectional)

    Returns:
        PinDirectionMap with 10 pin direction mappings
    """
    return PinDirectionMap(
        directions={
            "A": PinDirection.INPUT,
            "B": PinDirection.INPUT,
            "Y": PinDirection.OUTPUT,
            "Z": PinDirection.OUTPUT,
            "CLK": PinDirection.INPUT,
            "Q": PinDirection.OUTPUT,
            "QN": PinDirection.OUTPUT,
            "D": PinDirection.INPUT,
            "EN": PinDirection.INOUT,
            "VDD": PinDirection.INOUT,
        }
    )


@pytest.fixture
def empty_direction_map() -> PinDirectionMap:
    """Create an empty PinDirectionMap for edge case testing.

    Returns:
        PinDirectionMap with no pin directions defined
    """
    return PinDirectionMap(directions={})


@pytest.fixture
def large_direction_map() -> PinDirectionMap:
    """Create a large PinDirectionMap with 1000+ pins for performance testing.

    Generates pins with patterns:
    - IN_0 to IN_332: INPUT pins
    - OUT_0 to OUT_332: OUTPUT pins
    - IO_0 to IO_332: INOUT pins

    Returns:
        PinDirectionMap with 999 pin direction mappings
    """
    directions: dict[str, PinDirection] = {}
    for i in range(333):
        directions[f"IN_{i}"] = PinDirection.INPUT
        directions[f"OUT_{i}"] = PinDirection.OUTPUT
        directions[f"IO_{i}"] = PinDirection.INOUT
    return PinDirectionMap(directions=directions)


@pytest.fixture
def service(sample_direction_map: PinDirectionMap) -> PinDirectionServiceImpl:
    """Create a PinDirectionServiceImpl with sample data.

    Args:
        sample_direction_map: Injected fixture with sample pin directions

    Returns:
        Configured PinDirectionServiceImpl instance
    """
    return PinDirectionServiceImpl(_direction_map=sample_direction_map)


@pytest.fixture
def empty_service(empty_direction_map: PinDirectionMap) -> PinDirectionServiceImpl:
    """Create a PinDirectionServiceImpl with empty data.

    Args:
        empty_direction_map: Injected fixture with no pin directions

    Returns:
        PinDirectionServiceImpl instance with empty mapping
    """
    return PinDirectionServiceImpl(_direction_map=empty_direction_map)


@pytest.fixture
def large_service(large_direction_map: PinDirectionMap) -> PinDirectionServiceImpl:
    """Create a PinDirectionServiceImpl with large dataset.

    Args:
        large_direction_map: Injected fixture with 1000+ pins

    Returns:
        PinDirectionServiceImpl instance with large mapping
    """
    return PinDirectionServiceImpl(_direction_map=large_direction_map)


# =============================================================================
# Test Classes: Organized by method/functionality
# =============================================================================


class TestPinDirectionServiceGetDirection:
    """Tests for get_direction() method.

    The get_direction() method should:
    - Return the correct PinDirection for known pins
    - Return PinDirection.INOUT for unknown pins (default behavior)
    - Handle case-sensitive pin names correctly
    """

    def test_returns_input_for_input_pin(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify get_direction returns INPUT for a known INPUT pin.

        The service should correctly look up the direction for pin "A"
        which is defined as INPUT in the sample direction map.
        """
        result = service.get_direction("A")
        assert result == PinDirection.INPUT

    def test_returns_output_for_output_pin(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify get_direction returns OUTPUT for a known OUTPUT pin.

        The service should correctly look up the direction for pin "Y"
        which is defined as OUTPUT in the sample direction map.
        """
        result = service.get_direction("Y")
        assert result == PinDirection.OUTPUT

    def test_returns_inout_for_inout_pin(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify get_direction returns INOUT for a known INOUT pin.

        The service should correctly look up the direction for pin "EN"
        which is defined as INOUT in the sample direction map.
        """
        result = service.get_direction("EN")
        assert result == PinDirection.INOUT

    def test_returns_inout_for_unknown_pin(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify get_direction returns INOUT for an unknown pin.

        When a pin is not defined in the direction map, the service
        should return INOUT as the safe default (allows both fanin/fanout).
        """
        result = service.get_direction("UNKNOWN_PIN")
        assert result == PinDirection.INOUT

    def test_case_sensitive_lookup_exact_match(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify pin name lookup is case-sensitive (exact match works).

        Pin names in the direction map should be matched exactly,
        respecting case. "CLK" should be found correctly.
        """
        result = service.get_direction("CLK")
        assert result == PinDirection.INPUT

    def test_case_sensitive_lookup_wrong_case(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify case-sensitive lookup (wrong case returns default).

        Pin names are case-sensitive, so "clk" should not match "CLK"
        and should return the default INOUT.
        """
        result = service.get_direction("clk")
        assert result == PinDirection.INOUT

    def test_multiple_pins_lookup(self, service: PinDirectionServiceImpl) -> None:
        """Verify get_direction works correctly for multiple different pins.

        Test a sequence of lookups to ensure the service correctly
        handles multiple queries without state corruption.
        """
        assert service.get_direction("A") == PinDirection.INPUT
        assert service.get_direction("B") == PinDirection.INPUT
        assert service.get_direction("Y") == PinDirection.OUTPUT
        assert service.get_direction("Q") == PinDirection.OUTPUT
        assert service.get_direction("EN") == PinDirection.INOUT


class TestPinDirectionServiceHasPin:
    """Tests for has_pin() method.

    The has_pin() method should:
    - Return True for pins that exist in the mapping
    - Return False for pins that don't exist
    - Handle case-sensitivity correctly
    """

    def test_returns_true_for_existing_pin(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify has_pin returns True for a pin in the mapping."""
        assert service.has_pin("A") is True

    def test_returns_true_for_inout_pin(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify has_pin returns True for an explicitly defined INOUT pin.

        This distinguishes between a pin explicitly set to INOUT vs
        an unknown pin that defaults to INOUT.
        """
        assert service.has_pin("EN") is True

    def test_returns_false_for_missing_pin(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify has_pin returns False for a pin not in the mapping."""
        assert service.has_pin("NONEXISTENT") is False

    def test_case_sensitive_check(self, service: PinDirectionServiceImpl) -> None:
        """Verify has_pin is case-sensitive."""
        assert service.has_pin("CLK") is True
        assert service.has_pin("clk") is False
        assert service.has_pin("Clk") is False

    def test_empty_string_pin_name(self, service: PinDirectionServiceImpl) -> None:
        """Verify has_pin handles empty string correctly."""
        assert service.has_pin("") is False


class TestPinDirectionServiceGetAllPins:
    """Tests for get_all_pins() method.

    The get_all_pins() method should:
    - Return all pin-to-direction mappings
    - Return a copy (not the internal dict)
    - Work correctly with empty maps
    """

    def test_returns_all_pins(self, service: PinDirectionServiceImpl) -> None:
        """Verify get_all_pins returns the complete mapping."""
        all_pins = service.get_all_pins()
        assert len(all_pins) == 10
        assert all_pins["A"] == PinDirection.INPUT
        assert all_pins["Y"] == PinDirection.OUTPUT
        assert all_pins["EN"] == PinDirection.INOUT

    def test_returns_copy_not_reference(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify get_all_pins returns a copy to prevent mutation.

        Modifying the returned dictionary should not affect the
        internal state of the service.
        """
        all_pins = service.get_all_pins()
        # Modify the returned dict
        all_pins["A"] = PinDirection.OUTPUT
        all_pins["NEW_PIN"] = PinDirection.INPUT

        # Original service should be unchanged
        assert service.get_direction("A") == PinDirection.INPUT
        assert service.has_pin("NEW_PIN") is False

    def test_empty_map_returns_empty_dict(
        self, empty_service: PinDirectionServiceImpl
    ) -> None:
        """Verify get_all_pins returns empty dict for empty map."""
        all_pins = empty_service.get_all_pins()
        assert all_pins == {}
        assert len(all_pins) == 0


class TestPinDirectionServiceGetPinCount:
    """Tests for get_pin_count() method.

    The get_pin_count() method should return the total number of
    pins with defined directions.
    """

    def test_returns_correct_count(self, service: PinDirectionServiceImpl) -> None:
        """Verify get_pin_count returns the correct number of pins."""
        assert service.get_pin_count() == 10

    def test_empty_map_returns_zero(
        self, empty_service: PinDirectionServiceImpl
    ) -> None:
        """Verify get_pin_count returns 0 for empty map."""
        assert empty_service.get_pin_count() == 0

    def test_large_map_returns_correct_count(
        self, large_service: PinDirectionServiceImpl
    ) -> None:
        """Verify get_pin_count handles large maps correctly."""
        assert large_service.get_pin_count() == 999


class TestPinDirectionServiceGetPinsByDirection:
    """Tests for get_pins_by_direction() method.

    The get_pins_by_direction() method should return all pin names
    with a specific direction.
    """

    def test_get_input_pins(self, service: PinDirectionServiceImpl) -> None:
        """Verify filtering INPUT pins works correctly."""
        input_pins = service.get_pins_by_direction(PinDirection.INPUT)
        assert set(input_pins) == {"A", "B", "CLK", "D"}

    def test_get_output_pins(self, service: PinDirectionServiceImpl) -> None:
        """Verify filtering OUTPUT pins works correctly."""
        output_pins = service.get_pins_by_direction(PinDirection.OUTPUT)
        assert set(output_pins) == {"Y", "Z", "Q", "QN"}

    def test_get_inout_pins(self, service: PinDirectionServiceImpl) -> None:
        """Verify filtering INOUT pins works correctly."""
        inout_pins = service.get_pins_by_direction(PinDirection.INOUT)
        assert set(inout_pins) == {"EN", "VDD"}

    def test_empty_result_for_no_matching_pins(
        self, sample_direction_map: PinDirectionMap
    ) -> None:
        """Verify empty list returned when no pins match direction."""
        # Create a map with only INPUT pins
        input_only_map = PinDirectionMap(
            directions={
                "A": PinDirection.INPUT,
                "B": PinDirection.INPUT,
            }
        )
        service = PinDirectionServiceImpl(_direction_map=input_only_map)
        output_pins = service.get_pins_by_direction(PinDirection.OUTPUT)
        assert output_pins == []


class TestPinDirectionServiceEdgeCases:
    """Edge case tests for PinDirectionServiceImpl.

    Tests unusual but valid scenarios:
    - Empty direction maps
    - Large direction maps
    - Special characters in pin names
    """

    def test_empty_map_get_direction_returns_inout(
        self, empty_service: PinDirectionServiceImpl
    ) -> None:
        """Verify empty map returns INOUT for any pin lookup."""
        assert empty_service.get_direction("ANY") == PinDirection.INOUT
        assert empty_service.get_direction("A") == PinDirection.INOUT

    def test_empty_map_has_pin_returns_false(
        self, empty_service: PinDirectionServiceImpl
    ) -> None:
        """Verify empty map returns False for any has_pin check."""
        assert empty_service.has_pin("ANY") is False

    def test_large_map_performance(
        self, large_service: PinDirectionServiceImpl
    ) -> None:
        """Verify large map operations complete quickly (O(1) lookup).

        With 1000 pins, lookups should still be O(1) dictionary operations.
        This test verifies correctness; actual timing is implicit.
        """
        # Test multiple lookups in large map
        assert large_service.get_direction("IN_0") == PinDirection.INPUT
        assert large_service.get_direction("IN_332") == PinDirection.INPUT
        assert large_service.get_direction("OUT_0") == PinDirection.OUTPUT
        assert large_service.get_direction("OUT_332") == PinDirection.OUTPUT
        assert large_service.get_direction("IO_0") == PinDirection.INOUT
        assert large_service.get_direction("IO_332") == PinDirection.INOUT
        assert large_service.get_direction("UNKNOWN") == PinDirection.INOUT

    def test_pin_names_with_special_characters(self) -> None:
        """Verify pin names with special characters work correctly.

        Real netlists may have pins like "net[0]", "data<31>", or "clk_2".
        """
        special_map = PinDirectionMap(
            directions={
                "net[0]": PinDirection.INPUT,
                "data<31>": PinDirection.OUTPUT,
                "clk_2": PinDirection.INPUT,
                "VDD!": PinDirection.INOUT,
            }
        )
        service = PinDirectionServiceImpl(_direction_map=special_map)

        assert service.get_direction("net[0]") == PinDirection.INPUT
        assert service.get_direction("data<31>") == PinDirection.OUTPUT
        assert service.get_direction("clk_2") == PinDirection.INPUT
        assert service.get_direction("VDD!") == PinDirection.INOUT
        assert service.has_pin("net[0]") is True

    def test_numeric_pin_names(self) -> None:
        """Verify numeric pin names work correctly.

        Some netlists may use purely numeric pin names like "0", "1".
        """
        numeric_map = PinDirectionMap(
            directions={
                "0": PinDirection.INPUT,
                "1": PinDirection.OUTPUT,
                "123": PinDirection.INOUT,
            }
        )
        service = PinDirectionServiceImpl(_direction_map=numeric_map)

        assert service.get_direction("0") == PinDirection.INPUT
        assert service.get_direction("1") == PinDirection.OUTPUT
        assert service.get_direction("123") == PinDirection.INOUT


class TestPinDirectionServiceLogging:
    """Tests for logging behavior in PinDirectionServiceImpl.

    The service should log debug messages for missing pins to aid
    troubleshooting without spamming logs during normal operation.
    """

    def test_logs_debug_for_unknown_pin(
        self, sample_direction_map: PinDirectionMap, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify debug log is emitted for unknown pin lookup.

        When get_direction() is called for a pin not in the mapping,
        a debug-level log should be emitted to help with troubleshooting.
        """
        # Create service with captured logging
        with caplog.at_level(logging.DEBUG):
            service = PinDirectionServiceImpl(_direction_map=sample_direction_map)
            service.get_direction("UNKNOWN_PIN")

        # Verify debug message was logged
        assert len(caplog.records) >= 1
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("UNKNOWN_PIN" in msg for msg in debug_messages)
        assert any("INOUT" in msg or "not found" in msg.lower() for msg in debug_messages)

    def test_no_log_for_known_pin(
        self, sample_direction_map: PinDirectionMap, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify no debug log for known pin lookup.

        Looking up a known pin should not generate any debug logs
        since this is normal operation.
        """
        with caplog.at_level(logging.DEBUG):
            service = PinDirectionServiceImpl(_direction_map=sample_direction_map)
            service.get_direction("A")

        # Filter to only debug messages about pins
        pin_debug_messages = [
            r.message for r in caplog.records
            if r.levelno == logging.DEBUG and "not found" in r.message.lower()
        ]
        assert len(pin_debug_messages) == 0

    def test_custom_logger_injection(
        self, sample_direction_map: PinDirectionMap
    ) -> None:
        """Verify custom logger can be injected.

        The service should accept a custom logger for testing and
        integration scenarios.
        """
        mock_logger = MagicMock(spec=logging.Logger)
        service = PinDirectionServiceImpl(
            _direction_map=sample_direction_map, _logger=mock_logger
        )

        # Trigger a debug log by looking up unknown pin
        service.get_direction("UNKNOWN")

        # Verify the mock logger was used
        mock_logger.debug.assert_called()


class TestPinDirectionServiceImmutability:
    """Tests for immutability guarantees of PinDirectionServiceImpl.

    The service should protect its internal state from external mutation.
    """

    def test_get_all_pins_mutation_does_not_affect_service(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify mutating get_all_pins result doesn't affect service."""
        pins = service.get_all_pins()
        original_a_direction = pins["A"]

        # Attempt to mutate
        pins["A"] = PinDirection.OUTPUT
        pins["INJECTED"] = PinDirection.INPUT

        # Service should be unchanged
        assert service.get_direction("A") == original_a_direction
        assert service.has_pin("INJECTED") is False

    def test_repeated_get_all_pins_returns_fresh_copy(
        self, service: PinDirectionServiceImpl
    ) -> None:
        """Verify each call to get_all_pins returns a new copy."""
        pins1 = service.get_all_pins()
        pins2 = service.get_all_pins()

        # Should be equal in content
        assert pins1 == pins2

        # But not the same object
        assert pins1 is not pins2

        # Modifying one doesn't affect the other
        pins1["A"] = PinDirection.OUTPUT
        assert pins2["A"] == PinDirection.INPUT
