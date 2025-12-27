"""Panel state data structures for tracking dock widget configuration.

This module provides immutable data structures for representing the state of
dock widgets (panels) in the Ink main window. The state includes visibility,
dock area, floating status, geometry, and tab group information.

Design Decisions:
    - DockArea enum provides type-safe area representation with a custom
      FLOATING value (-1) for undocked panels, avoiding magic numbers.
    - PanelGeometry is a simple dataclass with defaults, enabling creation
      with partial data (just size or just position as needed).
    - PanelInfo uses dataclass with field() for mutable default (geometry)
      to avoid the classic mutable default argument pitfall.
    - PanelState stores both structured data (panels dict) and Qt's opaque
      state blobs for maximum flexibility and accurate restoration.

Why Two-Tier State Storage?
    Qt's saveState() produces a binary blob that perfectly preserves complex
    dock layouts but is opaque and cannot be queried. The structured PanelState
    provides queryable runtime state while Qt blobs ensure accurate restoration.

See Also:
    - Spec E06-F05-T01 for panel state management requirements
    - Pre-docs E06-F05-T01.pre-docs.md for architecture decisions
    - Qt QMainWindow.saveState() for the Qt state blob format
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

if TYPE_CHECKING:
    from PySide6.QtCore import QByteArray


class DockArea(Enum):
    """Enumeration of dock widget areas with Qt mappings.

    This enum provides a simplified, type-safe representation of Qt's
    DockWidgetArea values. It includes a custom FLOATING value (-1) for
    panels that are undocked and displayed as separate floating windows.

    The enum values map directly to Qt constants for LEFT, RIGHT, and BOTTOM,
    enabling easy conversion between DockArea and Qt.DockWidgetArea.

    Attributes:
        LEFT: Maps to Qt.DockWidgetArea.LeftDockWidgetArea for left-side panels.
        RIGHT: Maps to Qt.DockWidgetArea.RightDockWidgetArea for right-side panels.
        BOTTOM: Maps to Qt.DockWidgetArea.BottomDockWidgetArea for bottom panels.
        FLOATING: Custom value (-1) for undocked floating windows.

    Example:
        >>> area = DockArea.LEFT
        >>> qt_area = area.value  # Returns Qt.DockWidgetArea.LeftDockWidgetArea
        >>> is_floating = area == DockArea.FLOATING

    Note:
        TOP dock area is not included because the Ink UI only uses LEFT, RIGHT,
        and BOTTOM areas. TOP is reserved for toolbars in Qt's layout system.
    """

    LEFT = Qt.DockWidgetArea.LeftDockWidgetArea
    RIGHT = Qt.DockWidgetArea.RightDockWidgetArea
    BOTTOM = Qt.DockWidgetArea.BottomDockWidgetArea
    FLOATING = -1  # Custom value for floating (undocked) panels


@dataclass
class PanelGeometry:
    """Geometry information for a panel including size and position.

    This dataclass captures the complete geometry of a panel, supporting both
    docked panels (where only size is relevant) and floating panels (where
    both size and position are relevant for screen placement).

    All fields default to zero, enabling creation with partial data:
    - Just size for docked panels: PanelGeometry(width=200, height=300)
    - Full geometry for floating: PanelGeometry(width=400, height=600, x=100, y=50)

    Attributes:
        width: Panel width in pixels. Relevant for all panel states.
        height: Panel height in pixels. Relevant for all panel states.
        x: Horizontal screen position in pixels. Only relevant for floating panels.
        y: Vertical screen position in pixels. Only relevant for floating panels.

    Example:
        >>> # Docked panel - only size matters
        >>> docked_geom = PanelGeometry(width=200, height=400)
        >>> # Floating panel - position matters for screen placement
        >>> floating_geom = PanelGeometry(width=400, height=600, x=100, y=50)

    Note:
        Qt's geometry coordinates are in screen pixels, relative to the primary
        screen's top-left corner. For floating panels restored on systems with
        changed monitor configurations, Qt's restoreGeometry() handles repositioning.
    """

    width: int = 0
    height: int = 0
    x: int = 0  # Position x-coordinate (relevant for floating panels)
    y: int = 0  # Position y-coordinate (relevant for floating panels)


@dataclass
class PanelInfo:
    """Complete metadata for a single panel's state.

    This dataclass captures all information needed to describe and restore
    a panel's state, including visibility, dock area, floating status,
    geometry, and optional tab group membership.

    The tab_group field is reserved for future use when implementing
    support for tabbed dock widgets.

    Attributes:
        name: Unique identifier for the panel (e.g., "Hierarchy", "Properties").
        visible: Whether the panel is currently visible. Defaults to True.
        area: Which dock area the panel occupies. Defaults to DockArea.LEFT.
        is_floating: Whether the panel is floating (undocked). Defaults to False.
        geometry: Size and position information. Defaults to zero-initialized.
        tab_group: Identifier for tabbed panel groups. None if not tabbed.

    Example:
        >>> # Basic visible panel on the left
        >>> info = PanelInfo(name="Hierarchy")
        >>> # Hidden panel with custom area
        >>> info = PanelInfo(name="Properties", visible=False, area=DockArea.RIGHT)
        >>> # Floating panel with position
        >>> geom = PanelGeometry(width=400, height=500, x=100, y=100)
        >>> info = PanelInfo(
        ...     name="FloatingPanel",
        ...     is_floating=True,
        ...     area=DockArea.FLOATING,
        ...     geometry=geom
        ... )

    Design Decision:
        The geometry field uses field(default_factory=PanelGeometry) instead of
        a default value to avoid the mutable default argument pitfall in Python.
        Each PanelInfo instance gets its own PanelGeometry instance.
    """

    name: str
    visible: bool = True
    area: DockArea = DockArea.LEFT
    is_floating: bool = False
    geometry: PanelGeometry = field(default_factory=PanelGeometry)
    tab_group: str | None = None  # Reserved for future tabbed panel support


@dataclass
class PanelState:
    """Complete state of all panels in the application.

    This dataclass aggregates panel information and Qt's native state blobs
    for comprehensive state capture and restoration. It provides convenience
    methods for querying and modifying individual panel states.

    Two types of state are stored:
    1. Structured state (panels dict): Queryable panel metadata for runtime
       logic and serialization inspection.
    2. Qt native state (qt_state, qt_geometry): Opaque blobs from
       QMainWindow.saveState() and saveGeometry() for accurate restoration.

    Both are needed because Qt's state blob perfectly preserves complex layouts
    but cannot be queried, while structured state enables application logic.

    Attributes:
        panels: Dictionary mapping panel names to PanelInfo objects.
        qt_state: QByteArray from QMainWindow.saveState(). May be None.
        qt_geometry: QByteArray from QMainWindow.saveGeometry(). May be None.

    Example:
        >>> # Create empty state
        >>> state = PanelState()
        >>> # Create with panels
        >>> panels = {
        ...     "Hierarchy": PanelInfo(name="Hierarchy"),
        ...     "Properties": PanelInfo(name="Properties", area=DockArea.RIGHT),
        ... }
        >>> state = PanelState(panels=panels)
        >>> # Query state
        >>> state.is_panel_visible("Hierarchy")  # True
        >>> state.get_panel("Properties").area  # DockArea.RIGHT

    Design Decision:
        Methods that modify state (set_panel_visible) operate directly on the
        panels dict rather than returning new instances. This follows Qt's
        mutable model pattern and matches how PanelStateManager uses the state.
    """

    panels: dict[str, PanelInfo] = field(default_factory=dict)
    qt_state: QByteArray | None = None
    qt_geometry: QByteArray | None = None

    def get_panel(self, name: str) -> PanelInfo | None:
        """Get panel info by name.

        Retrieves the PanelInfo for a panel with the given name. Returns None
        if no panel with that name exists in the state.

        Args:
            name: Panel identifier (e.g., "Hierarchy", "Properties", "Messages").

        Returns:
            PanelInfo for the panel if found, None otherwise.

        Example:
            >>> state = PanelState(panels={"Test": PanelInfo(name="Test")})
            >>> info = state.get_panel("Test")
            >>> info.name
            'Test'
            >>> state.get_panel("NonExistent") is None
            True
        """
        return self.panels.get(name)

    def set_panel_visible(self, name: str, visible: bool) -> None:
        """Update panel visibility.

        Sets the visibility state for a panel. If the panel doesn't exist
        in the state, this method does nothing (no error is raised).

        Args:
            name: Panel identifier to update.
            visible: New visibility state (True = visible, False = hidden).

        Example:
            >>> state = PanelState(panels={"Test": PanelInfo(name="Test")})
            >>> state.is_panel_visible("Test")
            True
            >>> state.set_panel_visible("Test", False)
            >>> state.is_panel_visible("Test")
            False
        """
        if name in self.panels:
            self.panels[name].visible = visible

    def is_panel_visible(self, name: str) -> bool:
        """Check if panel is visible.

        Returns the visibility state of a panel. If the panel doesn't exist,
        returns False (non-existent panels are considered not visible).

        Args:
            name: Panel identifier to check.

        Returns:
            True if the panel exists and is visible, False otherwise.

        Example:
            >>> state = PanelState(panels={
            ...     "Visible": PanelInfo(name="Visible", visible=True),
            ...     "Hidden": PanelInfo(name="Hidden", visible=False),
            ... })
            >>> state.is_panel_visible("Visible")
            True
            >>> state.is_panel_visible("Hidden")
            False
            >>> state.is_panel_visible("NonExistent")
            False
        """
        panel = self.get_panel(name)
        return panel.visible if panel else False
