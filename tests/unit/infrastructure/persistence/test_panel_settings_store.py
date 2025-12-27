"""Unit tests for PanelSettingsStore class.

This module tests the PanelSettingsStore class which persists panel layout
state using Qt's QSettings. The store handles saving and loading PanelState
including Qt's native state blobs and custom panel metadata.

Test Strategy:
    - Use temporary QSettings path to avoid polluting user settings
    - Test save/load round-trip for complete PanelState
    - Verify individual panel info serialization/deserialization
    - Test graceful handling of missing and corrupted settings
    - Verify enum parsing with fallback defaults

TDD Phase: RED - Tests written before implementation.

See Also:
    - Spec E06-F05-T02 for panel layout persistence requirements
    - Pre-docs E06-F05-T02.pre-docs.md for architecture decisions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QByteArray, QSettings

from ink.infrastructure.persistence.panel_settings_store import PanelSettingsStore
from ink.presentation.state.panel_state import PanelState

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


# =============================================================================
# Module-level Fixtures
# =============================================================================


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide isolated QSettings storage for each test.

    This fixture:
    1. Creates a temporary directory for settings
    2. Configures QSettings to use this directory
    3. Clears any existing settings
    4. Yields the path for test use

    Args:
        tmp_path: Pytest-provided temporary directory (unique per test).

    Yields:
        Path to temporary settings directory.
    """
    settings_path = tmp_path / "settings"
    settings_path.mkdir()

    # Configure QSettings to use temporary path for INI format
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    # Clear any existing settings to ensure test isolation
    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.clear()
    temp_settings.sync()

    yield settings_path


@pytest.fixture
def panel_settings_store(isolated_settings: Path) -> PanelSettingsStore:
    """Create PanelSettingsStore instance with isolated storage.

    Args:
        isolated_settings: Temporary settings directory (ensures isolation).

    Returns:
        Fresh PanelSettingsStore instance.
    """
    return PanelSettingsStore()


@pytest.fixture
def sample_panel_state() -> PanelState:
    """Create a sample PanelState for testing.

    Returns:
        PanelState with typical panel configuration.
    """
    from ink.presentation.state.panel_state import (
        DockArea,
        PanelGeometry,
        PanelInfo,
    )

    panels = {
        "Hierarchy": PanelInfo(
            name="Hierarchy",
            visible=True,
            area=DockArea.LEFT,
            is_floating=False,
            geometry=PanelGeometry(width=200, height=400, x=0, y=0),
        ),
        "Properties": PanelInfo(
            name="Properties",
            visible=True,
            area=DockArea.RIGHT,
            is_floating=False,
            geometry=PanelGeometry(width=300, height=500, x=0, y=0),
        ),
        "Messages": PanelInfo(
            name="Messages",
            visible=False,
            area=DockArea.BOTTOM,
            is_floating=False,
            geometry=PanelGeometry(width=800, height=150, x=0, y=0),
        ),
    }

    return PanelState(
        panels=panels,
        qt_state=QByteArray(b"mock_qt_state_data"),
        qt_geometry=QByteArray(b"mock_qt_geometry_data"),
    )


# =============================================================================
# Test Classes
# =============================================================================


class TestPanelSettingsStoreInit:
    """Test PanelSettingsStore initialization."""

    def test_creates_instance(self, isolated_settings: Path) -> None:
        """Verify PanelSettingsStore can be instantiated."""
        from ink.infrastructure.persistence.panel_settings_store import (
            PanelSettingsStore,
        )

        store = PanelSettingsStore()
        assert store is not None

    def test_has_settings_attribute(self, panel_settings_store) -> None:
        """Verify store has QSettings instance."""
        assert hasattr(panel_settings_store, "settings")
        assert isinstance(panel_settings_store.settings, QSettings)

    def test_has_settings_group_constant(self) -> None:
        """Verify SETTINGS_GROUP constant is defined."""
        from ink.infrastructure.persistence.panel_settings_store import (
            PanelSettingsStore,
        )

        assert hasattr(PanelSettingsStore, "SETTINGS_GROUP")
        assert PanelSettingsStore.SETTINGS_GROUP == "panels"

    def test_has_geometry_group_constant(self) -> None:
        """Verify GEOMETRY_GROUP constant is defined."""
        from ink.infrastructure.persistence.panel_settings_store import (
            PanelSettingsStore,
        )

        assert hasattr(PanelSettingsStore, "GEOMETRY_GROUP")
        assert PanelSettingsStore.GEOMETRY_GROUP == "geometry"


class TestPanelSettingsStoreHasSavedSettings:
    """Test has_saved_settings() method."""

    def test_returns_false_when_no_settings(self, panel_settings_store) -> None:
        """Verify returns False when no panel settings exist."""
        assert panel_settings_store.has_saved_settings() is False

    def test_returns_true_when_geometry_exists(self, panel_settings_store) -> None:
        """Verify returns True when geometry settings exist."""
        from ink.presentation.state.panel_state import PanelState

        # Save minimal state with geometry
        state = PanelState(qt_geometry=QByteArray(b"geometry"))
        panel_settings_store.save_panel_state(state)

        assert panel_settings_store.has_saved_settings() is True

    def test_returns_true_when_panels_exist(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify returns True when panel settings exist."""
        panel_settings_store.save_panel_state(sample_panel_state)
        assert panel_settings_store.has_saved_settings() is True


class TestPanelSettingsStoreSave:
    """Test save_panel_state() method."""

    def test_save_panel_state_creates_settings(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify save_panel_state creates settings entries."""
        panel_settings_store.save_panel_state(sample_panel_state)
        assert panel_settings_store.has_saved_settings() is True

    def test_save_panel_state_stores_qt_geometry(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify Qt geometry blob is stored."""
        panel_settings_store.save_panel_state(sample_panel_state)

        # Check geometry group has window key
        panel_settings_store.settings.beginGroup("geometry")
        has_window = panel_settings_store.settings.contains("window")
        panel_settings_store.settings.endGroup()

        assert has_window is True

    def test_save_panel_state_stores_qt_state(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify Qt state blob is stored."""
        panel_settings_store.save_panel_state(sample_panel_state)

        # Check geometry group has state key
        panel_settings_store.settings.beginGroup("geometry")
        has_state = panel_settings_store.settings.contains("state")
        panel_settings_store.settings.endGroup()

        assert has_state is True

    def test_save_panel_state_stores_panel_visibility(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify individual panel visibility is stored."""
        panel_settings_store.save_panel_state(sample_panel_state)

        # Check Hierarchy panel visible flag
        panel_settings_store.settings.beginGroup("panels/Hierarchy")
        visible = panel_settings_store.settings.value("visible", type=bool)
        panel_settings_store.settings.endGroup()

        assert visible is True

    def test_save_panel_state_stores_panel_area(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify individual panel area is stored as string."""
        panel_settings_store.save_panel_state(sample_panel_state)

        # Check Properties panel area
        panel_settings_store.settings.beginGroup("panels/Properties")
        area = panel_settings_store.settings.value("area", type=str)
        panel_settings_store.settings.endGroup()

        assert area == "RIGHT"

    def test_save_panel_state_stores_panel_geometry(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify panel geometry dict is stored."""
        panel_settings_store.save_panel_state(sample_panel_state)

        # Check Hierarchy panel geometry
        # Note: QSettings doesn't support dict type parameter, load without type
        panel_settings_store.settings.beginGroup("panels/Hierarchy")
        geometry = panel_settings_store.settings.value("geometry", {})
        panel_settings_store.settings.endGroup()

        assert geometry is not None
        assert isinstance(geometry, dict)
        assert geometry.get("width") == 200
        assert geometry.get("height") == 400

    def test_save_panel_state_stores_floating_state(
        self, panel_settings_store
    ) -> None:
        """Verify floating state is stored."""
        from ink.presentation.state.panel_state import (
            DockArea,
            PanelGeometry,
            PanelInfo,
            PanelState,
        )

        floating_panel = PanelInfo(
            name="FloatingPanel",
            visible=True,
            area=DockArea.FLOATING,
            is_floating=True,
            geometry=PanelGeometry(width=400, height=300, x=100, y=200),
        )
        state = PanelState(panels={"FloatingPanel": floating_panel})

        panel_settings_store.save_panel_state(state)

        panel_settings_store.settings.beginGroup("panels/FloatingPanel")
        is_floating = panel_settings_store.settings.value("is_floating", type=bool)
        panel_settings_store.settings.endGroup()

        assert is_floating is True

    def test_save_panel_state_stores_tab_group(self, panel_settings_store) -> None:
        """Verify tab group is stored when present."""
        from ink.presentation.state.panel_state import PanelInfo, PanelState

        panel_with_tab = PanelInfo(name="TabbedPanel", tab_group="group1")
        state = PanelState(panels={"TabbedPanel": panel_with_tab})

        panel_settings_store.save_panel_state(state)

        panel_settings_store.settings.beginGroup("panels/TabbedPanel")
        tab_group = panel_settings_store.settings.value("tab_group", type=str)
        panel_settings_store.settings.endGroup()

        assert tab_group == "group1"

    def test_save_panel_state_calls_sync(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify sync is called after save to force disk write."""
        # Save state and verify settings exist (implies sync worked)
        panel_settings_store.save_panel_state(sample_panel_state)

        # Create new instance and verify settings persist
        from ink.infrastructure.persistence.panel_settings_store import (
            PanelSettingsStore,
        )

        new_store = PanelSettingsStore()
        assert new_store.has_saved_settings() is True


class TestPanelSettingsStoreLoad:
    """Test load_panel_state() method."""

    def test_load_returns_none_when_no_settings(self, panel_settings_store) -> None:
        """Verify load returns None when no settings exist."""
        result = panel_settings_store.load_panel_state()
        assert result is None

    def test_load_returns_panel_state(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify load returns PanelState when settings exist."""
        from ink.presentation.state.panel_state import PanelState

        panel_settings_store.save_panel_state(sample_panel_state)
        result = panel_settings_store.load_panel_state()

        assert result is not None
        assert isinstance(result, PanelState)

    def test_load_restores_qt_geometry(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify Qt geometry blob is restored correctly."""
        panel_settings_store.save_panel_state(sample_panel_state)
        result = panel_settings_store.load_panel_state()

        assert result.qt_geometry == sample_panel_state.qt_geometry

    def test_load_restores_qt_state(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify Qt state blob is restored correctly."""
        panel_settings_store.save_panel_state(sample_panel_state)
        result = panel_settings_store.load_panel_state()

        assert result.qt_state == sample_panel_state.qt_state

    def test_load_restores_panel_visibility(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify panel visibility is restored correctly."""
        panel_settings_store.save_panel_state(sample_panel_state)
        result = panel_settings_store.load_panel_state()

        # Messages panel was hidden in sample
        assert result.panels["Messages"].visible is False
        assert result.panels["Hierarchy"].visible is True

    def test_load_restores_panel_area(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify panel dock area is restored correctly."""
        from ink.presentation.state.panel_state import DockArea

        panel_settings_store.save_panel_state(sample_panel_state)
        result = panel_settings_store.load_panel_state()

        assert result.panels["Hierarchy"].area == DockArea.LEFT
        assert result.panels["Properties"].area == DockArea.RIGHT
        assert result.panels["Messages"].area == DockArea.BOTTOM

    def test_load_restores_panel_geometry(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify panel geometry is restored correctly."""
        panel_settings_store.save_panel_state(sample_panel_state)
        result = panel_settings_store.load_panel_state()

        hierarchy_geom = result.panels["Hierarchy"].geometry
        assert hierarchy_geom.width == 200
        assert hierarchy_geom.height == 400

    def test_load_restores_floating_state(self, panel_settings_store) -> None:
        """Verify floating state is restored correctly."""
        from ink.presentation.state.panel_state import (
            DockArea,
            PanelInfo,
            PanelState,
        )

        floating_panel = PanelInfo(
            name="FloatingPanel",
            is_floating=True,
            area=DockArea.FLOATING,
        )
        state = PanelState(panels={"FloatingPanel": floating_panel})

        panel_settings_store.save_panel_state(state)
        result = panel_settings_store.load_panel_state()

        assert result.panels["FloatingPanel"].is_floating is True

    def test_load_restores_tab_group(self, panel_settings_store) -> None:
        """Verify tab group is restored correctly."""
        from ink.presentation.state.panel_state import PanelInfo, PanelState

        panel = PanelInfo(name="TabbedPanel", tab_group="group1")
        state = PanelState(panels={"TabbedPanel": panel})

        panel_settings_store.save_panel_state(state)
        result = panel_settings_store.load_panel_state()

        assert result.panels["TabbedPanel"].tab_group == "group1"


class TestPanelSettingsStoreRoundTrip:
    """Test save/load round-trip preserves data integrity."""

    def test_roundtrip_preserves_complete_state(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify complete state survives round-trip."""
        panel_settings_store.save_panel_state(sample_panel_state)
        result = panel_settings_store.load_panel_state()

        # Check all panels exist
        assert len(result.panels) == len(sample_panel_state.panels)

        # Check each panel
        for name, original_info in sample_panel_state.panels.items():
            loaded_info = result.panels[name]
            assert loaded_info.name == original_info.name
            assert loaded_info.visible == original_info.visible
            assert loaded_info.area == original_info.area
            assert loaded_info.is_floating == original_info.is_floating
            assert loaded_info.geometry.width == original_info.geometry.width
            assert loaded_info.geometry.height == original_info.geometry.height
            assert loaded_info.geometry.x == original_info.geometry.x
            assert loaded_info.geometry.y == original_info.geometry.y

    def test_roundtrip_across_instances(
        self, isolated_settings, sample_panel_state
    ) -> None:
        """Verify state persists across store instances."""
        from ink.infrastructure.persistence.panel_settings_store import (
            PanelSettingsStore,
        )

        # Save with first instance
        store1 = PanelSettingsStore()
        store1.save_panel_state(sample_panel_state)

        # Load with second instance
        store2 = PanelSettingsStore()
        result = store2.load_panel_state()

        assert result is not None
        assert len(result.panels) == 3


class TestPanelSettingsStoreErrorHandling:
    """Test error handling for corrupted or missing settings."""

    def test_load_handles_invalid_area_name(self, panel_settings_store) -> None:
        """Verify invalid area name defaults to LEFT."""
        from ink.presentation.state.panel_state import DockArea

        # Manually create settings with invalid area
        panel_settings_store.settings.beginGroup("panels/BadPanel")
        panel_settings_store.settings.setValue("visible", True)
        panel_settings_store.settings.setValue("area", "INVALID_AREA")
        panel_settings_store.settings.setValue("is_floating", False)
        geometry = {"width": 100, "height": 100, "x": 0, "y": 0}
        panel_settings_store.settings.setValue("geometry", geometry)
        panel_settings_store.settings.endGroup()
        panel_settings_store.settings.sync()

        result = panel_settings_store.load_panel_state()

        # Should default to LEFT
        assert result.panels["BadPanel"].area == DockArea.LEFT

    def test_load_handles_missing_geometry_fields(self, panel_settings_store) -> None:
        """Verify missing geometry fields default to zero."""
        # Manually create settings with partial geometry
        panel_settings_store.settings.beginGroup("panels/PartialPanel")
        panel_settings_store.settings.setValue("visible", True)
        panel_settings_store.settings.setValue("area", "LEFT")
        panel_settings_store.settings.setValue("is_floating", False)
        panel_settings_store.settings.setValue("geometry", {"width": 100})  # Missing height, x, y
        panel_settings_store.settings.endGroup()
        panel_settings_store.settings.sync()

        result = panel_settings_store.load_panel_state()

        geom = result.panels["PartialPanel"].geometry
        assert geom.width == 100
        assert geom.height == 0  # Default
        assert geom.x == 0  # Default
        assert geom.y == 0  # Default

    def test_load_handles_missing_panel_settings(self, panel_settings_store) -> None:
        """Verify panels without 'visible' key are skipped."""
        # Create panel with missing required field
        panel_settings_store.settings.beginGroup("panels/IncompletePanel")
        panel_settings_store.settings.setValue("area", "LEFT")  # No 'visible' key
        panel_settings_store.settings.endGroup()
        panel_settings_store.settings.sync()

        result = panel_settings_store.load_panel_state()

        # Panel should be skipped, not loaded
        assert "IncompletePanel" not in result.panels if result else True

    def test_load_handles_empty_geometry_dict(self, panel_settings_store) -> None:
        """Verify empty geometry dict uses defaults."""
        panel_settings_store.settings.beginGroup("panels/EmptyGeom")
        panel_settings_store.settings.setValue("visible", True)
        panel_settings_store.settings.setValue("area", "LEFT")
        panel_settings_store.settings.setValue("is_floating", False)
        panel_settings_store.settings.setValue("geometry", {})  # Empty dict
        panel_settings_store.settings.endGroup()
        panel_settings_store.settings.sync()

        result = panel_settings_store.load_panel_state()

        geom = result.panels["EmptyGeom"].geometry
        assert geom.width == 0
        assert geom.height == 0
        assert geom.x == 0
        assert geom.y == 0


class TestPanelSettingsStoreClear:
    """Test clear_panel_state() method."""

    def test_clear_removes_geometry_settings(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify clear removes geometry group settings."""
        panel_settings_store.save_panel_state(sample_panel_state)
        panel_settings_store.clear_panel_state()

        # Check geometry group is empty
        panel_settings_store.settings.beginGroup("geometry")
        has_window = panel_settings_store.settings.contains("window")
        panel_settings_store.settings.endGroup()

        assert has_window is False

    def test_clear_removes_panel_settings(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify clear removes panels group settings."""
        panel_settings_store.save_panel_state(sample_panel_state)
        panel_settings_store.clear_panel_state()

        # Check panels group is empty
        panel_settings_store.settings.beginGroup("panels")
        child_groups = panel_settings_store.settings.childGroups()
        panel_settings_store.settings.endGroup()

        assert len(child_groups) == 0

    def test_clear_makes_has_saved_settings_false(
        self, panel_settings_store, sample_panel_state
    ) -> None:
        """Verify has_saved_settings returns False after clear."""
        panel_settings_store.save_panel_state(sample_panel_state)
        panel_settings_store.clear_panel_state()

        assert panel_settings_store.has_saved_settings() is False

    def test_clear_calls_sync(
        self, panel_settings_store, sample_panel_state, isolated_settings
    ) -> None:
        """Verify sync is called after clear to persist changes."""
        from ink.infrastructure.persistence.panel_settings_store import (
            PanelSettingsStore,
        )

        panel_settings_store.save_panel_state(sample_panel_state)
        panel_settings_store.clear_panel_state()

        # Create new instance and verify clear persisted
        new_store = PanelSettingsStore()
        assert new_store.has_saved_settings() is False


class TestPanelSettingsStoreFloatingPanelGeometry:
    """Test floating panel geometry position persistence."""

    def test_floating_panel_position_preserved(self, panel_settings_store) -> None:
        """Verify floating panel x,y position is preserved."""
        from ink.presentation.state.panel_state import (
            DockArea,
            PanelGeometry,
            PanelInfo,
            PanelState,
        )

        floating = PanelInfo(
            name="FloatingPanel",
            visible=True,
            area=DockArea.FLOATING,
            is_floating=True,
            geometry=PanelGeometry(width=400, height=300, x=150, y=250),
        )
        state = PanelState(panels={"FloatingPanel": floating})

        panel_settings_store.save_panel_state(state)
        result = panel_settings_store.load_panel_state()

        geom = result.panels["FloatingPanel"].geometry
        assert geom.x == 150
        assert geom.y == 250
        assert geom.width == 400
        assert geom.height == 300
