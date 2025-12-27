"""Unit tests for Toolbar Infrastructure - E06-F03-T01.

Tests verify the main toolbar meets all requirements from spec E06-F03-T01:
- QToolBar instance created with name "Main Toolbar"
- Toolbar has object name "MainToolBar" for settings persistence
- Toolbar is non-movable (setMovable(False))
- Icon size set to 24x24 pixels
- Button style set to icon-only mode
- Toolbar attached to main window in top toolbar area
- Toolbar reference stored in instance variable (self._toolbar)

These tests follow TDD methodology:
- RED phase: Tests written before implementation (expect failures)
- GREEN phase: Implementation makes tests pass
- REFACTOR phase: Code cleanup with tests as safety net

See Also:
    - Spec E06-F03-T01 for toolbar infrastructure requirements
    - Spec E06-F03-T02 for view control tools (adds actions)
    - Spec E06-F03-T03 for edit/search tools (adds actions)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtWidgets import QToolBar

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


# =============================================================================
# Test Classes - Toolbar Creation
# =============================================================================


class TestToolbarCreated:
    """Tests for toolbar creation and attachment to main window."""

    def test_toolbar_exists_in_main_window(self, main_window: InkMainWindow) -> None:
        """Test that a QToolBar instance is created and attached to main window.

        The toolbar should be findable via Qt's findChild mechanism using
        the object name "MainToolBar".

        Acceptance Criteria:
            - QToolBar instance created with name "Main Toolbar"
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None, "MainToolBar should exist as child of main window"

    def test_toolbar_has_correct_window_title(self, main_window: InkMainWindow) -> None:
        """Test toolbar has window title "Main Toolbar".

        The window title is displayed when toolbar is floated (future feature)
        and helps identify the toolbar in Qt Designer/Inspector.

        Acceptance Criteria:
            - QToolBar instance created with name "Main Toolbar"
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None
        assert toolbar.windowTitle() == "Main Toolbar"

    def test_toolbar_has_object_name_for_persistence(self, main_window: InkMainWindow) -> None:
        """Test toolbar has object name "MainToolBar" for QSettings persistence.

        Object name is required for Qt's saveState()/restoreState() to work
        across sessions. Without it, toolbar state cannot be persisted.

        Acceptance Criteria:
            - Toolbar has object name "MainToolBar" for settings persistence
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None
        assert toolbar.objectName() == "MainToolBar"


# =============================================================================
# Test Classes - Toolbar Configuration
# =============================================================================


class TestToolbarConfiguration:
    """Tests for toolbar configuration properties."""

    def test_toolbar_is_not_movable(self, main_window: InkMainWindow) -> None:
        """Test toolbar is fixed (non-movable) for MVP.

        A fixed toolbar provides consistent layout and prevents accidental
        rearrangement. Customization can be added in future versions.

        Acceptance Criteria:
            - Toolbar is non-movable (setMovable(False))
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None
        assert not toolbar.isMovable(), "Toolbar should be non-movable for MVP"

    def test_toolbar_icon_size_is_24x24(self, main_window: InkMainWindow) -> None:
        """Test toolbar icon size is 24x24 pixels.

        24x24 is a standard toolbar icon size that:
        - Is readable on high-DPI displays
        - Maintains consistent button sizing
        - Works well with common icon libraries

        Acceptance Criteria:
            - Icon size set to 24x24 pixels
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None
        expected_size = QSize(24, 24)
        assert toolbar.iconSize() == expected_size, f"Icon size should be {expected_size}"

    def test_toolbar_button_style_is_icon_only(self, main_window: InkMainWindow) -> None:
        """Test toolbar button style is icon-only mode.

        Icon-only mode provides:
        - Compact toolbar appearance
        - Focus on visual recognition
        - Space efficiency (tooltips provide text labels)

        Acceptance Criteria:
            - Button style set to icon-only mode
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None
        assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly


# =============================================================================
# Test Classes - Toolbar Position
# =============================================================================


class TestToolbarPosition:
    """Tests for toolbar position in main window."""

    def test_toolbar_is_in_top_area(self, main_window: InkMainWindow) -> None:
        """Test toolbar is attached to top toolbar area.

        Top toolbar area is the standard position for primary toolbars,
        located below the menu bar but above the central widget.

        Acceptance Criteria:
            - Toolbar attached to main window in top toolbar area
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        area = main_window.toolBarArea(toolbar)
        assert area == Qt.ToolBarArea.TopToolBarArea, "Toolbar should be in top area"


# =============================================================================
# Test Classes - Toolbar Reference
# =============================================================================


class TestToolbarReference:
    """Tests for toolbar instance variable storage."""

    def test_toolbar_stored_as_instance_variable(self, main_window: InkMainWindow) -> None:
        """Test toolbar reference is stored in _toolbar instance variable.

        The toolbar reference is needed for:
        - Adding actions in subsequent tasks (T02, T03)
        - Adding separators between action groups
        - Runtime manipulation of toolbar state

        Acceptance Criteria:
            - Toolbar reference stored in instance variable (self._toolbar)
        """
        assert hasattr(main_window, "_toolbar"), "Window should have _toolbar attribute"
        assert main_window._toolbar is not None, "_toolbar should not be None"
        assert isinstance(main_window._toolbar, QToolBar), "_toolbar should be a QToolBar instance"

    def test_toolbar_reference_matches_findchild(self, main_window: InkMainWindow) -> None:
        """Test _toolbar reference is the same object as findChild result.

        Ensures consistency between the instance variable and Qt's object tree.
        """
        toolbar_from_ref = main_window._toolbar
        toolbar_from_find = main_window.findChild(QToolBar, "MainToolBar")

        assert toolbar_from_ref is toolbar_from_find, (
            "_toolbar should reference the same object found via findChild"
        )


# =============================================================================
# Test Classes - No Runtime Errors
# =============================================================================


class TestToolbarNoErrors:
    """Tests for error-free toolbar operation."""

    def test_main_window_launches_without_toolbar_errors(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test main window can be created with toolbar without runtime errors.

        This is a smoke test to ensure the toolbar integration doesn't break
        the main window initialization.

        Acceptance Criteria:
            - No runtime errors when main window launches with toolbar
        """
        # This should not raise any exceptions
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Window should be created successfully
        assert window is not None

        # Toolbar should be accessible
        toolbar = window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

    def test_toolbar_visible_after_window_show(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test toolbar is visible when main window is shown.

        Acceptance Criteria:
            - Toolbar visible below menu bar when main window displayed
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)
        window.show()
        qtbot.waitExposed(window)

        toolbar = window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None
        assert toolbar.isVisible(), "Toolbar should be visible when window is shown"
