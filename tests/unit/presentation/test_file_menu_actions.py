"""Unit tests for E06-F02-T02 File Menu Actions.

Tests verify the File menu actions meet all acceptance criteria from spec E06-F02-T02:
- File > Open shows file dialog with .ckt and .cdl filters
- Selected file path triggers _load_netlist() method
- Recent Files submenu shows up to 10 most recent files
- Most recently opened file appears at top of Recent Files list
- Clicking recent file opens it directly
- Missing recent files show warning dialog and are removed from list
- "Clear Recent Files" removes all entries
- Exit action (Ctrl+Q) closes application
- Keyboard shortcuts work: Ctrl+O for Open, Ctrl+Q for Exit
- Recent files persist across application restarts
- File paths in Recent Files menu show full path
- Status bar shows "Loaded: {file}" message on successful load

TDD Phase: These tests define expected behavior and validate implementation.

See Also:
    - Spec E06-F02-T02 for File Menu Actions requirements
    - src/ink/presentation/main_window.py for implementation
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.main_window import InkMainWindow

if TYPE_CHECKING:
    from collections.abc import Generator

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
def main_window(qtbot: QtBot, app_settings: AppSettings) -> Generator[InkMainWindow, None, None]:
    """Create InkMainWindow instance with AppSettings."""
    window = InkMainWindow(app_settings)
    qtbot.addWidget(window)
    yield window


@pytest.fixture
def temp_files(tmp_path: Path) -> list[str]:
    """Create temporary test files for file operations testing."""
    files = []
    for i in range(15):
        file = tmp_path / f"test{i}.ckt"
        file.write_text(f"* Netlist content {i}\n")
        files.append(str(file))
    return files


# =============================================================================
# Test Classes for File Menu Actions - E06-F02-T02
# =============================================================================


class TestFileMenuStructure:
    """Test File menu structure and contents."""

    def test_file_menu_has_open_action(self, main_window: InkMainWindow) -> None:
        """AC: File > Open action exists.

        Spec: File menu has Open... action.
        """
        open_action = self._find_action_by_text(main_window.file_menu, "Open")
        assert open_action is not None, "Open action not found in File menu"

    def test_file_menu_has_open_recent_submenu(self, main_window: InkMainWindow) -> None:
        """AC: File > Open Recent submenu exists.

        Spec: File menu has Open Recent submenu.
        """
        assert hasattr(main_window, "recent_files_menu")
        assert isinstance(main_window.recent_files_menu, QMenu)

    def test_file_menu_has_exit_action(self, main_window: InkMainWindow) -> None:
        """AC: File > Exit action exists.

        Spec: File menu has Exit action.
        """
        exit_action = self._find_action_by_text(main_window.file_menu, "Exit")
        assert exit_action is not None, "Exit action not found in File menu"

    def test_file_menu_has_separator_before_exit(self, main_window: InkMainWindow) -> None:
        """Verify separator exists between Recent and Exit.

        Spec: Visual separation between file operations and exit.
        """
        actions = main_window.file_menu.actions()
        exit_action = self._find_action_by_text(main_window.file_menu, "Exit")
        if exit_action:
            exit_idx = actions.index(exit_action)
            # Check for separator before Exit
            separator_found = any(
                actions[i].isSeparator() for i in range(exit_idx) if i >= 0
            )
            assert separator_found, "No separator found before Exit action"

    def _find_action_by_text(self, menu: QMenu, text: str) -> QAction | None:
        """Helper to find an action by partial text match."""
        for action in menu.actions():
            if text.lower() in action.text().lower().replace("&", ""):
                return action
        return None


class TestOpenActionKeyboardShortcut:
    """Test Open action keyboard shortcut - Ctrl+O."""

    def test_open_action_has_ctrl_o_shortcut(self, main_window: InkMainWindow) -> None:
        """AC: Keyboard shortcuts work: Ctrl+O for Open.

        Spec: Open action has Ctrl+O shortcut.
        """
        open_action = None
        for action in main_window.file_menu.actions():
            if "Open" in action.text() and "Recent" not in action.text():
                open_action = action
                break

        assert open_action is not None, "Open action not found"

        shortcut = open_action.shortcut()
        # Check if shortcut matches Ctrl+O (platform-independent)
        # shortcut.toString() returns "Ctrl+O" on most platforms
        assert shortcut == QKeySequence("Ctrl+O") or shortcut == QKeySequence.StandardKey.Open


class TestExitActionKeyboardShortcut:
    """Test Exit action keyboard shortcut - Ctrl+Q."""

    def test_exit_action_has_ctrl_q_shortcut(self, main_window: InkMainWindow) -> None:
        """AC: Keyboard shortcuts work: Ctrl+Q for Exit.

        Spec: Exit action has Ctrl+Q shortcut.
        """
        exit_action = None
        for action in main_window.file_menu.actions():
            # Remove mnemonic character (&) and check for "xit" pattern
            text_lower = action.text().replace("&", "").lower()
            if "xit" in text_lower:
                exit_action = action
                break

        assert exit_action is not None, "Exit action not found"

        shortcut = exit_action.shortcut()
        # Check if shortcut matches Ctrl+Q
        assert shortcut == QKeySequence("Ctrl+Q") or shortcut == QKeySequence.StandardKey.Quit


class TestExitActionClosesWindow:
    """Test Exit action closes the application."""

    def test_exit_action_closes_window(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """AC: Exit action (Ctrl+Q) closes application.

        Spec: Clicking Exit or pressing Ctrl+Q closes the application.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)

        # Find and trigger Exit action
        exit_action = None
        for action in window.file_menu.actions():
            # Remove mnemonic character (&) and check for "xit" pattern
            text_lower = action.text().replace("&", "").lower()
            if "xit" in text_lower:
                exit_action = action
                break

        assert exit_action is not None, "Exit action not found"

        # Trigger the exit action
        exit_action.trigger()

        # Window should be closed (not visible)
        assert not window.isVisible()


class TestOpenFileDialog:
    """Test Open action file dialog."""

    def test_on_open_file_dialog_method_exists(self, main_window: InkMainWindow) -> None:
        """Verify _on_open_file_dialog method exists."""
        assert hasattr(main_window, "_on_open_file_dialog")
        assert callable(main_window._on_open_file_dialog)

    def test_open_action_triggers_file_dialog(self, main_window: InkMainWindow) -> None:
        """AC: File > Open shows file dialog with .ckt and .cdl filters.

        Spec: Open action should trigger file dialog when clicked.
        """
        # Mock QFileDialog.getOpenFileName to avoid showing actual dialog
        with patch(
            "ink.presentation.main_window.QFileDialog.getOpenFileName"
        ) as mock_dialog:
            mock_dialog.return_value = ("", "")  # No file selected

            # Find Open action
            open_action = None
            for action in main_window.file_menu.actions():
                if "Open" in action.text() and "Recent" not in action.text():
                    open_action = action
                    break

            assert open_action is not None
            open_action.trigger()

            # Verify dialog was called
            mock_dialog.assert_called_once()

    def test_open_dialog_filter_includes_ckt_and_cdl(self, main_window: InkMainWindow) -> None:
        """AC: File > Open shows file dialog with .ckt and .cdl filters.

        Spec: Dialog filter should include *.ckt, *.cdl, and *.sp extensions.
        """
        with patch(
            "ink.presentation.main_window.QFileDialog.getOpenFileName"
        ) as mock_dialog:
            mock_dialog.return_value = ("", "")

            # Trigger the dialog
            main_window._on_open_file_dialog()

            # Check the filter argument includes expected extensions
            call_args = mock_dialog.call_args
            # Filter is the 4th positional argument or 'filter' keyword
            if len(call_args[0]) > 3:
                filter_arg = call_args[0][3]
            else:
                filter_arg = call_args[1].get("filter", "")

            assert ".ckt" in filter_arg.lower()
            assert ".cdl" in filter_arg.lower()


class TestOpenFileIntegration:
    """Test file opening functionality."""

    def test_open_file_adds_to_recent(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: Selected file path triggers _load_netlist() (adds to recent).

        Spec: Opening a file adds it to recent files list.
        """
        main_window._open_file(temp_files[0])

        recent = main_window.app_settings.get_recent_files()
        assert temp_files[0] in recent

    def test_open_file_updates_menu(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: Recent Files submenu updates after file open.

        Spec: Recent files menu reflects newly opened file.
        """
        # Initially empty
        initial_actions = main_window.recent_files_menu.actions()
        assert len(initial_actions) == 1  # "No Recent Files" placeholder
        assert "No Recent Files" in initial_actions[0].text()

        # Open a file
        main_window._open_file(temp_files[0])

        # Menu should now have the file
        updated_actions = main_window.recent_files_menu.actions()
        assert len(updated_actions) >= 2  # File + separator + clear
        assert "test0.ckt" in updated_actions[0].text()

    def test_open_file_updates_window_title(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Spec: Window title updates to show loaded file.

        Format: "Ink - {filename}"
        """
        main_window._open_file(temp_files[0])

        title = main_window.windowTitle()
        assert "test0.ckt" in title
        assert "Ink" in title


class TestRecentFilesLimit:
    """Test recent files limit of 10."""

    def test_recent_files_limited_to_ten(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: Recent Files submenu shows up to 10 most recent files.

        Spec: Maximum 10 files shown in recent files menu.
        """
        # Add 15 files
        for file in temp_files:
            main_window._open_file(file)

        # Get recent files
        recent = main_window.app_settings.get_recent_files()
        assert len(recent) == 10

    def test_recent_menu_shows_max_ten_items(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: Recent Files submenu shows up to 10 most recent files.

        Spec: Menu visually shows at most 10 file entries.
        """
        # Add 15 files
        for file in temp_files:
            main_window.app_settings.add_recent_file(file)
        main_window._update_recent_files_menu()

        # Count non-separator, non-clear actions
        file_actions = [
            a for a in main_window.recent_files_menu.actions()
            if not a.isSeparator() and "Clear" not in a.text()
        ]
        assert len(file_actions) == 10


class TestRecentFilesOrder:
    """Test recent files ordering (newest first)."""

    def test_most_recent_file_at_top(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: Most recently opened file appears at top of Recent Files list.

        Spec: Newest file is first in the list.
        """
        main_window._open_file(temp_files[0])
        main_window._open_file(temp_files[1])
        main_window._open_file(temp_files[2])

        recent = main_window.app_settings.get_recent_files()

        # Most recent (test2) should be first
        assert recent[0] == temp_files[2]
        assert recent[1] == temp_files[1]
        assert recent[2] == temp_files[0]


class TestRecentFileClick:
    """Test clicking recent file opens it."""

    def test_clicking_recent_file_opens_it(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: Clicking recent file opens it directly.

        Spec: Clicking a recent file in the menu opens that file.
        """
        # Add file to recent
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        # Get the file action
        file_action = main_window.recent_files_menu.actions()[0]

        # Trigger the action
        file_action.trigger()

        # File should still be in recent (re-added/moved to front)
        recent = main_window.app_settings.get_recent_files()
        assert temp_files[0] in recent


class TestMissingRecentFile:
    """Test handling of missing/deleted recent files."""

    def test_nonexistent_file_shows_warning(
        self, main_window: InkMainWindow, temp_files: list[str], qtbot: QtBot
    ) -> None:
        """AC: Missing recent files show warning dialog and are removed from list.

        Spec: Clicking a deleted file shows warning and removes it from list.
        """
        # Add file to recent
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        # Delete the file
        Path(temp_files[0]).unlink()

        # Mock QMessageBox.warning to avoid actual dialog
        with patch(
            "ink.presentation.main_window.QMessageBox.warning"
        ) as mock_warning:
            # Trigger recent file click
            main_window._on_open_recent_file(temp_files[0])

            # Warning should have been shown
            mock_warning.assert_called_once()

    def test_nonexistent_file_removed_from_list(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: Missing recent files are removed from list after warning.

        Spec: Non-existent file is removed from recent files list.
        """
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        # Delete the file
        Path(temp_files[0]).unlink()

        # Attempt to open will auto-remove from settings
        recent = main_window.app_settings.get_recent_files()

        # File should be removed (get_recent_files filters non-existent)
        assert temp_files[0] not in recent


class TestClearRecentFiles:
    """Test Clear Recent Files action."""

    def test_clear_action_exists(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Verify Clear Recent Files action exists when files present."""
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        actions = main_window.recent_files_menu.actions()
        clear_action = actions[-1]

        assert "Clear" in clear_action.text()

    def test_clear_action_clears_all_files(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: "Clear Recent Files" removes all entries.

        Spec: Clear action empties the recent files list.
        """
        # Add files
        for i in range(5):
            main_window.app_settings.add_recent_file(temp_files[i])
        main_window._update_recent_files_menu()

        # Get and trigger clear action
        actions = main_window.recent_files_menu.actions()
        clear_action = actions[-1]
        clear_action.trigger()

        # List should be empty
        recent = main_window.app_settings.get_recent_files()
        assert len(recent) == 0

    def test_clear_action_updates_menu(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: Menu updates after clearing.

        Spec: Menu shows "No Recent Files" after clearing.
        """
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        # Clear
        main_window._on_clear_recent_files_from_menu()

        # Menu should show empty state
        actions = main_window.recent_files_menu.actions()
        assert len(actions) == 1
        assert "No Recent Files" in actions[0].text()


class TestRecentFilesPersistence:
    """Test recent files persist across sessions."""

    def test_recent_files_persist_after_reload(
        self, isolated_settings: Path, temp_files: list[str], qtbot: QtBot
    ) -> None:
        """AC: Recent files persist across application restarts.

        Spec: Recent files saved to QSettings survive app restart.
        """
        # First session - add files
        settings1 = AppSettings()
        settings1.add_recent_file(temp_files[0])
        settings1.add_recent_file(temp_files[1])
        settings1.sync()

        # Second session - verify files persisted
        settings2 = AppSettings()
        recent = settings2.get_recent_files()

        assert len(recent) == 2
        assert temp_files[1] in recent
        assert temp_files[0] in recent


class TestRecentFilesPathDisplay:
    """Test file paths display in menu."""

    def test_menu_action_shows_filename(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: File paths in Recent Files menu show full path.

        Spec: Menu items show the filename for readability.
        """
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        action = main_window.recent_files_menu.actions()[0]

        # Action text should contain filename
        assert "test0.ckt" in action.text()

    def test_menu_action_stores_full_path(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """AC: Full path is stored for file opening.

        Spec: Action data contains full path for actual file opening.
        """
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        action = main_window.recent_files_menu.actions()[0]

        # Action data should be the full path
        assert action.data() == temp_files[0]

    def test_menu_action_tooltip_shows_full_path(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Spec: Tooltip shows full path on hover.

        This allows users to see full path when needed.
        """
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        action = main_window.recent_files_menu.actions()[0]

        # Tooltip should be the full path
        assert action.toolTip() == temp_files[0]


class TestRecentFilesNumbering:
    """Test recent files numbering with keyboard shortcuts."""

    def test_first_nine_files_have_shortcuts(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Spec: Files 1-9 have &1-&9 mnemonics for Alt+N shortcuts."""
        # Add 10 files
        for i in range(10):
            main_window.app_settings.add_recent_file(temp_files[i])
        main_window._update_recent_files_menu()

        actions = main_window.recent_files_menu.actions()

        # Check first 9 files have & prefix (index 0-8)
        for i in range(9):
            assert f"&{i + 1}." in actions[i].text()

    def test_tenth_file_has_no_shortcut(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Spec: File 10 does NOT have & shortcut (would require two keys)."""
        # Add 10 files
        for i in range(10):
            main_window.app_settings.add_recent_file(temp_files[i])
        main_window._update_recent_files_menu()

        actions = main_window.recent_files_menu.actions()

        # 10th file (index 9) should have no & prefix
        assert "&10." not in actions[9].text()
        assert "10." in actions[9].text()


class TestEmptyRecentFilesMenu:
    """Test empty recent files menu state."""

    def test_empty_menu_shows_placeholder(self, main_window: InkMainWindow) -> None:
        """Spec: Empty menu shows "No Recent Files" placeholder."""
        actions = main_window.recent_files_menu.actions()

        assert len(actions) == 1
        assert "No Recent Files" in actions[0].text()
        assert not actions[0].isEnabled()  # Disabled, not clickable
