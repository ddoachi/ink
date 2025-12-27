"""Integration tests for PinDirectionServiceImpl.

This module tests the full workflow of parsing a .pindir file and using the
PinDirectionServiceImpl to query pin directions. It verifies end-to-end
integration between:

1. PinDirectionParser: Parses .pindir files
2. PinDirectionMap: Holds parsed data
3. PinDirectionServiceImpl: Provides query API

These tests use real .pindir files from the examples/ directory to ensure
the complete workflow functions correctly in production scenarios.

Test Organization:
    - TestPinDirectionServiceIntegration: Full workflow tests
    - TestPinDirectionServicePerformance: Performance-related tests

See Also:
    - E01-F02-T02.spec.md: Full specification
    - examples/standard_cells.pindir: Sample pin direction file
"""

import time
from pathlib import Path

import pytest

from ink.domain.value_objects.pin_direction import PinDirection
from ink.infrastructure.parsing.pindir_parser import PinDirectionParser
from ink.infrastructure.services.pin_direction_service_impl import (
    PinDirectionServiceImpl,
)

# =============================================================================
# Fixtures: Test data and paths
# =============================================================================


@pytest.fixture
def examples_dir() -> Path:
    """Get the path to the examples directory.

    Returns:
        Path to the examples/ directory containing sample files
    """
    return Path(__file__).parents[5] / "examples"


@pytest.fixture
def standard_cells_pindir(examples_dir: Path) -> Path:
    """Get the path to the standard cells pindir file.

    Returns:
        Path to examples/standard_cells.pindir
    """
    return examples_dir / "standard_cells.pindir"


# =============================================================================
# Integration Tests
# =============================================================================


class TestPinDirectionServiceIntegration:
    """Integration tests for the full parse-to-query workflow.

    Tests the complete workflow from parsing a .pindir file to querying
    pin directions using the service implementation.
    """

    def test_full_workflow_with_standard_cells(
        self, standard_cells_pindir: Path
    ) -> None:
        """Test complete workflow: parse file -> create service -> query.

        This test verifies that the entire pipeline works correctly:
        1. Parse the .pindir file using PinDirectionParser
        2. Create a PinDirectionServiceImpl from the parsed map
        3. Query pin directions and verify correctness
        """
        # Skip if example file doesn't exist (for CI environments)
        if not standard_cells_pindir.exists():
            pytest.skip(f"Example file not found: {standard_cells_pindir}")

        # Step 1: Parse the file
        parser = PinDirectionParser()
        direction_map = parser.parse_file(standard_cells_pindir)

        # Step 2: Create service
        service = PinDirectionServiceImpl(_direction_map=direction_map)

        # Step 3: Verify the service has loaded data
        pin_count = service.get_pin_count()
        assert pin_count > 0, "Service should have at least one pin direction"

        # Step 4: Verify get_direction works with real data
        all_pins = service.get_all_pins()
        for pin_name, expected_direction in list(all_pins.items())[:5]:
            actual_direction = service.get_direction(pin_name)
            assert actual_direction == expected_direction, (
                f"Pin '{pin_name}' should be {expected_direction}, got {actual_direction}"
            )

        # Step 5: Verify unknown pins return INOUT
        unknown_result = service.get_direction("DEFINITELY_NOT_A_REAL_PIN_XYZ123")
        assert unknown_result == PinDirection.INOUT

    def test_service_creation_from_inline_content(self) -> None:
        """Test creating service from programmatically-created map.

        This test verifies the service works correctly when the
        PinDirectionMap is created directly (not from a file).
        """
        from ink.infrastructure.parsing.pindir_parser import PinDirectionMap

        # Create map programmatically
        direction_map = PinDirectionMap(
            directions={
                "CLK": PinDirection.INPUT,
                "RST": PinDirection.INPUT,
                "D": PinDirection.INPUT,
                "Q": PinDirection.OUTPUT,
                "QN": PinDirection.OUTPUT,
            }
        )

        # Create and verify service
        service = PinDirectionServiceImpl(_direction_map=direction_map)

        assert service.get_pin_count() == 5
        assert service.get_direction("CLK") == PinDirection.INPUT
        assert service.get_direction("Q") == PinDirection.OUTPUT
        assert service.has_pin("RST") is True
        assert service.has_pin("NONEXISTENT") is False

    def test_service_filtering_integration(self) -> None:
        """Test get_pins_by_direction with a mixed map.

        Verifies the filtering functionality works correctly when
        pins of all three directions are present.
        """
        from ink.infrastructure.parsing.pindir_parser import PinDirectionMap

        direction_map = PinDirectionMap(
            directions={
                "A": PinDirection.INPUT,
                "B": PinDirection.INPUT,
                "C": PinDirection.INPUT,
                "Y": PinDirection.OUTPUT,
                "Z": PinDirection.OUTPUT,
                "BUS": PinDirection.INOUT,
            }
        )

        service = PinDirectionServiceImpl(_direction_map=direction_map)

        # Verify filtering
        input_pins = service.get_pins_by_direction(PinDirection.INPUT)
        output_pins = service.get_pins_by_direction(PinDirection.OUTPUT)
        inout_pins = service.get_pins_by_direction(PinDirection.INOUT)

        assert len(input_pins) == 3
        assert len(output_pins) == 2
        assert len(inout_pins) == 1
        assert set(input_pins) == {"A", "B", "C"}
        assert set(output_pins) == {"Y", "Z"}
        assert set(inout_pins) == {"BUS"}


class TestPinDirectionServicePerformance:
    """Performance tests for PinDirectionServiceImpl.

    Verifies that the service meets performance requirements:
    - O(1) lookup time for get_direction() and has_pin()
    - Service creation overhead < 1ms for typical maps
    """

    def test_lookup_is_o1(self) -> None:
        """Verify lookup time doesn't scale with map size.

        By testing with increasingly large maps, we verify that
        lookup time remains constant (O(1) dictionary access).
        """
        from ink.infrastructure.parsing.pindir_parser import PinDirectionMap

        # Create maps of different sizes
        sizes = [100, 1000, 10000]
        lookup_times: list[float] = []

        for size in sizes:
            # Create map with 'size' pins
            directions = {f"PIN_{i}": PinDirection.INPUT for i in range(size)}
            direction_map = PinDirectionMap(directions=directions)
            service = PinDirectionServiceImpl(_direction_map=direction_map)

            # Time 1000 lookups
            start = time.perf_counter()
            for _ in range(1000):
                service.get_direction(f"PIN_{size // 2}")  # Lookup middle pin
            elapsed = time.perf_counter() - start

            lookup_times.append(elapsed)

        # Verify times don't scale significantly with size
        # The largest map should not take more than 3x the smallest
        # (accounting for cache effects and minor variations)
        ratio = lookup_times[-1] / lookup_times[0]
        assert ratio < 3, (
            f"Lookup time scaled too much with map size. "
            f"Times: {lookup_times}, Ratio: {ratio}"
        )

    def test_service_creation_overhead(self) -> None:
        """Verify service creation is fast (<1ms for typical maps).

        Service creation should be essentially instantaneous since
        it's just wrapping an existing PinDirectionMap.
        """
        from ink.infrastructure.parsing.pindir_parser import PinDirectionMap

        # Create a typical-size map (100 pins)
        directions = {f"PIN_{i}": PinDirection.INPUT for i in range(100)}
        direction_map = PinDirectionMap(directions=directions)

        # Time service creation (average of 1000 iterations)
        start = time.perf_counter()
        for _ in range(1000):
            PinDirectionServiceImpl(_direction_map=direction_map)
        elapsed = time.perf_counter() - start

        average_time_ms = (elapsed / 1000) * 1000  # Convert to ms

        assert average_time_ms < 1, (
            f"Service creation took {average_time_ms:.3f}ms on average, "
            f"expected < 1ms"
        )

    def test_get_all_pins_copy_overhead(self) -> None:
        """Verify get_all_pins copy overhead is acceptable.

        While get_all_pins() creates a copy for safety, the overhead
        should be reasonable for typical map sizes.
        """
        from ink.infrastructure.parsing.pindir_parser import PinDirectionMap

        # Create a map with 1000 pins
        directions = {f"PIN_{i}": PinDirection.INPUT for i in range(1000)}
        direction_map = PinDirectionMap(directions=directions)
        service = PinDirectionServiceImpl(_direction_map=direction_map)

        # Time 100 get_all_pins calls
        start = time.perf_counter()
        for _ in range(100):
            service.get_all_pins()
        elapsed = time.perf_counter() - start

        average_time_ms = (elapsed / 100) * 1000  # Convert to ms

        # Should be under 1ms even for 1000-pin maps
        assert average_time_ms < 1, (
            f"get_all_pins took {average_time_ms:.3f}ms on average for 1000 pins"
        )
