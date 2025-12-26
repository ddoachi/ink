"""Unit tests for SchematicCanvas widget.

Tests verify the schematic canvas meets all requirements from spec E06-F01-T02:
- Canvas instantiation without errors
- Canvas accepts parent widget
- Placeholder UI is displayed correctly
- Proper layout with no margins

These tests run in TDD RED phase first (expecting failures), then GREEN after implementation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ink.presentation.canvas import SchematicCanvas

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


class TestSchematicCanvasCreation:
    """Tests for SchematicCanvas instantiation."""

    def test_canvas_can_be_created(self, qtbot: QtBot) -> None:
        """Test that SchematicCanvas can be instantiated without errors.

        Verifies:
        - No exceptions during construction
        - Returns a valid object instance
        """
        canvas = SchematicCanvas()
        qtbot.addWidget(canvas)

        assert canvas is not None

    def test_canvas_is_qwidget_subclass(self, qtbot: QtBot) -> None:
        """Test that SchematicCanvas inherits from QWidget.

        QWidget is appropriate for placeholder; E02 will use QGraphicsView.
        """
        canvas = SchematicCanvas()
        qtbot.addWidget(canvas)

        assert isinstance(canvas, QWidget)


class TestSchematicCanvasParent:
    """Tests for parent widget handling."""

    def test_canvas_accepts_parent_widget(self, qtbot: QtBot) -> None:
        """Test canvas can be created with a parent widget.

        Parent ownership is essential for Qt memory management -
        when parent is deleted, children are automatically deleted.
        """
        parent = QWidget()
        qtbot.addWidget(parent)

        canvas = SchematicCanvas(parent=parent)

        assert canvas.parent() == parent

    def test_canvas_without_parent_has_none_parent(self, qtbot: QtBot) -> None:
        """Test canvas created without parent has None parent.

        This is valid for top-level widgets or widgets added later.
        """
        canvas = SchematicCanvas()
        qtbot.addWidget(canvas)

        assert canvas.parent() is None


class TestSchematicCanvasLayout:
    """Tests for canvas layout configuration."""

    def test_canvas_has_vbox_layout(self, qtbot: QtBot) -> None:
        """Test canvas uses QVBoxLayout for child arrangement.

        VBoxLayout is simple and appropriate for centered placeholder.
        """
        canvas = SchematicCanvas()
        qtbot.addWidget(canvas)

        layout = canvas.layout()

        assert layout is not None
        assert isinstance(layout, QVBoxLayout)

    def test_canvas_layout_has_no_margins(self, qtbot: QtBot) -> None:
        """Test canvas layout has zero margins.

        Zero margins ensure canvas fills entire central area without gaps.
        """
        canvas = SchematicCanvas()
        qtbot.addWidget(canvas)

        layout = canvas.layout()
        assert layout is not None  # Layout should exist

        margins = layout.contentsMargins()

        assert margins.left() == 0
        assert margins.top() == 0
        assert margins.right() == 0
        assert margins.bottom() == 0


class TestSchematicCanvasPlaceholder:
    """Tests for placeholder UI elements."""

    def test_canvas_has_placeholder_label(self, qtbot: QtBot) -> None:
        """Test canvas contains a placeholder QLabel.

        Placeholder shows informative text until rendering is implemented.
        """
        canvas = SchematicCanvas()
        qtbot.addWidget(canvas)

        # Find QLabel child widget
        labels = canvas.findChildren(QLabel)

        assert len(labels) == 1

    def test_placeholder_text_contains_canvas_info(self, qtbot: QtBot) -> None:
        """Test placeholder shows schematic canvas description.

        Text should indicate this is the canvas area and reference E02.
        """
        canvas = SchematicCanvas()
        qtbot.addWidget(canvas)

        label = canvas.findChildren(QLabel)[0]
        text = label.text()

        assert "Schematic Canvas" in text or "schematic canvas" in text.lower()

    def test_placeholder_is_center_aligned(self, qtbot: QtBot) -> None:
        """Test placeholder label is center-aligned.

        Center alignment provides clear visual indication of canvas area.
        """
        canvas = SchematicCanvas()
        qtbot.addWidget(canvas)

        label = canvas.findChildren(QLabel)[0]
        alignment = label.alignment()

        assert alignment & Qt.AlignmentFlag.AlignCenter

    def test_placeholder_has_styling(self, qtbot: QtBot) -> None:
        """Test placeholder has stylesheet applied.

        Styling provides visual distinction from regular widgets.
        """
        canvas = SchematicCanvas()
        qtbot.addWidget(canvas)

        label = canvas.findChildren(QLabel)[0]
        stylesheet = label.styleSheet()

        # Should have some styling applied
        assert len(stylesheet) > 0
        assert "background-color" in stylesheet or "color" in stylesheet
