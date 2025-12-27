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
    - Three dock widgets for supporting panels (hierarchy, properties, messages)
    - Dock nesting enabled for complex layout configurations
    - AppSettings injected via constructor for testability and separation of concerns
    - Recent files menu dynamically updated from AppSettings

See Also:
    - Spec E06-F01-T01 for window shell requirements
    - Spec E06-F01-T02 for central widget requirements
    - Spec E06-F01-T03 for dock widget requirements
    - Spec E06-F06-T02 for window geometry persistence
    - Spec E06-F06-T03 for recent files menu requirements
    - Spec E06-F06-T04 for settings migration and reset
    - Qt documentation on QMainWindow for extension points
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QToolBar,
)

from ink.presentation.canvas import SchematicCanvas
from ink.presentation.panels import HierarchyPanel, MessagePanel, PropertyPanel
from ink.presentation.state import PanelStateManager

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
    - Three dock widgets for supporting panels
    - Dock nesting for complex layout configurations
    - Window geometry persistence across sessions (when app_settings provided)
    - Menu bar with Help > Settings for settings management

    When constructed with an AppSettings instance, the window automatically:
    - Restores saved geometry (size, position) on startup
    - Restores saved state (dock widget layout) on startup
    - Saves geometry and state when the window closes

    The window is designed to work well on 1080p displays while remaining
    usable on smaller 768p screens.

    Dock Widgets:
        - hierarchy_dock: Left area - design object tree navigation
        - property_dock: Right area - object property inspector
        - message_dock: Bottom area - search results and logs

    Attributes:
        app_settings: Application settings manager for recent files persistence.
        schematic_canvas: The central canvas widget for schematic visualization.
        recent_files_menu: Submenu for displaying recent files.
        panel_state_manager: Manages panel state tracking and visibility control.
        hierarchy_panel: Placeholder for hierarchy tree (full impl: E04-F01).
        hierarchy_dock: Dock widget containing hierarchy_panel.
        property_panel: Placeholder for property inspector (full impl: E04-F04).
        property_dock: Dock widget containing property_panel.
        message_panel: Placeholder for search/log panel (full impl: E04-F03).
        message_dock: Dock widget containing message_panel.

    Example:
        >>> from ink.presentation.main_window import InkMainWindow
        >>> from ink.infrastructure.persistence.app_settings import AppSettings
        >>> settings = AppSettings()
        >>> window = InkMainWindow(settings)
        >>> window.show()

    See Also:
        - E06-F01-T03: Dock widget configuration
        - E06-F01-T04: Integrates window into main.py entry point
        - E06-F02: Menu system with View menu for panel toggling
        - E06-F05: Panel state persistence with QSettings
        - E06-F06-T02: Window geometry persistence
        - E06-F06-T03: Recent files management (implemented here)
        - E06-F06-T04: Settings migration and reset functionality
    """

    # Instance attribute type hints for IDE/type checker support
    app_settings: AppSettings
    schematic_canvas: SchematicCanvas
    # Menu bar menus (E06-F02-T01)
    file_menu: QMenu
    edit_menu: QMenu
    view_menu: QMenu
    help_menu: QMenu
    recent_files_menu: QMenu
    panel_state_manager: PanelStateManager
    hierarchy_panel: HierarchyPanel
    hierarchy_dock: QDockWidget
    property_panel: PropertyPanel
    property_dock: QDockWidget
    message_panel: MessagePanel
    message_dock: QDockWidget
    _toolbar: QToolBar

    # Toolbar action type hints (E06-F03-T03)
    _open_action: QAction
    _undo_action: QAction
    _redo_action: QAction
    _search_action: QAction

    # Status bar widget type hints (E06-F04-T01)
    file_label: QLabel
    zoom_label: QLabel
    selection_label: QLabel
    object_count_label: QLabel

    # Window configuration constants
    # These are class-level to make requirements explicit and testable
    _WINDOW_TITLE: str = "Ink - Incremental Schematic Viewer"
    _DEFAULT_WIDTH: int = 1600  # Optimal for 1080p (1920x1080) with taskbar
    _DEFAULT_HEIGHT: int = 900  # 16:9 aspect ratio, fits 1080p displays
    _MIN_WIDTH: int = 1024  # Common minimum for professional tools
    _MIN_HEIGHT: int = 768  # Supports 768p displays as minimum

    # Maximum number of menu items that get keyboard shortcut (Alt+1 through Alt+9)
    _MAX_SHORTCUT_ITEMS: int = 9

    # Geometry persistence defaults (E06-F06-T02 spec)
    # When using app_settings, these smaller defaults leave room for
    # users to resize window without feeling constrained
    _GEOMETRY_DEFAULT_WIDTH: int = 1280
    _GEOMETRY_DEFAULT_HEIGHT: int = 800

    def __init__(self, app_settings: AppSettings) -> None:
        """Initialize the main window with configured properties.

        Sets up window title, size constraints, decorations, central widget,
        dock widgets, and menu bar. If app_settings is provided, restores
        saved geometry and state. Does not show the window - caller must call
        show() explicitly.

        Args:
            app_settings: Settings manager for geometry persistence,
                          recent files, and settings management.

        Initialization order:
            1. Window properties (title, size, flags)
            2. Central widget (schematic canvas)
            3. Dock widgets (hierarchy, properties, messages)
            4. Menu bar (File, Help > Settings)
            5. Restore geometry (if saved)
            6. Update recent files menu

        This order ensures dock widgets exist before restoreState() is called,
        as Qt requires dock widgets to be present for state restoration.
        """
        super().__init__()

        # Store settings reference for recent files management and geometry
        # This is injected rather than created here for testability
        self.app_settings = app_settings

        # Setup UI components BEFORE restoring geometry
        # restoreState() requires dock widgets to exist first
        self._setup_window()
        self._setup_central_widget()
        self._setup_dock_widgets()
        self._setup_status_bar()
        self._setup_menus()
        self._setup_toolbar()

        # Restore geometry AFTER all widgets are created
        self._restore_geometry()

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
            5. Dock nesting - enables complex dock arrangements
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

        # Enable dock nesting for complex layouts
        # This allows docks to be split horizontally or vertically within
        # a single dock area, enabling more flexible panel arrangements
        self.setDockNestingEnabled(True)

        # Enable animated dock transitions for smooth user experience
        self.setAnimated(True)

        # Apply visual polish styling
        self._apply_styling()

    def _apply_styling(self) -> None:
        """Apply visual polish styling to the main window.

        Enhances the visual appearance for a professional look:
        - Visible splitter handles for intuitive panel resizing
        - Hover effects on splitters for better discoverability
        - Styled dock widget title bars
        - Consistent background colors

        Design Decisions:
            - Neutral gray color palette for professional appearance
            - Subtle borders to differentiate panel boundaries
            - Hover effects to indicate interactivity
            - Minimal styling to avoid distracting from content

        The stylesheet is kept minimal for MVP - a full theming system
        is planned for P1. This provides functional polish without
        over-engineering.

        See Also:
            - E06-F01-T05 spec for UI polish requirements
            - Future: Theme system in E06 (P1)
        """
        self.setStyleSheet("""
            /* Main Window Background
               Light gray provides neutral backdrop for content panels */
            QMainWindow {
                background-color: #f5f5f5;
            }

            /* Dock Widget Title Bar Styling
               Slightly darker background makes titles distinguishable
               from content while maintaining visual harmony */
            QDockWidget::title {
                background-color: #e8e8e8;
                padding: 6px;
                border-bottom: 1px solid #d0d0d0;
            }

            /* Splitter Handle Styling
               Default Qt splitters are subtle (1px). These styles make
               them more visible and provide feedback on interaction */
            QSplitter::handle {
                background-color: #d0d0d0;
            }

            QSplitter::handle:hover {
                background-color: #b0b0b0;
            }

            /* Horizontal splitters (between left/right areas) */
            QSplitter::handle:horizontal {
                width: 2px;
            }

            /* Vertical splitters (between top/bottom areas) */
            QSplitter::handle:vertical {
                height: 2px;
            }

            /* Dock Widget Content Background
               White background for panel content provides clear
               visual separation from the main window background */
            QDockWidget QWidget {
                background-color: #ffffff;
            }
        """)

    def _setup_toolbar(self) -> None:
        """Create and configure the main toolbar.

        Creates a QToolBar with standard configuration for hosting action
        buttons. The toolbar is set up as infrastructure for subsequent
        tasks (E06-F03-T02, E06-F03-T03) to add actual action buttons.

        Toolbar Configuration:
            - Window title: "Main Toolbar" (displayed when floated)
            - Object name: "MainToolBar" (required for QSettings persistence)
            - Movable: False (fixed position for MVP simplicity)
            - Icon size: 24x24 pixels (standard toolbar icon size)
            - Button style: Icon only (compact appearance with tooltips)
            - Position: Top toolbar area (below menu bar)

        Group Structure (separators added in subsequent tasks):
            1. File Group: File operations (Open)
            2. Edit Group: Undo/Redo operations
            3. View Group: Zoom and view controls
            4. Search Group: Search functionality

        Design Decisions:
            - Non-movable for MVP prevents accidental rearrangement
            - 24x24 icon size is standard and works well on high-DPI displays
            - Icon-only style keeps toolbar compact; tooltips provide labels
            - Object name enables toolbar state persistence via QSettings

        See Also:
            - Spec E06-F03-T01 for toolbar infrastructure requirements
            - Spec E06-F03-T02 for view control tools (adds zoom/fit actions)
            - Spec E06-F03-T03 for edit/search tools (adds undo/redo/search)
            - Spec E06-F03-T04 for icon resources
        """
        # Create toolbar with descriptive title
        # Title is shown when toolbar is floated (future feature)
        toolbar = QToolBar("Main Toolbar", self)

        # Set object name for QSettings state persistence
        # Without this, saveState()/restoreState() cannot identify the toolbar
        toolbar.setObjectName("MainToolBar")

        # Make toolbar fixed (non-movable) for MVP
        # This prevents accidental rearrangement and simplifies the UI
        # Future enhancement: Allow customization via preferences
        toolbar.setMovable(False)

        # Set standard 24x24 icon size
        # This size is:
        # - Readable on high-DPI displays
        # - Consistent with common icon libraries
        # - Standard for professional applications
        toolbar.setIconSize(QSize(24, 24))

        # Set button style to icon-only for compact appearance
        # Text labels are available via tooltips on hover
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

        # Add toolbar to main window in top area (below menu bar)
        self.addToolBar(toolbar)

        # Store reference for action additions in subsequent tasks
        # Tasks T02 and T03 will use this to add their actions
        self._toolbar = toolbar

        # Add action groups with separators (E06-F03-T03)
        # Group 1: File operations
        self._add_file_actions(toolbar)
        toolbar.addSeparator()

        # Group 2: Edit operations (Undo/Redo)
        self._add_edit_actions(toolbar)
        toolbar.addSeparator()

        # Group 3: Search operations
        self._add_search_actions(toolbar)

    def _add_file_actions(self, toolbar: QToolBar) -> None:
        """Add file-related toolbar actions.

        Creates the Open button for loading netlist files. The Open action
        is always enabled and triggers the file dialog.

        Action Configuration:
            - Icon: document-open (from system theme)
            - Text: "Open"
            - Shortcut: Ctrl+O (QKeySequence.StandardKey.Open)
            - Tooltip: "Open netlist file (Ctrl+O)"
            - Enabled: Always (users can open files at any time)

        Args:
            toolbar: The QToolBar to add actions to.

        See Also:
            - Spec E06-F03-T03 for file action requirements
            - _on_open_file_dialog() for the file dialog handler
        """
        # Create Open action with system theme icon
        # The document-open icon is standard across desktop environments
        self._open_action = QAction(
            QIcon.fromTheme("document-open"),
            "Open",
            self,
        )

        # Set tooltip with keyboard shortcut for discoverability
        # Users hovering over the button will see this helpful hint
        self._open_action.setToolTip("Open netlist file (Ctrl+O)")

        # Use Qt's standard Open shortcut (Ctrl+O on most platforms)
        # This ensures platform-appropriate behavior
        self._open_action.setShortcut(QKeySequence.StandardKey.Open)

        # Connect to the existing file dialog handler from E06-F02-T02
        # This reuses the file opening infrastructure already in place
        self._open_action.triggered.connect(self._on_open_file_dialog)

        # Add to toolbar
        toolbar.addAction(self._open_action)

    def _add_edit_actions(self, toolbar: QToolBar) -> None:
        """Add edit-related toolbar actions (Undo/Redo).

        Creates Undo and Redo buttons for expansion/collapse operations.
        Both actions are initially disabled and their state is managed by
        _update_undo_redo_state() based on expansion service history.

        Undo Action Configuration:
            - Icon: edit-undo (from system theme)
            - Text: "Undo"
            - Shortcut: Ctrl+Z (QKeySequence.StandardKey.Undo)
            - Tooltip: "Undo expansion/collapse (Ctrl+Z)"
            - Enabled: Initially disabled, updated by service state

        Redo Action Configuration:
            - Icon: edit-redo (from system theme)
            - Text: "Redo"
            - Shortcut: Ctrl+Shift+Z (QKeySequence.StandardKey.Redo)
            - Tooltip: "Redo expansion/collapse (Ctrl+Shift+Z)"
            - Enabled: Initially disabled, updated by service state

        Args:
            toolbar: The QToolBar to add actions to.

        See Also:
            - Spec E06-F03-T03 for edit action requirements
            - _on_undo() and _on_redo() for action handlers
            - _update_undo_redo_state() for state management
        """
        # Create Undo action
        self._undo_action = QAction(
            QIcon.fromTheme("edit-undo"),
            "Undo",
            self,
        )
        self._undo_action.setToolTip("Undo expansion/collapse (Ctrl+Z)")
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        # Initially disabled - no history at startup
        self._undo_action.setEnabled(False)
        self._undo_action.triggered.connect(self._on_undo)
        toolbar.addAction(self._undo_action)

        # Create Redo action
        self._redo_action = QAction(
            QIcon.fromTheme("edit-redo"),
            "Redo",
            self,
        )
        self._redo_action.setToolTip("Redo expansion/collapse (Ctrl+Shift+Z)")
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        # Initially disabled - no redo history at startup
        self._redo_action.setEnabled(False)
        self._redo_action.triggered.connect(self._on_redo)
        toolbar.addAction(self._redo_action)

    def _add_search_actions(self, toolbar: QToolBar) -> None:
        """Add search-related toolbar actions.

        Creates the Search button for finding cells, nets, and pins.
        The Search action is always enabled and shows/focuses the search panel.

        Action Configuration:
            - Icon: edit-find (from system theme)
            - Text: "Search"
            - Shortcut: Ctrl+F (QKeySequence.StandardKey.Find)
            - Tooltip: "Search cells/nets/pins (Ctrl+F)"
            - Enabled: Always (search is available anytime)

        Args:
            toolbar: The QToolBar to add actions to.

        See Also:
            - Spec E06-F03-T03 for search action requirements
            - _on_find() for the search handler
        """
        # Create Search action
        self._search_action = QAction(
            QIcon.fromTheme("edit-find"),
            "Search",
            self,
        )
        self._search_action.setToolTip("Search cells/nets/pins (Ctrl+F)")
        self._search_action.setShortcut(QKeySequence.StandardKey.Find)
        self._search_action.triggered.connect(self._on_find)
        toolbar.addAction(self._search_action)

    def _on_undo(self) -> None:
        """Handle Undo action from toolbar or keyboard shortcut.

        Calls the expansion service's undo method if available, then updates
        the undo/redo button states. Uses defensive programming to handle
        the case where the expansion service is not yet initialized.

        This allows the UI to be functional even before all services are
        integrated (graceful degradation for MVP).

        See Also:
            - Spec E06-F03-T03 for undo requirements
            - _update_undo_redo_state() for state management
        """
        # Defensive check for expansion service existence
        # Service may not be initialized yet during early development
        if hasattr(self, "_expansion_service") and self._expansion_service is not None:
            self._expansion_service.undo()
            self._update_undo_redo_state()

    def _on_redo(self) -> None:
        """Handle Redo action from toolbar or keyboard shortcut.

        Calls the expansion service's redo method if available, then updates
        the undo/redo button states. Uses defensive programming to handle
        the case where the expansion service is not yet initialized.

        This allows the UI to be functional even before all services are
        integrated (graceful degradation for MVP).

        See Also:
            - Spec E06-F03-T03 for redo requirements
            - _update_undo_redo_state() for state management
        """
        # Defensive check for expansion service existence
        if hasattr(self, "_expansion_service") and self._expansion_service is not None:
            self._expansion_service.redo()
            self._update_undo_redo_state()

    def _on_find(self) -> None:
        """Handle Search action from toolbar or keyboard shortcut.

        Shows the search panel if hidden, or focuses the search input if
        the panel is already visible. Uses defensive programming to handle
        the case where the search panel is not yet initialized.

        Behavior:
            - Panel hidden: Show panel and focus search input
            - Panel visible: Focus search input (panel stays visible)
            - Panel not available: Show status bar message

        This design ensures users can quickly start searching without
        having to manually navigate to the search panel.

        See Also:
            - Spec E06-F03-T03 for search panel requirements
        """
        # Check for search panel existence
        if hasattr(self, "_search_panel") and self._search_panel is not None:
            if self._search_panel.isVisible():
                # Panel already visible - just focus the input
                self._search_panel.focus_search_input()
            else:
                # Panel hidden - show it and focus input
                self._search_panel.show()
                self._search_panel.focus_search_input()
        else:
            # Search panel not yet implemented - show status message
            self.statusBar().showMessage("Search panel not yet available", 3000)

    def _update_undo_redo_state(self) -> None:
        """Update Undo/Redo button enabled state based on expansion history.

        Queries the expansion service for undo/redo availability and updates
        the toolbar button states accordingly. Uses defensive programming
        to handle the case where the expansion service is not initialized.

        State Transitions:
            - No history: Both disabled
            - After expansion: Undo enabled, Redo disabled
            - After undo: Undo disabled (if empty), Redo enabled
            - After redo: Undo enabled, Redo disabled (if empty)

        This method is called:
            - After undo operation
            - After redo operation
            - After expansion/collapse (via signal connection when available)
            - When design is loaded (to reset state)

        See Also:
            - Spec E06-F03-T03 for state management requirements
        """
        # Defensive check for expansion service existence
        if hasattr(self, "_expansion_service") and self._expansion_service is not None:
            # Query service for current state
            can_undo = self._expansion_service.can_undo()
            can_redo = self._expansion_service.can_redo()

            # Update button states based on service response
            self._undo_action.setEnabled(can_undo)
            self._redo_action.setEnabled(can_redo)
        # If no service, buttons remain in their current state (disabled by default)

    def _setup_menus(self) -> None:
        """Set up application menu bar with File, Edit, View, and Help menus.

        Creates the main menu structure with all top-level menus in standard order.
        Each menu is stored as an instance variable for access by other components.
        Helper methods delegate menu population to keep code organized.

        Menu Structure (E06-F02-T01):
            File (E06-F02-T02 will populate)
            ├── Open... (Ctrl+O)
            ├── Open Recent ►
            ├── ─────────────
            └── Exit (Ctrl+Q)

            Edit (E06-F02-T03 will populate)
            └── (stub - populated by T03)

            View (E06-F02-T04 will populate)
            └── (stub - populated by T04)

            Help (E06-F02-T04 will populate)
            ├── ─────────────
            └── Settings ►

        The menus use mnemonics (& prefix) for Alt+key access:
        - &File → Alt+F
        - &Edit → Alt+E
        - &View → Alt+V
        - &Help → Alt+H

        See Also:
            - E06-F02-T01: Menu bar setup (this task)
            - E06-F02-T02: File menu actions
            - E06-F02-T03: Edit menu actions
            - E06-F02-T04: View and Help menu actions
        """
        # Get the menu bar (automatically created by QMainWindow)
        menubar = self.menuBar()

        # =================================================================
        # Create all four top-level menus in standard order
        # Store as instance variables for access by other components
        # =================================================================

        # File Menu - first in order, mnemonic Alt+F
        self.file_menu = menubar.addMenu("&File")
        self._create_file_menu()

        # Edit Menu - second in order, mnemonic Alt+E
        self.edit_menu = menubar.addMenu("&Edit")
        self._create_edit_menu()

        # View Menu - third in order, mnemonic Alt+V
        self.view_menu = menubar.addMenu("&View")
        self._create_view_menu()

        # Help Menu - last in order (standard placement), mnemonic Alt+H
        self.help_menu = menubar.addMenu("&Help")
        self._create_help_menu()

    def _create_file_menu(self) -> None:
        """Create File menu items.

        Populates the File menu with:
        - Open... (Ctrl+O): Opens file dialog for netlist selection
        - Open Recent: Submenu with recently opened files
        - Exit (Ctrl+Q): Closes the application

        This method contains the existing File menu implementation.
        Future tasks may add additional items (Save, Export, etc.)

        See Also:
            - E06-F02-T02: Will add additional file operations
            - E06-F06-T03: Recent files management
        """
        # Open action - opens file dialog for netlist selection
        open_action = self.file_menu.addAction("&Open...")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file_dialog)

        # Recent files submenu - dynamically populated from settings
        # Menu is stored as instance attribute for updates
        self.recent_files_menu = self.file_menu.addMenu("Open &Recent")

        self.file_menu.addSeparator()

        # Exit action - closes the application
        exit_action = self.file_menu.addAction("E&xit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)

    def _create_edit_menu(self) -> None:
        """Create Edit menu items.

        Currently a stub - will be populated by E06-F02-T03 with:
        - Undo/Redo actions
        - Selection actions
        - Copy/Paste operations

        See Also:
            - E06-F02-T03: Edit menu actions implementation
        """
        # Stub: Edit menu items will be added by E06-F02-T03
        pass

    def _create_view_menu(self) -> None:
        """Create View menu items.

        Currently a stub - will be populated by E06-F02-T04 with:
        - Zoom controls
        - Panel visibility toggles
        - Layout options

        See Also:
            - E06-F02-T04: View and Help menu actions implementation
        """
        # Stub: View menu items will be added by E06-F02-T04
        pass

    def _create_help_menu(self) -> None:
        """Create Help menu items.

        Populates the Help menu with:
        - Settings submenu for application settings management

        Future tasks may add additional help items (About, Documentation, etc.)

        See Also:
            - E06-F02-T04: Will add additional help items
            - E06-F06-T04: Settings management functionality
        """
        # Add separator before settings submenu
        self.help_menu.addSeparator()

        # Settings submenu for settings management
        settings_menu = QMenu("&Settings", self)
        self.help_menu.addMenu(settings_menu)

        # Reset Window Layout action
        reset_geometry_action = settings_menu.addAction("Reset Window Layout")
        reset_geometry_action.triggered.connect(self._on_reset_geometry)

        # Clear Recent Files action (in settings menu)
        reset_recent_action = settings_menu.addAction("Clear Recent Files")
        reset_recent_action.triggered.connect(self._on_clear_recent_files)

        settings_menu.addSeparator()

        # Reset All Settings action (destructive, at bottom with separator)
        reset_all_action = settings_menu.addAction("Reset All Settings...")
        reset_all_action.triggered.connect(self._on_reset_all_settings)

        settings_menu.addSeparator()

        # Show Settings File Location action (diagnostic)
        show_settings_action = settings_menu.addAction("Show Settings File Location")
        show_settings_action.triggered.connect(self._on_show_settings_location)

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
                    lambda _checked=False, path=file_path: self._on_open_recent_file(path)
                )

            self.recent_files_menu.addSeparator()

            # Add "Clear Recent Files" action at the end
            clear_action = self.recent_files_menu.addAction("Clear Recent Files")
            clear_action.triggered.connect(self._on_clear_recent_files_from_menu)
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

    def _on_clear_recent_files_from_menu(self) -> None:
        """Handle Clear Recent Files action from the recent files submenu.

        Clears all entries from the recent files list and updates the menu
        to show the empty state placeholder. No confirmation dialog.
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

    def _setup_dock_widgets(self) -> None:
        """Create and configure dockable panels.

        Creates three dock widgets with placeholder content:
        - Hierarchy panel (left): Design object tree navigation
        - Property panel (right): Object property inspector
        - Message panel (bottom): Search results and logs

        Each dock is configured with:
        - Object name: Required for QSettings state persistence
        - Allowed areas: Restricts docking to appropriate areas
        - Initial position: Default docking location
        - Minimum size: Prevents unusable panel sizes

        Dock Widget Architecture:
            QDockWidget (container providing dock behavior)
                └── QWidget (panel content - HierarchyPanel, etc.)

        The panel widgets are stored as separate instance attributes
        (hierarchy_panel, property_panel, message_panel) for direct access
        when implementing panel functionality in future epics.

        After creating dock widgets, a PanelStateManager is initialized to
        track panel state changes. The manager enables:
        - Reactive state tracking via Qt signals
        - Panel visibility control (show/hide/toggle)
        - State capture for persistence

        See Also:
            - E06-F02: View menu toggle actions for panels
            - E06-F05: saveState()/restoreState() for dock persistence
            - E06-F05-T01: PanelStateManager implementation
        """
        self._setup_hierarchy_dock()
        self._setup_property_dock()
        self._setup_message_dock()
        self._set_initial_dock_sizes()
        self._setup_panel_state_manager()

    def _setup_hierarchy_dock(self) -> None:
        """Create and configure the hierarchy dock widget (left area).

        The hierarchy dock contains a placeholder panel that will be replaced
        with a full QTreeView-based hierarchy browser in E04-F01.

        Configuration:
            - Position: Left dock area (default)
            - Allowed areas: Left and Right (vertical panels)
            - Object name: "HierarchyDock" (for state persistence)
        """
        # Create panel content - placeholder for now, full impl in E04-F01
        self.hierarchy_panel = HierarchyPanel(self)

        # Create dock widget container
        self.hierarchy_dock = QDockWidget("Hierarchy", self)

        # Set object name - required for saveState()/restoreState() to work
        # Qt uses object names to identify docks across sessions
        self.hierarchy_dock.setObjectName("HierarchyDock")

        # Set panel as dock content
        self.hierarchy_dock.setWidget(self.hierarchy_panel)

        # Restrict to left/right areas - vertical lists fit better on sides
        # Prevents awkward layouts like hierarchy on bottom
        self.hierarchy_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        # Add to left dock area by default
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.hierarchy_dock)

    def _setup_property_dock(self) -> None:
        """Create and configure the property dock widget (right area).

        The property dock contains a placeholder panel that will be replaced
        with a full property editor in E04-F04.

        Configuration:
            - Position: Right dock area (default)
            - Allowed areas: Left and Right (vertical panels)
            - Object name: "PropertyDock" (for state persistence)
        """
        # Create panel content - placeholder for now, full impl in E04-F04
        self.property_panel = PropertyPanel(self)

        # Create dock widget container
        self.property_dock = QDockWidget("Properties", self)

        # Set object name - required for saveState()/restoreState() to work
        self.property_dock.setObjectName("PropertyDock")

        # Set panel as dock content
        self.property_dock.setWidget(self.property_panel)

        # Restrict to left/right areas - property key-value pairs fit better on sides
        self.property_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        # Add to right dock area by default
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.property_dock)

    def _setup_message_dock(self) -> None:
        """Create and configure the message dock widget (bottom area).

        The message dock contains a placeholder panel that will be replaced
        with a full search/log panel in E04-F03.

        Configuration:
            - Position: Bottom dock area (default and only allowed)
            - Allowed areas: Bottom only (horizontal log view)
            - Object name: "MessageDock" (for state persistence)
        """
        # Create panel content - placeholder for now, full impl in E04-F03
        self.message_panel = MessagePanel(self)

        # Create dock widget container
        self.message_dock = QDockWidget("Messages", self)

        # Set object name - required for saveState()/restoreState() to work
        self.message_dock.setObjectName("MessageDock")

        # Set panel as dock content
        self.message_dock.setWidget(self.message_panel)

        # Restrict to bottom area only - horizontal log/search view fits bottom
        # Message on sides would waste vertical space
        self.message_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)

        # Add to bottom dock area
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.message_dock)

    def _set_initial_dock_sizes(self) -> None:
        """Set initial size hints for dock widgets.

        Uses minimum sizes to guide Qt's layout system toward desired
        proportions. Exact sizing is approximate due to Qt's complex
        dock layout algorithm.

        Target ratios (for 1600x900 window):
            - Hierarchy (left): ~15% width (240px)
            - Property (right): ~25% width (400px)
            - Message (bottom): ~20% height (180px)
            - Central canvas: Remaining space

        Design decision: Use minimum sizes rather than exact sizing
        because:
            1. Qt's dock layout algorithm is complex
            2. Users will resize to preference anyway
            3. E06-F05 will save/restore exact sizes with QSettings
            4. Minimum sizes prevent unusable panel sizes

        See Also:
            - E06-F05: Exact sizing via saveState()/restoreState()
        """
        # Hierarchy (left): minimum usable width for tree view
        # 150px allows ~20 chars of text plus expand/collapse icons
        self.hierarchy_dock.setMinimumWidth(150)
        self.hierarchy_panel.setMinimumSize(150, 200)

        # Property (right): wider for property names and values
        # 200px allows key-value pairs to be readable
        self.property_dock.setMinimumWidth(200)
        self.property_panel.setMinimumSize(200, 200)

        # Message (bottom): minimum height for log viewing
        # 100px allows ~4-5 lines of log messages
        self.message_dock.setMinimumHeight(100)
        self.message_panel.setMinimumSize(300, 100)

    def _setup_panel_state_manager(self) -> None:
        """Initialize PanelStateManager and register all dock panels.

        Creates a PanelStateManager to track dock widget state changes.
        The manager monitors visibility, floating, and location changes
        via Qt signals and maintains synchronized panel state.

        Panel Registration:
            - "Hierarchy": hierarchy_dock (left area)
            - "Properties": property_dock (right area)
            - "Messages": message_dock (bottom area)

        The manager enables:
            - Reactive state tracking via custom signals
            - Panel visibility control (show/hide/toggle)
            - State capture for persistence

        See Also:
            - E06-F05-T01: PanelStateManager specification
            - PanelStateManager for API documentation
        """
        # Create the panel state manager with reference to this window
        self.panel_state_manager = PanelStateManager(self)

        # Register all dock widgets for state tracking
        # Names match the dock widget titles for consistency
        self.panel_state_manager.register_panel("Hierarchy", self.hierarchy_dock)
        self.panel_state_manager.register_panel("Properties", self.property_dock)
        self.panel_state_manager.register_panel("Messages", self.message_dock)

    # =========================================================================
    # Status Bar Setup (E06-F04-T01)
    # =========================================================================
    # Status bar provides persistent display of contextual information:
    # - File name: Currently loaded netlist file
    # - Zoom level: Current zoom percentage
    # - Selection count: Number of selected objects
    # - Object counts: Visible cells and nets

    def _setup_status_bar(self) -> None:
        """Create and configure the status bar with persistent widgets.

        Sets up a QStatusBar with four permanent widgets for displaying:
        1. File name - current netlist file or "No file loaded"
        2. Zoom level - current zoom percentage (default 100%)
        3. Selection count - number of selected objects
        4. Object counts - visible cells and nets

        All widgets are added as permanent widgets so they remain visible
        even when temporary status messages are shown. Visual separators
        using the Unicode pipe character (│) provide clear section boundaries.

        Layout Structure:
            [File: design.ckt] │ [Zoom: 100%] │ [Selected: 3] │ [Cells: 45 / Nets: 67]

        Design Decisions:
            - Permanent widgets: Won't be displaced by temporary messages
            - Fixed minimum widths: Prevent layout jumping when content changes
            - Gray separators: Subtle visual division without distracting
            - Placeholder text: Meaningful initial state (no file, 100% zoom, etc.)

        See Also:
            - E06-F04-T02: Selection status display (updates selection_label)
            - E06-F04-T03: Zoom level display (updates zoom_label)
            - E06-F04-T04: File and object count display (updates file_label, object_count_label)
        """
        # Create status bar and attach to main window
        # QMainWindow.setStatusBar() replaces any existing status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # File name label (leftmost widget)
        # Displays current file name or "No file loaded" placeholder
        # 200px min width accommodates typical filenames like "circuit_design_v2.ckt"
        self.file_label = QLabel("No file loaded")
        self.file_label.setMinimumWidth(200)
        status_bar.addPermanentWidget(self.file_label)

        # Separator between file and zoom
        status_bar.addPermanentWidget(self._create_separator())

        # Zoom level label
        # Displays current zoom percentage from 10% to 1000%
        # 100px min width accommodates "Zoom: 1000%" (max zoom)
        self.zoom_label = QLabel("Zoom: 100%")
        self.zoom_label.setMinimumWidth(100)
        status_bar.addPermanentWidget(self.zoom_label)

        # Separator between zoom and selection
        status_bar.addPermanentWidget(self._create_separator())

        # Selection count label
        # Displays number of currently selected objects
        # 100px min width accommodates "Selected: 9999" (large selections)
        self.selection_label = QLabel("Selected: 0")
        self.selection_label.setMinimumWidth(100)
        status_bar.addPermanentWidget(self.selection_label)

        # Separator between selection and object count
        status_bar.addPermanentWidget(self._create_separator())

        # Object count label (rightmost widget)
        # Displays visible cell and net counts
        # 150px min width accommodates "Cells: 9999 / Nets: 9999"
        self.object_count_label = QLabel("Cells: 0 / Nets: 0")
        self.object_count_label.setMinimumWidth(150)
        status_bar.addPermanentWidget(self.object_count_label)

    def _create_separator(self) -> QLabel:
        """Create a visual separator for the status bar.

        Returns a QLabel configured as a vertical separator using the
        Unicode box-drawing character (│, U+2502). The separator is
        styled with gray color for subtle visual distinction.

        Returns:
            QLabel configured as a separator widget.

        Design Decisions:
            - Unicode pipe (│): Clean vertical line, cross-platform compatible
            - Gray color: Subtle appearance, doesn't compete with content
            - Spaces around pipe: Provide padding between sections
            - QLabel (not QFrame): Simpler, consistent rendering, lighter weight
        """
        separator = QLabel(" │ ")
        separator.setStyleSheet("color: gray;")
        return separator

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
                "Window layout has been reset.\n\nRestart the application to apply the new layout.",
            )

    def _on_clear_recent_files(self) -> None:
        """Handle Clear Recent Files action from Help > Settings menu.

        Clears the recent files list with confirmation dialog.
        """
        reply = QMessageBox.question(
            self,
            "Clear Recent Files",
            "Clear the list of recently opened files?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.app_settings.reset_recent_files()
            self._update_recent_files_menu()
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
            self._update_recent_files_menu()
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
        settings_path = self.app_settings.get_settings_file_path()

        QMessageBox.information(
            self,
            "Settings File Location",
            f"Settings are stored at:\n\n{settings_path}",
        )
