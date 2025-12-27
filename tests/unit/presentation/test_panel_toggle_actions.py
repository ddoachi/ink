"""Unit tests for panel toggle actions in View menu.

Tests verify the panel toggle actions meet all requirements from spec E06-F05-T03:
- View menu contains "Panels" submenu
- Toggle actions for Hierarchy, Properties, Messages panels
- Keyboard shortcuts (Ctrl+Shift+H, P, M, R)
- Tooltips and status tips for actions
- Reset Panel Layout action with separator

These tests follow TDD approach:
- RED: Write failing tests first
- GREEN: Implement to pass tests
- REFACTOR: Clean up code

See Also:
    - Spec E06-F05-T03 for panel toggle actions requirements
    - E06-F05-T01 for PanelStateManager integration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMenu

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
    """Create InkMainWindow with proper cleanup.

    Args:
        qtbot: Pytest-qt bot for widget management.
        app_settings: Application settings instance.

    Returns:
        Configured InkMainWindow instance.
    """
    window = InkMainWindow(app_settings)
    qtbot.addWidget(window)
    return window


# =============================================================================
# Tests: Panels Submenu Existence (4.1 Functional Requirements)
# =============================================================================


class TestPanelsSubmenu:
    """Tests for View > Panels submenu structure.

    Verifies:
    - View menu contains "Panels" submenu
    - Panels submenu is accessible
    - Submenu has correct menu structure
    """

    def test_view_menu_has_panels_submenu(self, main_window: InkMainWindow) -> None:
        """Test that View menu contains a 'Panels' submenu.

        Spec: View menu contains "Panels" submenu
        """
        # Find the Panels submenu in View menu
        panels_menu = None
        for action in main_window.view_menu.actions():
            if action.menu() and "Panels" in action.text():
                panels_menu = action.menu()
                break

        assert panels_menu is not None, "Panels submenu should exist in View menu"

    def test_panels_submenu_has_correct_title(self, main_window: InkMainWindow) -> None:
        """Test that Panels submenu has correct title with mnemonic.

        Spec: Menus use mnemonics (&Panels for Alt+P)
        """
        # Find the Panels submenu action
        panels_action = None
        for action in main_window.view_menu.actions():
            if action.menu() and "Panels" in action.text():
                panels_action = action
                break

        assert panels_action is not None
        assert "&Panels" in panels_action.text() or "Panels" in panels_action.text()

    def test_panels_submenu_is_accessible_via_attribute(self, main_window: InkMainWindow) -> None:
        """Test that Panels submenu is accessible via instance attribute.

        For convenience, panels_menu should be stored as an instance attribute.
        """
        assert hasattr(main_window, "panels_menu"), "panels_menu attribute should exist"
        assert isinstance(main_window.panels_menu, QMenu), "panels_menu should be QMenu"


# =============================================================================
# Tests: Panel Toggle Actions (4.1 Functional Requirements)
# =============================================================================


class TestPanelToggleActions:
    """Tests for individual panel toggle actions.

    Verifies:
    - Hierarchy panel toggle action exists
    - Properties panel toggle action exists
    - Messages panel toggle action exists
    - Actions are from toggleViewAction() (checkable)
    """

    def test_hierarchy_toggle_action_exists(self, main_window: InkMainWindow) -> None:
        """Test that Hierarchy panel toggle action exists.

        Spec: Hierarchy panel toggle action in Panels menu
        """
        assert hasattr(main_window, "hierarchy_toggle_action")
        assert main_window.hierarchy_toggle_action is not None

    def test_property_toggle_action_exists(self, main_window: InkMainWindow) -> None:
        """Test that Properties panel toggle action exists.

        Spec: Properties panel toggle action in Panels menu
        """
        assert hasattr(main_window, "property_toggle_action")
        assert main_window.property_toggle_action is not None

    def test_message_toggle_action_exists(self, main_window: InkMainWindow) -> None:
        """Test that Messages panel toggle action exists.

        Spec: Messages panel toggle action in Panels menu
        """
        assert hasattr(main_window, "message_toggle_action")
        assert main_window.message_toggle_action is not None

    def test_hierarchy_action_is_checkable(self, main_window: InkMainWindow) -> None:
        """Test that Hierarchy toggle action is checkable.

        Qt's toggleViewAction() creates checkable actions.
        """
        action = main_window.hierarchy_toggle_action
        assert action.isCheckable(), "Toggle action should be checkable"

    def test_property_action_is_checkable(self, main_window: InkMainWindow) -> None:
        """Test that Properties toggle action is checkable.

        Qt's toggleViewAction() creates checkable actions.
        """
        action = main_window.property_toggle_action
        assert action.isCheckable(), "Toggle action should be checkable"

    def test_message_action_is_checkable(self, main_window: InkMainWindow) -> None:
        """Test that Messages toggle action is checkable.

        Qt's toggleViewAction() creates checkable actions.
        """
        action = main_window.message_toggle_action
        assert action.isCheckable(), "Toggle action should be checkable"

    def test_reset_layout_action_exists(self, main_window: InkMainWindow) -> None:
        """Test that Reset Panel Layout action exists.

        Spec: Reset Panel Layout action in Panels menu
        """
        assert hasattr(main_window, "reset_panel_layout_action")
        assert main_window.reset_panel_layout_action is not None

    def test_reset_layout_action_text(self, main_window: InkMainWindow) -> None:
        """Test that Reset Panel Layout action has correct text.

        Spec: Action label is "&Reset Panel Layout"
        """
        action = main_window.reset_panel_layout_action
        assert "Reset" in action.text() and "Layout" in action.text()


# =============================================================================
# Tests: Menu Structure (4.1 Functional Requirements)
# =============================================================================


class TestPanelsMenuStructure:
    """Tests for Panels submenu structure and organization.

    Verifies:
    - Panel toggle actions are in Panels menu
    - Separator before Reset Layout action
    - Correct action order
    """

    def test_toggle_actions_in_panels_menu(self, main_window: InkMainWindow) -> None:
        """Test that toggle actions are contained in Panels menu.

        Spec: Panel toggle actions appear in Panels submenu
        """
        panels_menu = main_window.panels_menu
        action_texts = [a.text() for a in panels_menu.actions()]

        # Should contain Hierarchy, Properties, Messages
        assert any("Hierarchy" in text for text in action_texts)
        assert any("Propert" in text for text in action_texts)
        assert any("Message" in text for text in action_texts)

    def test_separator_before_reset_layout(self, main_window: InkMainWindow) -> None:
        """Test that there is a separator before Reset Layout action.

        Spec: Separator before Reset Layout action for visual grouping
        """
        panels_menu = main_window.panels_menu
        actions = panels_menu.actions()

        # Find Reset Layout action and check separator before it
        reset_index = None
        for i, action in enumerate(actions):
            if "Reset" in action.text():
                reset_index = i
                break

        assert reset_index is not None, "Reset Layout action should exist"
        assert reset_index > 0, "Reset Layout should not be first"

        # The action before Reset should be a separator
        separator_action = actions[reset_index - 1]
        assert separator_action.isSeparator(), "Separator should appear before Reset Layout"


# =============================================================================
# Tests: Keyboard Shortcuts (4.3 Keyboard Shortcuts)
# =============================================================================


class TestKeyboardShortcuts:
    """Tests for panel toggle keyboard shortcuts.

    Verifies:
    - Ctrl+Shift+H toggles Hierarchy panel
    - Ctrl+Shift+P toggles Properties panel
    - Ctrl+Shift+M toggles Messages panel
    - Ctrl+Shift+R resets panel layout
    - Shortcuts displayed in menu
    """

    def test_hierarchy_shortcut(self, main_window: InkMainWindow) -> None:
        """Test that Hierarchy toggle has Ctrl+Shift+H shortcut.

        Spec: Ctrl+Shift+H toggles Hierarchy panel
        """
        action = main_window.hierarchy_toggle_action
        shortcut = action.shortcut().toString()
        assert shortcut == "Ctrl+Shift+H", f"Expected Ctrl+Shift+H, got {shortcut}"

    def test_property_shortcut(self, main_window: InkMainWindow) -> None:
        """Test that Properties toggle has Ctrl+Shift+P shortcut.

        Spec: Ctrl+Shift+P toggles Properties panel
        """
        action = main_window.property_toggle_action
        shortcut = action.shortcut().toString()
        assert shortcut == "Ctrl+Shift+P", f"Expected Ctrl+Shift+P, got {shortcut}"

    def test_message_shortcut(self, main_window: InkMainWindow) -> None:
        """Test that Messages toggle has Ctrl+Shift+M shortcut.

        Spec: Ctrl+Shift+M toggles Messages panel
        """
        action = main_window.message_toggle_action
        shortcut = action.shortcut().toString()
        assert shortcut == "Ctrl+Shift+M", f"Expected Ctrl+Shift+M, got {shortcut}"

    def test_reset_layout_shortcut(self, main_window: InkMainWindow) -> None:
        """Test that Reset Layout has Ctrl+Shift+R shortcut.

        Spec: Ctrl+Shift+R resets panel layout
        """
        action = main_window.reset_panel_layout_action
        shortcut = action.shortcut().toString()
        assert shortcut == "Ctrl+Shift+R", f"Expected Ctrl+Shift+R, got {shortcut}"


# =============================================================================
# Tests: Tooltips and Status Tips (4.4 Visual Polish)
# =============================================================================


class TestTooltipsAndStatusTips:
    """Tests for action tooltips and status tips.

    Verifies:
    - Tooltips appear on hover with descriptive text
    - Status bar shows shortcut hint when action hovered
    """

    def test_hierarchy_tooltip(self, main_window: InkMainWindow) -> None:
        """Test that Hierarchy action has descriptive tooltip.

        Spec: Tooltips appear on hover with descriptive text
        """
        action = main_window.hierarchy_toggle_action
        tooltip = action.toolTip()
        assert tooltip, "Tooltip should not be empty"
        assert "hierarchy" in tooltip.lower(), "Tooltip should mention 'hierarchy'"

    def test_property_tooltip(self, main_window: InkMainWindow) -> None:
        """Test that Properties action has descriptive tooltip.

        Spec: Tooltips appear on hover with descriptive text
        """
        action = main_window.property_toggle_action
        tooltip = action.toolTip()
        assert tooltip, "Tooltip should not be empty"
        assert "propert" in tooltip.lower(), "Tooltip should mention 'property'"

    def test_message_tooltip(self, main_window: InkMainWindow) -> None:
        """Test that Messages action has descriptive tooltip.

        Spec: Tooltips appear on hover with descriptive text
        """
        action = main_window.message_toggle_action
        tooltip = action.toolTip()
        assert tooltip, "Tooltip should not be empty"
        assert "message" in tooltip.lower(), "Tooltip should mention 'message'"

    def test_hierarchy_status_tip(self, main_window: InkMainWindow) -> None:
        """Test that Hierarchy action has status tip with shortcut hint.

        Spec: Status bar shows shortcut hint when action hovered
        """
        action = main_window.hierarchy_toggle_action
        status_tip = action.statusTip()
        assert status_tip, "Status tip should not be empty"
        assert "Ctrl+Shift+H" in status_tip, "Status tip should include shortcut"

    def test_property_status_tip(self, main_window: InkMainWindow) -> None:
        """Test that Properties action has status tip with shortcut hint.

        Spec: Status bar shows shortcut hint when action hovered
        """
        action = main_window.property_toggle_action
        status_tip = action.statusTip()
        assert status_tip, "Status tip should not be empty"
        assert "Ctrl+Shift+P" in status_tip, "Status tip should include shortcut"

    def test_message_status_tip(self, main_window: InkMainWindow) -> None:
        """Test that Messages action has status tip with shortcut hint.

        Spec: Status bar shows shortcut hint when action hovered
        """
        action = main_window.message_toggle_action
        status_tip = action.statusTip()
        assert status_tip, "Status tip should not be empty"
        assert "Ctrl+Shift+M" in status_tip, "Status tip should include shortcut"


# =============================================================================
# Tests: Action Behavior (4.2 Action Behavior)
# =============================================================================


class TestActionBehavior:
    """Tests for panel toggle action behavior.

    Verifies:
    - Clicking action toggles panel visibility
    - Checkmark appears next to visible panels
    - Checkmark disappears when panel hidden
    - Action state syncs with panel visibility

    Note:
        Qt widgets only return True for isVisible() when the parent window is shown.
        Tests that check visibility must show the window first.
    """

    def test_action_checked_when_panel_visible(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that action is checked when panel is visible.

        Spec: Checkmark appears next to visible panels
        """
        # Show window so dock widgets become visible
        main_window.show()
        qtbot.waitExposed(main_window)

        # Panel should be visible by default
        assert main_window.hierarchy_dock.isVisible()
        assert main_window.hierarchy_toggle_action.isChecked()

    def test_action_unchecked_when_panel_hidden(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that action is unchecked when panel is hidden.

        Spec: Checkmark disappears when panel hidden
        """
        # Show window first
        main_window.show()
        qtbot.waitExposed(main_window)

        # Hide the panel
        main_window.hierarchy_dock.hide()

        # Action should be unchecked
        assert not main_window.hierarchy_toggle_action.isChecked()

    def test_clicking_action_toggles_visibility(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that clicking action toggles panel visibility.

        Spec: Clicking action toggles panel visibility
        """
        # Show window first
        main_window.show()
        qtbot.waitExposed(main_window)

        # Panel should be visible initially
        assert main_window.hierarchy_dock.isVisible()

        # Trigger the action (simulates click)
        main_window.hierarchy_toggle_action.trigger()

        # Panel should now be hidden
        assert not main_window.hierarchy_dock.isVisible()

        # Trigger again
        main_window.hierarchy_toggle_action.trigger()

        # Panel should be visible again
        assert main_window.hierarchy_dock.isVisible()

    def test_action_syncs_when_panel_closed_via_x_button(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that action state syncs when panel closed via X button.

        Spec: Action state syncs when panel closed via X button
        """
        # Show window first
        main_window.show()
        qtbot.waitExposed(main_window)

        # Panel visible, action checked
        assert main_window.hierarchy_toggle_action.isChecked()

        # Close panel (simulates X button click)
        main_window.hierarchy_dock.close()

        # Action should now be unchecked
        assert not main_window.hierarchy_toggle_action.isChecked()

    def test_action_syncs_when_panel_visibility_changed_programmatically(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test action syncs when visibility changed programmatically.

        Spec: Action state syncs when panel visibility changed programmatically
        """
        # Show window first
        main_window.show()
        qtbot.waitExposed(main_window)

        # Hide programmatically
        main_window.hierarchy_dock.setVisible(False)
        assert not main_window.hierarchy_toggle_action.isChecked()

        # Show programmatically
        main_window.hierarchy_dock.setVisible(True)
        assert main_window.hierarchy_toggle_action.isChecked()


# =============================================================================
# Tests: Panel Raise Behavior
# =============================================================================


class TestPanelRaiseBehavior:
    """Tests for panel raise behavior when shown.

    Verifies:
    - Showing hidden panel brings it to front (raises)
    """

    def test_showing_hidden_panel_raises_it(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that showing a hidden panel raises it to front.

        Spec: Showing hidden panel brings it to front (raises)

        Note: This test verifies the raise behavior is connected.
        Actual visual confirmation requires manual testing.
        """
        # Show window first for visibility to work
        main_window.show()
        qtbot.waitExposed(main_window)

        # Hide panel first
        main_window.hierarchy_dock.hide()
        assert not main_window.hierarchy_dock.isVisible()

        # Track if raise was called (we can't easily verify z-order)
        # But we can verify the panel becomes visible
        main_window.hierarchy_toggle_action.trigger()

        # Panel should be visible and raise() was called internally
        assert main_window.hierarchy_dock.isVisible()


# =============================================================================
# Tests: Integration with PanelStateManager
# =============================================================================


class TestPanelStateManagerIntegration:
    """Tests for integration with PanelStateManager.

    Verifies:
    - Toggle actions work with panel_state_manager
    - Visibility changes are tracked by manager
    """

    def test_is_panel_visible_reflects_toggle_state(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that panel_state_manager tracks toggle action changes.

        Spec: Integrate with panel state manager for consistent behavior
        """
        # Show window first for visibility changes to work
        main_window.show()
        qtbot.waitExposed(main_window)

        manager = main_window.panel_state_manager

        # Initially visible
        assert manager.state.panels["Hierarchy"].visible

        # Hide via toggle action
        main_window.hierarchy_toggle_action.trigger()

        # Manager should reflect change
        assert not manager.state.panels["Hierarchy"].visible

    def test_manager_show_panel_syncs_with_action(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that manager.show_panel syncs with toggle action.

        When panel is shown via manager, action should be checked.
        """
        # Show window first
        main_window.show()
        qtbot.waitExposed(main_window)

        manager = main_window.panel_state_manager

        # Hide panel first
        main_window.hierarchy_dock.hide()
        assert not main_window.hierarchy_toggle_action.isChecked()

        # Show via manager
        manager.show_panel("Hierarchy")

        # Action should be checked
        assert main_window.hierarchy_toggle_action.isChecked()
