"""Integration tests for InkMainWindow dock widget setup.

This module tests the dock widget integration in the main window:
- Three dock widgets are created (Hierarchy, Properties, Messages)
- Docks are positioned in correct areas (left, right, bottom)
- Docks have proper object names for state persistence
- Docks have correct allowed areas configured
- Docks can be closed and shown again
- Dock nesting is enabled for complex layouts

See Also:
    - Spec E06-F01-T03 for dock widget requirements
    - Pre-docs E06-F01-T03 for architecture decisions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QDockWidget

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.main_window import InkMainWindow
from ink.presentation.panels import HierarchyPanel, MessagePanel, PropertyPanel

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


@pytest.fixture(scope="module")
def qapp() -> Generator[QApplication, None, None]:
    """Provide QApplication instance for Qt widget tests.

    Qt requires exactly one QApplication instance per process.
    This fixture ensures we reuse an existing instance or create a new one.
    """
    existing = QApplication.instance()
    if existing is not None and isinstance(existing, QApplication):
        yield existing
    else:
        app = QApplication([])
        yield app


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Redirect QSettings to temporary directory for test isolation.

    Uses QSettings.setPath() to redirect INI file storage to a temp
    directory. This ensures tests don't affect real user settings and
    each test run starts with a clean slate.

    Yields:
        Path to the temporary settings directory.
    """
    settings_path = tmp_path / "settings"
    settings_path.mkdir(exist_ok=True)

    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    yield settings_path


@pytest.fixture
def app_settings(isolated_settings: Path) -> AppSettings:
    """Create AppSettings instance for testing.

    Args:
        isolated_settings: Temporary settings directory (ensures isolation).

    Returns:
        Fresh AppSettings instance.
    """
    return AppSettings()


@pytest.fixture
def window(
    qapp: QApplication, app_settings: AppSettings
) -> Generator[InkMainWindow, None, None]:
    """Create main window for each test and cleanup after.

    Each test gets a fresh window instance to avoid state pollution
    between tests. Window is closed after test completes.
    """
    win = InkMainWindow(app_settings)
    yield win
    win.close()


class TestDockWidgetCreation:
    """Tests for dock widget creation in main window."""

    def test_hierarchy_dock_exists(self, window: InkMainWindow) -> None:
        """Test hierarchy dock widget is created."""
        assert hasattr(window, "hierarchy_dock")
        assert isinstance(window.hierarchy_dock, QDockWidget)

    def test_hierarchy_dock_title(self, window: InkMainWindow) -> None:
        """Test hierarchy dock has correct window title."""
        assert window.hierarchy_dock.windowTitle() == "Hierarchy"

    def test_hierarchy_dock_contains_panel(self, window: InkMainWindow) -> None:
        """Test hierarchy dock contains HierarchyPanel widget."""
        assert hasattr(window, "hierarchy_panel")
        assert isinstance(window.hierarchy_panel, HierarchyPanel)
        assert window.hierarchy_dock.widget() == window.hierarchy_panel

    def test_property_dock_exists(self, window: InkMainWindow) -> None:
        """Test property dock widget is created."""
        assert hasattr(window, "property_dock")
        assert isinstance(window.property_dock, QDockWidget)

    def test_property_dock_title(self, window: InkMainWindow) -> None:
        """Test property dock has correct window title."""
        assert window.property_dock.windowTitle() == "Properties"

    def test_property_dock_contains_panel(self, window: InkMainWindow) -> None:
        """Test property dock contains PropertyPanel widget."""
        assert hasattr(window, "property_panel")
        assert isinstance(window.property_panel, PropertyPanel)
        assert window.property_dock.widget() == window.property_panel

    def test_message_dock_exists(self, window: InkMainWindow) -> None:
        """Test message dock widget is created."""
        assert hasattr(window, "message_dock")
        assert isinstance(window.message_dock, QDockWidget)

    def test_message_dock_title(self, window: InkMainWindow) -> None:
        """Test message dock has correct window title."""
        assert window.message_dock.windowTitle() == "Messages"

    def test_message_dock_contains_panel(self, window: InkMainWindow) -> None:
        """Test message dock contains MessagePanel widget."""
        assert hasattr(window, "message_panel")
        assert isinstance(window.message_panel, MessagePanel)
        assert window.message_dock.widget() == window.message_panel


class TestDockWidgetPositions:
    """Tests for dock widget positioning in correct areas."""

    def test_hierarchy_dock_on_left(self, window: InkMainWindow) -> None:
        """Test hierarchy dock is positioned in left area by default."""
        area = window.dockWidgetArea(window.hierarchy_dock)
        assert area == Qt.DockWidgetArea.LeftDockWidgetArea

    def test_property_dock_on_right(self, window: InkMainWindow) -> None:
        """Test property dock is positioned in right area by default."""
        area = window.dockWidgetArea(window.property_dock)
        assert area == Qt.DockWidgetArea.RightDockWidgetArea

    def test_message_dock_on_bottom(self, window: InkMainWindow) -> None:
        """Test message dock is positioned in bottom area by default."""
        area = window.dockWidgetArea(window.message_dock)
        assert area == Qt.DockWidgetArea.BottomDockWidgetArea


class TestDockWidgetAllowedAreas:
    """Tests for dock widget allowed area restrictions."""

    def test_hierarchy_dock_allowed_areas(self, window: InkMainWindow) -> None:
        """Test hierarchy dock only allows left and right areas.

        Hierarchy panel shows vertical tree structure, so it makes
        sense only on left or right sides, not top or bottom.
        """
        allowed = window.hierarchy_dock.allowedAreas()
        # Should allow left and right
        assert allowed & Qt.DockWidgetArea.LeftDockWidgetArea
        assert allowed & Qt.DockWidgetArea.RightDockWidgetArea
        # Should not allow top or bottom
        assert not (allowed & Qt.DockWidgetArea.TopDockWidgetArea)
        assert not (allowed & Qt.DockWidgetArea.BottomDockWidgetArea)

    def test_property_dock_allowed_areas(self, window: InkMainWindow) -> None:
        """Test property dock only allows left and right areas.

        Property panel shows vertical key-value pairs, so it makes
        sense only on left or right sides, not top or bottom.
        """
        allowed = window.property_dock.allowedAreas()
        # Should allow left and right
        assert allowed & Qt.DockWidgetArea.LeftDockWidgetArea
        assert allowed & Qt.DockWidgetArea.RightDockWidgetArea
        # Should not allow top or bottom
        assert not (allowed & Qt.DockWidgetArea.TopDockWidgetArea)
        assert not (allowed & Qt.DockWidgetArea.BottomDockWidgetArea)

    def test_message_dock_allowed_areas(self, window: InkMainWindow) -> None:
        """Test message dock only allows bottom area.

        Message panel shows horizontal log/search results, so it
        makes sense only at the bottom, not on sides.
        """
        allowed = window.message_dock.allowedAreas()
        # Should allow only bottom
        assert allowed & Qt.DockWidgetArea.BottomDockWidgetArea
        # Should not allow left, right, or top
        assert not (allowed & Qt.DockWidgetArea.LeftDockWidgetArea)
        assert not (allowed & Qt.DockWidgetArea.RightDockWidgetArea)
        assert not (allowed & Qt.DockWidgetArea.TopDockWidgetArea)


class TestDockWidgetObjectNames:
    """Tests for dock widget object names (required for state persistence)."""

    def test_hierarchy_dock_object_name(self, window: InkMainWindow) -> None:
        """Test hierarchy dock has object name for QSettings persistence."""
        assert window.hierarchy_dock.objectName() == "HierarchyDock"

    def test_property_dock_object_name(self, window: InkMainWindow) -> None:
        """Test property dock has object name for QSettings persistence."""
        assert window.property_dock.objectName() == "PropertyDock"

    def test_message_dock_object_name(self, window: InkMainWindow) -> None:
        """Test message dock has object name for QSettings persistence."""
        assert window.message_dock.objectName() == "MessageDock"


class TestDockWidgetVisibility:
    """Tests for dock widget visibility operations."""

    def test_all_docks_not_hidden_initially(self, window: InkMainWindow) -> None:
        """Test all docks are not explicitly hidden when window is created.

        Note: isVisible() returns False before show() is called on the window.
        We test isHidden() which checks if the widget is explicitly hidden,
        not whether it's actually displayed on screen.
        """
        # Docks should not be explicitly hidden (isHidden checks hidden flag)
        assert not window.hierarchy_dock.isHidden()
        assert not window.property_dock.isHidden()
        assert not window.message_dock.isHidden()

    def test_hierarchy_dock_can_be_closed(self, window: InkMainWindow) -> None:
        """Test hierarchy dock can be closed and hidden."""
        window.hierarchy_dock.close()
        assert not window.hierarchy_dock.isVisible()

    def test_closed_dock_can_be_shown(self, window: InkMainWindow) -> None:
        """Test closed dock can be made visible again.

        After close(), the dock is explicitly hidden. After show(), the
        hidden flag is cleared. We test isHidden() rather than isVisible()
        because the window isn't actually shown in this test.
        """
        window.hierarchy_dock.close()
        assert window.hierarchy_dock.isHidden()

        window.hierarchy_dock.show()
        assert not window.hierarchy_dock.isHidden()

    def test_property_dock_can_be_closed(self, window: InkMainWindow) -> None:
        """Test property dock can be closed."""
        window.property_dock.close()
        assert not window.property_dock.isVisible()

    def test_message_dock_can_be_closed(self, window: InkMainWindow) -> None:
        """Test message dock can be closed."""
        window.message_dock.close()
        assert not window.message_dock.isVisible()


class TestDockWidgetFeatures:
    """Tests for dock widget feature flags."""

    def test_hierarchy_dock_features(self, window: InkMainWindow) -> None:
        """Test hierarchy dock has standard dock features enabled.

        By default Qt enables all features: closable, movable, floatable.
        """
        features = window.hierarchy_dock.features()
        assert features & QDockWidget.DockWidgetFeature.DockWidgetClosable
        assert features & QDockWidget.DockWidgetFeature.DockWidgetMovable
        assert features & QDockWidget.DockWidgetFeature.DockWidgetFloatable

    def test_property_dock_features(self, window: InkMainWindow) -> None:
        """Test property dock has standard dock features enabled."""
        features = window.property_dock.features()
        assert features & QDockWidget.DockWidgetFeature.DockWidgetClosable
        assert features & QDockWidget.DockWidgetFeature.DockWidgetMovable
        assert features & QDockWidget.DockWidgetFeature.DockWidgetFloatable

    def test_message_dock_features(self, window: InkMainWindow) -> None:
        """Test message dock has standard dock features enabled."""
        features = window.message_dock.features()
        assert features & QDockWidget.DockWidgetFeature.DockWidgetClosable
        assert features & QDockWidget.DockWidgetFeature.DockWidgetMovable
        assert features & QDockWidget.DockWidgetFeature.DockWidgetFloatable


class TestMainWindowDockConfiguration:
    """Tests for main window dock configuration settings."""

    def test_dock_nesting_enabled(self, window: InkMainWindow) -> None:
        """Test dock nesting is enabled for complex layouts.

        Dock nesting allows docks to be arranged in more complex
        configurations, such as splitting a dock area horizontally
        or vertically.
        """
        assert window.isDockNestingEnabled()


class TestDockWidgetMinimumSizes:
    """Tests for dock widget minimum size constraints."""

    def test_hierarchy_dock_minimum_width(self, window: InkMainWindow) -> None:
        """Test hierarchy dock has reasonable minimum width."""
        min_width = window.hierarchy_dock.minimumWidth()
        assert min_width >= 150  # Usable width for tree view

    def test_hierarchy_panel_minimum_size(self, window: InkMainWindow) -> None:
        """Test hierarchy panel has minimum size set."""
        min_size = window.hierarchy_panel.minimumSize()
        assert min_size.width() >= 150
        assert min_size.height() >= 200

    def test_property_dock_minimum_width(self, window: InkMainWindow) -> None:
        """Test property dock has reasonable minimum width."""
        min_width = window.property_dock.minimumWidth()
        assert min_width >= 200  # Wider for property names/values

    def test_property_panel_minimum_size(self, window: InkMainWindow) -> None:
        """Test property panel has minimum size set."""
        min_size = window.property_panel.minimumSize()
        assert min_size.width() >= 200
        assert min_size.height() >= 200

    def test_message_dock_minimum_height(self, window: InkMainWindow) -> None:
        """Test message dock has reasonable minimum height."""
        min_height = window.message_dock.minimumHeight()
        assert min_height >= 100  # Usable height for log view

    def test_message_panel_minimum_size(self, window: InkMainWindow) -> None:
        """Test message panel has minimum size set."""
        min_size = window.message_panel.minimumSize()
        assert min_size.width() >= 300
        assert min_size.height() >= 100
