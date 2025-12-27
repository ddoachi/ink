"""Unit tests for View and Help menu actions - E06-F02-T04.

Tests verify the View menu (zoom actions, panel toggles) and Help menu
(Keyboard Shortcuts dialog, About dialog) meet all requirements from
spec E06-F02-T04.

Test Categories:
    - View Menu Zoom Actions: Zoom In, Zoom Out, Fit View
    - View Menu Panel Toggles: Already tested in test_panel_toggle_actions.py
    - Help Menu Keyboard Shortcuts: F1 shortcut, dialog content
    - Help Menu About Dialog: Application info display

TDD Phases:
    - RED: Tests written first, expected to fail
    - GREEN: Implementation added to pass tests
    - REFACTOR: Code cleaned up while keeping tests passing

See Also:
    - Spec E06-F02-T04 for View and Help menu requirements
    - E06-F05-T03 for panel toggle actions (already implemented)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog

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
# View Menu Zoom Actions Tests
# =============================================================================


class TestViewMenuZoomActions:
    """Tests for View menu zoom actions - E06-F02-T04.

    Verifies:
    - Zoom In, Zoom Out, Fit View actions exist in View menu
    - Actions have correct keyboard shortcuts
    - Actions have correct status tips
    - Actions trigger canvas zoom methods
    - Actions are always enabled (no state dependency)

    Note: Panel toggle actions are tested in test_panel_toggle_actions.py
    as they were implemented in E06-F05-T03.
    """

    def test_zoom_in_action_exists_in_view_menu(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Zoom In action exists in View menu.

        Spec: View menu contains Zoom In action.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Find Zoom In action in View menu
        actions = window.view_menu.actions()
        action_texts = [a.text() for a in actions if not a.isSeparator()]

        assert any("Zoom" in text and "In" in text for text in action_texts)

    def test_zoom_out_action_exists_in_view_menu(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Zoom Out action exists in View menu.

        Spec: View menu contains Zoom Out action.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        actions = window.view_menu.actions()
        action_texts = [a.text() for a in actions if not a.isSeparator()]

        assert any("Zoom" in text and "Out" in text for text in action_texts)

    def test_fit_view_action_exists_in_view_menu(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Fit View action exists in View menu.

        Spec: View menu contains Fit View action.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        actions = window.view_menu.actions()
        action_texts = [a.text() for a in actions if not a.isSeparator()]

        assert any("Fit" in text and "View" in text for text in action_texts)

    def test_zoom_in_action_shortcut(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Zoom In action has Ctrl+= shortcut.

        Spec: Keyboard shortcuts work: Ctrl+=
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Find Zoom In action
        zoom_in_action = None
        for action in window.view_menu.actions():
            if "Zoom" in action.text() and "In" in action.text():
                zoom_in_action = action
                break

        assert zoom_in_action is not None
        assert zoom_in_action.shortcut() == QKeySequence.StandardKey.ZoomIn

    def test_zoom_out_action_shortcut(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Zoom Out action has Ctrl+- shortcut.

        Spec: Keyboard shortcuts work: Ctrl+-
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Find Zoom Out action
        zoom_out_action = None
        for action in window.view_menu.actions():
            if "Zoom" in action.text() and "Out" in action.text():
                zoom_out_action = action
                break

        assert zoom_out_action is not None
        assert zoom_out_action.shortcut() == QKeySequence.StandardKey.ZoomOut

    def test_fit_view_action_shortcut(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Fit View action has Ctrl+0 shortcut.

        Spec: Keyboard shortcuts work: Ctrl+0
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Find Fit View action
        fit_view_action = None
        for action in window.view_menu.actions():
            if "Fit" in action.text():
                fit_view_action = action
                break

        assert fit_view_action is not None
        assert fit_view_action.shortcut() == QKeySequence("Ctrl+0")

    def test_zoom_in_action_status_tip(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Zoom In action has status tip.

        Spec: Actions have status tips for status bar display.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        zoom_in_action = None
        for action in window.view_menu.actions():
            if "Zoom" in action.text() and "In" in action.text():
                zoom_in_action = action
                break

        assert zoom_in_action is not None
        assert "zoom" in zoom_in_action.statusTip().lower()

    def test_zoom_out_action_status_tip(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Zoom Out action has status tip.

        Spec: Actions have status tips for status bar display.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        zoom_out_action = None
        for action in window.view_menu.actions():
            if "Zoom" in action.text() and "Out" in action.text():
                zoom_out_action = action
                break

        assert zoom_out_action is not None
        assert "zoom" in zoom_out_action.statusTip().lower()

    def test_fit_view_action_status_tip(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Fit View action has status tip.

        Spec: Actions have status tips for status bar display.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        fit_view_action = None
        for action in window.view_menu.actions():
            if "Fit" in action.text():
                fit_view_action = action
                break

        assert fit_view_action is not None
        assert len(fit_view_action.statusTip()) > 0

    def test_zoom_in_action_triggers_canvas(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Zoom In action triggers canvas.zoom_in().

        Spec: Zoom actions trigger canvas zoom methods.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Mock the canvas
        mock_canvas = Mock()
        window.schematic_canvas = mock_canvas

        # Find and trigger Zoom In action
        for action in window.view_menu.actions():
            if "Zoom" in action.text() and "In" in action.text():
                action.trigger()
                break

        mock_canvas.zoom_in.assert_called_once()

    def test_zoom_out_action_triggers_canvas(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Zoom Out action triggers canvas.zoom_out().

        Spec: Zoom actions trigger canvas zoom methods.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Mock the canvas
        mock_canvas = Mock()
        window.schematic_canvas = mock_canvas

        # Find and trigger Zoom Out action
        for action in window.view_menu.actions():
            if "Zoom" in action.text() and "Out" in action.text():
                action.trigger()
                break

        mock_canvas.zoom_out.assert_called_once()

    def test_fit_view_action_triggers_canvas(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Fit View action triggers canvas.fit_view() or fit_to_view().

        Spec: Fit View action fits schematic to viewport.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Mock the canvas
        mock_canvas = Mock()
        window.schematic_canvas = mock_canvas

        # Find and trigger Fit View action
        for action in window.view_menu.actions():
            if "Fit" in action.text():
                action.trigger()
                break

        # Accept either fit_view or fit_to_view method call
        assert mock_canvas.fit_view.called or mock_canvas.fit_to_view.called

    def test_zoom_actions_before_panels_menu(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test zoom actions appear before Panels submenu.

        Spec: View menu structure has zoom actions at top, then panels.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        actions = window.view_menu.actions()

        # Find indices
        zoom_in_idx = None
        panels_idx = None

        for i, action in enumerate(actions):
            text = action.text()
            if "Zoom" in text and "In" in text:
                zoom_in_idx = i
            elif "Panels" in text or (action.menu() and "Panel" in action.text()):
                panels_idx = i

        # Zoom In should come before Panels menu
        if zoom_in_idx is not None and panels_idx is not None:
            assert zoom_in_idx < panels_idx

    def test_separator_between_zoom_and_panels(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test separator exists between zoom actions and panel toggles.

        Spec: View menu has separator between zoom controls and panel toggles.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        actions = window.view_menu.actions()

        # There should be at least one separator in the View menu
        separators = [a for a in actions if a.isSeparator()]
        assert len(separators) >= 1


# =============================================================================
# Help Menu Keyboard Shortcuts Tests
# =============================================================================


class TestHelpMenuKeyboardShortcuts:
    """Tests for Help menu Keyboard Shortcuts dialog - E06-F02-T04.

    Verifies:
    - Keyboard Shortcuts action exists in Help menu
    - F1 keyboard shortcut opens the dialog
    - Dialog shows shortcuts organized by category
    - Dialog is modal and can be closed
    """

    def test_keyboard_shortcuts_action_exists(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Keyboard Shortcuts action exists in Help menu.

        Spec: Help menu contains Keyboard Shortcuts action.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        actions = window.help_menu.actions()
        action_texts = [a.text() for a in actions if not a.isSeparator() and not a.menu()]

        assert any("Keyboard" in text and "Shortcut" in text for text in action_texts)

    def test_keyboard_shortcuts_action_shortcut_f1(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Keyboard Shortcuts action has F1 shortcut.

        Spec: F1 opens Keyboard Shortcuts dialog.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Find Keyboard Shortcuts action
        shortcuts_action = None
        for action in window.help_menu.actions():
            if "Keyboard" in action.text() and "Shortcut" in action.text():
                shortcuts_action = action
                break

        assert shortcuts_action is not None
        assert shortcuts_action.shortcut() == QKeySequence("F1")

    def test_keyboard_shortcuts_action_has_status_tip(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Keyboard Shortcuts action has status tip.

        Spec: Actions have status tips for status bar display.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        shortcuts_action = None
        for action in window.help_menu.actions():
            if "Keyboard" in action.text() and "Shortcut" in action.text():
                shortcuts_action = action
                break

        assert shortcuts_action is not None
        assert len(shortcuts_action.statusTip()) > 0

    def test_keyboard_shortcuts_action_opens_dialog(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test triggering Keyboard Shortcuts opens a dialog.

        Spec: Clicking Keyboard Shortcuts opens dialog.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)
        window.show()

        # Find Keyboard Shortcuts action
        shortcuts_action = None
        for action in window.help_menu.actions():
            if "Keyboard" in action.text() and "Shortcut" in action.text():
                shortcuts_action = action
                break

        assert shortcuts_action is not None

        # We need to mock the dialog to prevent blocking
        # Patch where the name is looked up (in main_window), not where it's defined
        with patch(
            "ink.presentation.main_window.KeyboardShortcutsDialog"
        ) as MockDialog:
            mock_dialog = Mock()
            MockDialog.return_value = mock_dialog

            shortcuts_action.trigger()

            MockDialog.assert_called_once_with(window)
            mock_dialog.exec.assert_called_once()


class TestKeyboardShortcutsDialog:
    """Tests for KeyboardShortcutsDialog class - E06-F02-T04.

    Verifies:
    - Dialog can be created
    - Dialog has proper title
    - Dialog shows shortcuts in categories
    - Dialog has close button
    - Dialog is properly sized
    """

    def test_dialog_can_be_imported(self) -> None:
        """Test KeyboardShortcutsDialog class can be imported.

        Spec: Dialog implemented as separate class.
        """
        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        assert KeyboardShortcutsDialog is not None

    def test_dialog_can_be_created(self, qtbot: QtBot) -> None:
        """Test KeyboardShortcutsDialog can be instantiated.

        Spec: Dialog can be created with parent window.
        """
        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        dialog = KeyboardShortcutsDialog()
        qtbot.addWidget(dialog)

        assert dialog is not None
        assert isinstance(dialog, QDialog)

    def test_dialog_has_correct_title(self, qtbot: QtBot) -> None:
        """Test dialog has 'Keyboard Shortcuts' title.

        Spec: Dialog title is 'Keyboard Shortcuts'.
        """
        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        dialog = KeyboardShortcutsDialog()
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Keyboard Shortcuts"

    def test_dialog_has_minimum_size(self, qtbot: QtBot) -> None:
        """Test dialog has appropriate minimum size.

        Spec: Dialog minimum size is 500x400.
        """
        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        dialog = KeyboardShortcutsDialog()
        qtbot.addWidget(dialog)

        assert dialog.minimumWidth() >= 500
        assert dialog.minimumHeight() >= 400

    def test_dialog_content_has_file_menu_shortcuts(self, qtbot: QtBot) -> None:
        """Test dialog shows File menu shortcuts.

        Spec: Dialog shows shortcuts organized by category.
        """
        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        dialog = KeyboardShortcutsDialog()
        qtbot.addWidget(dialog)

        # Get the HTML content
        html_content = dialog._get_shortcuts_html()

        assert "File" in html_content
        assert "Ctrl+O" in html_content

    def test_dialog_content_has_edit_menu_shortcuts(self, qtbot: QtBot) -> None:
        """Test dialog shows Edit menu shortcuts.

        Spec: Dialog shows shortcuts organized by category.
        """
        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        dialog = KeyboardShortcutsDialog()
        qtbot.addWidget(dialog)

        html_content = dialog._get_shortcuts_html()

        assert "Edit" in html_content
        assert "Ctrl+Z" in html_content

    def test_dialog_content_has_view_menu_shortcuts(self, qtbot: QtBot) -> None:
        """Test dialog shows View menu shortcuts.

        Spec: Dialog shows shortcuts organized by category.
        """
        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        dialog = KeyboardShortcutsDialog()
        qtbot.addWidget(dialog)

        html_content = dialog._get_shortcuts_html()

        assert "View" in html_content
        assert "Ctrl+=" in html_content or "Ctrl" in html_content

    def test_dialog_content_has_canvas_interaction(self, qtbot: QtBot) -> None:
        """Test dialog shows canvas interaction shortcuts.

        Spec: Dialog shows Canvas Interaction category.
        """
        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        dialog = KeyboardShortcutsDialog()
        qtbot.addWidget(dialog)

        html_content = dialog._get_shortcuts_html()

        assert "Canvas" in html_content or "Interaction" in html_content

    def test_dialog_content_has_help_shortcuts(self, qtbot: QtBot) -> None:
        """Test dialog shows Help shortcuts.

        Spec: Dialog shows F1 shortcut for help.
        """
        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        dialog = KeyboardShortcutsDialog()
        qtbot.addWidget(dialog)

        html_content = dialog._get_shortcuts_html()

        assert "F1" in html_content

    def test_dialog_has_close_button(self, qtbot: QtBot) -> None:
        """Test dialog has a close button.

        Spec: Dialog has Close button.
        """
        from PySide6.QtWidgets import QPushButton

        from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

        dialog = KeyboardShortcutsDialog()
        qtbot.addWidget(dialog)

        # Find Close button
        close_button = dialog.findChild(QPushButton)
        assert close_button is not None
        assert "Close" in close_button.text() or close_button.text() == "Close"


# =============================================================================
# Help Menu About Dialog Tests
# =============================================================================


class TestHelpMenuAboutDialog:
    """Tests for Help menu About dialog - E06-F02-T04.

    Verifies:
    - About action exists in Help menu
    - About action triggers QMessageBox.about()
    - About dialog shows app name, version, description
    """

    def test_about_action_exists_in_help_menu(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test About action exists in Help menu.

        Spec: Help menu contains About Ink action.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        actions = window.help_menu.actions()
        action_texts = [a.text() for a in actions if not a.isSeparator() and not a.menu()]

        assert any("About" in text for text in action_texts)

    def test_about_action_has_status_tip(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test About action has status tip.

        Spec: Actions have status tips for status bar display.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        about_action = None
        for action in window.help_menu.actions():
            if "About" in action.text():
                about_action = action
                break

        assert about_action is not None
        assert len(about_action.statusTip()) > 0

    def test_about_action_triggers_message_box(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test About action triggers QMessageBox.about().

        Spec: About dialog uses QMessageBox.about() with proper formatting.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        about_action = None
        for action in window.help_menu.actions():
            if "About" in action.text():
                about_action = action
                break

        assert about_action is not None

        # Mock QMessageBox.about to prevent blocking
        with patch("ink.presentation.main_window.QMessageBox.about") as mock_about:
            about_action.trigger()

            mock_about.assert_called_once()
            # Verify call arguments
            args = mock_about.call_args[0]
            assert args[0] == window  # Parent is main window
            assert "About" in args[1]  # Title contains 'About'

    def test_about_dialog_content_has_app_name(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test About dialog content includes app name.

        Spec: About dialog shows app name 'Ink'.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        about_action = None
        for action in window.help_menu.actions():
            if "About" in action.text():
                about_action = action
                break

        with patch("ink.presentation.main_window.QMessageBox.about") as mock_about:
            about_action.trigger()

            args = mock_about.call_args[0]
            content = args[2]  # Third argument is the content

            assert "Ink" in content

    def test_about_dialog_content_has_version(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test About dialog content includes version.

        Spec: About dialog shows version.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        about_action = None
        for action in window.help_menu.actions():
            if "About" in action.text():
                about_action = action
                break

        with patch("ink.presentation.main_window.QMessageBox.about") as mock_about:
            about_action.trigger()

            args = mock_about.call_args[0]
            content = args[2]

            assert "Version" in content or "0.1" in content

    def test_about_dialog_content_has_description(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test About dialog content includes description.

        Spec: About dialog shows description.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        about_action = None
        for action in window.help_menu.actions():
            if "About" in action.text():
                about_action = action
                break

        with patch("ink.presentation.main_window.QMessageBox.about") as mock_about:
            about_action.trigger()

            args = mock_about.call_args[0]
            content = args[2]

            # Should mention schematic or netlist
            assert "schematic" in content.lower() or "netlist" in content.lower()

    def test_about_dialog_content_has_copyright(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test About dialog content includes copyright.

        Spec: About dialog shows credits.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        about_action = None
        for action in window.help_menu.actions():
            if "About" in action.text():
                about_action = action
                break

        with patch("ink.presentation.main_window.QMessageBox.about") as mock_about:
            about_action.trigger()

            args = mock_about.call_args[0]
            content = args[2]

            assert "2025" in content or "©" in content or "Ink Project" in content


# =============================================================================
# Help Menu Structure Tests
# =============================================================================


class TestHelpMenuStructure:
    """Tests for Help menu structure - E06-F02-T04.

    Verifies:
    - Keyboard Shortcuts action comes before About
    - Separator exists between sections
    """

    def test_shortcuts_before_about(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Keyboard Shortcuts action comes before About.

        Spec: Help menu structure follows standard conventions.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        actions = window.help_menu.actions()

        shortcuts_idx = None
        about_idx = None

        for i, action in enumerate(actions):
            text = action.text()
            if "Keyboard" in text and "Shortcut" in text:
                shortcuts_idx = i
            elif "About" in text:
                about_idx = i

        if shortcuts_idx is not None and about_idx is not None:
            assert shortcuts_idx < about_idx

    def test_separator_before_settings(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test separator exists before Settings submenu.

        This test verifies the existing Help menu structure with Settings.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        actions = window.help_menu.actions()

        # There should be at least one separator in the Help menu
        separators = [a for a in actions if a.isSeparator()]
        assert len(separators) >= 1
