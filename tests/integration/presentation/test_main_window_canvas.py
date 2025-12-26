"""Integration tests for InkMainWindow with SchematicCanvas.

Tests verify the integration between main window and central canvas widget
as specified in E06-F01-T02:
- Main window has canvas as central widget
- Canvas parent is correctly set to main window
- Canvas fills the central area properly
- Schematic canvas attribute is accessible

These integration tests verify components work together correctly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ink.presentation.canvas import SchematicCanvas
from ink.presentation.main_window import InkMainWindow

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestMainWindowCentralWidget:
    """Tests for central widget integration."""

    def test_main_window_has_central_widget(self, qtbot: QtBot) -> None:
        """Test main window has a central widget set.

        Central widget is required for QMainWindow to display primary content.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        central = window.centralWidget()

        assert central is not None

    def test_central_widget_is_schematic_canvas(self, qtbot: QtBot) -> None:
        """Test central widget is a SchematicCanvas instance.

        SchematicCanvas is the designated primary workspace for schematics.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        central = window.centralWidget()

        assert isinstance(central, SchematicCanvas)

    def test_schematic_canvas_attribute_exists(self, qtbot: QtBot) -> None:
        """Test main window has schematic_canvas attribute.

        Attribute provides direct access to canvas for signal connections.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert hasattr(window, "schematic_canvas")
        assert window.schematic_canvas is not None

    def test_central_widget_matches_attribute(self, qtbot: QtBot) -> None:
        """Test centralWidget() returns same object as schematic_canvas.

        Both access methods should reference the same canvas instance.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        assert window.centralWidget() is window.schematic_canvas


class TestCanvasParentRelationship:
    """Tests for Qt parent-child relationship."""

    def test_canvas_parent_is_main_window(self, qtbot: QtBot) -> None:
        """Test canvas parent is set to main window.

        Qt ownership: parent automatically deletes children on destruction.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        # Note: centralWidget's parent is the window, verified via parent()
        assert window.schematic_canvas.parent() == window

    def test_canvas_is_child_of_main_window(self, qtbot: QtBot) -> None:
        """Test canvas appears in main window's children.

        Verifies proper Qt object hierarchy.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        # Canvas should be findable as child
        canvases = window.findChildren(SchematicCanvas)

        assert len(canvases) == 1
        assert canvases[0] is window.schematic_canvas


class TestCanvasVisibility:
    """Tests for canvas visibility in main window."""

    def test_canvas_visible_when_window_shown(self, qtbot: QtBot) -> None:
        """Test canvas becomes visible when main window is shown.

        Central widget should automatically become visible with parent.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        window.show()
        qtbot.waitExposed(window)

        assert window.schematic_canvas.isVisible()

    def test_canvas_geometry_is_reasonable(self, qtbot: QtBot) -> None:
        """Test canvas has non-zero dimensions when window is shown.

        Canvas should expand to fill available central area.
        """
        window = InkMainWindow()
        qtbot.addWidget(window)

        window.show()
        qtbot.waitExposed(window)

        canvas = window.schematic_canvas

        # Canvas should have meaningful size (at least 100x100)
        assert canvas.width() > 100
        assert canvas.height() > 100
