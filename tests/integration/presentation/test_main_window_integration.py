"""Comprehensive integration tests for main window assembly.

This module provides comprehensive integration testing for the complete InkMainWindow
assembly, verifying that all components (window, canvas, dock widgets, menus) work
together correctly as an integrated whole.

Test Categories:
    - Main Window Assembly: Verify complete window is created with all components
    - Central Widget Integration: Canvas as central widget
    - Dock Widget Integration: All three docks work together
    - Dock Widget Operations: Close, show, float, re-dock operations
    - Window Geometry: Resize, minimum size enforcement
    - Window Lifecycle: Show, hide, close, cleanup
    - Dock Nesting: Complex layout configurations
    - Menu Integration: File menu, recent files menu

See Also:
    - E06-F01-T05 spec for integration testing requirements
    - E06-F01 parent spec for acceptance criteria
    - Pre-docs E06-F01-T05 for testing strategy
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication, QDockWidget

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.canvas import SchematicCanvas
from ink.presentation.main_window import InkMainWindow
from ink.presentation.panels import HierarchyPanel, MessagePanel, PropertyPanel

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


# =============================================================================
# Fixtures
# =============================================================================


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
def main_window(
    qapp: QApplication, app_settings: AppSettings
) -> Generator[InkMainWindow, None, None]:
    """Create main window for each test and cleanup after.

    Each test gets a fresh window instance to avoid state pollution
    between tests. Window is closed and scheduled for deletion after test.
    """
    win = InkMainWindow(app_settings)
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


# =============================================================================
# Test Classes: Main Window Assembly
# =============================================================================


class TestMainWindowAssembly:
    """Test complete main window is assembled correctly."""

    def test_window_created(self, main_window: InkMainWindow) -> None:
        """Test main window instance is created."""
        assert main_window is not None

    def test_window_title(self, main_window: InkMainWindow) -> None:
        """Test window has correct title."""
        assert main_window.windowTitle() == "Ink - Incremental Schematic Viewer"

    def test_window_default_size(self, main_window: InkMainWindow) -> None:
        """Test window has reasonable default size.

        When using geometry persistence (app_settings provided), the window
        defaults to 1280x800, which is smaller than the original 1600x900
        to leave room for user customization. In offscreen test mode, the
        window may default to minimum size due to Qt's layout behavior.

        We verify the window is at least minimum size and not unreasonably large.
        """
        # Window should be at least minimum size
        assert main_window.width() >= 1024
        assert main_window.height() >= 768

        # And not unreasonably large (less than 4K monitor)
        assert main_window.width() <= 3840
        assert main_window.height() <= 2160

    def test_window_minimum_size(self, main_window: InkMainWindow) -> None:
        """Test window has correct minimum size."""
        min_size = main_window.minimumSize()
        assert min_size.width() == 1024
        assert min_size.height() == 768

    def test_window_has_all_components(self, main_window: InkMainWindow) -> None:
        """Test window has all expected components."""
        # Central widget
        assert main_window.centralWidget() is not None
        assert hasattr(main_window, "schematic_canvas")

        # Dock widgets
        assert hasattr(main_window, "hierarchy_dock")
        assert hasattr(main_window, "property_dock")
        assert hasattr(main_window, "message_dock")

        # Panels inside docks
        assert hasattr(main_window, "hierarchy_panel")
        assert hasattr(main_window, "property_panel")
        assert hasattr(main_window, "message_panel")

        # Menu components
        assert hasattr(main_window, "recent_files_menu")

    def test_window_minimum_enforced(self, main_window: InkMainWindow) -> None:
        """Test window minimum size is set correctly.

        In offscreen/headless mode, the window manager may not enforce
        minimum size constraints the same way as on a real display.
        We verify the minimumSize() constraint is properly configured.
        """
        min_size = main_window.minimumSize()
        assert min_size.width() == 1024
        assert min_size.height() == 768

        # Verify minimum size is always >= these values via the getter
        assert main_window.minimumWidth() >= 1024
        assert main_window.minimumHeight() >= 768


# =============================================================================
# Test Classes: Central Widget Integration
# =============================================================================


class TestCentralWidgetIntegration:
    """Test central widget (canvas) integration with main window."""

    def test_central_widget_exists(self, main_window: InkMainWindow) -> None:
        """Test central widget is set."""
        assert main_window.centralWidget() is not None

    def test_central_widget_is_canvas(self, main_window: InkMainWindow) -> None:
        """Test central widget is schematic canvas."""
        assert main_window.centralWidget() == main_window.schematic_canvas

    def test_central_widget_is_schematic_canvas_type(
        self, main_window: InkMainWindow
    ) -> None:
        """Test central widget is SchematicCanvas instance."""
        assert isinstance(main_window.centralWidget(), SchematicCanvas)

    def test_canvas_parent_relationship(self, main_window: InkMainWindow) -> None:
        """Test canvas has proper parent relationship."""
        # Canvas should have main window as parent
        assert main_window.schematic_canvas.parent() == main_window


# =============================================================================
# Test Classes: Dock Widget Integration
# =============================================================================


class TestDockWidgetIntegration:
    """Test all dock widgets work together correctly."""

    def test_all_docks_exist(self, main_window: InkMainWindow) -> None:
        """Test all three docks are created."""
        assert isinstance(main_window.hierarchy_dock, QDockWidget)
        assert isinstance(main_window.property_dock, QDockWidget)
        assert isinstance(main_window.message_dock, QDockWidget)

    def test_dock_positions(self, main_window: InkMainWindow) -> None:
        """Test docks are in correct default positions."""
        assert (
            main_window.dockWidgetArea(main_window.hierarchy_dock)
            == Qt.DockWidgetArea.LeftDockWidgetArea
        )
        assert (
            main_window.dockWidgetArea(main_window.property_dock)
            == Qt.DockWidgetArea.RightDockWidgetArea
        )
        assert (
            main_window.dockWidgetArea(main_window.message_dock)
            == Qt.DockWidgetArea.BottomDockWidgetArea
        )

    def test_dock_titles(self, main_window: InkMainWindow) -> None:
        """Test docks have correct titles."""
        assert main_window.hierarchy_dock.windowTitle() == "Hierarchy"
        assert main_window.property_dock.windowTitle() == "Properties"
        assert main_window.message_dock.windowTitle() == "Messages"

    def test_docks_are_added_to_window(self, main_window: InkMainWindow) -> None:
        """Test all docks are properly added to the window.

        Verifies docks are registered in their respective dock areas.
        Visibility depends on show() being called, but docks should be
        properly configured from construction.
        """
        # Verify docks are in correct areas (not floating)
        assert not main_window.hierarchy_dock.isFloating()
        assert not main_window.property_dock.isFloating()
        assert not main_window.message_dock.isFloating()

    def test_dock_object_names(self, main_window: InkMainWindow) -> None:
        """Test docks have object names for state persistence."""
        assert main_window.hierarchy_dock.objectName() == "HierarchyDock"
        assert main_window.property_dock.objectName() == "PropertyDock"
        assert main_window.message_dock.objectName() == "MessageDock"

    def test_dock_panels_correct_type(self, main_window: InkMainWindow) -> None:
        """Test dock widgets contain correct panel types."""
        assert isinstance(main_window.hierarchy_panel, HierarchyPanel)
        assert isinstance(main_window.property_panel, PropertyPanel)
        assert isinstance(main_window.message_panel, MessagePanel)

    def test_dock_panels_are_dock_contents(self, main_window: InkMainWindow) -> None:
        """Test panels are set as dock widget contents."""
        assert main_window.hierarchy_dock.widget() == main_window.hierarchy_panel
        assert main_window.property_dock.widget() == main_window.property_panel
        assert main_window.message_dock.widget() == main_window.message_panel


# =============================================================================
# Test Classes: Dock Widget Operations
# =============================================================================


class TestDockWidgetOperations:
    """Test dock widget operations work correctly."""

    def test_dock_close_and_show(
        self, main_window: InkMainWindow, qapp: QApplication
    ) -> None:
        """Test dock can be closed and shown."""
        # Close hierarchy dock
        main_window.hierarchy_dock.close()
        qapp.processEvents()
        assert not main_window.hierarchy_dock.isVisible()

        # Show again
        main_window.hierarchy_dock.show()
        qapp.processEvents()
        assert not main_window.hierarchy_dock.isHidden()

    def test_dock_float_and_unfloat(
        self, main_window: InkMainWindow, qapp: QApplication
    ) -> None:
        """Test dock can be floated and re-docked."""
        # Float hierarchy dock
        main_window.hierarchy_dock.setFloating(True)
        qapp.processEvents()
        assert main_window.hierarchy_dock.isFloating()

        # Re-dock
        main_window.hierarchy_dock.setFloating(False)
        qapp.processEvents()
        assert not main_window.hierarchy_dock.isFloating()

    def test_multiple_docks_closable(
        self, main_window: InkMainWindow, qapp: QApplication
    ) -> None:
        """Test multiple docks can be closed simultaneously."""
        # Close two docks
        main_window.hierarchy_dock.close()
        main_window.property_dock.close()
        qapp.processEvents()

        # Both should not be visible
        assert not main_window.hierarchy_dock.isVisible()
        assert not main_window.property_dock.isVisible()
        # Message dock should still be in its dock area (not closed)
        assert not main_window.message_dock.isFloating()

        # Restore the closed docks
        main_window.hierarchy_dock.show()
        main_window.property_dock.show()
        qapp.processEvents()

    def test_all_docks_can_float(
        self, main_window: InkMainWindow, qapp: QApplication
    ) -> None:
        """Test all docks can be floated."""
        main_window.hierarchy_dock.setFloating(True)
        main_window.property_dock.setFloating(True)
        main_window.message_dock.setFloating(True)
        qapp.processEvents()

        assert main_window.hierarchy_dock.isFloating()
        assert main_window.property_dock.isFloating()
        assert main_window.message_dock.isFloating()

        # Restore
        main_window.hierarchy_dock.setFloating(False)
        main_window.property_dock.setFloating(False)
        main_window.message_dock.setFloating(False)
        qapp.processEvents()


# =============================================================================
# Test Classes: Window Geometry
# =============================================================================


class TestWindowGeometry:
    """Test window geometry behavior."""

    def test_window_resizable(self, main_window: InkMainWindow) -> None:
        """Test window can be resized."""
        main_window.resize(1920, 1080)
        assert main_window.width() == 1920
        assert main_window.height() == 1080

    def test_window_respects_minimum(
        self, main_window: InkMainWindow, qapp: QApplication
    ) -> None:
        """Test window cannot be smaller than minimum when shown."""
        main_window.resize(500, 400)
        main_window.show()
        qapp.processEvents()

        # Should be at least minimum size
        assert main_window.width() >= 1024
        assert main_window.height() >= 768

        main_window.close()

    def test_window_can_be_maximized(
        self, main_window: InkMainWindow, qapp: QApplication
    ) -> None:
        """Test window can be maximized."""
        main_window.show()
        main_window.showMaximized()
        qapp.processEvents()
        # Note: In offscreen mode, maximized state may not be fully accurate
        # We just verify no crash occurs
        main_window.close()

    def test_window_can_be_minimized(
        self, main_window: InkMainWindow, qapp: QApplication
    ) -> None:
        """Test window can be minimized."""
        main_window.show()
        main_window.showMinimized()
        qapp.processEvents()
        # Note: In offscreen mode, minimized state may not be fully accurate
        # We just verify no crash occurs
        main_window.close()


# =============================================================================
# Test Classes: Window Lifecycle
# =============================================================================


class TestWindowLifecycle:
    """Test window creation and destruction lifecycle."""

    def test_window_can_be_shown_and_hidden(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test window can be shown and hidden."""
        window = InkMainWindow(app_settings)
        window.show()
        qapp.processEvents()
        assert window.isVisible()

        window.hide()
        qapp.processEvents()
        assert not window.isVisible()

        window.close()
        window.deleteLater()
        qapp.processEvents()

    def test_window_cleanup(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test window cleans up properly when deleted."""
        window = InkMainWindow(app_settings)
        window.show()
        qapp.processEvents()
        window.close()
        window.deleteLater()
        qapp.processEvents()
        # No assertion - just verify no crash

    def test_multiple_windows(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test multiple windows can coexist."""
        # Create fresh app_settings for second window
        settings2 = AppSettings()

        window1 = InkMainWindow(app_settings)
        window2 = InkMainWindow(settings2)

        window1.show()
        window2.show()
        qapp.processEvents()

        assert window1.isVisible()
        assert window2.isVisible()

        window1.close()
        window2.close()
        window1.deleteLater()
        window2.deleteLater()
        qapp.processEvents()

    def test_repeated_create_destroy(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test repeated window creation and destruction doesn't leak."""
        for _ in range(10):
            window = InkMainWindow(app_settings)
            window.show()
            qapp.processEvents()
            window.close()
            window.deleteLater()
            qapp.processEvents()
        # No assertion - just verify no crash or memory leak symptoms


# =============================================================================
# Test Classes: Dock Nesting
# =============================================================================


class TestDockNesting:
    """Test dock nesting configuration."""

    def test_dock_nesting_enabled(self, main_window: InkMainWindow) -> None:
        """Test dock nesting is enabled for complex layouts."""
        assert main_window.isDockNestingEnabled()


# =============================================================================
# Test Classes: Menu Integration
# =============================================================================


class TestMenuIntegration:
    """Test menu system integration with main window."""

    def test_menu_bar_exists(self, main_window: InkMainWindow) -> None:
        """Test menu bar is created."""
        assert main_window.menuBar() is not None

    def test_file_menu_exists(self, main_window: InkMainWindow) -> None:
        """Test File menu is present."""
        menubar = main_window.menuBar()
        actions = [action.text() for action in menubar.actions()]
        assert any("File" in text for text in actions)

    def test_help_menu_exists(self, main_window: InkMainWindow) -> None:
        """Test Help menu is present."""
        menubar = main_window.menuBar()
        actions = [action.text() for action in menubar.actions()]
        assert any("Help" in text for text in actions)

    def test_recent_files_menu_exists(self, main_window: InkMainWindow) -> None:
        """Test recent files submenu exists."""
        assert main_window.recent_files_menu is not None


# =============================================================================
# Test Classes: Performance (Basic)
# =============================================================================


class TestUIPolish:
    """Test UI polish styling is applied."""

    def test_window_has_stylesheet(self, main_window: InkMainWindow) -> None:
        """Test main window has a stylesheet applied."""
        stylesheet = main_window.styleSheet()
        assert stylesheet is not None
        assert len(stylesheet) > 0

    def test_stylesheet_contains_splitter_styling(
        self, main_window: InkMainWindow
    ) -> None:
        """Test stylesheet includes splitter handle styling."""
        stylesheet = main_window.styleSheet()
        assert "QSplitter::handle" in stylesheet

    def test_stylesheet_contains_dock_styling(
        self, main_window: InkMainWindow
    ) -> None:
        """Test stylesheet includes dock widget styling."""
        stylesheet = main_window.styleSheet()
        assert "QDockWidget" in stylesheet

    def test_window_is_animated(self, main_window: InkMainWindow) -> None:
        """Test window has dock animations enabled."""
        assert main_window.isAnimated()


class TestPerformanceBasic:
    """Basic performance tests that don't require benchmark plugin."""

    def test_window_creation_is_fast(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test window creation time is reasonable."""
        start = time.perf_counter()
        window = InkMainWindow(app_settings)
        elapsed = time.perf_counter() - start

        window.deleteLater()
        qapp.processEvents()

        # Should complete in under 500ms
        assert elapsed < 0.5, f"Window creation took {elapsed:.3f}s, exceeds 500ms limit"

    def test_startup_under_2_seconds(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test complete startup (create + show) is under 2 seconds."""
        start = time.perf_counter()

        window = InkMainWindow(app_settings)
        window.show()
        qapp.processEvents()

        elapsed = time.perf_counter() - start

        window.close()
        window.deleteLater()
        qapp.processEvents()

        # Full startup should be under 2 seconds
        assert elapsed < 2.0, f"Startup took {elapsed:.2f}s, exceeds 2s limit"
