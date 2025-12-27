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

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QStatusBar,
    QToolBar,
)

from ink.infrastructure.persistence.panel_settings_store import PanelSettingsStore
from ink.presentation.canvas import SchematicCanvas
from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog
from ink.presentation.panels import HierarchyPanel, MessagePanel, PropertyPanel
from ink.presentation.state import PanelStateManager
from ink.presentation.utils.icon_provider import IconProvider

if TYPE_CHECKING:
    from collections.abc import Callable

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
    # Panels submenu and toggle actions (E06-F05-T03)
    panels_menu: QMenu
    hierarchy_toggle_action: QAction
    property_toggle_action: QAction
    message_toggle_action: QAction
    reset_panel_layout_action: QAction
    panel_state_manager: PanelStateManager
    panel_settings_store: PanelSettingsStore
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

    # Edit menu actions (E06-F02-T03)
    undo_action: QAction
    redo_action: QAction
    find_action: QAction

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

        # Create panel settings store for panel layout persistence (E06-F05-T02)
        # This must be created before dock widgets are set up, as it's used
        # during panel state restoration
        self.panel_settings_store = PanelSettingsStore()

        # Setup UI components BEFORE restoring geometry
        # restoreState() requires dock widgets to exist first
        self._setup_window()
        self._setup_central_widget()
        self._setup_dock_widgets()
        self._setup_status_bar()
        self._setup_menus()
        self._setup_toolbar()

        # Connect canvas signals to status bar updates (E06-F04-T03)
        # Must be called after both canvas and status bar are created
        self._connect_status_signals()

        # Restore geometry AFTER all widgets are created
        self._restore_geometry()

        # Restore panel layout from saved state (E06-F05-T02)
        # This is called after dock widgets are created and registered
        self._restore_panel_layout()

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

        # Add action groups with separators
        # Group 1: File operations (E06-F03-T03)
        self._add_file_actions(toolbar)
        toolbar.addSeparator()

        # Group 2: Edit operations - Undo/Redo (E06-F03-T03)
        self._add_edit_actions(toolbar)
        toolbar.addSeparator()

        # Group 3: Search operations (E06-F03-T03)
        self._add_search_actions(toolbar)
        toolbar.addSeparator()

        # Group 4: View operations - Zoom controls (E06-F03-T02)
        self._add_view_actions(toolbar)
        toolbar.addSeparator()

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
        # Create Open action with icon from IconProvider
        # IconProvider tries system theme first, falls back to bundled SVG
        self._open_action = QAction(
            IconProvider.get_icon("document-open"),
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
        # Create Undo action with icon from IconProvider
        self._undo_action = QAction(
            IconProvider.get_icon("edit-undo"),
            "Undo",
            self,
        )
        self._undo_action.setToolTip("Undo expansion/collapse (Ctrl+Z)")
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        # Initially disabled - no history at startup
        self._undo_action.setEnabled(False)
        self._undo_action.triggered.connect(self._on_undo)
        toolbar.addAction(self._undo_action)

        # Create Redo action with icon from IconProvider
        self._redo_action = QAction(
            IconProvider.get_icon("edit-redo"),
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
        # Create Search action with icon from IconProvider
        self._search_action = QAction(
            IconProvider.get_icon("edit-find"),
            "Search",
            self,
        )
        self._search_action.setToolTip("Search cells/nets/pins (Ctrl+F)")
        self._search_action.setShortcut(QKeySequence.StandardKey.Find)
        self._search_action.triggered.connect(self._on_find)
        toolbar.addAction(self._search_action)

    def _add_view_actions(self, toolbar: QToolBar) -> None:
        """Add view-related toolbar actions.

        Creates three view control buttons in conventional order:
        - Zoom Out: Decrease view scale (Ctrl+-)
        - Zoom In: Increase view scale (Ctrl+=)
        - Fit View: Fit all content in viewport (Ctrl+0)

        All actions are always enabled. Handlers gracefully handle missing canvas
        by checking for None/missing methods before calling canvas methods.

        Args:
            toolbar: QToolBar instance to add actions to.

        Design Decisions:
            - Button Order: Zoom Out → Zoom In → Fit View (industry convention)
            - Tooltips: Include action name + keyboard shortcut in parentheses
            - Shortcuts: Qt standard keys for zoom, custom Ctrl+0 for fit view
            - No State Management: Actions always enabled (unlike undo/redo)

        See Also:
            - Spec E06-F03-T02 for view control tools requirements
            - Pre-docs E06-F03-T02 for implementation details
        """
        # Zoom Out (decrease first, conventional order)
        # Uses Qt standard ZoomOut shortcut (Ctrl+-) for platform consistency
        zoom_out_action = QAction(
            IconProvider.get_icon("zoom-out"),
            "Zoom Out",
            self,
        )
        zoom_out_action.setToolTip("Zoom out (Ctrl+-)")
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._on_zoom_out)
        toolbar.addAction(zoom_out_action)

        # Zoom In (increase second)
        # Uses Qt standard ZoomIn shortcut (Ctrl+=) for platform consistency
        zoom_in_action = QAction(
            IconProvider.get_icon("zoom-in"),
            "Zoom In",
            self,
        )
        zoom_in_action.setToolTip("Zoom in (Ctrl+=)")
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._on_zoom_in)
        toolbar.addAction(zoom_in_action)

        # Fit View (special operation last)
        # Uses custom Ctrl+0 shortcut (industry convention: Figma, CAD tools)
        fit_view_action = QAction(
            IconProvider.get_icon("zoom-fit-best"),
            "Fit View",
            self,
        )
        fit_view_action.setToolTip("Fit view to content (Ctrl+0)")
        fit_view_action.setShortcut(QKeySequence("Ctrl+0"))
        fit_view_action.triggered.connect(self._on_fit_view)
        toolbar.addAction(fit_view_action)

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
        the panel is already visible. Falls back to showing message_dock
        as a placeholder when the full search panel is not yet implemented.

        Behavior:
            - Search panel available: Show/focus the search panel
            - Search panel not available: Fall back to message_dock
            - Neither available: Show status bar message

        This design ensures users can quickly start searching without
        having to manually navigate to the search panel.

        See Also:
            - Spec E06-F03-T03 for search panel requirements
            - E06-F02-T03 for Edit menu Find action
        """
        # Check for dedicated search panel existence (E05 implementation)
        if hasattr(self, "_search_panel") and self._search_panel is not None:
            if self._search_panel.isVisible():
                # Panel already visible - just focus the input
                self._search_panel.focus_search_input()
            else:
                # Panel hidden - show it and focus input
                self._search_panel.show()
                self._search_panel.focus_search_input()
        elif hasattr(self, "message_dock") and self.message_dock is not None:
            # Fall back to message_dock as search panel placeholder (E06-F02-T03)
            if not self.message_dock.isVisible():
                self.message_dock.setVisible(True)
            # Focus on search input field for immediate typing
            if hasattr(self, "message_panel") and self.message_panel is not None:
                self.message_panel.focus_search_input()
        else:
            # Neither search panel nor message dock available
            self.statusBar().showMessage("Search panel not yet available", 3000)

    def _update_undo_redo_state(self) -> None:
        """Update Undo/Redo button enabled state based on expansion history.

        Queries the expansion service for undo/redo availability and updates
        both toolbar and menu action states accordingly. Uses defensive
        programming to handle the case where the expansion service is not
        initialized.

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

            # Update toolbar button states based on service response
            self._undo_action.setEnabled(can_undo)
            self._redo_action.setEnabled(can_redo)

            # Update menu action states as well (E06-F02-T03)
            if hasattr(self, "undo_action"):
                self.undo_action.setEnabled(can_undo)
            if hasattr(self, "redo_action"):
                self.redo_action.setEnabled(can_redo)
        # If no service, buttons remain in their current state (disabled by default)

    def _on_zoom_in(self) -> None:
        """Handle zoom in action.

        Calls canvas.zoom_in() if canvas exists and has the method.
        Gracefully handles missing canvas (no-op with no error).

        Design Decision:
            Uses hasattr() check first in case schematic_canvas was never set,
            then checks canvas truthiness in case it was set to None.
            Finally checks for method existence to support different canvas types.
        """
        if (
            hasattr(self, "schematic_canvas")
            and self.schematic_canvas
            and hasattr(self.schematic_canvas, "zoom_in")
        ):
            self.schematic_canvas.zoom_in()

    def _on_zoom_out(self) -> None:
        """Handle zoom out action.

        Calls canvas.zoom_out() if canvas exists and has the method.
        Gracefully handles missing canvas (no-op with no error).
        """
        if (
            hasattr(self, "schematic_canvas")
            and self.schematic_canvas
            and hasattr(self.schematic_canvas, "zoom_out")
        ):
            self.schematic_canvas.zoom_out()

    def _on_fit_view(self) -> None:
        """Handle fit view action.

        Calls canvas.fit_view() if canvas exists and has the method.
        Gracefully handles missing canvas (no-op with no error).
        """
        if (
            hasattr(self, "schematic_canvas")
            and self.schematic_canvas
            and hasattr(self.schematic_canvas, "fit_view")
        ):
            self.schematic_canvas.fit_view()

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

        Populates the Edit menu with:
        - Undo (Ctrl+Z): Undo last expansion/collapse operation
        - Redo (Ctrl+Shift+Z): Redo last undone operation
        - Find... (Ctrl+F): Open search panel and focus input

        Undo/Redo actions are initially disabled and will be enabled when
        expansion/collapse operations create history. The action text updates
        dynamically to show what will be undone/redone.

        Design Decisions:
            - Uses Qt StandardKey shortcuts for cross-platform compatibility
            - Undo/Redo initially disabled to indicate no history available
            - Find always enabled as search is always available
            - Status tips provide context for status bar display

        See Also:
            - E06-F02-T03: Edit menu actions implementation
            - E04-F03: Undo/Redo integration with ExpansionService
            - E05-F01: Search panel focus method
        """
        # =====================================================================
        # Undo Action (Ctrl+Z)
        # Undoes the last expansion or collapse operation. Initially disabled
        # until the user performs an operation that can be undone.
        # =====================================================================
        self.undo_action = QAction("&Undo", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.setStatusTip("Undo last expansion/collapse operation")
        self.undo_action.setEnabled(False)  # Initially disabled - no history
        self.undo_action.triggered.connect(self._on_undo)
        self.edit_menu.addAction(self.undo_action)

        # =====================================================================
        # Redo Action (Ctrl+Shift+Z)
        # Redoes the last undone operation. Initially disabled until the user
        # performs an undo operation.
        # =====================================================================
        self.redo_action = QAction("&Redo", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.setStatusTip("Redo last undone operation")
        self.redo_action.setEnabled(False)  # Initially disabled - no history
        self.redo_action.triggered.connect(self._on_redo)
        self.edit_menu.addAction(self.redo_action)

        # Separator between Undo/Redo and Find
        self.edit_menu.addSeparator()

        # =====================================================================
        # Find Action (Ctrl+F)
        # Opens the search panel (message dock) and focuses the search input.
        # Always enabled as search functionality is always available.
        # =====================================================================
        self.find_action = QAction("&Find...", self)
        self.find_action.setShortcut(QKeySequence.StandardKey.Find)
        self.find_action.setStatusTip("Search for cells, nets, or ports")
        self.find_action.triggered.connect(self._on_find)
        self.edit_menu.addAction(self.find_action)

    def _create_view_menu(self) -> None:
        """Create View menu items with zoom controls and panel toggle actions.

        Populates the View menu with:
        - Zoom In, Zoom Out, Fit View actions (E06-F02-T04)
        - Separator between zoom and panels
        - Panels submenu for panel visibility toggles
        - Panel toggle actions using Qt's toggleViewAction()
        - Reset Panel Layout action

        Zoom Actions (E06-F02-T04):
            - Zoom In (Ctrl+=): Increase view scale
            - Zoom Out (Ctrl+-): Decrease view scale
            - Fit View (Ctrl+0): Fit all content in viewport

        Panel Toggle Actions:
            Uses Qt's built-in toggleViewAction() from QDockWidget which provides:
            - Automatic checkable state (shows checkmark when visible)
            - Bidirectional sync (menu ↔ panel visibility)
            - Action text matches dock widget window title
            - No manual signal handling needed

        Keyboard Shortcuts:
            - Ctrl+=: Zoom in
            - Ctrl+-: Zoom out
            - Ctrl+0: Fit view
            - Ctrl+Shift+H: Toggle Hierarchy panel
            - Ctrl+Shift+P: Toggle Properties panel
            - Ctrl+Shift+M: Toggle Messages panel
            - Ctrl+Shift+R: Reset panel layout

        Design Decisions:
            - Zoom actions at top of menu (most frequently used)
            - Separator between zoom and panel controls
            - Use Ctrl+Shift for panel toggles to avoid conflicts with zoom shortcuts
            - First letter of panel name for easy memorization
            - Reset Layout at bottom with separator for visual grouping

        See Also:
            - Spec E06-F02-T04 for View menu zoom actions
            - Spec E06-F05-T03 for panel toggle actions requirements
            - E06-F05-T01: PanelStateManager integration
        """
        # =====================================================================
        # Zoom Actions (E06-F02-T04)
        # =====================================================================

        # Zoom In action (Ctrl+=)
        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.setStatusTip("Zoom in on schematic")
        zoom_in_action.triggered.connect(self._on_zoom_in)
        self.view_menu.addAction(zoom_in_action)

        # Zoom Out action (Ctrl+-)
        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.setStatusTip("Zoom out on schematic")
        zoom_out_action.triggered.connect(self._on_zoom_out)
        self.view_menu.addAction(zoom_out_action)

        # Fit View action (Ctrl+0)
        fit_view_action = QAction("&Fit View", self)
        fit_view_action.setShortcut(QKeySequence("Ctrl+0"))
        fit_view_action.setStatusTip("Fit schematic to view")
        fit_view_action.triggered.connect(self._on_fit_view)
        self.view_menu.addAction(fit_view_action)

        # Separator between zoom controls and panel toggles
        self.view_menu.addSeparator()

        # =====================================================================
        # Panels Submenu (E06-F05-T03)
        # =====================================================================

        # Create Panels submenu for panel visibility toggles
        # Using mnemonic &Panels for Alt+P keyboard access
        self.panels_menu = self.view_menu.addMenu("&Panels")

        # Get toggle actions from dock widgets
        # Qt's toggleViewAction() provides automatic state synchronization:
        # - Checkmark appears when panel is visible
        # - Clicking toggles panel visibility
        # - State syncs when panel is closed via X button
        self._setup_panel_toggle_actions()

        # Add separator before Reset Layout for visual grouping
        self.panels_menu.addSeparator()

        # Add Reset Panel Layout action
        self._setup_reset_panel_layout_action()

    def _setup_panel_toggle_actions(self) -> None:
        """Set up toggle actions for each panel dock widget.

        Creates checkable toggle actions using Qt's toggleViewAction() API.
        Each action is configured with:
        - Keyboard shortcut (Ctrl+Shift+<key>)
        - Tooltip describing the action
        - Status tip with shortcut hint for status bar display

        The actions are added to the Panels submenu and stored as instance
        attributes for programmatic access.

        Note:
            toggleViewAction() must be called after dock widgets are created.
            The action text is automatically set to the dock widget's windowTitle.
        """
        # Hierarchy panel toggle action
        # Uses dock widget's toggleViewAction() for automatic state sync
        self.hierarchy_toggle_action = self.hierarchy_dock.toggleViewAction()
        self.hierarchy_toggle_action.setShortcut("Ctrl+Shift+H")
        self.hierarchy_toggle_action.setToolTip(
            "Show or hide the hierarchy navigation panel"
        )
        self.hierarchy_toggle_action.setStatusTip(
            "Toggle hierarchy panel visibility (Ctrl+Shift+H)"
        )
        self.panels_menu.addAction(self.hierarchy_toggle_action)

        # Properties panel toggle action
        self.property_toggle_action = self.property_dock.toggleViewAction()
        self.property_toggle_action.setShortcut("Ctrl+Shift+P")
        self.property_toggle_action.setToolTip(
            "Show or hide the property inspector panel"
        )
        self.property_toggle_action.setStatusTip(
            "Toggle property panel visibility (Ctrl+Shift+P)"
        )
        self.panels_menu.addAction(self.property_toggle_action)

        # Messages panel toggle action
        self.message_toggle_action = self.message_dock.toggleViewAction()
        self.message_toggle_action.setShortcut("Ctrl+Shift+M")
        self.message_toggle_action.setToolTip(
            "Show or hide the message log panel"
        )
        self.message_toggle_action.setStatusTip(
            "Toggle message panel visibility (Ctrl+Shift+M)"
        )
        self.panels_menu.addAction(self.message_toggle_action)

        # Connect additional behavior for raising panels when shown
        self._connect_panel_raise_behavior()

    def _connect_panel_raise_behavior(self) -> None:
        """Connect signals to raise panels when toggled to visible.

        When a panel is toggled on via the menu action, it should be raised
        (brought to front) to ensure the user sees the result of their action.
        This is especially important when panels are tabbed together.

        Note:
            The triggered signal is emitted when the action is activated.
            We check if the panel is now visible and raise it if so.
        """
        # Helper function to raise panel when toggled on
        def make_raise_handler(dock_widget: QDockWidget) -> Callable[[bool], None]:
            """Create a handler that raises the dock widget if visible.

            Args:
                dock_widget: The dock widget to potentially raise.

            Returns:
                Handler function for the triggered signal.
            """
            def handler(checked: bool) -> None:
                # If action was checked (panel shown), raise to front
                if checked:
                    dock_widget.raise_()
            return handler

        # Connect raise handlers to toggle actions
        self.hierarchy_toggle_action.triggered.connect(
            make_raise_handler(self.hierarchy_dock)
        )
        self.property_toggle_action.triggered.connect(
            make_raise_handler(self.property_dock)
        )
        self.message_toggle_action.triggered.connect(
            make_raise_handler(self.message_dock)
        )

    def _setup_reset_panel_layout_action(self) -> None:
        """Create and configure Reset Panel Layout action.

        This action restores panels to their default layout:
        - Hierarchy on left
        - Properties on right
        - Messages on bottom
        - All panels visible

        The action is added to the Panels submenu with a keyboard shortcut.

        See Also:
            - Spec E06-F05-T04 for default layout reset requirements
            - reset_panel_layout() for the implementation
        """
        self.reset_panel_layout_action = QAction("&Reset Panel Layout", self)
        self.reset_panel_layout_action.setShortcut("Ctrl+Shift+R")
        self.reset_panel_layout_action.setToolTip(
            "Reset panels to default layout"
        )
        self.reset_panel_layout_action.setStatusTip(
            "Reset panel layout to defaults (Ctrl+Shift+R)"
        )
        # Connect to public method that includes confirmation dialog
        self.reset_panel_layout_action.triggered.connect(self.reset_panel_layout)
        self.panels_menu.addAction(self.reset_panel_layout_action)

    def _create_help_menu(self) -> None:
        """Create Help menu items.

        Populates the Help menu with:
        - Keyboard Shortcuts (F1): Opens keyboard shortcuts dialog
        - About Ink: Shows application information dialog
        - Separator
        - Settings submenu for application settings management

        Dialog Actions (E06-F02-T04):
            - Keyboard Shortcuts: Opens KeyboardShortcutsDialog with F1 shortcut
            - About Ink: Shows QMessageBox.about() with app info

        See Also:
            - E06-F02-T04: Keyboard Shortcuts and About dialogs
            - E06-F06-T04: Settings management functionality
        """
        # =====================================================================
        # Keyboard Shortcuts Action (F1) - E06-F02-T04
        # =====================================================================
        shortcuts_action = QAction("&Keyboard Shortcuts", self)
        shortcuts_action.setShortcut(QKeySequence("F1"))
        shortcuts_action.setStatusTip("Show keyboard shortcuts")
        shortcuts_action.triggered.connect(self._on_show_shortcuts)
        self.help_menu.addAction(shortcuts_action)

        # =====================================================================
        # About Ink Action - E06-F02-T04
        # =====================================================================
        about_action = QAction("&About Ink", self)
        about_action.setStatusTip("About this application")
        about_action.triggered.connect(self._on_about)
        self.help_menu.addAction(about_action)

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
    # Status Bar Update Methods (E06-F04-T02, E06-F04-T03)
    # =========================================================================
    # These methods update status bar widgets when canvas/selection state changes.
    # They are connected to canvas/service signals for real-time updates.

    def update_zoom_status(self, zoom_percent: float) -> None:
        """Update zoom level in status bar.

        Updates the zoom_label text to show the current zoom level as a
        percentage. The value is rounded to the nearest integer for display
        (no decimal places).

        This method is connected to SchematicCanvas.zoom_changed signal
        for automatic updates when the user zooms in/out.

        Args:
            zoom_percent: Current zoom level as percentage (e.g., 150.0 for 150%).
                Expected range is 10.0 to 1000.0 (10% to 1000%).

        Example:
            >>> window.update_zoom_status(150.0)  # Shows "Zoom: 150%"
            >>> window.update_zoom_status(75.5)   # Shows "Zoom: 76%" (rounded)

        See Also:
            - Spec E06-F04-T03 for zoom level display requirements
            - SchematicCanvas.zoom_changed for the signal that triggers updates
        """
        # Format zoom percentage as integer (no decimal places)
        # Using :.0f rounds to nearest integer
        self.zoom_label.setText(f"Zoom: {zoom_percent:.0f}%")

    def update_selection_status(self, count: int) -> None:
        """Update selection count in status bar.

        Updates the selection_label widget to display the current number
        of selected objects in the format "Selected: N".

        This method is called:
            - When selection changes via user interaction
            - When selection service emits selection_changed signal
            - When selection is cleared (count=0)

        Args:
            count: Number of currently selected objects. Should be non-negative.

        Example:
            >>> window.update_selection_status(0)    # "Selected: 0"
            >>> window.update_selection_status(1)    # "Selected: 1"
            >>> window.update_selection_status(42)   # "Selected: 42"

        Note:
            For performance, this method directly updates the label text
            without additional validation. The count is trusted to come
            from the selection service which manages the selection state.

        See Also:
            - E06-F04-T02: Selection status display specification
            - E04-F01: Selection service (emits selection_changed signal)
        """
        self.selection_label.setText(f"Selected: {count}")

    def update_file_status(self, file_path: str | None) -> None:
        """Update file name in status bar.

        Updates the file_label text to show the current file's base name.
        The full path is stored in the tooltip for user reference on hover.
        When no file is loaded (file_path is None), shows placeholder text.

        This method is called:
            - When a file is loaded via File > Open or recent files
            - When the file is closed (with None)
            - At application startup (initial state shows placeholder)

        Args:
            file_path: Absolute path to loaded file, or None if no file loaded.

        Example:
            >>> window.update_file_status("/home/user/project/design.ckt")
            # Shows "File: design.ckt" with full path in tooltip
            >>> window.update_file_status(None)
            # Shows "No file loaded" with empty tooltip

        See Also:
            - Spec E06-F04-T04 for file status display requirements
            - E01-F02: File service (emits file_loaded/file_closed signals)
        """
        if file_path:
            # Extract base name using pathlib for cross-platform compatibility
            # Path handles unicode filenames correctly
            file_name = Path(file_path).name
            self.file_label.setText(f"File: {file_name}")
            # Store full path in tooltip for reference on hover
            self.file_label.setToolTip(file_path)
        else:
            # No file loaded - show placeholder text
            self.file_label.setText("No file loaded")
            # Clear tooltip when no file
            self.file_label.setToolTip("")

    def update_object_count_status(self, cell_count: int, net_count: int) -> None:
        """Update visible object counts in status bar.

        Updates the object_count_label text to show the current number of
        visible cells and nets in the format "Cells: N / Nets: M".

        This method is called:
            - After initial file load and expansion
            - When cells are expanded (counts increase)
            - When cells are collapsed (counts decrease)
            - When file is closed (counts reset to 0)

        Args:
            cell_count: Number of currently visible/rendered cells.
            net_count: Number of currently visible/rendered nets.

        Example:
            >>> window.update_object_count_status(45, 67)
            # Shows "Cells: 45 / Nets: 67"
            >>> window.update_object_count_status(0, 0)
            # Shows "Cells: 0 / Nets: 0"

        Note:
            For performance, this method directly updates the label text
            without validation. The counts are trusted to come from the
            expansion state which manages visible objects.

        See Also:
            - Spec E06-F04-T04 for object count display requirements
            - E03-F01: Expansion service (emits view_changed signal)
        """
        self.object_count_label.setText(f"Cells: {cell_count} / Nets: {net_count}")

    def _update_view_counts(self) -> None:
        """Query and update visible object counts from expansion state.

        This helper method retrieves the current visible cell and net counts
        from the expansion_state and calls update_object_count_status() to
        update the display. If expansion_state is not available, resets
        counts to zero.

        This method is typically connected to the expansion service's
        view_changed signal for automatic updates when the user expands
        or collapses cells.

        Defensive handling:
            - If expansion_state attribute doesn't exist: Shows 0 counts
            - If expansion_state is None: Shows 0 counts
            - If visible_cells/visible_nets are empty sets: Shows 0 counts

        See Also:
            - Spec E06-F04-T04 for object count display requirements
            - E03-F01: Expansion service (provides expansion_state)
        """
        # Check if expansion_state exists and is not None
        if hasattr(self, "expansion_state") and self.expansion_state:
            # Query visible object counts from expansion state
            cell_count = len(self.expansion_state.visible_cells)
            net_count = len(self.expansion_state.visible_nets)
            self.update_object_count_status(cell_count, net_count)
        else:
            # No expansion state available - show zeros
            self.update_object_count_status(0, 0)

    def _connect_status_signals(self) -> None:
        """Connect signals to status bar update methods.

        Establishes signal-slot connections between the schematic canvas,
        application services, and status bar update methods. This enables
        real-time status bar updates when state changes.

        Signal Connections:
            - schematic_canvas.zoom_changed → update_zoom_status (E06-F04-T03)
            - selection_service.selection_changed → update_selection_status (E06-F04-T02)
            - file_service.file_loaded → update_file_status (E06-F04-T04)
            - file_service.file_closed → update_file_status(None) (E06-F04-T04)
            - expansion_service.view_changed → _update_view_counts (E06-F04-T04)

        This method handles the case where the canvas or services may not yet
        be initialized by checking for attribute existence before attempting
        connection. This defensive approach allows the UI to be functional
        even before all services are integrated (graceful degradation).

        Called during window initialization after both the canvas and
        status bar have been created.

        See Also:
            - Spec E06-F04-T03 for zoom level display requirements
            - Spec E06-F04-T04 for file and object count display requirements
            - E06-F04-T02: Selection status display specification
            - E04-F01: Selection service (provides selection_changed signal)
            - E01-F02: File service (provides file_loaded/file_closed signals)
            - E03-F01: Expansion service (provides view_changed signal)
        """
        # Connect zoom changes from canvas to status update (E06-F04-T03)
        # Check for signal existence to handle placeholder canvas gracefully
        if hasattr(self, "schematic_canvas") and hasattr(self.schematic_canvas, "zoom_changed"):
            self.schematic_canvas.zoom_changed.connect(self.update_zoom_status)

        # Connect selection service signal if service is available (E06-F04-T02)
        # The selection service emits selection_changed with a list of selected items
        if hasattr(self, "selection_service"):
            service = self.selection_service
            # Verify the service has the expected signal before connecting
            if hasattr(service, "selection_changed"):
                service.selection_changed.connect(
                    lambda items: self.update_selection_status(len(items))
                )

        # Connect file service signals for file status updates (E06-F04-T04)
        # file_loaded emits the absolute file path when a file is opened
        # file_closed emits when the file is closed (clears status)
        if hasattr(self, "file_service"):
            service = self.file_service
            # Connect file_loaded signal to update file status display
            if hasattr(service, "file_loaded"):
                service.file_loaded.connect(self.update_file_status)
            # Connect file_closed signal to clear file status display
            if hasattr(service, "file_closed"):
                service.file_closed.connect(lambda: self.update_file_status(None))

        # Connect expansion service signal for object count updates (E06-F04-T04)
        # view_changed emits when visible cells/nets change (expand/collapse)
        if hasattr(self, "expansion_service"):
            service = self.expansion_service
            if hasattr(service, "view_changed"):
                service.view_changed.connect(self._update_view_counts)

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
        """Handle window close event - save geometry, state, and panel layout.

        This method is called by Qt when the user closes the window.
        It saves the current window layout before allowing the close.

        Args:
            event: The close event from Qt. Call accept() to close,
                   ignore() to prevent closing.

        Persistence order:
            1. Save window geometry (size, position)
            2. Save panel layout (dock visibility, areas, Qt state)
        """
        # Save geometry before closing
        self._save_geometry()

        # Save panel layout (E06-F05-T02)
        self._save_panel_layout()

        # Accept the close event - window will close
        event.accept()

    # =========================================================================
    # Panel Layout Persistence (E06-F05-T02)
    # =========================================================================
    # These methods handle saving and restoring panel layout state.
    # They integrate with PanelSettingsStore for complete dock widget persistence.

    def _restore_panel_layout(self) -> None:
        """Restore panel layout from saved settings.

        This method is called during initialization (after dock widgets are
        created and registered with PanelStateManager) to restore the panel
        layout from the previous session.

        Restoration includes:
        - Qt state blobs (dock positions, sizes, tabbing)
        - Individual panel visibility
        - Floating panel positions

        If no saved state exists (first run), panels remain in their default
        positions as set during dock widget creation.

        See Also:
            - _save_panel_layout: Saves state on window close
            - reset_panel_layout: Clears saved state for defaults
        """
        # Load saved panel state
        saved_state = self.panel_settings_store.load_panel_state()

        if saved_state is not None:
            # Use PanelStateManager to restore the state
            # This handles Qt blob restoration and individual visibility
            self.panel_state_manager.restore_state(saved_state)

    def _save_panel_layout(self) -> None:
        """Save current panel layout to settings.

        This method is called from closeEvent() to persist the panel
        layout before the application exits.

        Saves:
        - Qt state blobs (complete dock layout from saveState())
        - Individual panel metadata (visibility, area, geometry)

        The PanelStateManager.capture_state() method is used to collect
        all panel state including Qt's native state blobs.

        See Also:
            - _restore_panel_layout: Restores state on startup
            - PanelStateManager.capture_state: Collects panel state
        """
        # Capture current panel state via PanelStateManager
        current_state = self.panel_state_manager.capture_state()

        # Save to persistent storage
        self.panel_settings_store.save_panel_state(current_state)

    def reset_panel_layout(self) -> None:
        """Reset panel layout to default configuration with confirmation.

        Shows a confirmation dialog before resetting. If confirmed:
        1. Clears all saved panel state from QSettings
        2. Removes and re-adds dock widgets in default positions
        3. Sets all panels visible and docked (not floating)
        4. Applies default sizes (15%, 25%, 20%)
        5. Updates panel state manager with new state
        6. Shows success message in status bar

        The confirmation dialog prevents accidental resets and clearly
        explains the consequences of the action.

        This method is connected to:
        - View > Panels > Reset Panel Layout menu action
        - Keyboard shortcut Ctrl+Shift+R

        Design Decisions:
            - Requires confirmation (destructive action, no undo in MVP)
            - Default button is "No" (safe default, user must click Yes)
            - Remove/re-add approach clears all Qt internal state
            - Status bar message provides non-intrusive success feedback
            - Error handling prevents crashes and logs issues

        See Also:
            - Spec E06-F05-T04 for default layout reset requirements
            - Pre-docs E06-F05-T04.pre-docs.md for implementation details
            - _apply_default_panel_layout() for the actual layout reset
        """
        # Step 1: Show confirmation dialog
        # Destructive action requires explicit user consent
        result = QMessageBox.question(
            self,
            "Reset Panel Layout",
            "This will reset all panels to their default positions and sizes.\n"
            "Any custom layout will be lost.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,  # Default to No for safety
        )

        # User cancelled the reset
        if result != QMessageBox.StandardButton.Yes:
            return

        # Step 2: Perform reset with error handling
        try:
            # Clear saved panel settings from QSettings
            # This ensures the reset persists across restarts
            self.panel_settings_store.clear_panel_state()

            # Apply the default panel layout
            self._apply_default_panel_layout()

            # Show success feedback in status bar (3 second timeout)
            self.statusBar().showMessage("Panel layout reset to default", 3000)

        except Exception as e:
            # Log the error for debugging
            logging.exception("Failed to reset panel layout")

            # Show user-friendly error message
            QMessageBox.warning(
                self,
                "Reset Failed",
                f"Failed to reset panel layout: {e!s}\n\n"
                "Please restart the application.",
                QMessageBox.StandardButton.Ok,
            )

    def _apply_default_panel_layout(self) -> None:
        """Apply the default panel layout configuration.

        Removes all dock widgets and re-adds them in default positions.
        This approach ensures a clean slate by clearing Qt's internal
        dock layout state (splitters, tabs, z-order).

        Default Layout:
            - Hierarchy: Left dock area, 15% width
            - Properties: Right dock area, 25% width
            - Messages: Bottom dock area, 20% height
            - All panels visible and docked (not floating)

        This method is called by reset_panel_layout() after confirmation.
        It should not be called directly as it doesn't handle persistence.

        Design Decisions:
            - Remove/re-add clears all Qt internal dock state
            - setFloating(False) before addDockWidget ensures docked state
            - show() after addDockWidget ensures visibility
            - processEvents() before resize ensures accurate geometry
            - capture_state() updates PanelStateManager with new state

        See Also:
            - Spec E06-F05-T04 for default layout requirements
            - _set_default_dock_sizes() for size application
        """
        # Step 1: Remove all dock widgets to clear Qt's internal state
        # This clears tabs, splitters, and nested dock arrangements
        self.removeDockWidget(self.hierarchy_dock)
        self.removeDockWidget(self.property_dock)
        self.removeDockWidget(self.message_dock)

        # Step 2: Re-add dock widgets in default positions
        self.addDockWidget(
            Qt.DockWidgetArea.LeftDockWidgetArea,
            self.hierarchy_dock,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.RightDockWidgetArea,
            self.property_dock,
        )
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea,
            self.message_dock,
        )

        # Step 3: Ensure all panels are visible and docked (not floating)
        for dock in [self.hierarchy_dock, self.property_dock, self.message_dock]:
            dock.setFloating(False)
            dock.show()

        # Step 4: Apply default sizes
        self._set_default_dock_sizes()

        # Step 5: Update panel state manager with new state
        # This ensures state tracking is synchronized with the UI
        self.panel_state_manager.capture_state()

    def _set_default_dock_sizes(self) -> None:
        """Set default panel sizes as percentages of window dimensions.

        Applies proportional sizing to dock widgets:
            - Hierarchy: 15% of window width
            - Properties: 25% of window width
            - Messages: 20% of window height

        Uses processEvents() before resizing to ensure Qt's layout
        system has processed the dock widget additions and geometry
        calculations are accurate.

        This method is called by _apply_default_panel_layout() after
        dock widgets have been positioned.

        Design Decisions:
            - Proportional sizing adapts to different window sizes
            - processEvents() ensures accurate geometry calculations
            - resizeDocks() is the Qt-recommended way to set dock sizes

        See Also:
            - Spec E06-F05-T04 for default size specifications
        """
        # Wait for layout to settle (Qt layout is asynchronous)
        # This ensures width() and height() return accurate values
        QApplication.processEvents()

        width = self.width()
        height = self.height()

        # Hierarchy panel: 15% of window width (narrow tree view)
        self.resizeDocks(
            [self.hierarchy_dock],
            [int(width * 0.15)],
            Qt.Orientation.Horizontal,
        )

        # Property panel: 25% of window width (wider for property details)
        self.resizeDocks(
            [self.property_dock],
            [int(width * 0.25)],
            Qt.Orientation.Horizontal,
        )

        # Message panel: 20% of window height (bottom strip for logs)
        self.resizeDocks(
            [self.message_dock],
            [int(height * 0.20)],
            Qt.Orientation.Vertical,
        )

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

    # =========================================================================
    # Help Menu Action Handlers (E06-F02-T04)
    # =========================================================================

    def _on_show_shortcuts(self) -> None:
        """Handle Help > Keyboard Shortcuts action.

        Opens the KeyboardShortcutsDialog which displays all available
        keyboard shortcuts organized by category (File, Edit, View, etc.).

        The dialog is modal and blocks until the user closes it.

        See Also:
            - E06-F02-T04: Keyboard Shortcuts dialog requirements
            - KeyboardShortcutsDialog: The dialog class
        """
        dialog = KeyboardShortcutsDialog(self)
        dialog.exec()

    def _on_about(self) -> None:
        """Handle Help > About Ink action.

        Displays an About dialog using QMessageBox.about() with:
        - Application name and version
        - Brief description of the application
        - Key features list
        - Technology stack (PySide6, Python)
        - Copyright information

        The dialog uses platform-native styling via QMessageBox.about().

        See Also:
            - E06-F02-T04: About dialog requirements
        """
        QMessageBox.about(
            self,
            "About Ink",
            "<h2>Ink - Incremental Schematic Viewer</h2>"
            "<p>Version 0.1.0 (MVP)</p>"
            "<p>A GUI tool for schematic exploration targeting gate-level netlists.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Incremental exploration from user-selected points</li>"
            "<li>Hop-based fanin/fanout expansion</li>"
            "<li>Orthogonal net routing with Sugiyama layout</li>"
            "<li>Search and navigation</li>"
            "</ul>"
            "<p>Built with PySide6 and Python</p>"
            "<p>&copy; 2025 Ink Project</p>",
        )
