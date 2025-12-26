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
    - Three dock widgets for supporting panels (hierarchy, properties, messages)
    - Dock nesting enabled for complex layout configurations

See Also:
    - Spec E06-F01-T01 for window shell requirements
    - Spec E06-F01-T02 for central widget requirements
    - Spec E06-F01-T03 for dock widget requirements
    - Qt documentation on QMainWindow for extension points
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow

from ink.presentation.canvas import SchematicCanvas
from ink.presentation.panels import HierarchyPanel, MessagePanel, PropertyPanel


class InkMainWindow(QMainWindow):
    """Main application window shell for Ink schematic viewer.

    This window serves as the root container for the entire Ink application,
    providing the foundation for the presentation layer. It handles:
    - Window title and identification
    - Default and minimum window sizing
    - Standard window decorations (minimize, maximize, close)
    - Three dock widgets for supporting panels
    - Dock nesting for complex layout configurations

    The window is designed to work well on 1080p displays while remaining
    usable on smaller 768p screens.

    Dock Widgets:
        - hierarchy_dock: Left area - design object tree navigation
        - property_dock: Right area - object property inspector
        - message_dock: Bottom area - search results and logs

    Attributes:
        schematic_canvas: The central canvas widget for schematic visualization.
        hierarchy_panel: Placeholder for hierarchy tree (full impl: E04-F01).
        hierarchy_dock: Dock widget containing hierarchy_panel.
        property_panel: Placeholder for property inspector (full impl: E04-F04).
        property_dock: Dock widget containing property_panel.
        message_panel: Placeholder for search/log panel (full impl: E04-F03).
        message_dock: Dock widget containing message_panel.

    Example:
        >>> from ink.presentation.main_window import InkMainWindow
        >>> window = InkMainWindow()
        >>> window.show()

    See Also:
        - E06-F01-T03: Dock widget configuration
        - E06-F01-T04: Integrates window into main.py entry point
        - E06-F02: Menu system with View menu for panel toggling
        - E06-F05: Panel state persistence with QSettings
    """

    # Instance attribute type hints for IDE/type checker support
    schematic_canvas: SchematicCanvas
    hierarchy_panel: HierarchyPanel
    hierarchy_dock: QDockWidget
    property_panel: PropertyPanel
    property_dock: QDockWidget
    message_panel: MessagePanel
    message_dock: QDockWidget

    # Window configuration constants
    # These are class-level to make requirements explicit and testable
    _WINDOW_TITLE: str = "Ink - Incremental Schematic Viewer"
    _DEFAULT_WIDTH: int = 1600  # Optimal for 1080p (1920x1080) with taskbar
    _DEFAULT_HEIGHT: int = 900  # 16:9 aspect ratio, fits 1080p displays
    _MIN_WIDTH: int = 1024  # Common minimum for professional tools
    _MIN_HEIGHT: int = 768  # Supports 768p displays as minimum

    def __init__(self) -> None:
        """Initialize the main window with configured properties.

        Sets up window title, size constraints, decorations, central widget,
        and dock widgets. Does not show the window - caller must call show()
        explicitly.

        Initialization order:
            1. Window properties (title, size, flags)
            2. Central widget (schematic canvas)
            3. Dock widgets (hierarchy, properties, messages)

        This order ensures dock widgets can be positioned relative to the
        central widget and that window properties are set before adding docks.
        """
        super().__init__()
        self._setup_window()
        self._setup_central_widget()
        self._setup_dock_widgets()

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

        See Also:
            - E06-F02: View menu toggle actions for panels
            - E06-F05: saveState()/restoreState() for dock persistence
        """
        self._setup_hierarchy_dock()
        self._setup_property_dock()
        self._setup_message_dock()
        self._set_initial_dock_sizes()

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
