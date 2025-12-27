"""Unit tests for InkMainWindow status bar functionality.

Tests verify the status bar infrastructure meets all requirements from spec E06-F04-T01:
- QStatusBar created and attached to main window
- Four permanent widgets (file, zoom, selection, object count)
- Visual separators between widgets
- Initial placeholder text on all labels
- Minimum widths configured for all widgets

These tests follow TDD methodology:
- RED phase: Tests written first, expecting failures
- GREEN phase: Implementation to pass all tests
- REFACTOR phase: Code cleanup while tests pass

See Also:
    - Spec E06-F04-T01 for status bar setup requirements
    - Spec E06-F04-T02 for selection status display (downstream)
    - Spec E06-F04-T03 for zoom level display (downstream)
    - Spec E06-F04-T04 for file and object count display (downstream)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QLabel, QStatusBar

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
# Test Classes
# =============================================================================


class TestStatusBarCreation:
    """Tests for status bar creation and attachment."""

    def test_status_bar_exists(self, main_window: InkMainWindow) -> None:
        """Test that status bar is created and attached to main window.

        The status bar should be a QStatusBar instance attached via
        setStatusBar() during window initialization.
        """
        status_bar = main_window.statusBar()

        assert status_bar is not None
        assert isinstance(status_bar, QStatusBar)

    def test_status_bar_is_visible(self, main_window: InkMainWindow) -> None:
        """Test that status bar is visible by default.

        Status bar should be visible immediately on window creation,
        not hidden or collapsed.
        """
        main_window.show()
        status_bar = main_window.statusBar()

        assert status_bar.isVisible()


class TestStatusBarWidgets:
    """Tests for status bar widget creation."""

    def test_file_label_exists(self, main_window: InkMainWindow) -> None:
        """Test that file_label instance attribute is created.

        The file_label is a QLabel for displaying the current file name.
        """
        assert hasattr(main_window, "file_label")
        assert isinstance(main_window.file_label, QLabel)

    def test_zoom_label_exists(self, main_window: InkMainWindow) -> None:
        """Test that zoom_label instance attribute is created.

        The zoom_label is a QLabel for displaying the current zoom level.
        """
        assert hasattr(main_window, "zoom_label")
        assert isinstance(main_window.zoom_label, QLabel)

    def test_selection_label_exists(self, main_window: InkMainWindow) -> None:
        """Test that selection_label instance attribute is created.

        The selection_label is a QLabel for displaying selection count.
        """
        assert hasattr(main_window, "selection_label")
        assert isinstance(main_window.selection_label, QLabel)

    def test_object_count_label_exists(self, main_window: InkMainWindow) -> None:
        """Test that object_count_label instance attribute is created.

        The object_count_label is a QLabel for displaying cell/net counts.
        """
        assert hasattr(main_window, "object_count_label")
        assert isinstance(main_window.object_count_label, QLabel)


class TestStatusBarInitialText:
    """Tests for initial placeholder text on status labels."""

    def test_file_label_initial_text(self, main_window: InkMainWindow) -> None:
        """Test file_label shows 'No file loaded' initially.

        This indicates no netlist file is currently open.
        """
        assert main_window.file_label.text() == "No file loaded"

    def test_zoom_label_initial_text(self, main_window: InkMainWindow) -> None:
        """Test zoom_label shows 'Zoom: 100%' initially.

        100% is the default zoom level on application start.
        """
        assert main_window.zoom_label.text() == "Zoom: 100%"

    def test_selection_label_initial_text(self, main_window: InkMainWindow) -> None:
        """Test selection_label shows 'Selected: 0' initially.

        No objects are selected when the application starts.
        """
        assert main_window.selection_label.text() == "Selected: 0"

    def test_object_count_label_initial_text(self, main_window: InkMainWindow) -> None:
        """Test object_count_label shows 'Cells: 0 / Nets: 0' initially.

        No schematic is loaded, so both counts are zero.
        """
        assert main_window.object_count_label.text() == "Cells: 0 / Nets: 0"


class TestStatusBarWidgetMinimumWidths:
    """Tests for minimum width configuration on status labels."""

    def test_file_label_minimum_width(self, main_window: InkMainWindow) -> None:
        """Test file_label has minimum width of 200 pixels.

        This accommodates typical file names like 'circuit_design_v2.ckt'.
        """
        assert main_window.file_label.minimumWidth() >= 200

    def test_zoom_label_minimum_width(self, main_window: InkMainWindow) -> None:
        """Test zoom_label has minimum width of 100 pixels.

        This accommodates 'Zoom: 1000%' (maximum zoom level).
        """
        assert main_window.zoom_label.minimumWidth() >= 100

    def test_selection_label_minimum_width(self, main_window: InkMainWindow) -> None:
        """Test selection_label has minimum width of 100 pixels.

        This accommodates 'Selected: 9999' (large selections).
        """
        assert main_window.selection_label.minimumWidth() >= 100

    def test_object_count_label_minimum_width(self, main_window: InkMainWindow) -> None:
        """Test object_count_label has minimum width of 150 pixels.

        This accommodates 'Cells: 9999 / Nets: 9999'.
        """
        assert main_window.object_count_label.minimumWidth() >= 150


class TestStatusBarSeparators:
    """Tests for visual separators between status widgets."""

    def test_separators_exist(self, main_window: InkMainWindow) -> None:
        """Test that three separators exist between four widgets.

        Layout: [file] | [zoom] | [selection] | [count]
        Separators appear as QLabel widgets with '│' character.
        """
        status_bar = main_window.statusBar()

        # Find all QLabel children that contain the separator character
        separators = [child for child in status_bar.findChildren(QLabel) if "│" in child.text()]

        # Should have exactly 3 separators between 4 widgets
        assert len(separators) == 3

    def test_separator_has_gray_styling(self, main_window: InkMainWindow) -> None:
        """Test that separators have gray color styling.

        Separators should be subtle (gray) to not compete with content.
        The styling is applied via setStyleSheet().
        """
        status_bar = main_window.statusBar()

        # Find separator widgets
        separators = [child for child in status_bar.findChildren(QLabel) if "│" in child.text()]

        # At least one separator should have gray in its stylesheet
        assert len(separators) > 0

        # Check that separators have some styling applied
        # The exact stylesheet content may vary, but it should exist
        for sep in separators:
            stylesheet = sep.styleSheet()
            assert "gray" in stylesheet.lower() or "color" in stylesheet.lower()


class TestStatusBarLayout:
    """Tests for status bar layout behavior."""

    def test_status_bar_has_appropriate_height(self, main_window: InkMainWindow) -> None:
        """Test status bar has reasonable minimum height for readability.

        Status bar should not collapse to tiny size. A typical status bar
        is at least 20 pixels high to show readable text.
        """
        main_window.show()
        status_bar = main_window.statusBar()

        # Process events to ensure layout is calculated
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()

        # Status bar should have reasonable height (at least for readable text)
        assert status_bar.height() >= 20

    def test_widgets_are_permanent(self, main_window: InkMainWindow) -> None:
        """Test that status widgets are added as permanent widgets.

        Permanent widgets are not displaced by temporary status messages.
        They should persist even when showMessage() is called.
        """
        # Window must be shown for widget visibility to be testable
        main_window.show()

        status_bar = main_window.statusBar()

        # Show a temporary message
        status_bar.showMessage("Temporary message", 0)

        # Permanent widgets should still be accessible and visible
        assert main_window.file_label.isVisible()
        assert main_window.zoom_label.isVisible()
        assert main_window.selection_label.isVisible()
        assert main_window.object_count_label.isVisible()

        # Clear the temporary message
        status_bar.clearMessage()
