"""Unit tests for InkMainWindow selection status display functionality.

Tests verify the selection status display meets all requirements from spec E06-F04-T02:
- update_selection_status() method updates selection_label correctly
- Method handles various count values (0, 1, multiple, large numbers)
- Signal connection to selection service (when available)
- Graceful handling when selection service is not initialized

These tests follow TDD methodology:
- RED phase: Tests written first, expecting failures
- GREEN phase: Implementation to pass all tests
- REFACTOR phase: Code cleanup while tests pass

Dependencies:
    - E06-F04-T01: Status bar setup (selection_label exists)
    - E04-F01: Selection service (not yet implemented - tests handle gracefully)

See Also:
    - Spec E06-F04-T02 for selection status display requirements
    - Spec E06-F04-T01 for status bar setup (upstream dependency)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

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
# Test Classes - update_selection_status() Method
# =============================================================================


class TestUpdateSelectionStatusMethod:
    """Tests for update_selection_status() method existence and behavior."""

    def test_method_exists(self, main_window: InkMainWindow) -> None:
        """Test that update_selection_status() method exists on InkMainWindow.

        The method should be a callable that accepts a count parameter.
        """
        assert hasattr(main_window, "update_selection_status")
        assert callable(main_window.update_selection_status)

    def test_update_selection_status_zero(self, main_window: InkMainWindow) -> None:
        """Test selection status shows 0 for empty selection.

        When count is 0, the label should display "Selected: 0".
        """
        main_window.update_selection_status(0)
        assert main_window.selection_label.text() == "Selected: 0"

    def test_update_selection_status_single(self, main_window: InkMainWindow) -> None:
        """Test selection status shows 1 for single selection.

        When count is 1, the label should display "Selected: 1".
        """
        main_window.update_selection_status(1)
        assert main_window.selection_label.text() == "Selected: 1"

    def test_update_selection_status_multiple(
        self, main_window: InkMainWindow
    ) -> None:
        """Test selection status shows correct count for multiple selections.

        When count is greater than 1, the label should display "Selected: N".
        """
        main_window.update_selection_status(5)
        assert main_window.selection_label.text() == "Selected: 5"

        main_window.update_selection_status(42)
        assert main_window.selection_label.text() == "Selected: 42"

    def test_update_selection_status_large_count(
        self, main_window: InkMainWindow
    ) -> None:
        """Test selection status handles large counts correctly.

        Large selections (1000+ items) should display normally without
        any formatting issues or performance concerns.
        """
        main_window.update_selection_status(1000)
        assert main_window.selection_label.text() == "Selected: 1000"

        main_window.update_selection_status(9999)
        assert main_window.selection_label.text() == "Selected: 9999"

    def test_update_selection_status_format_consistency(
        self, main_window: InkMainWindow
    ) -> None:
        """Test selection status maintains consistent format.

        All count values should use the format "Selected: N" where N is
        the count. No extra spaces, no alternative formats.
        """
        # Test various values for consistent format
        test_values = [0, 1, 10, 100, 1000]

        for count in test_values:
            main_window.update_selection_status(count)
            expected = f"Selected: {count}"
            assert main_window.selection_label.text() == expected


class TestUpdateSelectionStatusEdgeCases:
    """Tests for edge cases in update_selection_status()."""

    def test_update_selection_status_rapid_updates(
        self, main_window: InkMainWindow
    ) -> None:
        """Test rapid consecutive updates are handled correctly.

        The label should reflect the most recent value after rapid updates.
        This simulates scenarios like box selection where many items may
        be selected in quick succession.
        """
        # Rapid updates
        for i in range(100):
            main_window.update_selection_status(i)

        # Should show the last value
        assert main_window.selection_label.text() == "Selected: 99"

    def test_update_selection_status_same_value(
        self, main_window: InkMainWindow
    ) -> None:
        """Test updating with same value doesn't cause issues.

        Calling update with the same count should work without errors.
        This can happen when selection is refreshed but hasn't changed.
        """
        main_window.update_selection_status(5)
        assert main_window.selection_label.text() == "Selected: 5"

        # Same value again
        main_window.update_selection_status(5)
        assert main_window.selection_label.text() == "Selected: 5"


# =============================================================================
# Test Classes - Signal Connection
# =============================================================================


class TestConnectStatusSignals:
    """Tests for _connect_status_signals() method."""

    def test_connect_status_signals_method_exists(
        self, main_window: InkMainWindow
    ) -> None:
        """Test that _connect_status_signals() method exists.

        This method is responsible for connecting selection service signals
        to the status bar update methods.
        """
        assert hasattr(main_window, "_connect_status_signals")
        assert callable(main_window._connect_status_signals)

    def test_no_error_without_selection_service(
        self, main_window: InkMainWindow
    ) -> None:
        """Test no error when selection service is not initialized.

        The method should handle the case where selection_service attribute
        doesn't exist yet (during initialization or before service is set up).
        """
        # Ensure selection_service doesn't exist
        if hasattr(main_window, "selection_service"):
            delattr(main_window, "selection_service")

        # Calling should not raise any exception
        main_window._connect_status_signals()

        # Window should still be functional
        assert main_window.selection_label.text() == "Selected: 0"


class TestSelectionServiceIntegration:
    """Tests for integration with selection service when available.

    These tests use mock selection service to verify signal connection
    works correctly. When E04-F01 (Selection Service) is implemented,
    additional integration tests may be added.
    """

    def test_selection_signal_updates_status(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test selection changes trigger status update.

        When selection_service.selection_changed signal is emitted with
        items, the selection_label should update to show the count.
        """
        from PySide6.QtCore import QObject

        # Create a mock selection service with a signal
        class MockSelectionService(QObject):
            """Mock selection service with selection_changed signal."""

            selection_changed = Signal(list)

        mock_service = MockSelectionService()
        main_window.selection_service = mock_service

        # Reconnect signals with the mock service
        main_window._connect_status_signals()

        # Emit selection changed signal with 3 items
        mock_items = [Mock(), Mock(), Mock()]
        mock_service.selection_changed.emit(mock_items)

        # Status should update
        assert main_window.selection_label.text() == "Selected: 3"

    def test_selection_cleared_updates_status(
        self, main_window: InkMainWindow, qtbot: QtBot
    ) -> None:
        """Test clearing selection shows 0.

        When selection is cleared (empty list emitted), the label should
        show "Selected: 0".
        """
        from PySide6.QtCore import QObject

        # Create a mock selection service with a signal
        class MockSelectionService(QObject):
            """Mock selection service with selection_changed signal."""

            selection_changed = Signal(list)

        mock_service = MockSelectionService()
        main_window.selection_service = mock_service

        # Reconnect signals with the mock service
        main_window._connect_status_signals()

        # Set initial selection
        mock_service.selection_changed.emit([Mock(), Mock()])
        assert main_window.selection_label.text() == "Selected: 2"

        # Clear selection
        mock_service.selection_changed.emit([])
        assert main_window.selection_label.text() == "Selected: 0"

    def test_selection_service_missing_signal(
        self, main_window: InkMainWindow
    ) -> None:
        """Test graceful handling when service lacks selection_changed signal.

        If a selection service exists but doesn't have the expected signal,
        the connection should be skipped without error.
        """
        # Create a mock without the signal
        mock_service = Mock(spec=[])  # Empty spec, no selection_changed

        main_window.selection_service = mock_service

        # Should not raise exception
        main_window._connect_status_signals()

        # Window should still be functional
        assert main_window.selection_label.text() == "Selected: 0"
