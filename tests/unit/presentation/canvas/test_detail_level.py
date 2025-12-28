"""Unit tests for DetailLevel enum and zoom-based LOD selection.

Tests verify the DetailLevel implementation meets all requirements from spec E02-F01-T04:
- DetailLevel.from_zoom() classmethod for zoom-to-LOD mapping
- Threshold values: MINIMAL (<25%), BASIC (25-75%), FULL (>75%)
- Edge case handling for boundary values
- Ordering comparisons work correctly

TDD Approach:
- RED phase: These tests will fail initially as from_zoom() doesn't exist yet
- GREEN phase: Implement from_zoom() to pass all tests
- REFACTOR phase: Clean up and optimize implementation

Architecture Notes:
- DetailLevel is a presentation-layer concept (no domain impact)
- Used by SchematicCanvas to determine LOD for graphics items
- from_zoom() is a factory method for creating appropriate LOD from zoom factor

See Also:
- Spec E02-F01-T04 for detailed requirements
- src/ink/presentation/canvas/detail_level.py for DetailLevel enum
"""

from __future__ import annotations

import pytest

from ink.presentation.canvas.detail_level import DetailLevel

# =============================================================================
# DetailLevel.from_zoom() Tests - Threshold Values
# =============================================================================


class TestDetailLevelFromZoomThresholds:
    """Tests for DetailLevel.from_zoom() threshold values.

    The zoom thresholds are:
    - MINIMAL: zoom_factor < 0.25 (less than 25%)
    - BASIC: 0.25 <= zoom_factor < 0.75 (25% to 75%)
    - FULL: zoom_factor >= 0.75 (75% and above)
    """

    def test_from_zoom_returns_minimal_at_zero(self) -> None:
        """Test that zoom factor 0 returns MINIMAL level.

        At 0% zoom (fully zoomed out), minimal detail is appropriate.
        """
        level = DetailLevel.from_zoom(0.0)

        assert level == DetailLevel.MINIMAL

    def test_from_zoom_returns_minimal_at_10_percent(self) -> None:
        """Test that 10% zoom returns MINIMAL level."""
        level = DetailLevel.from_zoom(0.10)

        assert level == DetailLevel.MINIMAL

    def test_from_zoom_returns_minimal_at_20_percent(self) -> None:
        """Test that 20% zoom returns MINIMAL level."""
        level = DetailLevel.from_zoom(0.20)

        assert level == DetailLevel.MINIMAL

    def test_from_zoom_returns_minimal_just_below_25_percent(self) -> None:
        """Test that just below 25% returns MINIMAL level.

        Edge case: 24.9% should still be MINIMAL.
        """
        level = DetailLevel.from_zoom(0.249)

        assert level == DetailLevel.MINIMAL

    def test_from_zoom_returns_basic_at_exactly_25_percent(self) -> None:
        """Test that exactly 25% zoom returns BASIC level.

        This is the lower boundary for BASIC level.
        """
        level = DetailLevel.from_zoom(0.25)

        assert level == DetailLevel.BASIC

    def test_from_zoom_returns_basic_at_50_percent(self) -> None:
        """Test that 50% zoom returns BASIC level."""
        level = DetailLevel.from_zoom(0.50)

        assert level == DetailLevel.BASIC

    def test_from_zoom_returns_basic_at_60_percent(self) -> None:
        """Test that 60% zoom returns BASIC level."""
        level = DetailLevel.from_zoom(0.60)

        assert level == DetailLevel.BASIC

    def test_from_zoom_returns_basic_just_below_75_percent(self) -> None:
        """Test that just below 75% returns BASIC level.

        Edge case: 74.9% should still be BASIC.
        """
        level = DetailLevel.from_zoom(0.749)

        assert level == DetailLevel.BASIC

    def test_from_zoom_returns_full_at_exactly_75_percent(self) -> None:
        """Test that exactly 75% zoom returns FULL level.

        This is the lower boundary for FULL level.
        """
        level = DetailLevel.from_zoom(0.75)

        assert level == DetailLevel.FULL

    def test_from_zoom_returns_full_at_100_percent(self) -> None:
        """Test that 100% zoom (1.0) returns FULL level."""
        level = DetailLevel.from_zoom(1.0)

        assert level == DetailLevel.FULL

    def test_from_zoom_returns_full_at_150_percent(self) -> None:
        """Test that 150% zoom returns FULL level."""
        level = DetailLevel.from_zoom(1.5)

        assert level == DetailLevel.FULL

    def test_from_zoom_returns_full_at_200_percent(self) -> None:
        """Test that 200% zoom returns FULL level."""
        level = DetailLevel.from_zoom(2.0)

        assert level == DetailLevel.FULL

    def test_from_zoom_returns_full_at_500_percent(self) -> None:
        """Test that 500% zoom (maximum) returns FULL level."""
        level = DetailLevel.from_zoom(5.0)

        assert level == DetailLevel.FULL


# =============================================================================
# DetailLevel.from_zoom() Tests - Edge Cases
# =============================================================================


class TestDetailLevelFromZoomEdgeCases:
    """Tests for edge cases in DetailLevel.from_zoom()."""

    def test_from_zoom_handles_very_small_positive_value(self) -> None:
        """Test that very small positive zoom returns MINIMAL."""
        level = DetailLevel.from_zoom(0.001)

        assert level == DetailLevel.MINIMAL

    def test_from_zoom_handles_very_large_value(self) -> None:
        """Test that very large zoom returns FULL."""
        level = DetailLevel.from_zoom(10.0)

        assert level == DetailLevel.FULL

    def test_from_zoom_handles_negative_value(self) -> None:
        """Test that negative zoom returns MINIMAL.

        Negative zoom is invalid but should be handled gracefully.
        """
        level = DetailLevel.from_zoom(-0.5)

        assert level == DetailLevel.MINIMAL

    def test_from_zoom_returns_detail_level_type(self) -> None:
        """Test that from_zoom returns a DetailLevel instance."""
        level = DetailLevel.from_zoom(1.0)

        assert isinstance(level, DetailLevel)


# =============================================================================
# DetailLevel.from_zoom() Tests - Return Value Properties
# =============================================================================


class TestDetailLevelFromZoomReturnValue:
    """Tests for properties of the return value from from_zoom()."""

    def test_from_zoom_minimal_has_value_zero(self) -> None:
        """Test that MINIMAL level has integer value 0."""
        level = DetailLevel.from_zoom(0.1)

        assert level.value == 0

    def test_from_zoom_basic_has_value_one(self) -> None:
        """Test that BASIC level has integer value 1."""
        level = DetailLevel.from_zoom(0.5)

        assert level.value == 1

    def test_from_zoom_full_has_value_two(self) -> None:
        """Test that FULL level has integer value 2."""
        level = DetailLevel.from_zoom(1.0)

        assert level.value == 2

    def test_from_zoom_levels_are_comparable(self) -> None:
        """Test that levels from from_zoom are comparable."""
        minimal = DetailLevel.from_zoom(0.1)
        basic = DetailLevel.from_zoom(0.5)
        full = DetailLevel.from_zoom(1.0)

        assert minimal < basic
        assert basic < full
        assert minimal < full


# =============================================================================
# DetailLevel.from_zoom() Tests - Consistent Behavior
# =============================================================================


class TestDetailLevelFromZoomConsistency:
    """Tests for consistent behavior of from_zoom()."""

    def test_from_zoom_is_deterministic(self) -> None:
        """Test that from_zoom returns same result for same input."""
        level1 = DetailLevel.from_zoom(0.5)
        level2 = DetailLevel.from_zoom(0.5)

        assert level1 == level2

    def test_from_zoom_transitions_smoothly(self) -> None:
        """Test that zoom transitions follow expected order.

        As zoom increases, detail level should never decrease.
        """
        zoom_values = [0.1, 0.2, 0.25, 0.5, 0.7, 0.75, 1.0, 2.0]
        levels = [DetailLevel.from_zoom(z) for z in zoom_values]

        # Levels should be monotonically non-decreasing
        for i in range(len(levels) - 1):
            assert levels[i] <= levels[i + 1], (
                f"Level at zoom {zoom_values[i]} should be <= level at zoom {zoom_values[i+1]}"
            )

    @pytest.mark.parametrize(
        "zoom,expected_level",
        [
            (0.0, DetailLevel.MINIMAL),
            (0.24, DetailLevel.MINIMAL),
            (0.25, DetailLevel.BASIC),
            (0.50, DetailLevel.BASIC),
            (0.74, DetailLevel.BASIC),
            (0.75, DetailLevel.FULL),
            (1.00, DetailLevel.FULL),
            (5.00, DetailLevel.FULL),
        ],
    )
    def test_from_zoom_parametrized(
        self, zoom: float, expected_level: DetailLevel
    ) -> None:
        """Parametrized test for from_zoom() threshold validation."""
        level = DetailLevel.from_zoom(zoom)

        assert level == expected_level
