"""Main application window for Ink schematic viewer.

This module provides the InkMainWindow class, the root container for the Ink
application. It establishes the presentation layer foundation with proper
window management (title, sizing, decorations) following Qt best practices.

Design Decisions:
    - Extends QMainWindow (not QWidget) for built-in menu, toolbar, dock support
    - Explicit window flags ensure consistent decorations across Linux WMs
    - Default 1600x900 size optimized for 1080p displays with taskbar visible
    - Minimum 1024x768 prevents unusable cramped layouts

See Also:
    - Spec E06-F01-T01 for detailed requirements
    - Qt documentation on QMainWindow for extension points
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QMainWindow


class InkMainWindow(QMainWindow):
    """Main application window shell for Ink schematic viewer.

    This window serves as the root container for the entire Ink application,
    providing the foundation for the presentation layer. It handles:
    - Window title and identification
    - Default and minimum window sizing
    - Standard window decorations (minimize, maximize, close)

    The window is designed to work well on 1080p displays while remaining
    usable on smaller 768p screens. Future tasks will add central widget
    (SchematicCanvas), dock widgets, and menu/toolbars.

    Attributes:
        _WINDOW_TITLE: Application title shown in title bar.
        _DEFAULT_WIDTH: Default window width in pixels (optimized for 1080p).
        _DEFAULT_HEIGHT: Default window height in pixels.
        _MIN_WIDTH: Minimum allowed window width.
        _MIN_HEIGHT: Minimum allowed window height.

    Example:
        >>> from ink.presentation.main_window import InkMainWindow
        >>> window = InkMainWindow()
        >>> window.show()

    See Also:
        - E06-F01-T02: Adds SchematicCanvas as central widget
        - E06-F01-T03: Adds dock widgets (hierarchy, properties)
        - E06-F01-T04: Integrates window into main.py entry point
    """

    # Window configuration constants
    # These are class-level to make requirements explicit and testable
    _WINDOW_TITLE: str = "Ink - Incremental Schematic Viewer"
    _DEFAULT_WIDTH: int = 1600  # Optimal for 1080p (1920x1080) with taskbar
    _DEFAULT_HEIGHT: int = 900  # 16:9 aspect ratio, fits 1080p displays
    _MIN_WIDTH: int = 1024  # Common minimum for professional tools
    _MIN_HEIGHT: int = 768  # Supports 768p displays as minimum

    def __init__(self) -> None:
        """Initialize the main window with configured properties.

        Sets up window title, size constraints, and decorations.
        Does not show the window - caller must call show() explicitly.
        """
        super().__init__()
        self._setup_window()

    def _setup_window(self) -> None:
        """Configure main window properties.

        This method centralizes all window configuration for clarity and
        maintainability. Each setting is documented with its rationale.

        Configuration includes:
            1. Window title - identifies the application
            2. Default size - optimized for common display resolutions
            3. Minimum size - prevents unusable cramped layouts
            4. Window flags - ensures consistent decorations across WMs
        """
        # Set window title for identification in taskbar and title bar
        # Format: "AppName - Description" is a common convention
        self.setWindowTitle(self._WINDOW_TITLE)

        # Set default size optimized for 1080p displays (1920x1080)
        # 1600x900 leaves room for:
        # - Taskbar/dock (typically 40-60px)
        # - Window decorations (title bar, borders)
        # - Other windows user may want visible alongside
        self.resize(self._DEFAULT_WIDTH, self._DEFAULT_HEIGHT)

        # Set minimum size to prevent unusable layouts
        # Below 1024x768, UI elements become too crowded:
        # - Property panel text becomes unreadable
        # - Hierarchy tree becomes too narrow
        # - Schematic canvas becomes too small for meaningful work
        self.setMinimumSize(QSize(self._MIN_WIDTH, self._MIN_HEIGHT))

        # Configure window flags for consistent decorations
        # Some Linux window managers require explicit flags to show
        # standard window controls. These flags ensure:
        # - Window type: Standard application window
        # - Title hint: Show title bar
        # - System menu: Right-click menu on title bar
        # - Minimize/Maximize/Close: Standard control buttons
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
