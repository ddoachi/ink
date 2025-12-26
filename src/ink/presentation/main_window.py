"""Main application window for Ink schematic viewer.

This module provides the InkMainWindow class, the root container for the Ink
application. It establishes the presentation layer foundation with proper
window management (title, sizing, decorations) following Qt best practices.

Design Decisions:
    - Extends QMainWindow (not QWidget) for built-in menu, toolbar, dock support
    - Explicit window flags ensure consistent decorations across Linux WMs
    - Default 1600x900 size optimized for 1080p displays with taskbar visible
    - Minimum 1024x768 prevents unusable cramped layouts
    - SchematicCanvas as central widget provides primary workspace area
    - AppSettings injected via constructor for testability and separation of concerns
    - Recent files menu dynamically updated from AppSettings

See Also:
    - Spec E06-F01-T01 for window shell requirements
    - Spec E06-F01-T02 for central widget requirements
    - Spec E06-F06-T03 for recent files menu requirements
    - Qt documentation on QMainWindow for extension points
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMenu, QMessageBox

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
    - File menu with Open and Recent Files functionality
    - Recent files list management

    The window is designed to work well on 1080p displays while remaining
    usable on smaller 768p screens.

    Attributes:
        app_settings: Application settings manager for recent files persistence.
        schematic_canvas: The central canvas widget for schematic visualization.
        recent_files_menu: Submenu for displaying recent files.
        _WINDOW_TITLE: Application title shown in title bar.
        _DEFAULT_WIDTH: Default window width in pixels (optimized for 1080p).
        _DEFAULT_HEIGHT: Default window height in pixels.
        _MIN_WIDTH: Minimum allowed window width.
        _MIN_HEIGHT: Minimum allowed window height.

    Example:
        >>> from ink.presentation.main_window import InkMainWindow
        >>> from ink.infrastructure.persistence.app_settings import AppSettings
        >>> settings = AppSettings()
        >>> window = InkMainWindow(settings)
        >>> window.show()

    See Also:
        - E06-F01-T03: Adds dock widgets (hierarchy, properties)
        - E06-F01-T04: Integrates window into main.py entry point
        - E06-F06-T03: Recent files management (implemented here)
    """

    # Instance attribute type hints for IDE/type checker support
    app_settings: AppSettings
    schematic_canvas: SchematicCanvas
    recent_files_menu: QMenu

    # Window configuration constants
    # These are class-level to make requirements explicit and testable
    _WINDOW_TITLE: str = "Ink - Incremental Schematic Viewer"
    _DEFAULT_WIDTH: int = 1600  # Optimal for 1080p (1920x1080) with taskbar
    _DEFAULT_HEIGHT: int = 900  # 16:9 aspect ratio, fits 1080p displays
    _MIN_WIDTH: int = 1024  # Common minimum for professional tools
    _MIN_HEIGHT: int = 768  # Supports 768p displays as minimum

    # Maximum number of menu items that get keyboard shortcut (Alt+1 through Alt+9)
    _MAX_SHORTCUT_ITEMS: int = 9

    def __init__(self, app_settings: AppSettings) -> None:
        """Initialize the main window with configured properties.

        Sets up window title, size constraints, decorations, menus, and central widget.
        Does not show the window - caller must call show() explicitly.

        Args:
            app_settings: Application settings manager for persisting recent files
                         and other application state.
        """
        super().__init__()

        # Store settings reference for recent files management
        # This is injected rather than created here for testability
        self.app_settings = app_settings

        self._setup_window()
        self._setup_menus()
        self._setup_central_widget()

        # Initialize recent files menu with current list
        self._update_recent_files_menu()

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

    def _setup_menus(self) -> None:
        """Set up application menu bar with File menu.

        Creates the main menu structure:
        - File menu with Open, Open Recent submenu, and Exit actions
        - Open Recent submenu dynamically populated with recent files
        - Keyboard shortcuts for common actions

        Menu Structure:
            File
            ├── Open... (Ctrl+O)
            ├── Open Recent ►
            │   ├── 1. file1.ckt
            │   ├── 2. file2.ckt
            │   ├── ───────────
            │   └── Clear Recent Files
            ├── ─────────────
            └── Exit (Ctrl+Q)
        """
        menubar = self.menuBar()

        # =================================================================
        # File Menu
        # =================================================================
        file_menu = menubar.addMenu("&File")

        # Open action - opens file dialog for netlist selection
        open_action = file_menu.addAction("&Open...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file_dialog)

        # Recent files submenu - dynamically populated from settings
        # Menu is stored as instance attribute for updates
        self.recent_files_menu = file_menu.addMenu("Open &Recent")

        file_menu.addSeparator()

        # Exit action - closes the application
        exit_action = file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

    def _update_recent_files_menu(self) -> None:
        """Update the recent files menu with current list from settings.

        Rebuilds the entire recent files menu:
        - Clears existing menu items
        - Adds action for each recent file (numbered 1-9 with shortcuts)
        - Adds separator and "Clear Recent Files" action
        - Shows "No Recent Files" placeholder if list is empty

        This method is called:
        - At window initialization
        - After opening a file
        - After clicking a recent file
        - After clearing recent files

        Menu items for files 1-9 have keyboard shortcuts (Alt+1 through Alt+9)
        via the & prefix in the menu text.
        """
        self.recent_files_menu.clear()

        recent_files = self.app_settings.get_recent_files()

        if recent_files:
            # Add action for each recent file
            for i, file_path in enumerate(recent_files):
                # Format display name with numbering
                display_name = self._format_recent_file_name(file_path, i)

                action = self.recent_files_menu.addAction(display_name)

                # Store full path in action data for retrieval on click
                action.setData(file_path)

                # Set tooltip to show full path on hover
                action.setToolTip(file_path)

                # Connect action to file open handler
                # Using lambda with default argument to capture current file_path
                # Note: checked parameter is required by Qt signal signature
                action.triggered.connect(
                    lambda _checked=False, path=file_path: self._on_open_recent_file(
                        path
                    )
                )

            self.recent_files_menu.addSeparator()

            # Add "Clear Recent Files" action at the end
            clear_action = self.recent_files_menu.addAction("Clear Recent Files")
            clear_action.triggered.connect(self._on_clear_recent_files)
        else:
            # Show "No Recent Files" placeholder when list is empty
            no_files_action = self.recent_files_menu.addAction("No Recent Files")
            no_files_action.setEnabled(False)  # Disabled, non-clickable

    def _format_recent_file_name(self, file_path: str, index: int) -> str:
        """Format a recent file path for menu display.

        Creates a menu-friendly display name with:
        - Number prefix (1-based)
        - & shortcut for items 1-9 (allows Alt+1 through Alt+9)
        - Just the filename (not full path)

        Args:
            file_path: Full absolute path to the file.
            index: Zero-based index in the recent files list.

        Returns:
            Formatted display name, e.g., "&1. design.ckt" or "10. other.ckt"

        Example:
            >>> window._format_recent_file_name("/path/to/design.ckt", 0)
            "&1. design.ckt"
            >>> window._format_recent_file_name("/path/to/other.ckt", 9)
            "10. other.ckt"
        """
        path = Path(file_path)

        # Use 1-based numbering for menu display (more natural for users)
        number = index + 1

        # Files 1-9 get & shortcut prefix for Alt+N keyboard access
        # File 10+ don't get shortcut (would require two-key shortcuts)
        if number <= self._MAX_SHORTCUT_ITEMS:
            return f"&{number}. {path.name}"
        return f"{number}. {path.name}"

    def _on_open_file_dialog(self) -> None:
        """Handle File > Open action.

        Opens a file dialog for the user to select a netlist file.
        Supports .ckt, .cdl, and .sp file extensions.
        If a file is selected, it is opened via _open_file().
        """
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Netlist File",
            "",  # Start in current/last directory
            "Netlist Files (*.ckt *.cdl *.sp);;All Files (*)",
        )

        if file_path:
            self._open_file(file_path)

    def _on_open_recent_file(self, file_path: str) -> None:
        """Handle clicking a recent file menu item.

        Checks if the file still exists before attempting to open:
        - If file exists: Opens it via _open_file()
        - If file doesn't exist: Shows warning and updates menu

        Args:
            file_path: Absolute path to the file from the recent files list.
        """
        if Path(file_path).exists():
            self._open_file(file_path)
        else:
            # File no longer exists - show warning to user
            QMessageBox.warning(
                self,
                "File Not Found",
                f"The file no longer exists:\n{file_path}",
            )

            # Refresh menu - get_recent_files() will auto-remove non-existent files
            self._update_recent_files_menu()

    def _open_file(self, file_path: str) -> None:
        """Open a netlist file.

        This is the central file opening method. All file opens (dialog,
        recent menu, command line) should go through this method to ensure
        consistent behavior:
        1. Parse the netlist file (TODO: implement when CDLParser is ready)
        2. Display on canvas (TODO: implement when canvas display is ready)
        3. Add to recent files list
        4. Update recent files menu
        5. Update window title

        Args:
            file_path: Absolute path to the netlist file.

        Note:
            For MVP, actual netlist parsing is not implemented yet.
            This method focuses on recent files management.
        """
        # Add file to recent files list (moves to front if already present)
        self.app_settings.add_recent_file(file_path)

        # Refresh the recent files menu to reflect the update
        self._update_recent_files_menu()

        # Update window title to show current file (format: "Ink - filename.ckt")
        filename = Path(file_path).name
        self.setWindowTitle(f"Ink - {filename}")

    def _on_clear_recent_files(self) -> None:
        """Handle Clear Recent Files action.

        Clears all entries from the recent files list and updates the menu
        to show the empty state placeholder.
        """
        self.app_settings.clear_recent_files()
        self._update_recent_files_menu()

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
