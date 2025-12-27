"""Integration tests for zoom status signal connection.

Tests verify the integration between InkMainWindow and SchematicCanvas
for zoom level display as specified in E06-F04-T03:
- Canvas zoom_changed signal connected to update_zoom_status
- Zoom display updates when canvas emits zoom_changed
- Multiple zoom changes tracked correctly
- Signal connection handles canvas not yet initialized

These integration tests verify signal/slot connections work correctly.

See Also:
    - Spec E06-F04-T03 for zoom level display requirements
    - Spec E06-F04-T01 for status bar setup (upstream dependency)
    - E02-F02 for schematic canvas zoom_changed signal
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings, Signal

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


class TestCanvasZoomSignal:
    """Tests for SchematicCanvas zoom_changed signal existence."""

    def test_canvas_has_zoom_changed_signal(self, main_window: InkMainWindow) -> None:
        """Test that SchematicCanvas has a zoom_changed signal.

        The zoom_changed signal should be a Qt Signal that emits float.
        """
        canvas = main_window.schematic_canvas

        assert hasattr(canvas, "zoom_changed")
        # Verify it's a signal (signals are descriptor instances)
        assert isinstance(type(canvas).zoom_changed, Signal)


class TestZoomSignalConnection:
    """Tests for zoom signal connection to status update."""

    def test_zoom_signal_connected(self, main_window: InkMainWindow) -> None:
        """Test that zoom_changed signal triggers status update.

        When canvas emits zoom_changed, zoom_label should update.
        """
        # Emit zoom changed signal with 150%
        main_window.schematic_canvas.zoom_changed.emit(150.0)

        # Status should update
        assert main_window.zoom_label.text() == "Zoom: 150%"

    def test_multiple_zoom_changes_tracked(self, main_window: InkMainWindow) -> None:
        """Test that status tracks multiple zoom changes.

        Each emission of zoom_changed should update the status.
        """
        main_window.schematic_canvas.zoom_changed.emit(200.0)
        assert main_window.zoom_label.text() == "Zoom: 200%"

        main_window.schematic_canvas.zoom_changed.emit(50.0)
        assert main_window.zoom_label.text() == "Zoom: 50%"

        main_window.schematic_canvas.zoom_changed.emit(100.0)
        assert main_window.zoom_label.text() == "Zoom: 100%"

    def test_zoom_signal_with_fractional_value(self, main_window: InkMainWindow) -> None:
        """Test that fractional zoom values are rounded.

        Signal with 123.456 should display as "Zoom: 123%".
        """
        main_window.schematic_canvas.zoom_changed.emit(123.456)
        assert main_window.zoom_label.text() == "Zoom: 123%"


class TestZoomStatusInitialization:
    """Tests for zoom status initialization behavior."""

    def test_initial_zoom_is_100_percent(self, main_window: InkMainWindow) -> None:
        """Test that initial zoom shows 100% on window creation.

        Before any zoom changes, status should show default 100%.
        """
        assert main_window.zoom_label.text() == "Zoom: 100%"


class TestConnectStatusSignalsMethod:
    """Tests for _connect_status_signals method."""

    def test_connect_status_signals_method_exists(self, main_window: InkMainWindow) -> None:
        """Test that _connect_status_signals method exists.

        This method should be called during initialization to connect
        canvas signals to status bar update methods.
        """
        assert hasattr(main_window, "_connect_status_signals")
        assert callable(main_window._connect_status_signals)

    def test_connect_status_signals_handles_missing_canvas(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test that _connect_status_signals handles missing canvas gracefully.

        If called when canvas doesn't have zoom_changed signal,
        it should not raise an exception.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Should not raise - if canvas doesn't have signal, just skip
        try:
            window._connect_status_signals()
        except AttributeError:
            pytest.fail("_connect_status_signals raised AttributeError for missing signal")


class TestZoomUpdateTriggers:
    """Tests for various zoom update scenarios."""

    def test_zoom_updates_for_minimum_zoom(self, main_window: InkMainWindow) -> None:
        """Test zoom status updates correctly for minimum zoom (10%).

        Canvas should emit 10.0 for minimum zoom level.
        """
        main_window.schematic_canvas.zoom_changed.emit(10.0)
        assert main_window.zoom_label.text() == "Zoom: 10%"

    def test_zoom_updates_for_maximum_zoom(self, main_window: InkMainWindow) -> None:
        """Test zoom status updates correctly for maximum zoom (1000%).

        Canvas should emit 1000.0 for maximum zoom level.
        """
        main_window.schematic_canvas.zoom_changed.emit(1000.0)
        assert main_window.zoom_label.text() == "Zoom: 1000%"

    def test_rapid_zoom_changes(self, main_window: InkMainWindow) -> None:
        """Test zoom status handles rapid consecutive updates.

        Multiple quick zoom changes should each update correctly.
        """
        for zoom in [50.0, 75.0, 100.0, 125.0, 150.0]:
            main_window.schematic_canvas.zoom_changed.emit(zoom)

        # Final value should be displayed
        assert main_window.zoom_label.text() == "Zoom: 150%"
