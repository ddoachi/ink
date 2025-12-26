"""Integration tests for recent files menu in InkMainWindow.

This module tests the integration between AppSettings recent files functionality
and the InkMainWindow File menu. Tests verify the full workflow from adding
files to displaying them in the menu.

Test Strategy:
    - Use temporary QSettings path for isolation
    - Use temporary test files
    - Test menu structure and behavior
    - Verify menu updates after file operations
    - Test keyboard shortcuts and action handling

TDD Phase: RED - These tests define expected menu behavior before implementation.

See Also:
    - Spec E06-F06-T03 for requirements
    - src/ink/presentation/main_window.py for implementation
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMenu

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.main_window import InkMainWindow

if TYPE_CHECKING:
    from collections.abc import Generator

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
def main_window(
    qtbot: QtBot, app_settings: AppSettings
) -> Generator[InkMainWindow, None, None]:
    """Create InkMainWindow instance with AppSettings.

    Args:
        qtbot: pytest-qt bot for Qt widget testing.
        app_settings: Isolated AppSettings instance.

    Yields:
        InkMainWindow instance for testing.
    """
    window = InkMainWindow(app_settings)
    qtbot.addWidget(window)
    yield window


@pytest.fixture
def temp_files(tmp_path: Path) -> list[str]:
    """Create temporary test files for recent files testing.

    Args:
        tmp_path: Pytest-provided temporary directory.

    Returns:
        List of absolute file paths as strings.
    """
    files = []
    for i in range(15):
        file = tmp_path / f"test{i}.ckt"
        file.write_text(f"* Netlist content {i}\n")
        files.append(str(file))
    return files


# =============================================================================
# Test Classes
# =============================================================================


class TestMainWindowHasRecentFilesMenu:
    """Test that InkMainWindow has recent files menu structure."""

    def test_main_window_accepts_app_settings(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test that InkMainWindow constructor accepts AppSettings parameter."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)
        assert hasattr(window, "app_settings")
        assert window.app_settings is app_settings

    def test_has_menubar(self, main_window: InkMainWindow) -> None:
        """Test that main window has a menu bar."""
        menubar = main_window.menuBar()
        assert menubar is not None

    def test_has_file_menu(self, main_window: InkMainWindow) -> None:
        """Test that main window has a File menu."""
        menubar = main_window.menuBar()
        file_menu = None

        for action in menubar.actions():
            if "File" in action.text():
                file_menu = action.menu()
                break

        assert file_menu is not None

    def test_file_menu_has_open_recent_submenu(
        self, main_window: InkMainWindow
    ) -> None:
        """Test that File menu has Open Recent submenu."""
        # Use the stored recent_files_menu attribute directly
        # This is more robust than searching through menu actions
        assert main_window.recent_files_menu is not None
        assert isinstance(main_window.recent_files_menu, QMenu)

        # Verify the menu title contains "Recent"
        assert "Recent" in main_window.recent_files_menu.title()

    def test_has_recent_files_menu_attribute(
        self, main_window: InkMainWindow
    ) -> None:
        """Test that InkMainWindow has recent_files_menu attribute."""
        assert hasattr(main_window, "recent_files_menu")
        assert isinstance(main_window.recent_files_menu, QMenu)


class TestRecentFilesMenuContent:
    """Test recent files menu content and display."""

    def test_empty_menu_shows_no_recent_files(
        self, main_window: InkMainWindow
    ) -> None:
        """Test that empty menu shows 'No Recent Files' placeholder."""
        actions = main_window.recent_files_menu.actions()

        # Should have one disabled action
        assert len(actions) == 1
        assert "No Recent Files" in actions[0].text()
        assert not actions[0].isEnabled()

    def test_menu_shows_recent_files(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that menu displays added recent files."""
        # Add files to settings
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window.app_settings.add_recent_file(temp_files[1])

        # Update menu
        main_window._update_recent_files_menu()

        actions = main_window.recent_files_menu.actions()

        # Should have: 2 files + separator + Clear action
        assert len(actions) >= 3

        # First two actions should be the files
        assert "test1.ckt" in actions[0].text()
        assert "test0.ckt" in actions[1].text()

    def test_menu_items_numbered(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that menu items are numbered 1-9."""
        # Add files
        for i in range(5):
            main_window.app_settings.add_recent_file(temp_files[i])

        main_window._update_recent_files_menu()

        actions = main_window.recent_files_menu.actions()

        # Check numbering (newest first, so test4 is 1, test3 is 2, etc.)
        assert "&1." in actions[0].text() or "1." in actions[0].text()
        assert "&2." in actions[1].text() or "2." in actions[1].text()
        assert "&3." in actions[2].text() or "3." in actions[2].text()

    def test_menu_has_clear_action(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that menu has 'Clear Recent Files' action when files exist."""
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        actions = main_window.recent_files_menu.actions()

        # Last action should be Clear Recent Files
        clear_action = actions[-1]
        assert "Clear" in clear_action.text()
        assert clear_action.isEnabled()

    def test_menu_has_separator_before_clear(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that separator exists before Clear action."""
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        actions = main_window.recent_files_menu.actions()

        # Second to last should be separator
        separator_action = actions[-2]
        assert separator_action.isSeparator()


class TestRecentFilesMenuUpdates:
    """Test that menu updates correctly after operations."""

    def test_menu_updates_after_file_open(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that menu updates when file is opened."""
        # Initially empty
        initial_actions = main_window.recent_files_menu.actions()
        assert len(initial_actions) == 1
        assert "No Recent Files" in initial_actions[0].text()

        # Open file (simulate)
        main_window._open_file(temp_files[0])

        # Menu should now have file
        updated_actions = main_window.recent_files_menu.actions()
        assert len(updated_actions) >= 2
        assert "test0.ckt" in updated_actions[0].text()

    def test_menu_updates_after_clear(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that menu shows empty state after clearing."""
        # Add files
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        # Clear using the no-dialog method (from File > Open Recent submenu)
        main_window._on_clear_recent_files_from_menu()

        # Should show empty state
        actions = main_window.recent_files_menu.actions()
        assert len(actions) == 1
        assert "No Recent Files" in actions[0].text()


class TestRecentFilesMenuActions:
    """Test recent files menu action functionality."""

    def test_clicking_file_opens_it(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that clicking a recent file menu item opens the file."""
        # Add file to recent
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        # Get file action
        file_action = main_window.recent_files_menu.actions()[0]

        # Trigger action
        file_action.trigger()

        # File should still be in recent (re-added at front)
        recent = main_window.app_settings.get_recent_files()
        assert temp_files[0] in recent

    def test_action_stores_file_path_in_data(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that file action stores full path in data."""
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        file_action = main_window.recent_files_menu.actions()[0]
        assert file_action.data() == temp_files[0]

    def test_clear_action_clears_list(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that Clear action removes all recent files."""
        # Add files
        for i in range(3):
            main_window.app_settings.add_recent_file(temp_files[i])
        main_window._update_recent_files_menu()

        # Trigger clear action (last action)
        actions = main_window.recent_files_menu.actions()
        clear_action = actions[-1]
        clear_action.trigger()

        # List should be empty
        recent = main_window.app_settings.get_recent_files()
        assert len(recent) == 0


class TestRecentFilesMenuMissingFile:
    """Test handling of non-existent files in menu."""

    def test_nonexistent_file_removed_from_list(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that non-existent files are removed from recent list on access."""
        # Add file
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        # Delete the file
        Path(temp_files[0]).unlink()

        # Get recent files - this should auto-remove the deleted file
        recent = main_window.app_settings.get_recent_files()

        # File should be removed since it no longer exists
        assert temp_files[0] not in recent


class TestFormatRecentFileName:
    """Test _format_recent_file_name helper method."""

    def test_format_includes_number(
        self, main_window: InkMainWindow, tmp_path: Path
    ) -> None:
        """Test that format includes file number."""
        file_path = str(tmp_path / "test.ckt")
        result = main_window._format_recent_file_name(file_path, 0)
        assert "1." in result  # Index 0 -> number 1

    def test_format_includes_filename(
        self, main_window: InkMainWindow, tmp_path: Path
    ) -> None:
        """Test that format includes filename."""
        file_path = str(tmp_path / "mydesign.ckt")
        result = main_window._format_recent_file_name(file_path, 0)
        assert "mydesign.ckt" in result

    def test_format_has_shortcut_for_first_nine(
        self, main_window: InkMainWindow, tmp_path: Path
    ) -> None:
        """Test that items 1-9 have & shortcut."""
        file_path = str(tmp_path / "test.ckt")

        for i in range(9):
            result = main_window._format_recent_file_name(file_path, i)
            assert f"&{i + 1}." in result

    def test_format_no_shortcut_for_tenth(
        self, main_window: InkMainWindow, tmp_path: Path
    ) -> None:
        """Test that item 10+ has no & shortcut."""
        file_path = str(tmp_path / "test.ckt")
        result = main_window._format_recent_file_name(file_path, 9)
        # Should be "10. test.ckt" not "&10. test.ckt"
        assert "&10." not in result
        assert "10." in result


class TestMainWindowFileOpen:
    """Test file opening methods in MainWindow."""

    def test_has_open_file_method(self, main_window: InkMainWindow) -> None:
        """Test that _open_file method exists."""
        assert hasattr(main_window, "_open_file")
        assert callable(main_window._open_file)

    def test_has_on_open_recent_file_method(
        self, main_window: InkMainWindow
    ) -> None:
        """Test that _on_open_recent_file method exists."""
        assert hasattr(main_window, "_on_open_recent_file")
        assert callable(main_window._on_open_recent_file)

    def test_has_update_recent_files_menu_method(
        self, main_window: InkMainWindow
    ) -> None:
        """Test that _update_recent_files_menu method exists."""
        assert hasattr(main_window, "_update_recent_files_menu")
        assert callable(main_window._update_recent_files_menu)

    def test_open_file_adds_to_recent(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that opening file adds it to recent list."""
        main_window._open_file(temp_files[0])

        recent = main_window.app_settings.get_recent_files()
        assert temp_files[0] in recent

    def test_open_file_updates_window_title(
        self, main_window: InkMainWindow, temp_files: list[str]
    ) -> None:
        """Test that opening file updates window title."""
        main_window._open_file(temp_files[0])

        title = main_window.windowTitle()
        assert "test0.ckt" in title
