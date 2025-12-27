"""Unit tests for InkMainWindow zoom status display functionality.

Tests verify the zoom status display meets all requirements from spec E06-F04-T03:
- update_zoom_status() method updates zoom_label text
- Zoom percentage formatted with no decimal places (integer)
- Format follows "Zoom: XXX%" pattern
- Handles full zoom range (10%-1000%)
- Handles fractional percentages (rounds to nearest integer)

These tests follow TDD methodology:
- RED phase: Tests written first, expecting failures
- GREEN phase: Implementation to pass all tests
- REFACTOR phase: Code cleanup while tests pass

See Also:
    - Spec E06-F04-T03 for zoom level display requirements
    - Spec E06-F04-T01 for status bar setup (upstream dependency)
    - E02-F02 for schematic canvas zoom_changed signal
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.main_window import InkMainWindow

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from pytestqt.qtbot import QtBot


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide isolated QSettings storage for each test.

    Args:
        tmp_path: Pytest-provided temporary directory (unique per test).

    Yields:
        Path to temporary settings directory.
    """
    settings_path = tmp_path / "settings"
    settings_path.mkdir()

    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.clear()
    temp_settings.sync()

    yield settings_path


@pytest.fixture
def app_settings(isolated_settings: Path) -> AppSettings:
    """Create AppSettings instance with isolated storage.

    Args:
        isolated_settings: Temporary settings directory (ensures isolation).

    Returns:
        Fresh AppSettings instance.
    """
    return AppSettings()


@pytest.fixture
def main_window(qtbot: QtBot, app_settings: AppSettings) -> InkMainWindow:
    """Create InkMainWindow instance for testing.

    Args:
        qtbot: Pytest-qt bot for widget management.
        app_settings: Application settings instance.

    Returns:
        InkMainWindow instance registered with qtbot.
    """
    window = InkMainWindow(app_settings)
    qtbot.addWidget(window)
    return window


# =============================================================================
# Test Classes
# =============================================================================


class TestUpdateZoomStatusMethod:
    """Tests for update_zoom_status() method existence and signature."""

    def test_update_zoom_status_method_exists(self, main_window: InkMainWindow) -> None:
        """Test that update_zoom_status method exists on InkMainWindow.

        The method should accept a zoom_percent float parameter and update
        the zoom_label text.
        """
        assert hasattr(main_window, "update_zoom_status")
        assert callable(main_window.update_zoom_status)

    def test_update_zoom_status_accepts_float(self, main_window: InkMainWindow) -> None:
        """Test that update_zoom_status accepts a float parameter.

        The method should accept zoom_percent as a float representing
        the zoom level as a percentage (e.g., 150.0 for 150%).
        """
        # Should not raise an exception
        main_window.update_zoom_status(100.0)


class TestZoomStatusFormatting:
    """Tests for zoom status display formatting."""

    def test_update_zoom_status_100_percent(self, main_window: InkMainWindow) -> None:
        """Zoom status should show 100% for default zoom.

        100% is the actual/default size zoom level.
        """
        main_window.update_zoom_status(100.0)
        assert main_window.zoom_label.text() == "Zoom: 100%"

    def test_update_zoom_status_formats_integer_round_up(self, main_window: InkMainWindow) -> None:
        """Zoom status should round up fractional percentages >= 0.5.

        150.7% should display as "Zoom: 151%" (rounds up).
        """
        main_window.update_zoom_status(150.7)
        assert main_window.zoom_label.text() == "Zoom: 151%"

    def test_update_zoom_status_formats_integer_round_down(
        self, main_window: InkMainWindow
    ) -> None:
        """Zoom status should round down fractional percentages < 0.5.

        75.3% should display as "Zoom: 75%" (rounds down).
        """
        main_window.update_zoom_status(75.3)
        assert main_window.zoom_label.text() == "Zoom: 75%"

    def test_update_zoom_status_minimum_zoom(self, main_window: InkMainWindow) -> None:
        """Zoom status should handle minimum zoom level (10%).

        The minimum supported zoom is 10%.
        """
        main_window.update_zoom_status(10.0)
        assert main_window.zoom_label.text() == "Zoom: 10%"

    def test_update_zoom_status_maximum_zoom(self, main_window: InkMainWindow) -> None:
        """Zoom status should handle maximum zoom level (1000%).

        The maximum supported zoom is 1000%.
        """
        main_window.update_zoom_status(1000.0)
        assert main_window.zoom_label.text() == "Zoom: 1000%"

    def test_update_zoom_status_fractional(self, main_window: InkMainWindow) -> None:
        """Zoom status should round multi-decimal percentages.

        123.456% should display as "Zoom: 123%" (truncates to integer).
        """
        main_window.update_zoom_status(123.456)
        assert main_window.zoom_label.text() == "Zoom: 123%"

    def test_update_zoom_status_zoomed_out(self, main_window: InkMainWindow) -> None:
        """Zoom status should handle zoomed out levels (< 100%).

        50% zoom is a common zoomed-out level.
        """
        main_window.update_zoom_status(50.0)
        assert main_window.zoom_label.text() == "Zoom: 50%"

    def test_update_zoom_status_zoomed_in(self, main_window: InkMainWindow) -> None:
        """Zoom status should handle zoomed in levels (> 100%).

        200% zoom is a common zoomed-in level.
        """
        main_window.update_zoom_status(200.0)
        assert main_window.zoom_label.text() == "Zoom: 200%"


class TestZoomStatusUpdates:
    """Tests for zoom status update behavior."""

    def test_zoom_status_updates_sequentially(self, main_window: InkMainWindow) -> None:
        """Zoom status should track sequential zoom changes.

        Multiple calls to update_zoom_status should each update the display.
        """
        main_window.update_zoom_status(50.0)
        assert main_window.zoom_label.text() == "Zoom: 50%"

        main_window.update_zoom_status(100.0)
        assert main_window.zoom_label.text() == "Zoom: 100%"

        main_window.update_zoom_status(200.0)
        assert main_window.zoom_label.text() == "Zoom: 200%"

    def test_zoom_status_updates_immediately(self, main_window: InkMainWindow) -> None:
        """Zoom status should update immediately on method call.

        No delay or deferred processing should be required.
        """
        initial_text = main_window.zoom_label.text()
        assert initial_text == "Zoom: 100%"  # Initial state

        main_window.update_zoom_status(150.0)

        # Should update immediately (no processEvents needed)
        assert main_window.zoom_label.text() == "Zoom: 150%"


class TestZoomStatusEdgeCases:
    """Tests for zoom status edge cases."""

    def test_zoom_status_exactly_100_no_rounding_error(self, main_window: InkMainWindow) -> None:
        """Zoom status should display exactly 100% without rounding issues.

        Floating point rounding should not cause 99% or 101% display.
        """
        main_window.update_zoom_status(100.0)
        assert main_window.zoom_label.text() == "Zoom: 100%"

    def test_zoom_status_near_boundary_values(self, main_window: InkMainWindow) -> None:
        """Zoom status should handle values near zoom boundaries.

        Values near 10% and 1000% should round correctly.
        """
        # Near minimum
        main_window.update_zoom_status(10.4)
        assert main_window.zoom_label.text() == "Zoom: 10%"

        main_window.update_zoom_status(10.6)
        assert main_window.zoom_label.text() == "Zoom: 11%"

        # Near maximum
        main_window.update_zoom_status(999.4)
        assert main_window.zoom_label.text() == "Zoom: 999%"

        main_window.update_zoom_status(999.6)
        assert main_window.zoom_label.text() == "Zoom: 1000%"
