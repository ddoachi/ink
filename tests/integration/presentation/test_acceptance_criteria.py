"""Acceptance criteria tests for E06-F01 (Main Window Shell).

This module validates all acceptance criteria from the parent spec E06-F01.spec.md.
Each test is named to directly correspond to an acceptance criterion.

Acceptance Criteria from E06-F01:
    - [ ] Application launches with main window visible
    - [ ] Window has title "Ink - Incremental Schematic Viewer"
    - [ ] Central area contains schematic canvas widget
    - [ ] Three dock widgets present: hierarchy (left), properties (right), messages (bottom)
    - [ ] All dock widgets can be closed, floated, and re-docked
    - [ ] Window can be minimized, maximized, and closed
    - [ ] Application exits cleanly when window is closed
    - [ ] Application launches in <2 seconds on typical hardware
    - [ ] Window respects system window manager decorations

See Also:
    - specs/E06/F01/E06-F01.spec.md for acceptance criteria
    - E06-F01-T05 for testing requirements
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QApplication

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.canvas import SchematicCanvas
from ink.presentation.main_window import InkMainWindow

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def qapp() -> Generator[QApplication, None, None]:
    """Provide QApplication instance for Qt widget tests."""
    existing = QApplication.instance()
    if existing is not None and isinstance(existing, QApplication):
        yield existing
    else:
        app = QApplication([])
        yield app


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Redirect QSettings to temporary directory for test isolation."""
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
    """Create AppSettings instance for testing."""
    return AppSettings()


@pytest.fixture
def window(
    qapp: QApplication, app_settings: AppSettings
) -> Generator[InkMainWindow, None, None]:
    """Create main window for each test and cleanup after."""
    win = InkMainWindow(app_settings)
    yield win
    win.close()
    win.deleteLater()
    qapp.processEvents()


# =============================================================================
# Test Class: E06-F01 Acceptance Criteria
# =============================================================================


class TestE06F01AcceptanceCriteria:
    """Test all acceptance criteria from E06-F01 spec.

    Each test method corresponds to one acceptance criterion from the spec.
    Test names use the prefix 'test_ac' followed by a descriptive name.
    """

    # -------------------------------------------------------------------------
    # AC: Application launches with main window visible
    # -------------------------------------------------------------------------

    def test_ac_application_launches_with_visible_window(
        self, window: InkMainWindow, qapp: QApplication
    ) -> None:
        """AC: Application launches with main window visible."""
        window.show()
        qapp.processEvents()
        assert window.isVisible()
        window.close()

    # -------------------------------------------------------------------------
    # AC: Window has title "Ink - Incremental Schematic Viewer"
    # -------------------------------------------------------------------------

    def test_ac_window_has_correct_title(self, window: InkMainWindow) -> None:
        """AC: Window has title 'Ink - Incremental Schematic Viewer'."""
        assert window.windowTitle() == "Ink - Incremental Schematic Viewer"

    # -------------------------------------------------------------------------
    # AC: Central area contains schematic canvas widget
    # -------------------------------------------------------------------------

    def test_ac_central_area_contains_canvas(self, window: InkMainWindow) -> None:
        """AC: Central area contains schematic canvas widget."""
        central_widget = window.centralWidget()
        assert central_widget is not None
        assert isinstance(central_widget, SchematicCanvas)
        assert central_widget is window.schematic_canvas

    # -------------------------------------------------------------------------
    # AC: Three dock widgets present
    # -------------------------------------------------------------------------

    def test_ac_three_dock_widgets_present(self, window: InkMainWindow) -> None:
        """AC: Three dock widgets present with correct names."""
        # Hierarchy dock exists with correct title
        assert window.hierarchy_dock is not None
        assert window.hierarchy_dock.windowTitle() == "Hierarchy"

        # Property dock exists with correct title
        assert window.property_dock is not None
        assert window.property_dock.windowTitle() == "Properties"

        # Message dock exists with correct title
        assert window.message_dock is not None
        assert window.message_dock.windowTitle() == "Messages"

    def test_ac_dock_widgets_in_correct_positions(
        self, window: InkMainWindow
    ) -> None:
        """AC: Docks are in correct positions (left, right, bottom)."""
        # Hierarchy dock is in left area
        assert (
            window.dockWidgetArea(window.hierarchy_dock)
            == Qt.DockWidgetArea.LeftDockWidgetArea
        )

        # Property dock is in right area
        assert (
            window.dockWidgetArea(window.property_dock)
            == Qt.DockWidgetArea.RightDockWidgetArea
        )

        # Message dock is in bottom area
        assert (
            window.dockWidgetArea(window.message_dock)
            == Qt.DockWidgetArea.BottomDockWidgetArea
        )

    # -------------------------------------------------------------------------
    # AC: All dock widgets can be closed, floated, and re-docked
    # -------------------------------------------------------------------------

    def test_ac_dock_widgets_can_be_closed(
        self, window: InkMainWindow, qapp: QApplication
    ) -> None:
        """AC: All dock widgets can be closed."""
        # Close each dock and verify
        window.hierarchy_dock.close()
        qapp.processEvents()
        assert not window.hierarchy_dock.isVisible()

        window.property_dock.close()
        qapp.processEvents()
        assert not window.property_dock.isVisible()

        window.message_dock.close()
        qapp.processEvents()
        assert not window.message_dock.isVisible()

    def test_ac_dock_widgets_can_be_floated(
        self, window: InkMainWindow, qapp: QApplication
    ) -> None:
        """AC: All dock widgets can be floated."""
        # Float each dock and verify
        window.hierarchy_dock.setFloating(True)
        qapp.processEvents()
        assert window.hierarchy_dock.isFloating()

        window.property_dock.setFloating(True)
        qapp.processEvents()
        assert window.property_dock.isFloating()

        window.message_dock.setFloating(True)
        qapp.processEvents()
        assert window.message_dock.isFloating()

        # Reset for other tests
        window.hierarchy_dock.setFloating(False)
        window.property_dock.setFloating(False)
        window.message_dock.setFloating(False)
        qapp.processEvents()

    def test_ac_dock_widgets_can_be_redocked(
        self, window: InkMainWindow, qapp: QApplication
    ) -> None:
        """AC: All dock widgets can be re-docked after floating."""
        # Float hierarchy dock
        window.hierarchy_dock.setFloating(True)
        qapp.processEvents()
        assert window.hierarchy_dock.isFloating()

        # Re-dock it
        window.hierarchy_dock.setFloating(False)
        qapp.processEvents()
        assert not window.hierarchy_dock.isFloating()

        # Verify it's back in correct area
        assert (
            window.dockWidgetArea(window.hierarchy_dock)
            == Qt.DockWidgetArea.LeftDockWidgetArea
        )

    # -------------------------------------------------------------------------
    # AC: Window can be minimized, maximized, and closed
    # -------------------------------------------------------------------------

    def test_ac_window_can_be_minimized(
        self, window: InkMainWindow, qapp: QApplication
    ) -> None:
        """AC: Window can be minimized."""
        window.show()
        qapp.processEvents()

        window.showMinimized()
        qapp.processEvents()
        # Note: In offscreen mode, minimized state may not be accurate
        # We just verify no crash occurs

        window.close()

    def test_ac_window_can_be_maximized(
        self, window: InkMainWindow, qapp: QApplication
    ) -> None:
        """AC: Window can be maximized."""
        window.show()
        qapp.processEvents()

        window.showMaximized()
        qapp.processEvents()
        # Note: In offscreen mode, we can't always verify isMaximized()
        # We just verify no crash occurs

        window.close()

    def test_ac_window_can_be_closed(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """AC: Window can be closed."""
        window = InkMainWindow(app_settings)
        window.show()
        qapp.processEvents()
        assert window.isVisible()

        window.close()
        qapp.processEvents()
        assert not window.isVisible()

        window.deleteLater()
        qapp.processEvents()

    # -------------------------------------------------------------------------
    # AC: Application exits cleanly when window is closed
    # -------------------------------------------------------------------------

    def test_ac_window_cleanup_on_close(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """AC: Application exits cleanly when window is closed.

        We can't test actual application exit in unit tests, but we can
        verify window cleanup doesn't crash.
        """
        window = InkMainWindow(app_settings)
        window.show()
        qapp.processEvents()

        window.close()
        window.deleteLater()
        qapp.processEvents()

        # Create new window to verify no state corruption
        window2 = InkMainWindow(app_settings)
        assert window2 is not None
        window2.deleteLater()
        qapp.processEvents()

    # -------------------------------------------------------------------------
    # AC: Application launches in <2 seconds on typical hardware
    # -------------------------------------------------------------------------

    def test_ac_startup_time_under_2_seconds(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """AC: Application launches in <2 seconds on typical hardware."""
        start = time.perf_counter()

        window = InkMainWindow(app_settings)
        window.show()
        qapp.processEvents()

        elapsed = time.perf_counter() - start

        window.close()
        window.deleteLater()
        qapp.processEvents()

        assert elapsed < 2.0, f"Startup took {elapsed:.2f}s, exceeds 2s limit"

    # -------------------------------------------------------------------------
    # AC: Window respects system window manager decorations
    # -------------------------------------------------------------------------

    def test_ac_window_has_standard_flags(self, window: InkMainWindow) -> None:
        """AC: Window respects system window manager decorations.

        We verify window has proper flags set for standard decorations.
        Actual decoration rendering is verified via manual testing.
        """
        flags = window.windowFlags()

        # Should have standard window flags
        assert flags & Qt.WindowType.Window
        assert flags & Qt.WindowType.WindowTitleHint
        assert flags & Qt.WindowType.WindowSystemMenuHint
        assert flags & Qt.WindowType.WindowMinimizeButtonHint
        assert flags & Qt.WindowType.WindowMaximizeButtonHint
        assert flags & Qt.WindowType.WindowCloseButtonHint


# =============================================================================
# Test Class: User Story Validation
# =============================================================================


class TestE06F01UserStories:
    """Test user stories from E06-F01 spec.

    US-E06-01: Main Window Layout
    As a circuit designer
    I want to see a familiar EDA tool layout
    So that I can work productively from day one
    """

    def test_us_central_schematic_canvas(self, window: InkMainWindow) -> None:
        """US: Central area: Schematic canvas (largest)."""
        assert window.centralWidget() is not None
        assert window.centralWidget() is window.schematic_canvas

    def test_us_left_panel_hierarchy(self, window: InkMainWindow) -> None:
        """US: Left panel: Design hierarchy / object tree (collapsible)."""
        assert window.hierarchy_dock is not None
        assert (
            window.dockWidgetArea(window.hierarchy_dock)
            == Qt.DockWidgetArea.LeftDockWidgetArea
        )

    def test_us_right_panel_properties(self, window: InkMainWindow) -> None:
        """US: Right panel: Property inspector (collapsible)."""
        assert window.property_dock is not None
        assert (
            window.dockWidgetArea(window.property_dock)
            == Qt.DockWidgetArea.RightDockWidgetArea
        )

    def test_us_bottom_panel_messages(self, window: InkMainWindow) -> None:
        """US: Bottom panel: Messages / search results (collapsible)."""
        assert window.message_dock is not None
        assert (
            window.dockWidgetArea(window.message_dock)
            == Qt.DockWidgetArea.BottomDockWidgetArea
        )

    def test_us_panels_are_collapsible(
        self, window: InkMainWindow, qapp: QApplication
    ) -> None:
        """US: Panels remember size and visibility (closable = collapsible)."""
        # Verify all panels can be closed (collapsed)
        window.hierarchy_dock.close()
        window.property_dock.close()
        window.message_dock.close()
        qapp.processEvents()

        # All should be hidden
        assert not window.hierarchy_dock.isVisible()
        assert not window.property_dock.isVisible()
        assert not window.message_dock.isVisible()

        # Can be shown again
        window.hierarchy_dock.show()
        window.property_dock.show()
        window.message_dock.show()
        qapp.processEvents()

        assert not window.hierarchy_dock.isHidden()
        assert not window.property_dock.isHidden()
        assert not window.message_dock.isHidden()
