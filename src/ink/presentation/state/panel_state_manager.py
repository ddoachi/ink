"""Panel state manager for tracking dock widget configuration changes.

This module provides the PanelStateManager class that monitors dock widget
state changes using Qt's signal/slot mechanism. The manager maintains a
synchronized view of all panel states and emits signals when changes occur.

Architecture:
    PanelStateManager follows a reactive pattern where Qt dock widget signals
    (visibilityChanged, topLevelChanged, dockLocationChanged) trigger internal
    state updates and custom signal emissions for application-layer integration.

    Signal Flow:
        QDockWidget signal → Manager handler → Update PanelState → Emit custom signal

Design Decisions:
    - PanelStateManager is a QObject to enable Qt signal/slot mechanism.
    - Registration-based tracking: panels must be explicitly registered.
    - Signals connected during registration for automatic state synchronization.
    - Two-tier state: structured PanelState + Qt's opaque saveState() blobs.

Usage Example:
    >>> from ink.presentation.state import PanelStateManager
    >>> manager = PanelStateManager(main_window)
    >>> manager.register_panel("Hierarchy", hierarchy_dock)
    >>> manager.state_changed.connect(on_state_changed)
    >>> state = manager.capture_state()

See Also:
    - Spec E06-F05-T01 for panel state management requirements
    - Pre-docs E06-F05-T01.pre-docs.md for architecture decisions
    - panel_state.py for data structures
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, Signal

from ink.presentation.state.panel_state import (
    DockArea,
    PanelGeometry,
    PanelInfo,
    PanelState,
)

if TYPE_CHECKING:
    from PySide6.QtWidgets import QDockWidget, QMainWindow


class PanelStateManager(QObject):
    """Manages panel state tracking and updates via Qt signals.

    This class monitors dock widget state changes and maintains a synchronized
    PanelState object. It connects to Qt dock widget signals during panel
    registration and emits custom signals when state changes occur.

    The manager provides both reactive updates (via signals) and explicit
    state capture/restore for persistence.

    Signals:
        state_changed: Emitted when any panel state changes.
        panel_visibility_changed: Emitted with (panel_name, visible) when
            a panel's visibility changes.
        panel_area_changed: Emitted with (panel_name, DockArea) when a
            panel's dock area changes.

    Attributes:
        main_window: Reference to the QMainWindow containing dock widgets.
        state: Current PanelState with all registered panel information.

    Example:
        >>> manager = PanelStateManager(main_window)
        >>> manager.register_panel("Hierarchy", hierarchy_dock)
        >>> manager.state_changed.connect(lambda: print("State changed!"))
        >>> manager.show_panel("Hierarchy")

    Design Pattern:
        The manager follows the Observer pattern, where dock widgets are
        subjects and the manager observes their state changes. Custom
        signals allow application code to observe the aggregated state.
    """

    # Custom signals for state change notifications
    # These enable application-layer reactions to panel state changes

    # Emitted when any panel state changes (visibility, area, floating)
    state_changed = Signal()

    # Emitted when a specific panel's visibility changes
    # Parameters: (panel_name: str, visible: bool)
    panel_visibility_changed = Signal(str, bool)

    # Emitted when a specific panel's dock area changes
    # Parameters: (panel_name: str, area: DockArea)
    panel_area_changed = Signal(str, DockArea)

    def __init__(self, main_window: QMainWindow) -> None:
        """Initialize the panel state manager.

        Creates an empty state and prepares for panel registration.
        Panels must be registered individually via register_panel().

        Args:
            main_window: The QMainWindow instance containing dock widgets.
                Used for querying dock widget areas and saving/restoring
                Qt's internal state.

        Note:
            The manager does not automatically discover dock widgets.
            Each panel must be explicitly registered to enable tracking.
        """
        super().__init__()
        self.main_window = main_window
        self.state = PanelState()
        self._dock_widgets: dict[str, QDockWidget] = {}

    def register_panel(self, name: str, dock_widget: QDockWidget) -> None:
        """Register a dock widget for state tracking.

        Adds the dock widget to the manager's tracking system, captures its
        current state, and connects to its signals for reactive updates.

        After registration, any changes to the dock widget's visibility,
        floating state, or dock area will be automatically tracked and
        reflected in the manager's state.

        Args:
            name: Unique identifier for the panel (e.g., "Hierarchy",
                "Properties", "Messages"). Used as the key in state.panels.
            dock_widget: The QDockWidget instance to track. Must be a valid
                dock widget that has been added to the main window.

        Example:
            >>> manager.register_panel("Hierarchy", hierarchy_dock)
            >>> manager.register_panel("Properties", property_dock)
            >>> print(manager.state.panels.keys())
            dict_keys(['Hierarchy', 'Properties'])

        Note:
            Signal connections are created during registration. If the dock
            widget is replaced, you must re-register to update tracking.
        """
        # Store reference to the dock widget
        self._dock_widgets[name] = dock_widget

        # Capture initial state from the dock widget
        panel_info = PanelInfo(
            name=name,
            visible=dock_widget.isVisible(),
            area=self._get_dock_area(dock_widget),
            is_floating=dock_widget.isFloating(),
            geometry=self._get_panel_geometry(dock_widget),
        )
        self.state.panels[name] = panel_info

        # Connect signals to track future changes
        self._connect_panel_signals(name, dock_widget)

    def _connect_panel_signals(self, name: str, dock_widget: QDockWidget) -> None:
        """Connect dock widget signals to state update handlers.

        Wires Qt dock widget signals to internal handler methods that
        update the manager's state and emit custom signals.

        Args:
            name: Panel identifier for handler context.
            dock_widget: Dock widget to connect signals from.

        Connected Signals:
            - visibilityChanged(bool): Panel shown or hidden
            - topLevelChanged(bool): Panel floated or docked
            - dockLocationChanged(Qt.DockWidgetArea): Panel moved to new area
        """
        # Lambda captures 'name' for use in handlers
        dock_widget.visibilityChanged.connect(
            lambda visible: self._on_visibility_changed(name, visible)
        )
        dock_widget.topLevelChanged.connect(
            lambda floating: self._on_floating_changed(name, floating)
        )
        dock_widget.dockLocationChanged.connect(lambda area: self._on_location_changed(name, area))

    def _on_visibility_changed(self, name: str, visible: bool) -> None:
        """Handle panel visibility change.

        Updates the panel's visibility state and emits appropriate signals.

        Args:
            name: Panel identifier.
            visible: New visibility state (True = visible, False = hidden).
        """
        if name in self.state.panels:
            self.state.panels[name].visible = visible
            self.panel_visibility_changed.emit(name, visible)
            self.state_changed.emit()

    def _on_floating_changed(self, name: str, floating: bool) -> None:
        """Handle panel floating state change.

        Updates the panel's floating state. When a panel becomes floating,
        its area is set to FLOATING and geometry is captured. When docked,
        the area will be updated by dockLocationChanged signal.

        Args:
            name: Panel identifier.
            floating: New floating state (True = floating, False = docked).
        """
        if name in self.state.panels:
            panel = self.state.panels[name]
            panel.is_floating = floating
            if floating:
                panel.area = DockArea.FLOATING
                # Update geometry when floating (position matters)
                if name in self._dock_widgets:
                    panel.geometry = self._get_panel_geometry(self._dock_widgets[name])
            self.state_changed.emit()

    def _on_location_changed(self, name: str, area: Qt.DockWidgetArea) -> None:
        """Handle panel dock area change.

        Updates the panel's dock area and emits appropriate signals.
        This is called when a docked panel is moved to a different area.

        Args:
            name: Panel identifier.
            area: New Qt dock area (LeftDockWidgetArea, RightDockWidgetArea, etc.)
        """
        if name in self.state.panels:
            dock_area = self._qt_area_to_dock_area(area)
            self.state.panels[name].area = dock_area
            self.panel_area_changed.emit(name, dock_area)
            self.state_changed.emit()

    def _get_dock_area(self, dock_widget: QDockWidget) -> DockArea:
        """Get current dock area of a widget.

        Determines whether a dock widget is floating or docked, and if
        docked, which area it occupies.

        Args:
            dock_widget: Dock widget to query.

        Returns:
            DockArea enum value: FLOATING if floating, or LEFT/RIGHT/BOTTOM
            based on the dock widget's current area.
        """
        if dock_widget.isFloating():
            return DockArea.FLOATING

        qt_area = self.main_window.dockWidgetArea(dock_widget)
        return self._qt_area_to_dock_area(qt_area)

    def _qt_area_to_dock_area(self, qt_area: Qt.DockWidgetArea) -> DockArea:
        """Convert Qt dock area to DockArea enum.

        Maps Qt's DockWidgetArea values to the simplified DockArea enum.
        Unknown or unsupported areas (like TOP) default to LEFT.

        Args:
            qt_area: Qt.DockWidgetArea value.

        Returns:
            Corresponding DockArea enum value.
        """
        area_map = {
            Qt.DockWidgetArea.LeftDockWidgetArea: DockArea.LEFT,
            Qt.DockWidgetArea.RightDockWidgetArea: DockArea.RIGHT,
            Qt.DockWidgetArea.BottomDockWidgetArea: DockArea.BOTTOM,
        }
        return area_map.get(qt_area, DockArea.LEFT)

    def _get_panel_geometry(self, dock_widget: QDockWidget) -> PanelGeometry:
        """Extract geometry information from a dock widget.

        Creates a PanelGeometry snapshot from the dock widget's current
        geometry (size and position).

        Args:
            dock_widget: Dock widget to get geometry from.

        Returns:
            PanelGeometry with width, height, x, y values.
        """
        geometry = dock_widget.geometry()
        return PanelGeometry(
            width=geometry.width(),
            height=geometry.height(),
            x=geometry.x(),
            y=geometry.y(),
        )

    def capture_state(self) -> PanelState:
        """Capture current state of all panels.

        Creates a complete snapshot of all panel states, including updated
        geometries and Qt's internal state blobs for accurate restoration.

        This method should be called before persisting state (e.g., on
        application close) to ensure all values are current.

        Returns:
            Complete PanelState snapshot with all panels and Qt blobs.

        Note:
            Qt's saveState() and saveGeometry() are called to capture the
            internal dock layout state that cannot be represented in our
            structured state alone.
        """
        # Update geometries for all panels before capturing
        for name, dock_widget in self._dock_widgets.items():
            if name in self.state.panels:
                self.state.panels[name].geometry = self._get_panel_geometry(dock_widget)

        # Capture Qt's internal state blobs
        self.state.qt_state = self.main_window.saveState()
        self.state.qt_geometry = self.main_window.saveGeometry()

        return self.state

    def restore_state(self, state: PanelState) -> None:
        """Restore panel state from a saved snapshot.

        Applies a previously captured state to restore the panel layout.
        Qt's internal state is restored first (handles complex docking),
        then individual panel visibilities are applied.

        Args:
            state: PanelState to restore from (typically from persistence).

        Note:
            The order matters: Qt's restoreState() must be called before
            individual visibility settings to handle dock arrangement first.
        """
        # Restore Qt's internal state first (handles complex docking)
        if state.qt_geometry is not None:
            self.main_window.restoreGeometry(state.qt_geometry)
        if state.qt_state is not None:
            self.main_window.restoreState(state.qt_state)

        # Apply individual panel visibility states
        for name, panel_info in state.panels.items():
            if name in self._dock_widgets:
                dock_widget = self._dock_widgets[name]
                dock_widget.setVisible(panel_info.visible)

        # Update our tracking state
        self.state = state

    def show_panel(self, name: str) -> None:
        """Show a panel by name.

        Makes the panel visible and raises it (brings to front if tabbed).

        Args:
            name: Panel identifier to show.

        Note:
            If the panel name is not registered, this method does nothing.
        """
        if name in self._dock_widgets:
            self._dock_widgets[name].show()
            self._dock_widgets[name].raise_()

    def hide_panel(self, name: str) -> None:
        """Hide a panel by name.

        Hides the panel without destroying it. The panel can be shown
        again using show_panel().

        Args:
            name: Panel identifier to hide.

        Note:
            If the panel name is not registered, this method does nothing.
        """
        if name in self._dock_widgets:
            self._dock_widgets[name].hide()

    def toggle_panel(self, name: str) -> None:
        """Toggle panel visibility.

        If the panel is visible, hides it. If hidden, shows and raises it.

        Args:
            name: Panel identifier to toggle.

        Note:
            If the panel name is not registered, this method does nothing.
        """
        if name in self._dock_widgets:
            dock_widget = self._dock_widgets[name]
            if dock_widget.isVisible():
                dock_widget.hide()
            else:
                dock_widget.show()
                dock_widget.raise_()

    def get_state(self) -> PanelState:
        """Get current panel state (snapshot).

        Convenience method that captures and returns the current state.
        Equivalent to calling capture_state().

        Returns:
            Complete PanelState snapshot.
        """
        return self.capture_state()
