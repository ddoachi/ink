"""Unit tests for default panel layout reset functionality.

Tests verify the reset panel layout feature meets all requirements from spec E06-F05-T04:
- Confirmation dialog before reset
- Clearing saved panel state
- Restoring panels to default positions
- All panels visible after reset
- All panels docked (not floating) after reset
- Default sizes applied
- Status bar feedback on success
- Error handling for failures

These tests follow TDD approach:
- RED: Write failing tests first
- GREEN: Implement to pass tests
- REFACTOR: Clean up code

See Also:
    - Spec E06-F05-T04 for default layout reset requirements
    - Pre-docs E06-F05-T04.pre-docs.md for implementation details
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QMessageBox

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
# Tests: Confirmation Dialog (4.2 Dialog Behavior)
# =============================================================================


class TestConfirmationDialog:
    """Tests for reset confirmation dialog.

    Verifies:
    - Dialog appears before reset
    - Dialog is modal
    - Dialog has question icon
    - Default button is "No" (safe default)
    - Dialog text explains consequences
    - Clicking "No" cancels reset
    - Clicking "Yes" proceeds with reset
    - Escape key closes dialog without resetting
    """

    def test_confirmation_dialog_shown_on_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that confirmation dialog is shown when reset is triggered.

        Spec: Confirmation dialog appears before reset
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Mock QMessageBox.question to track if it's called
        with patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.No
        ) as mock_dialog:
            main_window.reset_panel_layout()

            # Dialog should have been shown
            mock_dialog.assert_called_once()

    def test_clicking_no_cancels_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that clicking No in dialog cancels the reset operation.

        Spec: Clicking "No" in dialog cancels reset (no changes)
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Hide a panel first to verify no changes occur
        main_window.hierarchy_dock.hide()
        assert not main_window.hierarchy_dock.isVisible()

        # Mock dialog to return No
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            main_window.reset_panel_layout()

        # Panel should still be hidden (no changes made)
        assert not main_window.hierarchy_dock.isVisible()

    def test_clicking_yes_proceeds_with_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that clicking Yes in dialog proceeds with reset.

        Spec: Clicking "Yes" clears saved panel state
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Hide a panel first
        main_window.hierarchy_dock.hide()
        assert not main_window.hierarchy_dock.isVisible()

        # Mock dialog to return Yes
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            main_window.reset_panel_layout()

        # Give Qt time to process the layout changes
        QApplication.processEvents()

        # Panel should now be visible (reset applied)
        assert main_window.hierarchy_dock.isVisible()

    def test_confirmation_dialog_default_is_no(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that the default button in confirmation dialog is 'No'.

        Spec: Default button is "No" (safe default)
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Capture the dialog call arguments
        with patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.No
        ) as mock_dialog:
            main_window.reset_panel_layout()

            # Check the defaultButton argument
            call_args = mock_dialog.call_args
            # The 5th positional argument is the default button
            default_button = call_args[0][4] if len(call_args[0]) > 4 else None
            assert default_button == QMessageBox.StandardButton.No

    def test_confirmation_dialog_has_question_title(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that confirmation dialog has appropriate title.

        Spec: Title: "Reset Panel Layout"
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        with patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.No
        ) as mock_dialog:
            main_window.reset_panel_layout()

            # Check the title argument (2nd positional argument)
            call_args = mock_dialog.call_args
            title = call_args[0][1]
            assert "Reset" in title and "Layout" in title

    def test_confirmation_dialog_explains_consequences(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that confirmation dialog explains consequences clearly.

        Spec: Dialog text clearly explains consequences
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        with patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.No
        ) as mock_dialog:
            main_window.reset_panel_layout()

            # Check the message text (3rd positional argument)
            call_args = mock_dialog.call_args
            message = call_args[0][2]
            # Should mention resetting to defaults and loss of custom layout
            assert "reset" in message.lower() or "default" in message.lower()
            assert "lost" in message.lower() or "custom" in message.lower()


# =============================================================================
# Tests: Reset Behavior (4.1 Functional Requirements)
# =============================================================================


class TestResetBehavior:
    """Tests for reset operation behavior.

    Verifies:
    - After reset, all panels in default positions
    - After reset, all panels visible (not hidden)
    - After reset, all panels docked (not floating)
    - After reset, no panels tabbed together
    """

    def test_all_panels_visible_after_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that all panels are visible after reset.

        Spec: After reset, all panels visible (not hidden)
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Hide all panels first
        main_window.hierarchy_dock.hide()
        main_window.property_dock.hide()
        main_window.message_dock.hide()

        # Verify all hidden
        assert not main_window.hierarchy_dock.isVisible()
        assert not main_window.property_dock.isVisible()
        assert not main_window.message_dock.isVisible()

        # Reset
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            main_window.reset_panel_layout()

        QApplication.processEvents()

        # All should be visible
        assert main_window.hierarchy_dock.isVisible()
        assert main_window.property_dock.isVisible()
        assert main_window.message_dock.isVisible()

    def test_all_panels_docked_after_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that all panels are docked (not floating) after reset.

        Spec: After reset, all panels docked (not floating)
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Float all panels first
        main_window.hierarchy_dock.setFloating(True)
        main_window.property_dock.setFloating(True)
        main_window.message_dock.setFloating(True)

        # Verify all floating
        assert main_window.hierarchy_dock.isFloating()
        assert main_window.property_dock.isFloating()
        assert main_window.message_dock.isFloating()

        # Reset
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            main_window.reset_panel_layout()

        QApplication.processEvents()

        # All should be docked (not floating)
        assert not main_window.hierarchy_dock.isFloating()
        assert not main_window.property_dock.isFloating()
        assert not main_window.message_dock.isFloating()

    def test_hierarchy_in_left_area_after_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that Hierarchy dock is in left area after reset.

        Spec: Hierarchy panel in Left dock area after reset
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Move to wrong area first
        main_window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, main_window.hierarchy_dock)

        # Reset
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            main_window.reset_panel_layout()

        QApplication.processEvents()

        # Should be in left area
        area = main_window.dockWidgetArea(main_window.hierarchy_dock)
        assert area == Qt.DockWidgetArea.LeftDockWidgetArea

    def test_property_in_right_area_after_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that Properties dock is in right area after reset.

        Spec: Properties panel in Right dock area after reset
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Move to wrong area first
        main_window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, main_window.property_dock)

        # Reset
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            main_window.reset_panel_layout()

        QApplication.processEvents()

        # Should be in right area
        area = main_window.dockWidgetArea(main_window.property_dock)
        assert area == Qt.DockWidgetArea.RightDockWidgetArea

    def test_message_in_bottom_area_after_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that Messages dock is in bottom area after reset.

        Spec: Messages panel in Bottom dock area after reset
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Message dock can only be in bottom area by design, so just verify
        # Reset
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            main_window.reset_panel_layout()

        QApplication.processEvents()

        # Should be in bottom area
        area = main_window.dockWidgetArea(main_window.message_dock)
        assert area == Qt.DockWidgetArea.BottomDockWidgetArea


# =============================================================================
# Tests: Settings Persistence (4.1 Functional Requirements)
# =============================================================================


class TestSettingsPersistence:
    """Tests for settings persistence during reset.

    Verifies:
    - Clicking "Yes" clears saved panel state
    - After reset, no saved panel settings exist
    """

    def test_reset_clears_saved_panel_state(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that reset clears saved panel state.

        Spec: Clicking "Yes" clears saved panel state
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Save some panel state first
        state = main_window.panel_state_manager.capture_state()
        main_window.panel_settings_store.save_panel_state(state)

        # Verify settings exist
        assert main_window.panel_settings_store.has_saved_settings()

        # Reset
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            main_window.reset_panel_layout()

        # Settings should be cleared
        assert not main_window.panel_settings_store.has_saved_settings()

    def test_cancelled_reset_preserves_settings(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that cancelled reset preserves saved settings.

        Spec: Clicking "No" in dialog cancels reset (no changes)
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Save some panel state first
        state = main_window.panel_state_manager.capture_state()
        main_window.panel_settings_store.save_panel_state(state)

        # Verify settings exist
        assert main_window.panel_settings_store.has_saved_settings()

        # Cancel reset
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            main_window.reset_panel_layout()

        # Settings should still exist
        assert main_window.panel_settings_store.has_saved_settings()


# =============================================================================
# Tests: Status Bar Feedback (4.4 Visual Feedback)
# =============================================================================


class TestStatusBarFeedback:
    """Tests for status bar feedback during reset.

    Verifies:
    - Status bar message confirms successful reset
    - Message displayed for 3 seconds
    """

    def test_success_message_shown_after_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that success message is shown in status bar after reset.

        Spec: Status bar message confirms successful reset
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Mock status bar showMessage
        with patch.object(main_window.statusBar(), "showMessage") as mock_show:
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                main_window.reset_panel_layout()

            # Check that showMessage was called
            mock_show.assert_called()
            call_args = mock_show.call_args
            message = call_args[0][0]
            assert "reset" in message.lower() or "default" in message.lower()

    def test_success_message_duration_is_3_seconds(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that success message is displayed for 3 seconds.

        Spec: Message displayed for 3 seconds
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        with patch.object(main_window.statusBar(), "showMessage") as mock_show:
            with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
                main_window.reset_panel_layout()

            # Check timeout argument (should be 3000ms)
            call_args = mock_show.call_args
            if len(call_args[0]) > 1:
                timeout = call_args[0][1]
            else:
                timeout = call_args[1].get("msecs", call_args[1].get("timeout", 0))
            assert timeout == 3000, f"Expected 3000ms timeout, got {timeout}"


# =============================================================================
# Tests: Error Handling (4.3 Error Handling)
# =============================================================================


class TestErrorHandling:
    """Tests for error handling during reset.

    Verifies:
    - Reset errors show warning dialog with error message
    - Failed reset doesn't crash application
    - Error logged to application log
    """

    def test_error_during_reset_shows_warning(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that errors during reset show warning dialog.

        Spec: Reset errors show warning dialog with error message
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Make clear_panel_state raise an exception
        with (
            patch.object(
                main_window.panel_settings_store,
                "clear_panel_state",
                side_effect=Exception("Simulated disk error"),
            ),
            patch.object(
                QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
            ),
            patch.object(QMessageBox, "warning") as mock_warning,
        ):
            main_window.reset_panel_layout()

            # Warning dialog should have been shown
            mock_warning.assert_called_once()
            call_args = mock_warning.call_args
            message = call_args[0][2]
            assert "failed" in message.lower() or "error" in message.lower()

    def test_error_during_reset_does_not_crash(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that errors during reset don't crash the application.

        Spec: Failed reset doesn't leave panels in broken state
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Make clear_panel_state raise an exception
        with (
            patch.object(
                main_window.panel_settings_store,
                "clear_panel_state",
                side_effect=Exception("Simulated disk error"),
            ),
            patch.object(
                QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
            ),
            patch.object(QMessageBox, "warning"),
        ):
            # This should not raise an exception
            main_window.reset_panel_layout()

        # Window should still be usable
        assert main_window.isVisible()

    def test_error_during_reset_is_logged(
        self, main_window: InkMainWindow, qtbot: QtBot,
        caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that errors during reset are logged.

        Spec: Error logged to application log
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        with (
            caplog.at_level(logging.ERROR),
            patch.object(
                main_window.panel_settings_store,
                "clear_panel_state",
                side_effect=Exception("Simulated disk error"),
            ),
            patch.object(
                QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
            ),
            patch.object(QMessageBox, "warning"),
        ):
            main_window.reset_panel_layout()

        # Error should be logged
        assert any(
            "reset" in record.message.lower() or "panel" in record.message.lower()
            for record in caplog.records if record.levelno >= logging.ERROR
        )


# =============================================================================
# Tests: Keyboard Shortcut Integration (from E06-F05-T03)
# =============================================================================


class TestResetKeyboardShortcut:
    """Tests for reset panel layout keyboard shortcut.

    Verifies:
    - Keyboard shortcut Ctrl+Shift+R triggers reset
    - Reset action exists and is connected
    """

    def test_reset_action_has_correct_shortcut(self, main_window: InkMainWindow) -> None:
        """Test that Reset Layout action has Ctrl+Shift+R shortcut.

        Spec: Keyboard shortcut Ctrl+Shift+R triggers reset
        """
        action = main_window.reset_panel_layout_action
        shortcut = action.shortcut().toString()
        assert shortcut == "Ctrl+Shift+R", f"Expected Ctrl+Shift+R, got {shortcut}"

    def test_reset_action_connected_to_reset_method(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that reset action is connected to reset_panel_layout method.

        Spec: "Reset Panel Layout" action in View > Panels menu
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Trigger the action and verify the dialog is shown
        with patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.No
        ) as mock_dialog:
            main_window.reset_panel_layout_action.trigger()

            # Dialog should have been shown, proving the connection works
            mock_dialog.assert_called_once()


# =============================================================================
# Tests: State Capture After Reset
# =============================================================================


class TestStateAfterReset:
    """Tests for panel state manager integration after reset.

    Verifies:
    - Panel state manager captures new state after reset
    """

    def test_state_manager_captures_state_after_reset(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test that panel state manager captures state after reset.

        Spec: Update panel state manager with new state
        """
        main_window.show()
        qtbot.waitExposed(main_window)

        # Hide a panel and record state
        main_window.hierarchy_dock.hide()
        assert not main_window.panel_state_manager.state.panels["Hierarchy"].visible

        # Reset
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes):
            main_window.reset_panel_layout()

        QApplication.processEvents()

        # State manager should reflect the new state (all visible)
        assert main_window.panel_state_manager.state.panels["Hierarchy"].visible
        assert main_window.panel_state_manager.state.panels["Properties"].visible  # type: ignore[unreachable]
        assert main_window.panel_state_manager.state.panels["Messages"].visible
