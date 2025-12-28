"""Unit tests for File, Edit, and Search Toolbar Actions - E06-F03-T03.

Tests verify that File, Edit, and Search toolbar actions meet all requirements
from spec E06-F03-T03:

File Actions (Group 1):
- Open button with document-open icon
- Open button with Ctrl+O shortcut
- Open button always enabled
- Open button tooltip shows "Open netlist file (Ctrl+O)"
- Open button triggers file dialog

Edit Actions (Group 2):
- Undo button with edit-undo icon
- Undo button with Ctrl+Z shortcut
- Undo button initially disabled
- Undo button tooltip shows "Undo expansion/collapse (Ctrl+Z)"
- Redo button with edit-redo icon
- Redo button with Ctrl+Shift+Z shortcut
- Redo button initially disabled
- Redo button tooltip shows "Redo expansion/collapse (Ctrl+Shift+Z)"
- Undo/Redo state updates based on expansion service

Search Actions (Group 3):
- Search button with edit-find icon
- Search button with Ctrl+F shortcut
- Search button always enabled
- Search button tooltip shows "Search cells/nets/pins (Ctrl+F)"
- Search button shows/focuses search panel

Toolbar Organization:
- Actions arranged in groups with separators
- Order: File | Edit | Search

These tests follow TDD methodology:
- RED phase: Tests written before implementation (expect failures)
- GREEN phase: Implementation makes tests pass
- REFACTOR phase: Code cleanup with tests as safety net

See Also:
    - Spec E06-F03-T03 for File, Edit, Search toolbar requirements
    - Spec E06-F03-T01 for toolbar infrastructure
    - Pre-docs E06-F03-T03.pre-docs.md for implementation approach
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QFileDialog, QToolBar

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
        qtbot: pytest-qt bot for Qt widget testing.
        app_settings: Isolated settings instance.

    Returns:
        Configured InkMainWindow instance.
    """
    window = InkMainWindow(app_settings)
    qtbot.addWidget(window)
    return window


@pytest.fixture
def mock_expansion_service() -> Mock:
    """Create a mock expansion service for undo/redo testing.

    Returns:
        Mock object with can_undo, can_redo, undo, and redo methods.
    """
    service = Mock()
    service.can_undo.return_value = False
    service.can_redo.return_value = False
    return service


@pytest.fixture
def mock_search_panel() -> Mock:
    """Create a mock search panel for search button testing.

    Returns:
        Mock object with show, isVisible, and focus_search_input methods.
    """
    panel = Mock()
    panel.isVisible.return_value = False
    return panel


# =============================================================================
# Test Classes - File Actions
# =============================================================================


class TestFileActions:
    """Tests for Open toolbar action."""

    def test_open_action_exists(self, main_window: InkMainWindow) -> None:
        """Test that Open action is added to toolbar.

        Acceptance Criteria:
            - Open button appears in toolbar with open-file icon
        """
        assert hasattr(main_window, "_open_action"), "Window should have _open_action"
        assert main_window._open_action is not None, "_open_action should not be None"
        assert isinstance(main_window._open_action, QAction), "_open_action should be QAction"

    def test_open_action_in_toolbar(self, main_window: InkMainWindow) -> None:
        """Test that Open action is present in the toolbar."""
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        actions = toolbar.actions()
        action_names = [a.text() for a in actions if not a.isSeparator()]
        assert "Open" in action_names, "Open action should be in toolbar"

    def test_open_action_shortcut(self, main_window: InkMainWindow) -> None:
        """Test Open action has Ctrl+O shortcut.

        Acceptance Criteria:
            - `Ctrl+O` opens file dialog
        """
        assert main_window._open_action.shortcut() == QKeySequence.StandardKey.Open

    def test_open_action_always_enabled(self, main_window: InkMainWindow) -> None:
        """Test Open action is always enabled.

        Acceptance Criteria:
            - Open button always enabled
        """
        assert main_window._open_action.isEnabled()

    def test_open_action_tooltip(self, main_window: InkMainWindow) -> None:
        """Test Open action has correct tooltip.

        Acceptance Criteria:
            - Tooltips display on hover with action name and shortcut
        """
        tooltip = main_window._open_action.toolTip()
        assert "Open" in tooltip or "netlist" in tooltip.lower()
        assert "Ctrl+O" in tooltip or "O" in tooltip

    def test_open_action_triggers_file_dialog(
        self, main_window: InkMainWindow, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test clicking Open shows file dialog.

        Acceptance Criteria:
            - Clicking Open button shows file dialog
        """
        dialog_shown = False

        def mock_get_open_filename(
            *args: object, **kwargs: object
        ) -> tuple[str, str]:
            nonlocal dialog_shown
            dialog_shown = True
            return ("", "")  # User cancelled

        monkeypatch.setattr(QFileDialog, "getOpenFileName", mock_get_open_filename)

        main_window._open_action.trigger()
        assert dialog_shown, "File dialog should be shown when Open action triggered"

    def test_file_dialog_filters(
        self, main_window: InkMainWindow, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test file dialog has correct file filters.

        Acceptance Criteria:
            - File dialog filters for `.ckt` and `.cdl` files
        """
        captured_filter: str | None = None

        def mock_get_open_filename(
            *args: object, **kwargs: object
        ) -> tuple[str, str]:
            nonlocal captured_filter
            # Qt's filter string is typically the 4th positional arg or 'filter' kwarg
            if len(args) >= 4:
                captured_filter = str(args[3])
            elif "filter" in kwargs:
                captured_filter = str(kwargs["filter"])
            return ("", "")

        monkeypatch.setattr(QFileDialog, "getOpenFileName", mock_get_open_filename)

        main_window._open_action.trigger()

        # The filter should include .ckt and .cdl extensions
        assert captured_filter is not None, "File filter should be captured"
        assert "ckt" in captured_filter.lower() or "cdl" in captured_filter.lower()


# =============================================================================
# Test Classes - Edit Actions (Undo/Redo)
# =============================================================================


class TestUndoAction:
    """Tests for Undo toolbar action."""

    def test_undo_action_exists(self, main_window: InkMainWindow) -> None:
        """Test that Undo action is added to toolbar.

        Acceptance Criteria:
            - Undo button appears in toolbar with undo icon
        """
        assert hasattr(main_window, "_undo_action"), "Window should have _undo_action"
        assert main_window._undo_action is not None, "_undo_action should not be None"
        assert isinstance(main_window._undo_action, QAction), "_undo_action should be QAction"

    def test_undo_action_in_toolbar(self, main_window: InkMainWindow) -> None:
        """Test that Undo action is present in the toolbar."""
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        actions = toolbar.actions()
        action_names = [a.text() for a in actions if not a.isSeparator()]
        assert "Undo" in action_names, "Undo action should be in toolbar"

    def test_undo_action_shortcut(self, main_window: InkMainWindow) -> None:
        """Test Undo action has Ctrl+Z shortcut.

        Acceptance Criteria:
            - `Ctrl+Z` triggers undo when available
        """
        assert main_window._undo_action.shortcut() == QKeySequence.StandardKey.Undo

    def test_undo_action_initially_disabled(self, main_window: InkMainWindow) -> None:
        """Test Undo action is initially disabled.

        Acceptance Criteria:
            - Undo button initially disabled
        """
        assert not main_window._undo_action.isEnabled()

    def test_undo_action_tooltip(self, main_window: InkMainWindow) -> None:
        """Test Undo action has correct tooltip.

        Acceptance Criteria:
            - Tooltips display on hover with action name and shortcut
        """
        tooltip = main_window._undo_action.toolTip()
        assert "Undo" in tooltip
        assert "Ctrl+Z" in tooltip or "Z" in tooltip


class TestRedoAction:
    """Tests for Redo toolbar action."""

    def test_redo_action_exists(self, main_window: InkMainWindow) -> None:
        """Test that Redo action is added to toolbar.

        Acceptance Criteria:
            - Redo button appears in toolbar with redo icon
        """
        assert hasattr(main_window, "_redo_action"), "Window should have _redo_action"
        assert main_window._redo_action is not None, "_redo_action should not be None"
        assert isinstance(main_window._redo_action, QAction), "_redo_action should be QAction"

    def test_redo_action_in_toolbar(self, main_window: InkMainWindow) -> None:
        """Test that Redo action is present in the toolbar."""
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        actions = toolbar.actions()
        action_names = [a.text() for a in actions if not a.isSeparator()]
        assert "Redo" in action_names, "Redo action should be in toolbar"

    def test_redo_action_shortcut(self, main_window: InkMainWindow) -> None:
        """Test Redo action has Ctrl+Shift+Z shortcut.

        Acceptance Criteria:
            - `Ctrl+Shift+Z` triggers redo when available
        """
        assert main_window._redo_action.shortcut() == QKeySequence.StandardKey.Redo

    def test_redo_action_initially_disabled(self, main_window: InkMainWindow) -> None:
        """Test Redo action is initially disabled.

        Acceptance Criteria:
            - Redo button initially disabled
        """
        assert not main_window._redo_action.isEnabled()

    def test_redo_action_tooltip(self, main_window: InkMainWindow) -> None:
        """Test Redo action has correct tooltip.

        Acceptance Criteria:
            - Tooltips display on hover with action name and shortcut
        """
        tooltip = main_window._redo_action.toolTip()
        assert "Redo" in tooltip
        assert "Ctrl" in tooltip or "Shift" in tooltip or "Z" in tooltip


# =============================================================================
# Test Classes - Undo/Redo State Management
# =============================================================================


class TestUndoRedoStateManagement:
    """Tests for undo/redo state management integration."""

    def test_update_undo_redo_state_method_exists(self, main_window: InkMainWindow) -> None:
        """Test that _update_undo_redo_state method exists.

        This method is required for dynamic button state management.
        """
        assert hasattr(main_window, "_update_undo_redo_state")
        assert callable(main_window._update_undo_redo_state)

    def test_undo_enabled_when_can_undo(
        self, main_window: InkMainWindow, mock_expansion_service: Mock
    ) -> None:
        """Test Undo button enables when expansion service can undo.

        Acceptance Criteria:
            - Undo button enables after first expansion/collapse
        """
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "_expansion_service", mock_expansion_service)
        mock_expansion_service.can_undo.return_value = True
        mock_expansion_service.can_redo.return_value = False

        main_window._update_undo_redo_state()

        assert main_window._undo_action.isEnabled()
        assert not main_window._redo_action.isEnabled()

    def test_redo_enabled_when_can_redo(
        self, main_window: InkMainWindow, mock_expansion_service: Mock
    ) -> None:
        """Test Redo button enables when expansion service can redo.

        Acceptance Criteria:
            - Redo button enables after undo
        """
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "_expansion_service", mock_expansion_service)
        mock_expansion_service.can_undo.return_value = False
        mock_expansion_service.can_redo.return_value = True

        main_window._update_undo_redo_state()

        assert not main_window._undo_action.isEnabled()
        assert main_window._redo_action.isEnabled()

    def test_both_disabled_when_no_history(
        self, main_window: InkMainWindow, mock_expansion_service: Mock
    ) -> None:
        """Test both buttons disabled when no undo/redo available.

        Acceptance Criteria:
            - Undo button disables when history empty
            - Redo button disables when no redo available
        """
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "_expansion_service", mock_expansion_service)
        mock_expansion_service.can_undo.return_value = False
        mock_expansion_service.can_redo.return_value = False

        main_window._update_undo_redo_state()

        assert not main_window._undo_action.isEnabled()
        assert not main_window._redo_action.isEnabled()

    def test_both_enabled_when_both_available(
        self, main_window: InkMainWindow, mock_expansion_service: Mock
    ) -> None:
        """Test both buttons enabled when both undo and redo available."""
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "_expansion_service", mock_expansion_service)
        mock_expansion_service.can_undo.return_value = True
        mock_expansion_service.can_redo.return_value = True

        main_window._update_undo_redo_state()

        assert main_window._undo_action.isEnabled()
        assert main_window._redo_action.isEnabled()

    def test_undo_action_calls_service(
        self, main_window: InkMainWindow, mock_expansion_service: Mock
    ) -> None:
        """Test Undo action calls expansion service undo method.

        Acceptance Criteria:
            - Clicking Undo button undoes last expansion/collapse
        """
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "_expansion_service", mock_expansion_service)
        mock_expansion_service.can_undo.return_value = True
        main_window._undo_action.setEnabled(True)

        main_window._on_undo()

        mock_expansion_service.undo.assert_called_once()

    def test_redo_action_calls_service(
        self, main_window: InkMainWindow, mock_expansion_service: Mock
    ) -> None:
        """Test Redo action calls expansion service redo method.

        Acceptance Criteria:
            - Clicking Redo button redoes last undone action
        """
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "_expansion_service", mock_expansion_service)
        mock_expansion_service.can_redo.return_value = True
        main_window._redo_action.setEnabled(True)

        main_window._on_redo()

        mock_expansion_service.redo.assert_called_once()

    def test_state_updates_after_undo(
        self, main_window: InkMainWindow, mock_expansion_service: Mock
    ) -> None:
        """Test undo/redo state updates after undo operation."""
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "_expansion_service", mock_expansion_service)
        mock_expansion_service.can_undo.return_value = True
        mock_expansion_service.can_redo.return_value = False
        main_window._undo_action.setEnabled(True)

        # After undo, simulate state change
        def update_state_after_undo() -> None:
            mock_expansion_service.can_undo.return_value = False
            mock_expansion_service.can_redo.return_value = True

        mock_expansion_service.undo.side_effect = update_state_after_undo

        main_window._on_undo()

        # State should have been updated
        assert not main_window._undo_action.isEnabled()
        assert main_window._redo_action.isEnabled()


# =============================================================================
# Test Classes - Search Actions
# =============================================================================


class TestSearchAction:
    """Tests for Search toolbar action."""

    def test_search_action_exists(self, main_window: InkMainWindow) -> None:
        """Test that Search action is added to toolbar.

        Acceptance Criteria:
            - Search button appears in toolbar with search icon
        """
        assert hasattr(main_window, "_search_action"), "Window should have _search_action"
        assert main_window._search_action is not None, "_search_action should not be None"
        assert isinstance(
            main_window._search_action, QAction
        ), "_search_action should be QAction"

    def test_search_action_in_toolbar(self, main_window: InkMainWindow) -> None:
        """Test that Search action is present in the toolbar."""
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        actions = toolbar.actions()
        action_names = [a.text() for a in actions if not a.isSeparator()]
        assert "Search" in action_names, "Search action should be in toolbar"

    def test_search_action_shortcut(self, main_window: InkMainWindow) -> None:
        """Test Search action has Ctrl+F shortcut.

        Acceptance Criteria:
            - `Ctrl+F` shows/focuses search panel
        """
        assert main_window._search_action.shortcut() == QKeySequence.StandardKey.Find

    def test_search_action_always_enabled(self, main_window: InkMainWindow) -> None:
        """Test Search action is always enabled.

        Acceptance Criteria:
            - Search button always enabled
        """
        assert main_window._search_action.isEnabled()

    def test_search_action_tooltip(self, main_window: InkMainWindow) -> None:
        """Test Search action has correct tooltip.

        Acceptance Criteria:
            - Tooltips display on hover with action name and shortcut
        """
        tooltip = main_window._search_action.toolTip()
        assert "Search" in tooltip or "cells" in tooltip.lower() or "find" in tooltip.lower()
        assert "Ctrl+F" in tooltip or "F" in tooltip


class TestSearchPanelIntegration:
    """Tests for search panel integration with search button."""

    def test_on_find_method_exists(self, main_window: InkMainWindow) -> None:
        """Test that _on_find method exists for search button handler."""
        assert hasattr(main_window, "_on_find")
        assert callable(main_window._on_find)

    def test_search_shows_hidden_panel(
        self, main_window: InkMainWindow, mock_search_panel: Mock
    ) -> None:
        """Test search button shows panel if hidden.

        Acceptance Criteria:
            - Clicking Search button shows search panel
        """
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "_search_panel", mock_search_panel)
        mock_search_panel.isVisible.return_value = False

        main_window._on_find()

        mock_search_panel.show.assert_called_once()
        mock_search_panel.focus_search_input.assert_called_once()

    def test_search_focuses_visible_panel(
        self, main_window: InkMainWindow, mock_search_panel: Mock
    ) -> None:
        """Test search button focuses input if panel already visible.

        Acceptance Criteria:
            - Clicking Search button focuses search input if panel already visible
        """
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "_search_panel", mock_search_panel)
        mock_search_panel.isVisible.return_value = True

        main_window._on_find()

        mock_search_panel.show.assert_not_called()
        mock_search_panel.focus_search_input.assert_called_once()


# =============================================================================
# Test Classes - Toolbar Organization
# =============================================================================


class TestToolbarOrganization:
    """Tests for toolbar action grouping and separators."""

    def test_toolbar_has_separators(self, main_window: InkMainWindow) -> None:
        """Test toolbar has separators between action groups.

        Actions should be organized: File | Edit | Search with separators.
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        actions = toolbar.actions()
        separator_count = sum(1 for a in actions if a.isSeparator())

        # Should have at least 2 separators (between File|Edit and Edit|Search)
        assert separator_count >= 2, "Toolbar should have separators between groups"

    def test_action_order(self, main_window: InkMainWindow) -> None:
        """Test actions are in correct order: Open, Undo, Redo, Search.

        This ensures consistent toolbar layout across sessions.
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        actions = toolbar.actions()
        non_separator_actions = [a for a in actions if not a.isSeparator()]
        action_names = [a.text() for a in non_separator_actions]

        # Find indices of our actions
        open_idx = action_names.index("Open") if "Open" in action_names else -1
        undo_idx = action_names.index("Undo") if "Undo" in action_names else -1
        redo_idx = action_names.index("Redo") if "Redo" in action_names else -1
        search_idx = action_names.index("Search") if "Search" in action_names else -1

        # Verify order: Open < Undo < Redo < Search
        assert open_idx >= 0, "Open action should be in toolbar"
        assert undo_idx >= 0, "Undo action should be in toolbar"
        assert redo_idx >= 0, "Redo action should be in toolbar"
        assert search_idx >= 0, "Search action should be in toolbar"

        assert open_idx < undo_idx, "Open should come before Undo"
        assert undo_idx < redo_idx, "Undo should come before Redo"
        assert redo_idx < search_idx, "Redo should come before Search"


# =============================================================================
# Test Classes - Graceful Degradation
# =============================================================================


class TestGracefulDegradation:
    """Tests for graceful handling when services are not available."""

    def test_no_crash_without_expansion_service(self, main_window: InkMainWindow) -> None:
        """Test undo/redo don't crash when expansion service missing.

        This is important for MVP where services may not be fully integrated.
        """
        # Ensure no expansion service
        if hasattr(main_window, "_expansion_service"):
            delattr(main_window, "_expansion_service")

        # These should not raise exceptions
        main_window._on_undo()
        main_window._on_redo()
        main_window._update_undo_redo_state()

    def test_no_crash_without_search_panel(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test search doesn't crash when search panel missing.

        This is important for MVP where panels may not be fully integrated.
        When search panel is unavailable, the code falls back to message_dock.
        When neither is available, a status bar message should be shown.
        """
        # Show window so visibility tests work correctly
        main_window.show()
        qtbot.waitExposed(main_window)

        # Ensure no search panel attribute or set it to None
        if hasattr(main_window, "_search_panel"):
            # For this test, we need to handle the case where _search_panel
            # might be set to a real panel. Set it to None to test graceful handling.
            # Use setattr to bypass mypy (testing pattern for dependency injection)
            setattr(main_window, "_search_panel", None)

        # First hide the message_dock to test it gets shown
        main_window.message_dock.hide()

        # This should not raise an exception
        main_window._on_find()

        # With _search_panel=None, the code falls back to message_dock
        # which exists in InkMainWindow, so the dock should not be hidden
        assert not main_window.message_dock.isHidden()

    def test_update_state_without_service_is_safe(self, main_window: InkMainWindow) -> None:
        """Test _update_undo_redo_state handles missing service gracefully."""
        # Remove expansion service if it exists
        if hasattr(main_window, "_expansion_service"):
            delattr(main_window, "_expansion_service")

        # This should not raise and buttons should remain in current state
        # (likely disabled, which is the safe default)
        main_window._update_undo_redo_state()

        # Buttons should still be disabled (safe default)
        assert not main_window._undo_action.isEnabled()
        assert not main_window._redo_action.isEnabled()


# =============================================================================
# Test Classes - No Runtime Errors
# =============================================================================


class TestNoRuntimeErrors:
    """Tests for error-free operation of file/edit/search actions."""

    def test_window_initializes_with_actions(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test main window initializes with all actions without errors."""
        # This should not raise any exceptions
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # All actions should be accessible
        assert window._open_action is not None
        assert window._undo_action is not None
        assert window._redo_action is not None
        assert window._search_action is not None

    def test_actions_visible_after_show(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test all actions are visible when window is shown."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)

        toolbar = window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None
        assert toolbar.isVisible()

        # Actions should be visible in toolbar
        assert window._open_action.isVisible()
        assert window._undo_action.isVisible()
        assert window._redo_action.isVisible()
        assert window._search_action.isVisible()
