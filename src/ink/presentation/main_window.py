"""Main application window for Ink schematic viewer.

This module provides the InkMainWindow class, the root container for the Ink
application. It establishes the presentation layer foundation with proper
window management (title, sizing, decorations) following Qt best practices.

Design Decisions:
    - Extends QMainWindow (not QWidget) for built-in menu, toolbar, dock support
    - Explicit window flags ensure consistent decorations across Linux WMs
    - Default 1600x900 size optimized for 1080p displays with taskbar visible
    - When using geometry persistence (E06-F06-T02), defaults to 1280x800
    - Minimum 1024x768 prevents unusable cramped layouts
    - SchematicCanvas as central widget provides primary workspace area
    - Optional AppSettings injection for geometry persistence and settings management

See Also:
    - Spec E06-F01-T01 for window shell requirements
    - Spec E06-F01-T02 for central widget requirements
    - Spec E06-F06-T02 for window geometry persistence
    - Spec E06-F06-T04 for settings migration and reset
    - Qt documentation on QMainWindow for extension points
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCloseEvent, QGuiApplication
from PySide6.QtWidgets import QMainWindow, QMenu, QMessageBox

from ink.presentation.canvas import SchematicCanvas

if TYPE_CHECKING:
    from ink.infrastructure.persistence.app_settings import AppSettings


class InkMainWindow(QMainWindow):
    """Main application window shell for Ink schematic viewer.

    This window serves as the root container for the entire Ink application,
    providing the foundation for the presentation layer. It handles:
    - Window title and identification
    - Default and minimum window sizing
    - Standard window decorations (minimize, maximize, close)
    - Window geometry persistence across sessions (when app_settings provided)
    - Menu bar with Help > Settings for settings management

    When constructed with an AppSettings instance, the window automatically:
    - Restores saved geometry (size, position) on startup
    - Restores saved state (dock widget layout) on startup
    - Saves geometry and state when the window closes

    The window is designed to work well on 1080p displays while remaining
    usable on smaller 768p screens.

    Attributes:
        schematic_canvas: The central canvas widget for schematic visualization.
        app_settings: Optional settings manager for geometry persistence and management.
        _WINDOW_TITLE: Application title shown in title bar.
        _DEFAULT_WIDTH: Default window width in pixels (optimized for 1080p).
        _DEFAULT_HEIGHT: Default window height in pixels.
        _GEOMETRY_DEFAULT_WIDTH: Default width when using geometry persistence.
        _GEOMETRY_DEFAULT_HEIGHT: Default height when using geometry persistence.
        _MIN_WIDTH: Minimum allowed window width.
        _MIN_HEIGHT: Minimum allowed window height.

    Example:
        >>> from ink.presentation.main_window import InkMainWindow
        >>> window = InkMainWindow()
        >>> window.show()

        # With geometry persistence:
        >>> from ink.infrastructure.persistence.app_settings import AppSettings
        >>> settings = AppSettings()
        >>> window = InkMainWindow(app_settings=settings)
        >>> window.show()

    See Also:
        - E06-F01-T03: Adds dock widgets (hierarchy, properties)
        - E06-F01-T04: Integrates window into main.py entry point
        - E06-F06-T02: Window geometry persistence
        - E06-F06-T04: Settings migration and reset functionality
    """

    # Instance attribute type hints for IDE/type checker support
    schematic_canvas: SchematicCanvas
    app_settings: AppSettings | None

    # Window configuration constants
    # These are class-level to make requirements explicit and testable
    _WINDOW_TITLE: str = "Ink - Incremental Schematic Viewer"
    _DEFAULT_WIDTH: int = 1600  # Optimal for 1080p (1920x1080) with taskbar
    _DEFAULT_HEIGHT: int = 900  # 16:9 aspect ratio, fits 1080p displays
    _MIN_WIDTH: int = 1024  # Common minimum for professional tools
    _MIN_HEIGHT: int = 768  # Supports 768p displays as minimum

    # Geometry persistence defaults (E06-F06-T02 spec)
    # When using app_settings, these smaller defaults leave room for
    # users to resize window without feeling constrained
    _GEOMETRY_DEFAULT_WIDTH: int = 1280
    _GEOMETRY_DEFAULT_HEIGHT: int = 800

    def __init__(self, app_settings: AppSettings | None = None) -> None:
        """Initialize the main window with configured properties.

        Sets up window title, size constraints, decorations, central widget,
        and menu bar. If app_settings is provided, restores saved geometry
        and state. Does not show the window - caller must call show() explicitly.

        Args:
            app_settings: Optional settings manager for geometry persistence
                          and settings management. If provided, geometry will
                          be saved on close and restored on startup, and
                          settings menu items will be enabled.
        """
        super().__init__()
        self.app_settings = app_settings

        # Setup UI components BEFORE restoring geometry
        # restoreState() requires dock widgets to exist first
        self._setup_window()
        self._setup_central_widget()
        self._setup_menus()

        # Restore geometry AFTER all widgets are created
        if self.app_settings is not None:
            self._restore_geometry()

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

    def _setup_central_widget(self) -> None:
        """Create and configure the central schematic canvas.

        The central widget is the primary workspace area in QMainWindow.
        It occupies the largest portion of the window and cannot be
        closed or moved (unlike dock widgets).

        Design decisions:
            - SchematicCanvas is stored as instance attribute for future access
            - Parent set to self for Qt memory management (auto-deletion)
            - setCentralWidget() makes Qt manage layout automatically

        The canvas will be accessible via:
            - window.schematic_canvas (direct attribute access)
            - window.centralWidget() (Qt standard method)
        """
        # Create canvas with self as parent for proper Qt ownership
        # When InkMainWindow is destroyed, schematic_canvas is auto-deleted
        self.schematic_canvas = SchematicCanvas(parent=self)

        # Set as central widget - Qt handles layout and sizing
        # Central widget automatically fills available space between
        # toolbars, dock widgets, and status bar
        self.setCentralWidget(self.schematic_canvas)

    def _setup_menus(self) -> None:
        """Set up the application menu bar.

        Creates the menu structure:
        - Help menu with Settings submenu for managing application settings

        The Settings menu provides:
        - Reset Window Layout: Clears saved window geometry
        - Clear Recent Files: Clears the recent files list
        - Reset All Settings: Resets everything to defaults (with confirmation)
        - Show Settings File Location: Shows where settings are stored
        """
        menubar = self.menuBar()

        # Help menu (rightmost, as per convention)
        help_menu = menubar.addMenu("&Help")

        # Add separator before settings submenu
        help_menu.addSeparator()

        # Settings submenu for settings management
        settings_menu = QMenu("&Settings", self)
        help_menu.addMenu(settings_menu)

        # Reset Window Layout action
        reset_geometry_action = settings_menu.addAction("Reset Window Layout")
        reset_geometry_action.triggered.connect(self._on_reset_geometry)
        reset_geometry_action.setEnabled(self.app_settings is not None)

        # Clear Recent Files action
        reset_recent_action = settings_menu.addAction("Clear Recent Files")
        reset_recent_action.triggered.connect(self._on_clear_recent_files)
        reset_recent_action.setEnabled(self.app_settings is not None)

        settings_menu.addSeparator()

        # Reset All Settings action (destructive, at bottom with separator)
        reset_all_action = settings_menu.addAction("Reset All Settings...")
        reset_all_action.triggered.connect(self._on_reset_all_settings)
        reset_all_action.setEnabled(self.app_settings is not None)

        settings_menu.addSeparator()

        # Show Settings File Location action (diagnostic)
        show_settings_action = settings_menu.addAction("Show Settings File Location")
        show_settings_action.triggered.connect(self._on_show_settings_location)
        show_settings_action.setEnabled(self.app_settings is not None)

    # =========================================================================
    # Window Geometry Persistence (E06-F06-T02)
    # =========================================================================
    # These methods handle saving and restoring window geometry and state.
    # They integrate with AppSettings to persist window layout across sessions.

    def _restore_geometry(self) -> None:
        """Restore window geometry and state from settings.

        This method is called during initialization (after all widgets are
        created) to restore the window layout from the previous session.

        Restoration order:
        1. Load and apply geometry (size, position)
        2. If no geometry saved, use defaults and center on screen
        3. Load and apply state (dock widget layout)

        Qt's restoreGeometry() handles edge cases like:
        - Multi-monitor setups (saved screen no longer available)
        - Resolution changes (window would be off-screen)
        - Corrupted data (returns False, no crash)
        """
        if self.app_settings is None:
            return

        # Restore geometry (size, position, maximized state)
        geometry = self.app_settings.load_window_geometry()
        if geometry is not None and not geometry.isEmpty():
            # restoreGeometry returns bool indicating success
            # On failure (invalid data), window keeps current geometry
            if not self.restoreGeometry(geometry):
                # Restoration failed - use defaults
                self._apply_default_geometry()
        else:
            # First run - no saved geometry
            self._apply_default_geometry()

        # Restore state (dock widget layout, toolbar positions)
        state = self.app_settings.load_window_state()
        if state is not None and not state.isEmpty():
            # restoreState returns bool indicating success
            # On failure, window keeps default dock layout
            self.restoreState(state)

    def _apply_default_geometry(self) -> None:
        """Apply default geometry for first run or invalid saved geometry.

        Sets the window to the geometry persistence defaults (1280x800)
        and centers the window on the primary screen.
        """
        self.resize(self._GEOMETRY_DEFAULT_WIDTH, self._GEOMETRY_DEFAULT_HEIGHT)
        self._center_on_screen()

    def _center_on_screen(self) -> None:
        """Center the window on the primary screen.

        Calculates the center position of the primary screen and moves
        the window so its center aligns with the screen center.

        This provides a good initial position for first-run users,
        ensuring the window is fully visible and prominently placed.
        """
        screen = QGuiApplication.primaryScreen()
        # primaryScreen() returns QScreen which is never None in normal use
        # But for type safety, we check and skip centering if unavailable
        if screen is not None:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _save_geometry(self) -> None:
        """Save window geometry and state to settings.

        This method is called from closeEvent() to persist the window
        layout before the application exits.

        Saves:
        - Geometry: window size, position, maximized/minimized state
        - State: dock widget positions, sizes, visibility, floating state

        After saving, sync() is called to force immediate write to disk,
        ensuring data is not lost if the system crashes after closing.
        """
        if self.app_settings is None:
            return

        # Save current geometry and state
        self.app_settings.save_window_geometry(self.saveGeometry())
        self.app_settings.save_window_state(self.saveState())

        # Force write to disk to ensure persistence
        self.app_settings.sync()

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event - save geometry and state.

        This method is called by Qt when the user closes the window.
        It saves the current window layout before allowing the close.

        Args:
            event: The close event from Qt. Call accept() to close,
                   ignore() to prevent closing.
        """
        # Save geometry before closing
        self._save_geometry()

        # Accept the close event - window will close
        event.accept()

    # =========================================================================
    # Settings Menu Action Handlers (E06-F06-T04)
    # =========================================================================

    def _on_reset_geometry(self) -> None:
        """Handle Reset Window Layout action.

        Clears the saved window geometry and state, then informs the user
        that a restart is required for changes to take effect.
        """
        if self.app_settings is None:
            return

        reply = QMessageBox.question(
            self,
            "Reset Window Layout",
            "Reset window size and position to defaults?\n\n"
            "The application will use default layout on next restart.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.app_settings.reset_window_geometry()
            QMessageBox.information(
                self,
                "Window Layout Reset",
                "Window layout has been reset.\n\n"
                "Restart the application to apply the new layout.",
            )

    def _on_clear_recent_files(self) -> None:
        """Handle Clear Recent Files action.

        Clears the recent files list immediately without requiring restart.
        """
        if self.app_settings is None:
            return

        reply = QMessageBox.question(
            self,
            "Clear Recent Files",
            "Clear the list of recently opened files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.app_settings.reset_recent_files()
            QMessageBox.information(
                self,
                "Recent Files Cleared",
                "The recent files list has been cleared.",
            )

    def _on_reset_all_settings(self) -> None:
        """Handle Reset All Settings action.

        Shows a confirmation dialog with details about what will be reset,
        then resets all settings if confirmed. Informs user about restart.
        """
        if self.app_settings is None:
            return

        reply = QMessageBox.question(
            self,
            "Reset All Settings",
            "Reset all settings to defaults?\n\n"
            "This will:\n"
            "• Clear window layout\n"
            "• Clear recent files\n"
            "• Reset all preferences\n\n"
            "The application will use default settings on next restart.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,  # Default to No for safety
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.app_settings.reset_all_settings()
            QMessageBox.information(
                self,
                "Settings Reset",
                "All settings have been reset to defaults.\n\n"
                "Restart the application to apply the changes.",
            )

    def _on_show_settings_location(self) -> None:
        """Handle Show Settings File Location action.

        Displays an information dialog showing where settings are stored.
        Useful for debugging and support purposes.
        """
        if self.app_settings is None:
            return

        settings_path = self.app_settings.get_settings_file_path()

        QMessageBox.information(
            self,
            "Settings File Location",
            f"Settings are stored at:\n\n{settings_path}",
        )
