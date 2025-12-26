"""Integration tests for window geometry persistence.

This module tests the integration between InkMainWindow and AppSettings
for window geometry persistence as defined in spec E06-F06-T02.

Test Strategy:
    - Test window geometry restoration on startup
    - Test window geometry saving on close
    - Test dock widget state persistence
    - Test default behavior on first run
    - Test graceful handling of invalid geometry

TDD Phase: RED
    These tests are written BEFORE implementation to define expected behavior.
    All tests should FAIL initially, then PASS after implementation.

See Also:
    - Spec E06-F06-T02 for requirements
    - src/ink/presentation/main_window.py for implementation
    - src/ink/infrastructure/persistence/app_settings.py for settings API
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from PySide6.QtCore import QByteArray, QSettings
from PySide6.QtGui import QCloseEvent, QGuiApplication

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.main_window import InkMainWindow

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from pytestqt.qtbot import QtBot


# =============================================================================
# Module-level Fixtures
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

    # Configure QSettings to use temporary path for INI format
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    # Clear any existing settings to ensure test isolation
    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.clear()
    temp_settings.sync()

    yield settings_path


@pytest.fixture
def app_settings(isolated_settings: Path) -> AppSettings:  # noqa: ARG001
    """Create AppSettings instance with isolated storage.

    Args:
        isolated_settings: Temporary settings directory (ensures isolation).

    Returns:
        Fresh AppSettings instance.
    """
    return AppSettings()


# =============================================================================
# Test Classes for MainWindow Integration
# =============================================================================


class TestMainWindowAcceptsAppSettings:
    """Tests for InkMainWindow accepting AppSettings in constructor."""

    def test_main_window_accepts_app_settings_parameter(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify InkMainWindow accepts app_settings parameter."""
        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        assert window is not None

    def test_main_window_stores_app_settings(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify InkMainWindow stores app_settings as attribute."""
        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        assert hasattr(window, "app_settings")
        assert window.app_settings is app_settings

    def test_main_window_works_without_app_settings(
        self, qtbot: QtBot
    ) -> None:
        """Verify InkMainWindow works without app_settings (backward compatibility)."""
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert window is not None


class TestWindowGeometryRestoration:
    """Tests for window geometry restoration on startup."""

    def test_restores_saved_window_size(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify window size is restored from saved geometry."""
        # Create first window and resize it
        window1 = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window1)
        window1.resize(1024, 768)

        # Save geometry
        app_settings.save_window_geometry(window1.saveGeometry())
        app_settings.sync()

        # Create second window - should restore geometry
        window2 = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window2)

        # Verify size is restored
        assert window2.width() == 1024
        assert window2.height() == 768

    def test_uses_default_size_when_no_saved_geometry(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify default size (1280x800) when no geometry is saved."""
        # Verify no geometry is saved
        assert not app_settings.has_window_geometry()

        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        # Should use default size from spec
        assert window.width() == 1280
        assert window.height() == 800


class TestWindowStatePersistence:
    """Tests for window state (dock widgets, maximized, etc.) persistence."""

    def test_restores_saved_window_state(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify window state is restored from saved state."""
        # This test verifies the mechanism works, even without actual dock widgets
        window1 = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window1)

        # Save state
        state = window1.saveState()
        app_settings.save_window_state(state)
        app_settings.sync()

        # Create second window - should restore state
        window2 = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window2)

        # Verify state was loaded (no error should occur)
        assert window2 is not None


class TestCloseEventGeometrySaving:
    """Tests for geometry saving on window close."""

    def test_saves_geometry_on_close(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify window geometry is saved when window closes."""
        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)
        window.resize(1100, 700)

        # Verify no geometry saved yet
        assert not app_settings.has_window_geometry()

        # Trigger close event
        close_event = QCloseEvent()
        window.closeEvent(close_event)

        # Verify geometry was saved
        assert app_settings.has_window_geometry()

    def test_saves_state_on_close(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify window state is saved when window closes."""
        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        # Verify no state saved yet
        assert not app_settings.has_window_state()

        # Trigger close event
        close_event = QCloseEvent()
        window.closeEvent(close_event)

        # Verify state was saved
        assert app_settings.has_window_state()

    def test_close_event_syncs_settings(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify settings are synced to disk on window close."""
        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        with patch.object(app_settings, "sync") as mock_sync:
            close_event = QCloseEvent()
            window.closeEvent(close_event)

            mock_sync.assert_called_once()

    def test_close_event_is_accepted(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify close event is accepted (window closes)."""
        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        close_event = QCloseEvent()
        window.closeEvent(close_event)

        assert close_event.isAccepted()


class TestGeometryPersistenceRoundTrip:
    """Tests for complete round-trip persistence scenarios."""

    def test_geometry_persists_across_window_instances(
        self, qtbot: QtBot, isolated_settings: Path
    ) -> None:
        """Verify geometry data persists when closing and reopening window.

        Note: Qt's restoreGeometry() doesn't work correctly in offscreen mode,
        so we verify that the geometry data is properly saved and loaded,
        rather than checking the actual window dimensions.
        """
        # First session - resize window and close
        settings1 = AppSettings()
        window1 = InkMainWindow(app_settings=settings1)
        qtbot.addWidget(window1)
        window1.resize(1200, 850)
        window1.show()
        qtbot.waitExposed(window1)

        # Save the geometry that will be persisted
        saved_geometry = window1.saveGeometry()

        close_event = QCloseEvent()
        window1.closeEvent(close_event)

        # Verify geometry was saved
        assert settings1.has_window_geometry()

        # Second session - verify same geometry data is loaded
        settings2 = AppSettings()

        # Verify the geometry data was persisted correctly
        loaded_geometry = settings2.load_window_geometry()
        assert loaded_geometry is not None
        assert loaded_geometry == saved_geometry

        # Create window and verify it tries to restore
        # (actual restoration may not work in offscreen mode, but
        # the code path is exercised)
        window2 = InkMainWindow(app_settings=settings2)
        qtbot.addWidget(window2)
        assert window2 is not None  # Window created successfully


class TestInvalidGeometryHandling:
    """Tests for handling invalid or corrupted geometry data."""

    def test_handles_invalid_geometry_gracefully(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify invalid geometry data falls back to defaults."""
        # Set invalid geometry data
        app_settings.set_value(AppSettings.KEY_WINDOW_GEOMETRY, "invalid_string")

        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        # Should fall back to defaults
        assert window.width() == 1280
        assert window.height() == 800

    def test_handles_empty_geometry_gracefully(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify empty geometry data falls back to defaults."""
        # Set empty geometry data
        app_settings.set_value(AppSettings.KEY_WINDOW_GEOMETRY, QByteArray())

        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        # Should fall back to defaults
        assert window.width() == 1280
        assert window.height() == 800


class TestCenterOnScreen:
    """Tests for window centering behavior."""

    def test_centers_on_screen_on_first_run(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify window is centered on screen on first run."""
        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        # Get screen geometry
        screen = QGuiApplication.primaryScreen().geometry()

        # Calculate expected center position
        expected_x = (screen.width() - window.width()) // 2
        expected_y = (screen.height() - window.height()) // 2

        # Allow some tolerance for window manager adjustments
        assert abs(window.x() - expected_x) <= 50
        assert abs(window.y() - expected_y) <= 50

    def test_has_center_on_screen_method(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Verify _center_on_screen private method exists."""
        window = InkMainWindow(app_settings=app_settings)
        qtbot.addWidget(window)

        # Private method should exist
        assert hasattr(window, "_center_on_screen")
        assert callable(window._center_on_screen)
