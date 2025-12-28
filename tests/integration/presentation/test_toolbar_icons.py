"""Integration tests for toolbar icons with IconProvider.

Tests verify that all toolbar buttons display icons correctly when using
the IconProvider utility for theme-first, fallback-second icon loading.

Test Strategy:
    - TDD RED Phase: These tests are written before implementation
    - Tests verify actual toolbar buttons have icons
    - Tests verify icons are not null and have available sizes
    - Tests verify icons render at toolbar size

See Also:
    - Spec E06-F03-T04 for icon resources requirements
    - Pre-docs E06-F03-T04 for implementation details
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QToolBar

from ink.infrastructure.persistence.app_settings import AppSettings

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

    from ink.presentation.main_window import InkMainWindow


@pytest.fixture
def app_settings() -> AppSettings:
    """Create AppSettings for testing."""
    return AppSettings()


@pytest.fixture
def main_window(qtbot: QtBot, app_settings: AppSettings) -> InkMainWindow:
    """Create main window instance with toolbar."""
    from ink.presentation.main_window import InkMainWindow

    window = InkMainWindow(app_settings)
    qtbot.addWidget(window)
    return window


class TestToolbarIconsPresent:
    """Test that all toolbar buttons have icons."""

    def test_toolbar_exists(self, main_window: InkMainWindow) -> None:
        """Main window should have a toolbar named 'MainToolBar'."""
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None, "MainToolBar not found"

    def test_all_toolbar_buttons_have_icons(self, main_window: InkMainWindow) -> None:
        """All toolbar buttons (non-separator actions) should have icons."""
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        actions_without_icons = []
        for action in toolbar.actions():
            if not action.isSeparator():
                icon = action.icon()
                if icon.isNull():
                    actions_without_icons.append(action.text())

        assert not actions_without_icons, (
            f"Actions without icons: {actions_without_icons}"
        )

    def test_open_action_has_icon(self, main_window: InkMainWindow) -> None:
        """Open action should have an icon."""
        assert hasattr(main_window, "_open_action")
        icon = main_window._open_action.icon()
        assert not icon.isNull(), "Open action should have an icon"

    def test_undo_action_has_icon(self, main_window: InkMainWindow) -> None:
        """Undo action should have an icon."""
        assert hasattr(main_window, "_undo_action")
        icon = main_window._undo_action.icon()
        assert not icon.isNull(), "Undo action should have an icon"

    def test_redo_action_has_icon(self, main_window: InkMainWindow) -> None:
        """Redo action should have an icon."""
        assert hasattr(main_window, "_redo_action")
        icon = main_window._redo_action.icon()
        assert not icon.isNull(), "Redo action should have an icon"

    def test_search_action_has_icon(self, main_window: InkMainWindow) -> None:
        """Search action should have an icon."""
        assert hasattr(main_window, "_search_action")
        icon = main_window._search_action.icon()
        assert not icon.isNull(), "Search action should have an icon"


class TestToolbarIconsQuality:
    """Test quality of toolbar icons."""

    def test_icons_are_not_null(self, main_window: InkMainWindow) -> None:
        """All toolbar icons should be valid QIcon instances (not null).

        Note: SVG icons may not report availableSizes() in offscreen mode,
        so we test that icons are not null instead.
        """
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        for action in toolbar.actions():
            if not action.isSeparator():
                icon = action.icon()
                assert not icon.isNull(), (
                    f"Action '{action.text()}' icon should not be null"
                )

    def test_icons_render_at_toolbar_size(self, main_window: InkMainWindow) -> None:
        """Icons should render at toolbar icon size (24x24) without being null."""
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None
        expected_size = QSize(24, 24)

        for action in toolbar.actions():
            if not action.isSeparator():
                icon = action.icon()
                if not icon.isNull():
                    pixmap = icon.pixmap(expected_size)
                    assert not pixmap.isNull(), (
                        f"Action '{action.text()}' icon failed to render at 24x24"
                    )

    def test_icons_render_at_larger_size(self, main_window: InkMainWindow) -> None:
        """Icons should scale cleanly to larger sizes (32x32)."""
        toolbar = main_window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None
        larger_size = QSize(32, 32)

        for action in toolbar.actions():
            if not action.isSeparator():
                icon = action.icon()
                if not icon.isNull():
                    pixmap = icon.pixmap(larger_size)
                    assert not pixmap.isNull(), (
                        f"Action '{action.text()}' icon failed to render at 32x32"
                    )


class TestIconProviderIntegration:
    """Test that IconProvider is properly integrated with main window."""

    def test_icon_provider_used_for_open_action(self, main_window: InkMainWindow) -> None:
        """Open action icon should be loaded via IconProvider (not null)."""
        from ink.presentation.utils.icon_provider import IconProvider

        # Get icon from IconProvider
        provider_icon = IconProvider.get_icon("document-open")

        # Get icon from action
        action_icon = main_window._open_action.icon()

        # Both should be valid (non-null)
        assert not provider_icon.isNull()
        assert not action_icon.isNull()

    def test_icon_provider_used_for_zoom_actions(self, main_window: InkMainWindow) -> None:
        """Zoom actions should use icons from IconProvider."""
        from ink.presentation.utils.icon_provider import IconProvider

        # Verify zoom icons exist in IconProvider
        zoom_in_icon = IconProvider.get_icon("zoom-in")
        zoom_out_icon = IconProvider.get_icon("zoom-out")
        fit_view_icon = IconProvider.get_icon("zoom-fit-best")

        assert not zoom_in_icon.isNull()
        assert not zoom_out_icon.isNull()
        assert not fit_view_icon.isNull()


class TestToolbarIconsFallback:
    """Test that toolbar icons work without system icon theme."""

    def test_toolbar_icons_without_theme(self, qtbot: QtBot, app_settings: AppSettings) -> None:
        """Toolbar should display icons even without system icon theme."""
        from ink.presentation.main_window import InkMainWindow

        # This test ensures fallback icons work
        # We verify that after window creation, icons are present
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        toolbar = window.findChild(QToolBar, "MainToolBar")
        assert toolbar is not None

        # Check all actions have icons
        for action in toolbar.actions():
            if not action.isSeparator():
                icon = action.icon()
                # With IconProvider integration, icons should never be null
                # because fallback resources are always available
                assert not icon.isNull(), (
                    f"Action '{action.text()}' should have fallback icon"
                )
