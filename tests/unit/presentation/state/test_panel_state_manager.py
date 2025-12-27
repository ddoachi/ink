"""Unit tests for PanelStateManager.

This module tests the PanelStateManager class that tracks dock widget state
changes via Qt signals. Tests use mocked QDockWidget and QMainWindow to
isolate the manager logic from Qt's internal behavior.

Test Coverage:
    - Panel registration and initial state capture
    - Signal connection for visibility, floating, and location changes
    - Signal handlers updating internal state
    - Signal emission on state changes
    - Area conversion utilities

TDD Phase: RED - These tests should fail initially until implementation is complete.

See Also:
    - Spec E06-F05-T01 for panel state management requirements
    - Pre-docs E06-F05-T01 for architecture decisions
"""

from __future__ import annotations

from unittest.mock import MagicMock

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget, QMainWindow


class TestPanelStateManagerCreation:
    """Tests for PanelStateManager instantiation."""

    def test_can_create_manager_with_main_window(self) -> None:
        """Test manager can be created with a QMainWindow reference."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        assert manager is not None
        assert manager.main_window is main_window

    def test_manager_has_empty_state_initially(self) -> None:
        """Test manager starts with empty PanelState."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        assert len(manager.state.panels) == 0
        assert manager.state.qt_state is None
        assert manager.state.qt_geometry is None

    def test_manager_has_empty_dock_widgets_initially(self) -> None:
        """Test manager starts with no registered dock widgets."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        # Access internal _dock_widgets dict
        assert len(manager._dock_widgets) == 0


class TestPanelStateManagerSignals:
    """Tests for PanelStateManager custom signals."""

    def test_manager_has_state_changed_signal(self) -> None:
        """Test manager has state_changed signal."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        # Check signal exists on class
        assert hasattr(PanelStateManager, "state_changed")

    def test_manager_has_panel_visibility_changed_signal(self) -> None:
        """Test manager has panel_visibility_changed signal."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        assert hasattr(PanelStateManager, "panel_visibility_changed")

    def test_manager_has_panel_area_changed_signal(self) -> None:
        """Test manager has panel_area_changed signal."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        assert hasattr(PanelStateManager, "panel_area_changed")


class TestPanelRegistration:
    """Tests for panel registration functionality."""

    def test_register_panel_adds_to_dock_widgets(self) -> None:
        """Test register_panel adds dock widget to internal dict."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        main_window.dockWidgetArea.return_value = Qt.DockWidgetArea.LeftDockWidgetArea
        manager = PanelStateManager(main_window)

        dock = MagicMock(spec=QDockWidget)
        dock.isVisible.return_value = True
        dock.isFloating.return_value = False
        mock_geom = MagicMock()
        mock_geom.width.return_value = 200
        mock_geom.height.return_value = 300
        mock_geom.x.return_value = 0
        mock_geom.y.return_value = 0
        dock.geometry.return_value = mock_geom

        manager.register_panel("TestPanel", dock)

        assert "TestPanel" in manager._dock_widgets
        assert manager._dock_widgets["TestPanel"] is dock

    def test_register_panel_creates_panel_info(self) -> None:
        """Test register_panel creates PanelInfo in state."""
        from ink.presentation.state.panel_state import DockArea
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        main_window.dockWidgetArea.return_value = Qt.DockWidgetArea.LeftDockWidgetArea
        manager = PanelStateManager(main_window)

        dock = MagicMock(spec=QDockWidget)
        dock.isVisible.return_value = True
        dock.isFloating.return_value = False
        mock_geom = MagicMock()
        mock_geom.width.return_value = 200
        mock_geom.height.return_value = 300
        mock_geom.x.return_value = 0
        mock_geom.y.return_value = 0
        dock.geometry.return_value = mock_geom

        manager.register_panel("TestPanel", dock)

        assert "TestPanel" in manager.state.panels
        panel_info = manager.state.panels["TestPanel"]
        assert panel_info.name == "TestPanel"
        assert panel_info.visible is True
        assert panel_info.area == DockArea.LEFT

    def test_register_panel_captures_visibility(self) -> None:
        """Test register_panel captures current visibility state."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        main_window.dockWidgetArea.return_value = Qt.DockWidgetArea.RightDockWidgetArea
        manager = PanelStateManager(main_window)

        dock = MagicMock(spec=QDockWidget)
        dock.isVisible.return_value = False  # Hidden panel
        dock.isFloating.return_value = False
        mock_geom = MagicMock()
        mock_geom.width.return_value = 200
        mock_geom.height.return_value = 300
        mock_geom.x.return_value = 0
        mock_geom.y.return_value = 0
        dock.geometry.return_value = mock_geom

        manager.register_panel("HiddenPanel", dock)

        assert manager.state.panels["HiddenPanel"].visible is False

    def test_register_panel_captures_floating_state(self) -> None:
        """Test register_panel captures floating state."""
        from ink.presentation.state.panel_state import DockArea
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        dock = MagicMock(spec=QDockWidget)
        dock.isVisible.return_value = True
        dock.isFloating.return_value = True  # Floating panel
        mock_geom = MagicMock()
        mock_geom.width.return_value = 400
        mock_geom.height.return_value = 500
        mock_geom.x.return_value = 100
        mock_geom.y.return_value = 100
        dock.geometry.return_value = mock_geom

        manager.register_panel("FloatingPanel", dock)

        panel_info = manager.state.panels["FloatingPanel"]
        assert panel_info.is_floating is True
        assert panel_info.area == DockArea.FLOATING

    def test_register_panel_captures_geometry(self) -> None:
        """Test register_panel captures panel geometry."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        main_window.dockWidgetArea.return_value = Qt.DockWidgetArea.BottomDockWidgetArea
        manager = PanelStateManager(main_window)

        dock = MagicMock(spec=QDockWidget)
        dock.isVisible.return_value = True
        dock.isFloating.return_value = False
        mock_geom = MagicMock()
        mock_geom.width.return_value = 500
        mock_geom.height.return_value = 150
        mock_geom.x.return_value = 10
        mock_geom.y.return_value = 20
        dock.geometry.return_value = mock_geom

        manager.register_panel("SizedPanel", dock)

        panel_info = manager.state.panels["SizedPanel"]
        assert panel_info.geometry.width == 500
        assert panel_info.geometry.height == 150
        assert panel_info.geometry.x == 10
        assert panel_info.geometry.y == 20

    def test_register_panel_connects_signals(self) -> None:
        """Test register_panel connects to dock widget signals."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        main_window.dockWidgetArea.return_value = Qt.DockWidgetArea.LeftDockWidgetArea
        manager = PanelStateManager(main_window)

        dock = MagicMock(spec=QDockWidget)
        dock.isVisible.return_value = True
        dock.isFloating.return_value = False
        mock_geom = MagicMock()
        mock_geom.width.return_value = 200
        mock_geom.height.return_value = 300
        mock_geom.x.return_value = 0
        mock_geom.y.return_value = 0
        dock.geometry.return_value = mock_geom

        # Create mock signals
        visibility_signal = MagicMock()
        toplevel_signal = MagicMock()
        location_signal = MagicMock()

        dock.visibilityChanged = visibility_signal
        dock.topLevelChanged = toplevel_signal
        dock.dockLocationChanged = location_signal

        manager.register_panel("SignalPanel", dock)

        # Check signals were connected
        visibility_signal.connect.assert_called_once()
        toplevel_signal.connect.assert_called_once()
        location_signal.connect.assert_called_once()


class TestDockAreaConversion:
    """Tests for Qt dock area to DockArea enum conversion."""

    def test_left_area_conversion(self) -> None:
        """Test conversion of Left dock area."""
        from ink.presentation.state.panel_state import DockArea
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        result = manager._qt_area_to_dock_area(Qt.DockWidgetArea.LeftDockWidgetArea)
        assert result == DockArea.LEFT

    def test_right_area_conversion(self) -> None:
        """Test conversion of Right dock area."""
        from ink.presentation.state.panel_state import DockArea
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        result = manager._qt_area_to_dock_area(Qt.DockWidgetArea.RightDockWidgetArea)
        assert result == DockArea.RIGHT

    def test_bottom_area_conversion(self) -> None:
        """Test conversion of Bottom dock area."""
        from ink.presentation.state.panel_state import DockArea
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        result = manager._qt_area_to_dock_area(Qt.DockWidgetArea.BottomDockWidgetArea)
        assert result == DockArea.BOTTOM

    def test_unknown_area_defaults_to_left(self) -> None:
        """Test unknown dock area defaults to LEFT."""
        from ink.presentation.state.panel_state import DockArea
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        # TopDockWidgetArea is not in our mapping
        result = manager._qt_area_to_dock_area(Qt.DockWidgetArea.TopDockWidgetArea)
        assert result == DockArea.LEFT


class TestVisibilitySignalHandling:
    """Tests for visibility change signal handling."""

    def test_visibility_change_updates_state(self) -> None:
        """Test visibility change updates panel state."""
        from ink.presentation.state.panel_state import PanelInfo
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        # Manually add panel to state
        manager.state.panels["TestPanel"] = PanelInfo(name="TestPanel", visible=True)

        # Simulate visibility change
        manager._on_visibility_changed("TestPanel", False)

        assert manager.state.panels["TestPanel"].visible is False

    def test_visibility_change_emits_signal(self) -> None:
        """Test visibility change emits panel_visibility_changed signal."""
        from ink.presentation.state.panel_state import PanelInfo
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)
        manager.state.panels["TestPanel"] = PanelInfo(name="TestPanel", visible=True)

        # Connect a mock to the signal
        signal_handler = MagicMock()
        manager.panel_visibility_changed.connect(signal_handler)

        manager._on_visibility_changed("TestPanel", False)

        signal_handler.assert_called_once_with("TestPanel", False)

    def test_visibility_change_emits_state_changed(self) -> None:
        """Test visibility change emits state_changed signal."""
        from ink.presentation.state.panel_state import PanelInfo
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)
        manager.state.panels["TestPanel"] = PanelInfo(name="TestPanel", visible=True)

        signal_handler = MagicMock()
        manager.state_changed.connect(signal_handler)

        manager._on_visibility_changed("TestPanel", False)

        signal_handler.assert_called_once()


class TestFloatingSignalHandling:
    """Tests for floating state change signal handling."""

    def test_floating_change_updates_state(self) -> None:
        """Test floating change updates panel state."""
        from ink.presentation.state.panel_state import DockArea, PanelInfo
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)
        manager.state.panels["TestPanel"] = PanelInfo(name="TestPanel", is_floating=False)

        manager._on_floating_changed("TestPanel", True)

        assert manager.state.panels["TestPanel"].is_floating is True
        assert manager.state.panels["TestPanel"].area == DockArea.FLOATING

    def test_floating_to_docked_change(self) -> None:
        """Test floating to docked state change."""
        from ink.presentation.state.panel_state import DockArea, PanelInfo
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)
        manager.state.panels["TestPanel"] = PanelInfo(
            name="TestPanel", is_floating=True, area=DockArea.FLOATING
        )

        manager._on_floating_changed("TestPanel", False)

        assert manager.state.panels["TestPanel"].is_floating is False
        # Note: area will be updated by dockLocationChanged signal

    def test_floating_change_emits_state_changed(self) -> None:
        """Test floating change emits state_changed signal."""
        from ink.presentation.state.panel_state import PanelInfo
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)
        manager.state.panels["TestPanel"] = PanelInfo(name="TestPanel", is_floating=False)

        signal_handler = MagicMock()
        manager.state_changed.connect(signal_handler)

        manager._on_floating_changed("TestPanel", True)

        signal_handler.assert_called_once()


class TestLocationSignalHandling:
    """Tests for dock location change signal handling."""

    def test_location_change_updates_state(self) -> None:
        """Test dock location change updates panel state."""
        from ink.presentation.state.panel_state import DockArea, PanelInfo
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)
        manager.state.panels["TestPanel"] = PanelInfo(name="TestPanel", area=DockArea.LEFT)

        manager._on_location_changed("TestPanel", Qt.DockWidgetArea.RightDockWidgetArea)

        assert manager.state.panels["TestPanel"].area == DockArea.RIGHT

    def test_location_change_emits_panel_area_changed(self) -> None:
        """Test location change emits panel_area_changed signal."""
        from ink.presentation.state.panel_state import DockArea, PanelInfo
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)
        manager.state.panels["TestPanel"] = PanelInfo(name="TestPanel", area=DockArea.LEFT)

        signal_handler = MagicMock()
        manager.panel_area_changed.connect(signal_handler)

        manager._on_location_changed("TestPanel", Qt.DockWidgetArea.BottomDockWidgetArea)

        signal_handler.assert_called_once_with("TestPanel", DockArea.BOTTOM)

    def test_location_change_emits_state_changed(self) -> None:
        """Test location change emits state_changed signal."""
        from ink.presentation.state.panel_state import DockArea, PanelInfo
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)
        manager.state.panels["TestPanel"] = PanelInfo(name="TestPanel", area=DockArea.LEFT)

        signal_handler = MagicMock()
        manager.state_changed.connect(signal_handler)

        manager._on_location_changed("TestPanel", Qt.DockWidgetArea.RightDockWidgetArea)

        signal_handler.assert_called_once()


class TestGetDockArea:
    """Tests for _get_dock_area helper method."""

    def test_get_dock_area_for_floating_panel(self) -> None:
        """Test _get_dock_area returns FLOATING for floating panels."""
        from ink.presentation.state.panel_state import DockArea
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        dock = MagicMock(spec=QDockWidget)
        dock.isFloating.return_value = True

        result = manager._get_dock_area(dock)
        assert result == DockArea.FLOATING

    def test_get_dock_area_for_docked_panel(self) -> None:
        """Test _get_dock_area returns correct area for docked panels."""
        from ink.presentation.state.panel_state import DockArea
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        main_window.dockWidgetArea.return_value = Qt.DockWidgetArea.RightDockWidgetArea
        manager = PanelStateManager(main_window)

        dock = MagicMock(spec=QDockWidget)
        dock.isFloating.return_value = False

        result = manager._get_dock_area(dock)
        assert result == DockArea.RIGHT
        main_window.dockWidgetArea.assert_called_once_with(dock)


class TestGetPanelGeometry:
    """Tests for _get_panel_geometry helper method."""

    def test_get_panel_geometry_extracts_all_values(self) -> None:
        """Test _get_panel_geometry extracts width, height, x, y."""
        from ink.presentation.state.panel_state_manager import PanelStateManager

        main_window = MagicMock(spec=QMainWindow)
        manager = PanelStateManager(main_window)

        dock = MagicMock(spec=QDockWidget)
        mock_geom = MagicMock()
        mock_geom.width.return_value = 300
        mock_geom.height.return_value = 400
        mock_geom.x.return_value = 50
        mock_geom.y.return_value = 75
        dock.geometry.return_value = mock_geom

        result = manager._get_panel_geometry(dock)

        assert result.width == 300
        assert result.height == 400
        assert result.x == 50
        assert result.y == 75
