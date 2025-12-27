"""Panel settings store for persisting panel layout state.

This module provides the PanelSettingsStore class which handles persistence
of panel layout state using Qt's QSettings mechanism. It saves and loads
both Qt's native state blobs and custom panel metadata for accurate
restoration of dock widget layouts across application sessions.

Design Decisions:
    - Uses QSettings for platform-native storage (INI on Linux, Registry on Windows)
    - Stores both Qt state blobs (opaque but accurate) and structured metadata (queryable)
    - Validates settings on load with fallback defaults for robustness
    - Uses settings groups for hierarchical organization (geometry/, panels/)
    - Forces sync() after save/clear to ensure disk write

Why Store Both Qt State and Custom Metadata?
    Qt's saveState() produces a binary blob that perfectly preserves complex
    dock layouts (tabs, splitters, nested docks) but is opaque and cannot be
    queried. The structured panel metadata provides:
    - Queryable state for application logic
    - Migration support for future schema changes
    - Fallback restoration if Qt blob format changes
    - Human-readable settings in INI file for debugging

Storage Structure:
    ink/
    ├── geometry/
    │   ├── window          # QByteArray from saveGeometry()
    │   └── state           # QByteArray from saveState()
    └── panels/
        ├── Hierarchy/
        │   ├── visible     # bool
        │   ├── area        # string enum name
        │   ├── is_floating # bool
        │   ├── geometry    # dict {width, height, x, y}
        │   └── tab_group   # optional string
        └── ... (other panels)

See Also:
    - Spec E06-F05-T02 for panel layout persistence requirements
    - Pre-docs E06-F05-T02.pre-docs.md for architecture decisions
    - panel_state.py for PanelState data structures
    - app_settings.py for AppSettings base implementation
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

from ink.presentation.state.panel_state import (
    DockArea,
    PanelGeometry,
    PanelInfo,
    PanelState,
)


class PanelSettingsStore:
    """Handles persistence of panel layout state to QSettings.

    This class provides save/load operations for panel state, including
    Qt's native dock widget state blobs and structured panel metadata.
    It integrates with the PanelStateManager for complete layout persistence.

    The store uses hierarchical QSettings groups to organize data:
    - geometry/: Qt state blobs (window geometry, dock state)
    - panels/{name}/: Per-panel metadata (visibility, area, geometry)

    All operations are validated on load with graceful fallback to defaults
    for robustness against settings file corruption or manual editing.

    Attributes:
        SETTINGS_GROUP: Group name for panel metadata ("panels").
        GEOMETRY_GROUP: Group name for Qt state blobs ("geometry").
        settings: Underlying QSettings instance.

    Example:
        >>> from ink.infrastructure.persistence import PanelSettingsStore
        >>> store = PanelSettingsStore()
        >>> store.save_panel_state(panel_state)
        >>> # Later, on app restart:
        >>> restored_state = store.load_panel_state()
        >>> if restored_state:
        ...     panel_manager.restore_state(restored_state)

    See Also:
        - PanelStateManager.capture_state(): Creates PanelState for saving
        - PanelStateManager.restore_state(): Applies loaded PanelState
        - AppSettings: Sister class for application settings
    """

    # Settings group names for hierarchical organization
    # These match the storage structure documented in the module docstring
    SETTINGS_GROUP: str = "panels"
    GEOMETRY_GROUP: str = "geometry"

    def __init__(self) -> None:
        r"""Initialize the panel settings store.

        Creates a QSettings instance using the application's organization
        and application names (set in main.py via QCoreApplication).
        This ensures panel settings are stored alongside other app settings.

        Storage locations by platform:
            - Linux: ~/.config/InkProject/Ink.conf
            - Windows: HKEY_CURRENT_USER\\Software\\InkProject\\Ink
            - macOS: ~/Library/Preferences/com.InkProject.Ink.plist
        """
        # Use the same organization/app as AppSettings for consistent storage
        self.settings = QSettings("InkProject", "Ink")

    def save_panel_state(self, state: PanelState) -> None:
        """Save panel state to QSettings.

        Persists both Qt's native state blobs and structured panel metadata.
        Forces a sync() after saving to ensure data is written to disk,
        preventing data loss if the application crashes.

        Args:
            state: PanelState containing panels dict and Qt blobs to persist.

        Save Order:
            1. Save Qt geometry blob (window position/size)
            2. Save Qt state blob (dock layout)
            3. Save individual panel metadata (visibility, area, geometry)
            4. Force sync to disk

        Example:
            >>> state = panel_manager.capture_state()
            >>> store.save_panel_state(state)
        """
        # Save Qt's native state blobs for accurate restoration
        # These capture complex dock arrangements (tabs, splitters)
        self.settings.beginGroup(self.GEOMETRY_GROUP)
        if state.qt_geometry is not None:
            self.settings.setValue("window", state.qt_geometry)
        if state.qt_state is not None:
            self.settings.setValue("state", state.qt_state)
        self.settings.endGroup()

        # Save structured panel metadata for queryability and migration support
        self.settings.beginGroup(self.SETTINGS_GROUP)
        for panel_name, panel_info in state.panels.items():
            self._save_panel_info(panel_name, panel_info)
        self.settings.endGroup()

        # Force write to disk to ensure persistence
        # Without sync(), data may be lost if app crashes before normal exit
        self.settings.sync()

    def _save_panel_info(self, panel_name: str, panel_info: PanelInfo) -> None:
        """Save individual panel information to a settings subgroup.

        Creates a settings group for the panel and stores all metadata
        fields. Geometry is stored as a dict for JSON-like serialization.

        Args:
            panel_name: Unique identifier for the panel (e.g., "Hierarchy").
            panel_info: PanelInfo containing visibility, area, geometry, etc.

        Settings Structure (within panels/ group):
            {panel_name}/
            ├── visible     # bool
            ├── area        # string (enum name)
            ├── is_floating # bool
            ├── geometry    # dict {width, height, x, y}
            └── tab_group   # string (optional)
        """
        self.settings.beginGroup(panel_name)

        # Save primitive fields directly
        self.settings.setValue("visible", panel_info.visible)
        self.settings.setValue("area", panel_info.area.name)  # Enum to string
        self.settings.setValue("is_floating", panel_info.is_floating)

        # Save geometry as dict for structured storage
        # QSettings handles dict serialization automatically
        geometry_dict = {
            "width": panel_info.geometry.width,
            "height": panel_info.geometry.height,
            "x": panel_info.geometry.x,
            "y": panel_info.geometry.y,
        }
        self.settings.setValue("geometry", geometry_dict)

        # Save optional tab group if present
        if panel_info.tab_group is not None:
            self.settings.setValue("tab_group", panel_info.tab_group)

        self.settings.endGroup()

    def load_panel_state(self) -> PanelState | None:
        """Load panel state from QSettings.

        Reconstructs a PanelState from saved settings, including Qt state
        blobs and individual panel metadata. Returns None if no settings
        exist, allowing the caller to use default layout.

        Returns:
            PanelState with restored panels and Qt blobs, or None if no
            saved state exists.

        Validation:
            - Checks for settings existence before loading
            - Validates enum values with fallback to defaults
            - Handles missing geometry fields with zero defaults
            - Skips panels with missing required fields

        Example:
            >>> state = store.load_panel_state()
            >>> if state is not None:
            ...     panel_manager.restore_state(state)
            ... else:
            ...     # Use default layout
            ...     window.set_initial_dock_sizes()
        """
        # Check if any settings exist before attempting load
        if not self._has_saved_state():
            return None

        state = PanelState()

        # Load Qt's native state blobs
        self.settings.beginGroup(self.GEOMETRY_GROUP)
        qt_geometry = self.settings.value("window")
        qt_state = self.settings.value("state")
        self.settings.endGroup()

        # Store Qt blobs in state (may be None if not saved)
        state.qt_geometry = qt_geometry
        state.qt_state = qt_state

        # Load individual panel metadata
        self.settings.beginGroup(self.SETTINGS_GROUP)
        panel_groups = self.settings.childGroups()

        for panel_name in panel_groups:
            panel_info = self._load_panel_info(panel_name)
            if panel_info is not None:
                state.panels[panel_name] = panel_info

        self.settings.endGroup()

        return state

    def _load_panel_info(self, panel_name: str) -> PanelInfo | None:
        """Load individual panel information from a settings subgroup.

        Reconstructs a PanelInfo from saved settings with validation
        and fallback defaults for robustness.

        Args:
            panel_name: Name of the panel subgroup to load.

        Returns:
            PanelInfo with loaded values, or None if required fields
            are missing (indicating incomplete/invalid settings).

        Validation:
            - Requires 'visible' key to exist (indicator of valid panel)
            - Falls back to DockArea.LEFT for invalid area names
            - Uses zero defaults for missing geometry values
            - Handles missing tab_group gracefully
        """
        self.settings.beginGroup(panel_name)

        # Check for required 'visible' key as indicator of valid settings
        # If missing, panel settings are incomplete/corrupted
        if not self.settings.contains("visible"):
            self.settings.endGroup()
            return None

        # Load basic properties with type hints and defaults
        # Cast to ensure correct types for mypy (QSettings.value returns object)
        visible = bool(self.settings.value("visible", True, type=bool))
        area_name = str(self.settings.value("area", "LEFT", type=str))
        is_floating = bool(self.settings.value("is_floating", False, type=bool))

        # Parse area enum with fallback to LEFT for invalid values
        # This handles manual settings file edits or Qt version changes
        try:
            area = DockArea[area_name]
        except KeyError:
            area = DockArea.LEFT  # Safe default fallback

        # Load geometry dict with defaults for missing values
        # Note: QSettings doesn't support dict as type parameter, so we
        # load without type hint and validate manually
        geometry_value = self.settings.value("geometry", {})
        # Ensure we have a dict, default to empty if corrupted/missing
        geometry_dict = geometry_value if isinstance(geometry_value, dict) else {}
        geometry = PanelGeometry(
            width=geometry_dict.get("width", 0),
            height=geometry_dict.get("height", 0),
            x=geometry_dict.get("x", 0),
            y=geometry_dict.get("y", 0),
        )

        # Load optional tab group (None if not present)
        tab_group_value = self.settings.value("tab_group", None, type=str)
        tab_group: str | None = str(tab_group_value) if tab_group_value else None

        self.settings.endGroup()

        return PanelInfo(
            name=panel_name,
            visible=visible,
            area=area,
            is_floating=is_floating,
            geometry=geometry,
            tab_group=tab_group,
        )

    def _has_saved_state(self) -> bool:
        """Check if any saved panel state exists in settings.

        Checks both geometry group (Qt blobs) and panels group (metadata)
        to determine if any state has been saved.

        Returns:
            True if geometry or panel settings exist, False otherwise.
        """
        # Check geometry group for Qt blobs
        self.settings.beginGroup(self.GEOMETRY_GROUP)
        has_geometry = self.settings.contains("window")
        self.settings.endGroup()

        # Check panels group for panel metadata
        self.settings.beginGroup(self.SETTINGS_GROUP)
        has_panels = len(self.settings.childGroups()) > 0
        self.settings.endGroup()

        return has_geometry or has_panels

    def has_saved_settings(self) -> bool:
        """Check if saved panel settings exist.

        Public method for checking settings existence before attempting
        load. Equivalent to calling _has_saved_state().

        Returns:
            True if any panel settings exist, False for fresh install.

        Example:
            >>> if store.has_saved_settings():
            ...     state = store.load_panel_state()
            ... else:
            ...     print("No saved settings, using defaults")
        """
        return self._has_saved_state()

    def clear_panel_state(self) -> None:
        """Clear all saved panel state (reset to defaults).

        Removes all panel settings from both geometry and panels groups.
        Forces a sync() after clearing to ensure changes are persisted.

        This method is called by the main window's reset_panel_layout()
        to allow users to return to default panel arrangement.

        Post-clear Behavior:
            - has_saved_settings() returns False
            - load_panel_state() returns None
            - Next app start will use default layout
        """
        # Clear geometry group (Qt state blobs)
        self.settings.beginGroup(self.GEOMETRY_GROUP)
        self.settings.remove("")  # Remove all keys in group
        self.settings.endGroup()

        # Clear panels group (individual panel metadata)
        self.settings.beginGroup(self.SETTINGS_GROUP)
        self.settings.remove("")  # Remove all keys in group
        self.settings.endGroup()

        # Force write to disk to ensure clear persists
        self.settings.sync()
