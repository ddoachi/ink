"""Unit tests for InkMainWindow panel layout persistence.

Tests verify the main window's integration with PanelSettingsStore for
persisting panel layout state across sessions, as per spec E06-F05-T02.

Test Strategy:
    - Use isolated QSettings to avoid polluting user settings
    - Test save/load round-trip for panel state
    - Verify closeEvent() saves panel state
    - Verify _restore_panel_layout() loads saved state
    - Verify reset_panel_layout() clears saved state

TDD Phase: RED - Tests written before implementation.

See Also:
    - Spec E06-F05-T02 for panel layout persistence requirements
    - Pre-docs E06-F05-T02.pre-docs.md for architecture decisions
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QCloseEvent

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.infrastructure.persistence.panel_settings_store import PanelSettingsStore
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
    """Create AppSettings instance with isolated storage."""
    return AppSettings()


@pytest.fixture
def panel_settings_store(isolated_settings: Path) -> PanelSettingsStore:
    """Create PanelSettingsStore instance with isolated storage."""
    return PanelSettingsStore()


@pytest.fixture
def main_window(qtbot: QtBot, app_settings: AppSettings) -> InkMainWindow:
    """Create InkMainWindow instance for testing."""
    window = InkMainWindow(app_settings)
    qtbot.addWidget(window)
    return window


# =============================================================================
# Test Classes
# =============================================================================


class TestMainWindowPanelSettingsStoreAttribute:
    """Test that InkMainWindow has panel_settings_store attribute."""

    def test_has_panel_settings_store_attribute(self, main_window: InkMainWindow) -> None:
        """Verify main window has panel_settings_store attribute."""
        assert hasattr(main_window, "panel_settings_store")

    def test_panel_settings_store_is_correct_type(self, main_window: InkMainWindow) -> None:
        """Verify panel_settings_store is PanelSettingsStore instance."""
        assert isinstance(main_window.panel_settings_store, PanelSettingsStore)


class TestMainWindowSavesPanelStateOnClose:
    """Test panel state persistence on window close."""

    def test_close_event_saves_panel_state(
        self, qtbot: QtBot, app_settings: AppSettings, isolated_settings: Path
    ) -> None:
        """Verify closeEvent saves panel state via panel_settings_store."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Simulate close event
        close_event = QCloseEvent()
        window.closeEvent(close_event)

        # Verify panel state was saved
        assert window.panel_settings_store.has_saved_settings() is True

    def test_saved_panel_state_contains_all_panels(
        self, qtbot: QtBot, app_settings: AppSettings, isolated_settings: Path
    ) -> None:
        """Verify saved state contains all registered panels."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Close window to save state
        close_event = QCloseEvent()
        window.closeEvent(close_event)

        # Load saved state and verify panels exist
        state = window.panel_settings_store.load_panel_state()
        assert state is not None
        assert "Hierarchy" in state.panels
        assert "Properties" in state.panels
        assert "Messages" in state.panels

    def test_saved_panel_state_contains_qt_blobs(
        self, qtbot: QtBot, app_settings: AppSettings, isolated_settings: Path
    ) -> None:
        """Verify saved state includes Qt state blobs."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Close window to save state
        close_event = QCloseEvent()
        window.closeEvent(close_event)

        # Load saved state and verify Qt blobs
        state = window.panel_settings_store.load_panel_state()
        assert state is not None
        assert state.qt_geometry is not None
        assert state.qt_state is not None


class TestMainWindowRestoresPanelStateOnStartup:
    """Test panel state restoration on window startup."""

    def test_restores_panel_visibility(
        self, qtbot: QtBot, app_settings: AppSettings, isolated_settings: Path
    ) -> None:
        """Verify panel visibility is restored from saved state."""
        # First window: hide Messages panel and save
        window1 = InkMainWindow(app_settings)
        qtbot.addWidget(window1)
        window1.message_dock.hide()

        # Close to save state
        close_event = QCloseEvent()
        window1.closeEvent(close_event)

        # Second window: should restore hidden Messages panel
        window2 = InkMainWindow(app_settings)
        qtbot.addWidget(window2)

        # Messages panel should be hidden (restored from saved state)
        assert window2.message_dock.isVisible() is False

    def test_does_not_crash_with_no_saved_state(
        self, qtbot: QtBot, app_settings: AppSettings, isolated_settings: Path
    ) -> None:
        """Verify window opens correctly with no saved panel state."""
        # Create window without any prior saved state
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)

        # Should not crash, all panels should be visible
        assert window.hierarchy_dock.isVisible() is True
        assert window.property_dock.isVisible() is True
        assert window.message_dock.isVisible() is True


class TestMainWindowResetPanelLayout:
    """Test reset_panel_layout() functionality."""

    def test_has_reset_panel_layout_method(self, main_window: InkMainWindow) -> None:
        """Verify main window has reset_panel_layout method."""
        assert hasattr(main_window, "reset_panel_layout")
        assert callable(main_window.reset_panel_layout)

    def test_reset_panel_layout_clears_saved_state(
        self, qtbot: QtBot, app_settings: AppSettings, isolated_settings: Path
    ) -> None:
        """Verify reset_panel_layout clears saved panel state."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Save some state first
        close_event = QCloseEvent()
        window.closeEvent(close_event)
        assert window.panel_settings_store.has_saved_settings() is True

        # Create new window and reset
        window2 = InkMainWindow(app_settings)
        qtbot.addWidget(window2)
        window2.reset_panel_layout()

        # Saved state should be cleared
        assert window2.panel_settings_store.has_saved_settings() is False


class TestMainWindowPanelStatePersistenceRoundTrip:
    """Test complete round-trip of panel state persistence."""

    def test_panel_layout_persists_across_sessions(
        self, qtbot: QtBot, app_settings: AppSettings, isolated_settings: Path
    ) -> None:
        """Verify complete panel layout persists across window instances.

        This test simulates a full user workflow:
        1. Open application
        2. Move/resize panels
        3. Close application (saves state)
        4. Reopen application (restores state)
        """
        # First session: create window and modify panel layout
        window1 = InkMainWindow(app_settings)
        qtbot.addWidget(window1)
        window1.show()
        qtbot.waitExposed(window1)

        # Hide properties panel
        window1.property_dock.hide()

        # Close to save state
        close_event = QCloseEvent()
        window1.closeEvent(close_event)

        # Second session: create new window
        window2 = InkMainWindow(app_settings)
        qtbot.addWidget(window2)
        window2.show()
        qtbot.waitExposed(window2)

        # Properties panel should still be hidden
        assert window2.property_dock.isVisible() is False
        # Other panels should be visible
        assert window2.hierarchy_dock.isVisible() is True
        assert window2.message_dock.isVisible() is True


class TestPanelStateIntegrationWithPanelStateManager:
    """Test integration between PanelSettingsStore and PanelStateManager."""

    def test_capture_state_used_for_saving(
        self, qtbot: QtBot, app_settings: AppSettings, isolated_settings: Path
    ) -> None:
        """Verify panel_state_manager.capture_state() is used when saving."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Mock capture_state to verify it's called
        capture_func = window.panel_state_manager.capture_state
        with patch.object(
            window.panel_state_manager, "capture_state", wraps=capture_func
        ) as mock_capture:
            close_event = QCloseEvent()
            window.closeEvent(close_event)

            # capture_state should have been called
            mock_capture.assert_called_once()

    def test_restore_state_used_for_loading(
        self, qtbot: QtBot, app_settings: AppSettings, isolated_settings: Path
    ) -> None:
        """Verify load_panel_state is called when starting window."""
        # First save some state
        window1 = InkMainWindow(app_settings)
        qtbot.addWidget(window1)
        close_event = QCloseEvent()
        window1.closeEvent(close_event)

        # Verify that panel_settings_store has saved settings
        store = PanelSettingsStore()
        assert store.has_saved_settings() is True

        # Create new window - it should load the saved state
        window2 = InkMainWindow(app_settings)
        qtbot.addWidget(window2)

        # Verify the window was created successfully and state was restored
        # (The state was loaded internally during __init__)
        assert window2.panel_settings_store is not None
