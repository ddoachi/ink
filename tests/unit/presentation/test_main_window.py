"""Unit tests for InkMainWindow.

Tests verify the main application window meets all requirements from spec E06-F01-T01:
- Window instantiation without errors
- Correct window title
- Default size of 1600x900
- Minimum size of 1024x768
- Proper window flags for decorations

These tests run in TDD RED phase first (expecting failures), then GREEN after implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow

from ink.presentation.main_window import InkMainWindow

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestInkMainWindowCreation:
    """Tests for InkMainWindow instantiation."""

    def test_main_window_can_be_created(self, qtbot: QtBot) -> None:
        """Test that InkMainWindow can be instantiated without errors.

        Verifies:
        - No exceptions during construction
        - Returns a valid object instance
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert window is not None

    def test_main_window_is_qmainwindow_subclass(self, qtbot: QtBot) -> None:
        """Test that InkMainWindow inherits from QMainWindow.

        QMainWindow provides built-in support for:
        - Menu bar, toolbar, status bar, dock widgets
        - Window geometry persistence with QSettings
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert isinstance(window, QMainWindow)


class TestInkMainWindowTitle:
    """Tests for window title configuration."""

    def test_window_title_is_set_correctly(self, qtbot: QtBot) -> None:
        """Test window title matches spec requirement.

        Expected: "Ink - Incremental Schematic Viewer"
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert window.windowTitle() == "Ink - Incremental Schematic Viewer"


class TestInkMainWindowSize:
    """Tests for window size configuration."""

    def test_window_default_width_is_1600(self, qtbot: QtBot) -> None:
        """Test default window width is 1600 pixels.

        1600px optimized for 1080p displays (leaves room for taskbar).
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert window.width() == 1600

    def test_window_default_height_is_900(self, qtbot: QtBot) -> None:
        """Test default window height is 900 pixels.

        900px provides ample canvas while fitting on 1080p displays.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert window.height() == 900

    def test_window_minimum_width_is_1024(self, qtbot: QtBot) -> None:
        """Test minimum window width is 1024 pixels.

        Below this, UI elements become too crowded.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert window.minimumWidth() == 1024

    def test_window_minimum_height_is_768(self, qtbot: QtBot) -> None:
        """Test minimum window height is 768 pixels.

        1024x768 is common minimum for professional tools.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert window.minimumHeight() == 768

    def test_window_cannot_be_resized_below_minimum(self, qtbot: QtBot) -> None:
        """Test that window enforces minimum size constraint.

        Attempting to resize below minimum should clamp to minimum.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        # Try to resize below minimum
        window.resize(800, 600)

        # Should be clamped to minimum
        assert window.width() >= 1024
        assert window.height() >= 768


class TestInkMainWindowFlags:
    """Tests for window flags and decorations."""

    def test_window_has_title_hint(self, qtbot: QtBot) -> None:
        """Test window has title bar hint enabled."""
        window = InkMainWindow()
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowTitleHint

    def test_window_has_system_menu_hint(self, qtbot: QtBot) -> None:
        """Test window has system menu hint enabled."""
        window = InkMainWindow()
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowSystemMenuHint

    def test_window_has_minimize_button_hint(self, qtbot: QtBot) -> None:
        """Test window has minimize button hint enabled."""
        window = InkMainWindow()
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowMinimizeButtonHint

    def test_window_has_maximize_button_hint(self, qtbot: QtBot) -> None:
        """Test window has maximize button hint enabled."""
        window = InkMainWindow()
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowMaximizeButtonHint

    def test_window_has_close_button_hint(self, qtbot: QtBot) -> None:
        """Test window has close button hint enabled."""
        window = InkMainWindow()
        qtbot.addWidget(window)

        flags = window.windowFlags()
        assert flags & Qt.WindowType.WindowCloseButtonHint
