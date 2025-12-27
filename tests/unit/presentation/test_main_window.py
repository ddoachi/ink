"""Unit tests for InkMainWindow.

Tests verify the main application window meets all requirements from spec E06-F01-T01:
- Window instantiation without errors
- Correct window title
- Default size of 1600x900
- Minimum size of 1024x768
- Proper window flags for decorations

These tests run in TDD RED phase first (expecting failures), then GREEN after implementation.

See Also:
    - Spec E06-F01-T01 for window shell requirements
    - Spec E06-F06-T03 for recent files menu requirements
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QMainWindow

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


# =============================================================================
# Test Classes
# =============================================================================


class TestInkMainWindowCreation:
    """Tests for InkMainWindow instantiation."""

    def test_main_window_can_be_created(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test that InkMainWindow can be instantiated without errors.

        Verifies:
        - No exceptions during construction
        - Returns a valid object instance
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window is not None

    def test_main_window_is_qmainwindow_subclass(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test that InkMainWindow inherits from QMainWindow.

        QMainWindow provides built-in support for:
        - Menu bar, toolbar, status bar, dock widgets
        - Window geometry persistence with QSettings
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert isinstance(window, QMainWindow)


class TestInkMainWindowTitle:
    """Tests for window title configuration."""

    def test_window_title_is_set_correctly(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test window title matches spec requirement.

        Expected: "Ink - Incremental Schematic Viewer"
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.windowTitle() == "Ink - Incremental Schematic Viewer"


class TestInkMainWindowSize:
    """Tests for window size configuration."""

    def test_window_default_width_is_1280(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test default window width is 1280 pixels (geometry persistence default).

        With geometry persistence enabled, the window uses smaller defaults
        (1280x800) for first run, leaving room for users to resize.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.width() == 1280

    def test_window_default_height_is_800(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test default window height is 800 pixels (geometry persistence default).

        With geometry persistence enabled, the window uses smaller defaults
        (1280x800) for first run, leaving room for users to resize.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.height() == 800

    def test_window_minimum_width_is_1024(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test minimum window width is 1024 pixels.

        Below this, UI elements become too crowded.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.minimumWidth() == 1024

    def test_window_minimum_height_is_768(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test minimum window height is 768 pixels.

        1024x768 is common minimum for professional tools.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.minimumHeight() == 768

    def test_window_cannot_be_resized_below_minimum(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test that window enforces minimum size constraint.

        Attempting to resize below minimum should clamp to minimum.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Try to resize below minimum
        window.resize(800, 600)

        # Should be clamped to minimum
        assert window.width() >= 1024
        assert window.height() >= 768


class TestInkMainWindowFlags:
    """Tests for window flags and decorations."""

    def test_window_has_title_hint(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test window has title bar hint enabled."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowTitleHint

    def test_window_has_system_menu_hint(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test window has system menu hint enabled."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowSystemMenuHint

    def test_window_has_minimize_button_hint(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test window has minimize button hint enabled."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowMinimizeButtonHint

    def test_window_has_maximize_button_hint(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test window has maximize button hint enabled."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowMaximizeButtonHint

    def test_window_has_close_button_hint(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test window has close button hint enabled."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowCloseButtonHint


# =============================================================================
# Menu Bar Tests (E06-F02-T01)
# =============================================================================


class TestInkMainWindowMenuBar:
    """Tests for menu bar setup - E06-F02-T01.

    Verifies:
    - Menu bar is created
    - File, Edit, View, Help menus exist
    - Menus have correct mnemonics
    - Menu references stored as instance variables
    - Helper methods exist for each menu
    """

    def test_menu_bar_exists(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test that menu bar is created.

        Spec: Menu bar appears in main window.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        menubar = window.menuBar()
        assert menubar is not None

    def test_top_level_menus_exist(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test that File, Edit, View, Help menus exist.

        Spec: File, Edit, View, Help menus visible in menu bar.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # All four menus should exist as instance variables
        assert hasattr(window, "file_menu")
        assert hasattr(window, "edit_menu")
        assert hasattr(window, "view_menu")
        assert hasattr(window, "help_menu")

        # All menus should be non-None
        assert window.file_menu is not None
        assert window.edit_menu is not None
        assert window.view_menu is not None
        assert window.help_menu is not None

    def test_file_menu_title(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test File menu has correct title with mnemonic.

        Spec: Menus use correct mnemonics (&File).
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.file_menu.title() == "&File"

    def test_edit_menu_title(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test Edit menu has correct title with mnemonic.

        Spec: Menus use correct mnemonics (&Edit).
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.edit_menu.title() == "&Edit"

    def test_view_menu_title(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test View menu has correct title with mnemonic.

        Spec: Menus use correct mnemonics (&View).
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.view_menu.title() == "&View"

    def test_help_menu_title(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test Help menu has correct title with mnemonic.

        Spec: Menus use correct mnemonics (&Help).
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.help_menu.title() == "&Help"

    def test_menu_order_in_menubar(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test menus appear in correct order: File, Edit, View, Help.

        This is the standard order for application menus.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        menubar = window.menuBar()
        actions = menubar.actions()

        # Get menu titles in order (removing mnemonics for comparison)
        menu_titles = [action.text().replace("&", "") for action in actions]

        # First 4 should be File, Edit, View, Help in that order
        assert "File" in menu_titles
        assert "Edit" in menu_titles
        assert "View" in menu_titles
        assert "Help" in menu_titles

        # Check order
        file_idx = menu_titles.index("File")
        edit_idx = menu_titles.index("Edit")
        view_idx = menu_titles.index("View")
        help_idx = menu_titles.index("Help")

        assert file_idx < edit_idx < view_idx < help_idx

    def test_helper_methods_exist(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test helper methods for menu creation exist.

        Spec: Helper methods _create_file_menu(), _create_edit_menu(),
        _create_view_menu(), _create_help_menu() exist.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # All helper methods should exist and be callable
        assert hasattr(window, "_create_file_menu")
        assert callable(window._create_file_menu)

        assert hasattr(window, "_create_edit_menu")
        assert callable(window._create_edit_menu)

        assert hasattr(window, "_create_view_menu")
        assert callable(window._create_view_menu)

        assert hasattr(window, "_create_help_menu")
        assert callable(window._create_help_menu)

    def test_menus_are_clickable(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test that all menus are enabled and clickable.

        Spec: All four menus are clickable and open (though empty).
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # All menus should be enabled
        assert window.file_menu.isEnabled()
        assert window.edit_menu.isEnabled()
        assert window.view_menu.isEnabled()
        assert window.help_menu.isEnabled()


# =============================================================================
# View Control Toolbar Actions Tests (E06-F03-T02)
# =============================================================================


class TestViewControlActions:
    """Tests for view control toolbar actions - E06-F03-T02.

    Verifies:
    - View control actions are added to toolbar (Zoom In, Zoom Out, Fit View)
    - Actions have correct keyboard shortcuts
    - Actions have tooltips with shortcut hints
    - Actions trigger correct canvas methods
    - Actions handle missing canvas gracefully (no crash)
    - Actions are always enabled
    - Actions appear in correct order: Zoom Out, Zoom In, Fit View

    See Also:
        - Spec E06-F03-T02 for view control tools requirements
        - Pre-docs E06-F03-T02 for implementation details
    """

    def test_view_actions_created(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test view control actions are added to toolbar.

        Spec: Zoom In, Zoom Out, Fit View buttons appear in toolbar.
        """
        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        toolbar = window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        actions = toolbar.actions()
        action_texts = [a.text() for a in actions if not a.isSeparator()]

        assert "Zoom In" in action_texts
        assert "Zoom Out" in action_texts
        assert "Fit View" in action_texts

    def test_view_actions_order(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test view actions appear in correct order: Zoom Out, Zoom In, Fit View.

        Spec: Buttons arranged in order: Zoom Out, Zoom In, Fit View.
        This follows the conventional order (decrease first, increase second).
        """
        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = toolbar.actions()
        action_texts = [a.text() for a in actions if not a.isSeparator()]

        # Find indices of view actions
        zoom_out_idx = action_texts.index("Zoom Out")
        zoom_in_idx = action_texts.index("Zoom In")
        fit_view_idx = action_texts.index("Fit View")

        # Should be in order: Zoom Out < Zoom In < Fit View
        assert zoom_out_idx < zoom_in_idx < fit_view_idx

    def test_view_action_shortcuts(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test view actions have correct keyboard shortcuts.

        Spec:
        - Zoom In: Ctrl+= (Qt standard ZoomIn)
        - Zoom Out: Ctrl+- (Qt standard ZoomOut)
        - Fit View: Ctrl+0 (custom, industry convention)
        """
        from PySide6.QtGui import QKeySequence
        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}

        zoom_in = actions["Zoom In"]
        zoom_out = actions["Zoom Out"]
        fit_view = actions["Fit View"]

        assert zoom_in.shortcut() == QKeySequence.StandardKey.ZoomIn
        assert zoom_out.shortcut() == QKeySequence.StandardKey.ZoomOut
        assert fit_view.shortcut() == QKeySequence("Ctrl+0")

    def test_view_action_tooltips(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test tooltips include action name and keyboard shortcut.

        Spec: Tooltips display on hover with action name and shortcut.
        """
        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}

        # Tooltips should contain shortcut information
        assert "Ctrl" in actions["Zoom In"].toolTip()
        assert "Ctrl" in actions["Zoom Out"].toolTip()
        assert "Ctrl+0" in actions["Fit View"].toolTip()

    def test_zoom_in_triggered(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test zoom in action calls canvas.zoom_in().

        Spec: Clicking Zoom In button zooms canvas in.
        """
        from unittest.mock import Mock

        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Mock the canvas with zoom_in method
        mock_canvas = Mock()
        window.schematic_canvas = mock_canvas

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}

        actions["Zoom In"].trigger()
        mock_canvas.zoom_in.assert_called_once()

    def test_zoom_out_triggered(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test zoom out action calls canvas.zoom_out().

        Spec: Clicking Zoom Out button zooms canvas out.
        """
        from unittest.mock import Mock

        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Mock the canvas with zoom_out method
        mock_canvas = Mock()
        window.schematic_canvas = mock_canvas

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}

        actions["Zoom Out"].trigger()
        mock_canvas.zoom_out.assert_called_once()

    def test_fit_view_triggered(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test fit view action calls canvas.fit_view().

        Spec: Clicking Fit View button fits content to view.
        """
        from unittest.mock import Mock

        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Mock the canvas with fit_view method
        mock_canvas = Mock()
        window.schematic_canvas = mock_canvas

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}

        actions["Fit View"].trigger()
        mock_canvas.fit_view.assert_called_once()

    def test_view_actions_without_canvas(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test view actions don't crash when canvas is missing.

        Spec: Actions gracefully handle missing canvas (no crash).
        """
        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Set canvas to None to simulate missing canvas
        window.schematic_canvas = None  # type: ignore[assignment]

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}

        # Should not raise exception
        actions["Zoom In"].trigger()
        actions["Zoom Out"].trigger()
        actions["Fit View"].trigger()

    def test_view_actions_without_zoom_methods(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test view actions don't crash when canvas lacks zoom methods.

        Actions should gracefully handle a canvas that doesn't have
        the expected zoom_in/zoom_out/fit_view methods.
        """
        from unittest.mock import Mock

        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Create a mock canvas without zoom methods
        mock_canvas = Mock(spec=[])  # Empty spec means no methods
        window.schematic_canvas = mock_canvas

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}

        # Should not raise exception - graceful degradation
        actions["Zoom In"].trigger()
        actions["Zoom Out"].trigger()
        actions["Fit View"].trigger()

    def test_view_actions_always_enabled(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test view actions are always enabled.

        Spec: Buttons remain enabled at all times.
        Unlike undo/redo, view actions are not state-dependent.
        """
        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}

        assert actions["Zoom In"].isEnabled()
        assert actions["Zoom Out"].isEnabled()
        assert actions["Fit View"].isEnabled()

    def test_add_view_actions_method_exists(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test that _add_view_actions() method exists.

        Spec: Implementation uses _add_view_actions() helper method.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert hasattr(window, "_add_view_actions")
        assert callable(window._add_view_actions)

    def test_view_action_handlers_exist(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Test that action handler methods exist.

        Spec: _on_zoom_in(), _on_zoom_out(), _on_fit_view() handlers exist.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert hasattr(window, "_on_zoom_in")
        assert callable(window._on_zoom_in)

        assert hasattr(window, "_on_zoom_out")
        assert callable(window._on_zoom_out)

        assert hasattr(window, "_on_fit_view")
        assert callable(window._on_fit_view)

    def test_toolbar_has_separator_after_view_actions(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test visual separator is added after view control group.

        Spec: Visual separator before and after view group.
        """
        from PySide6.QtWidgets import QToolBar

        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        toolbar = window.findChild(QToolBar, "MainToolBar")
        actions = toolbar.actions()

        # Find Fit View action (last in view group)
        fit_view_idx = None
        for i, action in enumerate(actions):
            if action.text() == "Fit View":
                fit_view_idx = i
                break

        assert fit_view_idx is not None

        # Next action after Fit View should be a separator
        if fit_view_idx + 1 < len(actions):
            assert actions[fit_view_idx + 1].isSeparator()
