"""Unit tests for default pin direction handling.

This module contains TDD-driven tests for the default direction handling feature
in PinDirectionMap. It verifies:

1. Default INOUT behavior for missing pins
2. Missing pin tracking functionality
3. Statistics calculation for pin direction coverage
4. Immutability guarantees for returned sets

TDD Approach:
    - RED: These tests were written BEFORE implementation
    - GREEN: Implementation added to make tests pass
    - REFACTOR: Code improved while keeping tests green

Test Structure:
    - TestPinDirectionMapMissingPinTracking: Core tracking functionality
    - TestPinDirectionMapStatistics: Statistics calculation tests
    - TestPinDirectionMapImmutability: Immutability guarantees
    - TestPinDirectionMapEdgeCases: Edge case handling

See Also:
    - E01-F02-T03.spec.md: Full specification
    - ink.infrastructure.parsing.pindir_parser: PinDirectionMap implementation
"""

import pytest

from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.parsing.pindir_parser import PinDirectionMap

# =============================================================================
# Fixtures: Reusable test data
# =============================================================================


@pytest.fixture
def empty_map() -> PinDirectionMap:
    """Create an empty PinDirectionMap for edge case testing.

    Returns:
        PinDirectionMap with no pin directions defined
    """
    return PinDirectionMap(directions={})


@pytest.fixture
def partial_map() -> PinDirectionMap:
    """Create a PinDirectionMap with partial pin coverage.

    Contains a small set of defined pins, allowing tests to query
    both defined and undefined pins.

    Returns:
        PinDirectionMap with 5 pin direction mappings
    """
    return PinDirectionMap(
        directions={
            "A": PinDirection.INPUT,
            "B": PinDirection.INPUT,
            "Y": PinDirection.OUTPUT,
            "Z": PinDirection.OUTPUT,
            "EN": PinDirection.INOUT,
        }
    )


@pytest.fixture
def large_map() -> PinDirectionMap:
    """Create a PinDirectionMap with many pins for performance testing.

    Returns:
        PinDirectionMap with 100 pin direction mappings
    """
    directions: dict[str, PinDirection] = {}
    for i in range(100):
        directions[f"PIN_{i}"] = PinDirection.INPUT
    return PinDirectionMap(directions=directions)


# =============================================================================
# Test Classes: Organized by functionality
# =============================================================================


class TestPinDirectionMapMissingPinTracking:
    """Tests for missing pin tracking functionality.

    These tests verify that PinDirectionMap correctly tracks which pins
    were queried but not found in the direction mapping.
    """

    def test_querying_missing_pin_tracks_it(self, partial_map: PinDirectionMap) -> None:
        """Verify that querying a missing pin adds it to the tracked set.

        When get_direction() is called for a pin not in the mapping,
        that pin name should be added to _accessed_missing_pins.
        """
        # Query an undefined pin
        partial_map.get_direction("UNKNOWN_PIN")

        # Verify it was tracked
        missing_pins = partial_map.get_missing_pins()
        assert "UNKNOWN_PIN" in missing_pins

    def test_querying_defined_pin_does_not_track_it(
        self, partial_map: PinDirectionMap
    ) -> None:
        """Verify that querying a defined pin does not track it as missing.

        Pins that exist in the mapping should not be added to the
        missing pins set, even after being queried.
        """
        # Query a defined pin
        partial_map.get_direction("A")

        # Verify it was NOT tracked as missing
        missing_pins = partial_map.get_missing_pins()
        assert "A" not in missing_pins

    def test_multiple_missing_pins_tracked(self, partial_map: PinDirectionMap) -> None:
        """Verify that multiple different missing pins are all tracked.

        Each unique missing pin should be added to the tracking set.
        """
        # Query multiple undefined pins
        partial_map.get_direction("MISSING_1")
        partial_map.get_direction("MISSING_2")
        partial_map.get_direction("MISSING_3")

        # Verify all were tracked
        missing_pins = partial_map.get_missing_pins()
        assert "MISSING_1" in missing_pins
        assert "MISSING_2" in missing_pins
        assert "MISSING_3" in missing_pins
        assert len(missing_pins) == 3

    def test_repeated_queries_for_same_missing_pin_tracks_once(
        self, partial_map: PinDirectionMap
    ) -> None:
        """Verify that repeated queries for the same missing pin only track it once.

        The tracking set should only contain unique pin names, regardless
        of how many times each was queried.
        """
        # Query the same undefined pin multiple times
        partial_map.get_direction("REPEATED")
        partial_map.get_direction("REPEATED")
        partial_map.get_direction("REPEATED")

        # Verify it was tracked only once (set automatically deduplicates)
        missing_pins = partial_map.get_missing_pins()
        assert "REPEATED" in missing_pins
        assert len(missing_pins) == 1

    def test_has_pin_does_not_track_missing(self, partial_map: PinDirectionMap) -> None:
        """Verify that has_pin() does not track missing pins.

        Only get_direction() should trigger tracking, not has_pin().
        This allows checking for pin existence without side effects.
        """
        # Check for a missing pin using has_pin()
        partial_map.has_pin("CHECK_ONLY")

        # Verify it was NOT tracked
        missing_pins = partial_map.get_missing_pins()
        assert "CHECK_ONLY" not in missing_pins

    def test_empty_map_tracks_all_queries_as_missing(
        self, empty_map: PinDirectionMap
    ) -> None:
        """Verify that an empty map tracks all queried pins as missing.

        When no pins are defined, every query should add the pin to
        the missing set.
        """
        empty_map.get_direction("ANY_PIN_1")
        empty_map.get_direction("ANY_PIN_2")

        missing_pins = empty_map.get_missing_pins()
        assert "ANY_PIN_1" in missing_pins
        assert "ANY_PIN_2" in missing_pins
        assert len(missing_pins) == 2


class TestPinDirectionMapStatistics:
    """Tests for get_missing_pin_stats() method.

    These tests verify that statistics are calculated correctly for
    various pin direction and access patterns.
    """

    def test_stats_with_no_missing_accesses(
        self, partial_map: PinDirectionMap
    ) -> None:
        """Verify statistics when no missing pins have been accessed.

        Initial state should show:
        - defined_pins: count of pins in mapping
        - missing_pins_accessed: 0
        - total_unique_pins: same as defined_pins
        """
        stats = partial_map.get_missing_pin_stats()

        assert stats["defined_pins"] == 5
        assert stats["missing_pins_accessed"] == 0
        assert stats["total_unique_pins"] == 5

    def test_stats_after_missing_accesses(self, partial_map: PinDirectionMap) -> None:
        """Verify statistics after some missing pins have been accessed.

        After querying undefined pins, statistics should reflect:
        - defined_pins: unchanged
        - missing_pins_accessed: count of unique missing pins queried
        - total_unique_pins: defined + missing
        """
        # Query some missing pins
        partial_map.get_direction("MISSING_1")
        partial_map.get_direction("MISSING_2")
        partial_map.get_direction("MISSING_3")

        stats = partial_map.get_missing_pin_stats()

        assert stats["defined_pins"] == 5
        assert stats["missing_pins_accessed"] == 3
        assert stats["total_unique_pins"] == 8

    def test_stats_with_empty_map(self, empty_map: PinDirectionMap) -> None:
        """Verify statistics for an empty direction map.

        An empty map with some queries should show:
        - defined_pins: 0
        - missing_pins_accessed: count of queries
        - total_unique_pins: same as missing_pins_accessed
        """
        empty_map.get_direction("PIN_1")
        empty_map.get_direction("PIN_2")

        stats = empty_map.get_missing_pin_stats()

        assert stats["defined_pins"] == 0
        assert stats["missing_pins_accessed"] == 2
        assert stats["total_unique_pins"] == 2

    def test_stats_repeated_queries_dont_inflate_count(
        self, partial_map: PinDirectionMap
    ) -> None:
        """Verify that repeated queries don't inflate statistics.

        Querying the same missing pin multiple times should only count
        it once in the statistics.
        """
        # Query same pin multiple times
        for _ in range(10):
            partial_map.get_direction("SAME_PIN")

        stats = partial_map.get_missing_pin_stats()

        assert stats["missing_pins_accessed"] == 1

    def test_stats_mixed_defined_and_missing_queries(
        self, partial_map: PinDirectionMap
    ) -> None:
        """Verify statistics with a mix of defined and missing queries.

        Queries for defined pins should not affect missing_pins_accessed.
        """
        # Query defined pins
        partial_map.get_direction("A")
        partial_map.get_direction("B")
        partial_map.get_direction("Y")

        # Query missing pins
        partial_map.get_direction("MISSING_1")
        partial_map.get_direction("MISSING_2")

        stats = partial_map.get_missing_pin_stats()

        assert stats["defined_pins"] == 5
        assert stats["missing_pins_accessed"] == 2
        assert stats["total_unique_pins"] == 7


class TestPinDirectionMapImmutability:
    """Tests for immutability guarantees of get_missing_pins().

    The returned set should be a copy, ensuring that external
    modifications don't affect the internal tracking state.
    """

    def test_get_missing_pins_returns_copy(
        self, partial_map: PinDirectionMap
    ) -> None:
        """Verify get_missing_pins() returns a copy, not a reference.

        Modifying the returned set should not affect the internal state.
        """
        # Access some missing pins
        partial_map.get_direction("TRACKED_PIN")

        # Get the missing pins set
        missing_pins = partial_map.get_missing_pins()

        # Attempt to modify the returned set
        missing_pins.add("INJECTED_PIN")

        # Verify internal state is unchanged
        fresh_missing_pins = partial_map.get_missing_pins()
        assert "INJECTED_PIN" not in fresh_missing_pins

    def test_repeated_get_missing_pins_returns_fresh_copies(
        self, partial_map: PinDirectionMap
    ) -> None:
        """Verify each call to get_missing_pins() returns a new copy.

        Multiple calls should return equal but distinct objects.
        """
        partial_map.get_direction("PIN_X")

        copy1 = partial_map.get_missing_pins()
        copy2 = partial_map.get_missing_pins()

        # Should be equal in content
        assert copy1 == copy2

        # But not the same object
        assert copy1 is not copy2

    def test_clearing_returned_set_does_not_affect_tracking(
        self, partial_map: PinDirectionMap
    ) -> None:
        """Verify clearing the returned set doesn't clear internal tracking.

        Even drastic modifications to the returned set should not
        affect the internal state.
        """
        partial_map.get_direction("PIN_A")
        partial_map.get_direction("PIN_B")

        returned_set = partial_map.get_missing_pins()
        returned_set.clear()

        # Internal state should still have the tracked pins
        fresh_set = partial_map.get_missing_pins()
        assert "PIN_A" in fresh_set
        assert "PIN_B" in fresh_set


class TestPinDirectionMapEdgeCases:
    """Edge case tests for default direction handling.

    Tests unusual but valid scenarios:
    - Empty maps
    - Special characters in pin names
    - Large numbers of missing pins
    """

    def test_default_direction_is_inout(self, partial_map: PinDirectionMap) -> None:
        """Verify default direction for missing pins is INOUT.

        INOUT is the conservative/safe default that allows bidirectional
        traversal in graph operations.
        """
        result = partial_map.get_direction("UNDEFINED_PIN")
        assert result == PinDirection.INOUT

    def test_tracking_with_special_characters(self) -> None:
        """Verify tracking works with special characters in pin names.

        Real netlists may have pins like "net[0]", "data<31>", etc.
        """
        direction_map = PinDirectionMap(directions={})

        direction_map.get_direction("net[0]")
        direction_map.get_direction("data<31>")
        direction_map.get_direction("clk_2")

        missing_pins = direction_map.get_missing_pins()
        assert "net[0]" in missing_pins
        assert "data<31>" in missing_pins
        assert "clk_2" in missing_pins

    def test_large_number_of_missing_pins(self, large_map: PinDirectionMap) -> None:
        """Verify tracking works with many missing pins.

        Performance should remain reasonable even with many tracked pins.
        """
        # Query many undefined pins
        for i in range(1000):
            large_map.get_direction(f"MISSING_{i}")

        stats = large_map.get_missing_pin_stats()

        assert stats["defined_pins"] == 100
        assert stats["missing_pins_accessed"] == 1000
        assert stats["total_unique_pins"] == 1100

    def test_empty_string_pin_name_tracking(
        self, partial_map: PinDirectionMap
    ) -> None:
        """Verify empty string pin names are tracked correctly.

        While unusual, empty string should be handled like any other pin name.
        """
        partial_map.get_direction("")

        missing_pins = partial_map.get_missing_pins()
        assert "" in missing_pins

    def test_stats_keys_are_correct(self, partial_map: PinDirectionMap) -> None:
        """Verify get_missing_pin_stats() returns exactly the expected keys.

        The stats dictionary should have exactly three keys with specific names.
        """
        stats = partial_map.get_missing_pin_stats()

        expected_keys = {"defined_pins", "missing_pins_accessed", "total_unique_pins"}
        assert set(stats.keys()) == expected_keys


class TestPinDirectionMapNewFieldInitialization:
    """Tests for proper initialization of the _accessed_missing_pins field.

    These tests verify that the tracking field is correctly initialized
    and doesn't cause issues with dataclass behavior.
    """

    def test_new_map_has_empty_missing_pins(self) -> None:
        """Verify newly created map has empty missing pins set.

        The _accessed_missing_pins field should be initialized as empty.
        """
        direction_map = PinDirectionMap(
            directions={"A": PinDirection.INPUT}
        )

        missing_pins = direction_map.get_missing_pins()
        assert len(missing_pins) == 0

    def test_separate_maps_have_independent_tracking(self) -> None:
        """Verify separate map instances track independently.

        Each PinDirectionMap should have its own tracking state.
        """
        map1 = PinDirectionMap(directions={})
        map2 = PinDirectionMap(directions={})

        # Query different pins on each map
        map1.get_direction("PIN_ON_MAP1")
        map2.get_direction("PIN_ON_MAP2")

        # Verify independent tracking
        assert "PIN_ON_MAP1" in map1.get_missing_pins()
        assert "PIN_ON_MAP1" not in map2.get_missing_pins()
        assert "PIN_ON_MAP2" in map2.get_missing_pins()
        assert "PIN_ON_MAP2" not in map1.get_missing_pins()
