"""Unit tests for panel state data structures.

This module tests the panel state data structures in isolation:
- DockArea enum with Qt area mappings
- PanelGeometry dataclass for size/position tracking
- PanelInfo dataclass for individual panel metadata
- PanelState dataclass for complete panel state aggregation

These tests verify the data structures meet the requirements from spec E06-F05-T01
for panel state management.

TDD Phase: RED - These tests should fail initially until implementation is complete.

See Also:
    - Spec E06-F05-T01 for panel state management requirements
    - Pre-docs E06-F05-T01 for architecture decisions
"""

from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt


class TestDockAreaEnum:
    """Tests for DockArea enumeration.

    DockArea provides a simplified enum mapping to Qt's DockWidgetArea values,
    with an additional FLOATING value for undocked panels.
    """

    def test_dock_area_left_value(self) -> None:
        """Test LEFT area maps to Qt.DockWidgetArea.LeftDockWidgetArea."""
        from ink.presentation.state.panel_state import DockArea

        assert DockArea.LEFT.value == Qt.DockWidgetArea.LeftDockWidgetArea

    def test_dock_area_right_value(self) -> None:
        """Test RIGHT area maps to Qt.DockWidgetArea.RightDockWidgetArea."""
        from ink.presentation.state.panel_state import DockArea

        assert DockArea.RIGHT.value == Qt.DockWidgetArea.RightDockWidgetArea

    def test_dock_area_bottom_value(self) -> None:
        """Test BOTTOM area maps to Qt.DockWidgetArea.BottomDockWidgetArea."""
        from ink.presentation.state.panel_state import DockArea

        assert DockArea.BOTTOM.value == Qt.DockWidgetArea.BottomDockWidgetArea

    def test_dock_area_floating_value(self) -> None:
        """Test FLOATING has custom -1 value for undocked panels."""
        from ink.presentation.state.panel_state import DockArea

        assert DockArea.FLOATING.value == -1

    def test_dock_area_all_members(self) -> None:
        """Test DockArea has exactly four members."""
        from ink.presentation.state.panel_state import DockArea

        members = list(DockArea)
        assert len(members) == 4
        assert DockArea.LEFT in members
        assert DockArea.RIGHT in members
        assert DockArea.BOTTOM in members
        assert DockArea.FLOATING in members


class TestPanelGeometry:
    """Tests for PanelGeometry dataclass.

    PanelGeometry stores size (width, height) and position (x, y) for panels.
    Used for both docked panels (size only relevant) and floating panels
    (both size and position relevant).
    """

    def test_panel_geometry_default_values(self) -> None:
        """Test PanelGeometry has zero defaults for all fields."""
        from ink.presentation.state.panel_state import PanelGeometry

        geom = PanelGeometry()
        assert geom.width == 0
        assert geom.height == 0
        assert geom.x == 0
        assert geom.y == 0

    def test_panel_geometry_with_size(self) -> None:
        """Test PanelGeometry can be created with size values."""
        from ink.presentation.state.panel_state import PanelGeometry

        geom = PanelGeometry(width=200, height=300)
        assert geom.width == 200
        assert geom.height == 300
        assert geom.x == 0  # Still default
        assert geom.y == 0

    def test_panel_geometry_with_all_values(self) -> None:
        """Test PanelGeometry with all fields specified."""
        from ink.presentation.state.panel_state import PanelGeometry

        geom = PanelGeometry(width=400, height=600, x=100, y=50)
        assert geom.width == 400
        assert geom.height == 600
        assert geom.x == 100
        assert geom.y == 50

    def test_panel_geometry_equality(self) -> None:
        """Test PanelGeometry instances are equal when values match."""
        from ink.presentation.state.panel_state import PanelGeometry

        geom1 = PanelGeometry(width=200, height=300, x=10, y=20)
        geom2 = PanelGeometry(width=200, height=300, x=10, y=20)
        assert geom1 == geom2

    def test_panel_geometry_inequality(self) -> None:
        """Test PanelGeometry instances are not equal when values differ."""
        from ink.presentation.state.panel_state import PanelGeometry

        geom1 = PanelGeometry(width=200, height=300)
        geom2 = PanelGeometry(width=201, height=300)
        assert geom1 != geom2


class TestPanelInfo:
    """Tests for PanelInfo dataclass.

    PanelInfo stores complete metadata for a single panel, including name,
    visibility, dock area, floating state, geometry, and tab group.
    """

    def test_panel_info_with_name_only(self) -> None:
        """Test PanelInfo can be created with just a name (using defaults)."""
        from ink.presentation.state.panel_state import DockArea, PanelInfo

        info = PanelInfo(name="TestPanel")
        assert info.name == "TestPanel"
        assert info.visible is True  # Default
        assert info.area == DockArea.LEFT  # Default
        assert info.is_floating is False  # Default
        assert info.tab_group is None  # Default

    def test_panel_info_default_geometry(self) -> None:
        """Test PanelInfo has default geometry when not specified."""
        from ink.presentation.state.panel_state import PanelGeometry, PanelInfo

        info = PanelInfo(name="TestPanel")
        # Should have a PanelGeometry with default values
        assert isinstance(info.geometry, PanelGeometry)
        assert info.geometry.width == 0
        assert info.geometry.height == 0

    def test_panel_info_with_visibility(self) -> None:
        """Test PanelInfo visibility can be set to False."""
        from ink.presentation.state.panel_state import PanelInfo

        info = PanelInfo(name="HiddenPanel", visible=False)
        assert info.visible is False

    def test_panel_info_with_area(self) -> None:
        """Test PanelInfo dock area can be customized."""
        from ink.presentation.state.panel_state import DockArea, PanelInfo

        info = PanelInfo(name="RightPanel", area=DockArea.RIGHT)
        assert info.area == DockArea.RIGHT

    def test_panel_info_with_floating(self) -> None:
        """Test PanelInfo floating state can be set."""
        from ink.presentation.state.panel_state import DockArea, PanelInfo

        info = PanelInfo(name="FloatingPanel", is_floating=True, area=DockArea.FLOATING)
        assert info.is_floating is True
        assert info.area == DockArea.FLOATING

    def test_panel_info_with_geometry(self) -> None:
        """Test PanelInfo can have custom geometry."""
        from ink.presentation.state.panel_state import PanelGeometry, PanelInfo

        geom = PanelGeometry(width=400, height=500, x=100, y=100)
        info = PanelInfo(name="SizedPanel", geometry=geom)
        assert info.geometry.width == 400
        assert info.geometry.height == 500

    def test_panel_info_with_tab_group(self) -> None:
        """Test PanelInfo can have a tab group identifier."""
        from ink.presentation.state.panel_state import PanelInfo

        info = PanelInfo(name="TabbedPanel", tab_group="group1")
        assert info.tab_group == "group1"


class TestPanelState:
    """Tests for PanelState dataclass.

    PanelState aggregates multiple PanelInfo objects and stores Qt's native
    state blobs for accurate restoration.
    """

    def test_panel_state_empty_by_default(self) -> None:
        """Test PanelState has empty panels dict by default."""
        from ink.presentation.state.panel_state import PanelState

        state = PanelState()
        assert state.panels == {}
        assert state.qt_state is None
        assert state.qt_geometry is None

    def test_panel_state_with_panels(self) -> None:
        """Test PanelState can be created with panels dictionary."""
        from ink.presentation.state.panel_state import PanelInfo, PanelState

        panels = {
            "Hierarchy": PanelInfo(name="Hierarchy"),
            "Properties": PanelInfo(name="Properties"),
        }
        state = PanelState(panels=panels)
        assert len(state.panels) == 2
        assert "Hierarchy" in state.panels
        assert "Properties" in state.panels

    def test_panel_state_with_qt_blobs(self) -> None:
        """Test PanelState can store Qt state blobs."""
        from ink.presentation.state.panel_state import PanelState

        qt_state = QByteArray(b"state_data")
        qt_geometry = QByteArray(b"geometry_data")
        state = PanelState(qt_state=qt_state, qt_geometry=qt_geometry)
        assert state.qt_state == qt_state
        assert state.qt_geometry == qt_geometry

    def test_panel_state_get_panel_exists(self) -> None:
        """Test get_panel returns PanelInfo when panel exists."""
        from ink.presentation.state.panel_state import PanelInfo, PanelState

        panels = {"TestPanel": PanelInfo(name="TestPanel", visible=False)}
        state = PanelState(panels=panels)

        result = state.get_panel("TestPanel")
        assert result is not None
        assert result.name == "TestPanel"
        assert result.visible is False

    def test_panel_state_get_panel_not_exists(self) -> None:
        """Test get_panel returns None when panel doesn't exist."""
        from ink.presentation.state.panel_state import PanelState

        state = PanelState()
        result = state.get_panel("NonExistent")
        assert result is None

    def test_panel_state_set_panel_visible(self) -> None:
        """Test set_panel_visible updates visibility state."""
        from ink.presentation.state.panel_state import PanelInfo, PanelState

        panels = {"TestPanel": PanelInfo(name="TestPanel", visible=True)}
        state = PanelState(panels=panels)

        state.set_panel_visible("TestPanel", False)
        assert state.panels["TestPanel"].visible is False

    def test_panel_state_set_panel_visible_nonexistent(self) -> None:
        """Test set_panel_visible does nothing for non-existent panel."""
        from ink.presentation.state.panel_state import PanelState

        state = PanelState()
        # Should not raise an error
        state.set_panel_visible("NonExistent", False)
        # Panels dict still empty
        assert state.panels == {}

    def test_panel_state_is_panel_visible_true(self) -> None:
        """Test is_panel_visible returns True for visible panel."""
        from ink.presentation.state.panel_state import PanelInfo, PanelState

        panels = {"VisiblePanel": PanelInfo(name="VisiblePanel", visible=True)}
        state = PanelState(panels=panels)
        assert state.is_panel_visible("VisiblePanel") is True

    def test_panel_state_is_panel_visible_false(self) -> None:
        """Test is_panel_visible returns False for hidden panel."""
        from ink.presentation.state.panel_state import PanelInfo, PanelState

        panels = {"HiddenPanel": PanelInfo(name="HiddenPanel", visible=False)}
        state = PanelState(panels=panels)
        assert state.is_panel_visible("HiddenPanel") is False

    def test_panel_state_is_panel_visible_nonexistent(self) -> None:
        """Test is_panel_visible returns False for non-existent panel."""
        from ink.presentation.state.panel_state import PanelState

        state = PanelState()
        assert state.is_panel_visible("NonExistent") is False
