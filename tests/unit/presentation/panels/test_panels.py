"""Unit tests for panel placeholder widgets.

This module tests the three placeholder panel widgets that provide
placeholder content for the dock widget areas:
- HierarchyPanel: Left dock area (future object tree)
- PropertyPanel: Right dock area (future property inspector)
- MessagePanel: Bottom dock area (future search/log panel)

Each panel should:
- Be instantiable without errors
- Accept an optional parent widget
- Display placeholder text indicating future implementation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from ink.presentation.panels import HierarchyPanel, MessagePanel, PropertyPanel

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture(scope="module")
def qapp() -> Generator[QApplication, None, None]:
    """Provide QApplication instance for Qt widget tests.

    Qt requires exactly one QApplication instance per process.
    This fixture ensures we reuse an existing instance or create a new one.
    """
    existing = QApplication.instance()
    if existing is not None and isinstance(existing, QApplication):
        yield existing
    else:
        app = QApplication([])
        yield app


class TestHierarchyPanel:
    """Tests for HierarchyPanel placeholder widget."""

    def test_hierarchy_panel_creation(self, qapp: QApplication) -> None:
        """Test hierarchy panel can be instantiated without parent."""
        panel = HierarchyPanel()
        assert panel is not None
        assert isinstance(panel, QWidget)

    def test_hierarchy_panel_with_parent(self, qapp: QApplication) -> None:
        """Test hierarchy panel accepts and sets parent correctly."""
        parent = QWidget()
        panel = HierarchyPanel(parent)
        assert panel.parent() == parent

    def test_hierarchy_panel_has_layout(self, qapp: QApplication) -> None:
        """Test hierarchy panel has a vertical box layout."""
        panel = HierarchyPanel()
        layout = panel.layout()
        assert layout is not None
        assert isinstance(layout, QVBoxLayout)

    def test_hierarchy_panel_has_placeholder_label(self, qapp: QApplication) -> None:
        """Test hierarchy panel displays placeholder text."""
        panel = HierarchyPanel()
        # Find label in layout
        layout = panel.layout()
        assert layout is not None
        assert layout.count() >= 1
        layout_item = layout.itemAt(0)
        assert layout_item is not None
        label_widget = layout_item.widget()
        assert isinstance(label_widget, QLabel)
        assert "Hierarchy" in label_widget.text()
        assert "E04-F01" in label_widget.text()

    def test_hierarchy_panel_label_centered(self, qapp: QApplication) -> None:
        """Test placeholder label is center-aligned."""
        panel = HierarchyPanel()
        layout = panel.layout()
        assert layout is not None
        layout_item = layout.itemAt(0)
        assert layout_item is not None
        label_widget = layout_item.widget()
        assert isinstance(label_widget, QLabel)
        alignment = label_widget.alignment()
        assert alignment & Qt.AlignmentFlag.AlignCenter


class TestPropertyPanel:
    """Tests for PropertyPanel placeholder widget."""

    def test_property_panel_creation(self, qapp: QApplication) -> None:
        """Test property panel can be instantiated without parent."""
        panel = PropertyPanel()
        assert panel is not None
        assert isinstance(panel, QWidget)

    def test_property_panel_with_parent(self, qapp: QApplication) -> None:
        """Test property panel accepts and sets parent correctly."""
        parent = QWidget()
        panel = PropertyPanel(parent)
        assert panel.parent() == parent

    def test_property_panel_has_layout(self, qapp: QApplication) -> None:
        """Test property panel has a vertical box layout."""
        panel = PropertyPanel()
        layout = panel.layout()
        assert layout is not None
        assert isinstance(layout, QVBoxLayout)

    def test_property_panel_has_placeholder_label(self, qapp: QApplication) -> None:
        """Test property panel displays placeholder text."""
        panel = PropertyPanel()
        layout = panel.layout()
        assert layout is not None
        assert layout.count() >= 1
        layout_item = layout.itemAt(0)
        assert layout_item is not None
        label_widget = layout_item.widget()
        assert isinstance(label_widget, QLabel)
        assert "Property" in label_widget.text()
        assert "E04-F04" in label_widget.text()

    def test_property_panel_label_centered(self, qapp: QApplication) -> None:
        """Test placeholder label is center-aligned."""
        panel = PropertyPanel()
        layout = panel.layout()
        assert layout is not None
        layout_item = layout.itemAt(0)
        assert layout_item is not None
        label_widget = layout_item.widget()
        assert isinstance(label_widget, QLabel)
        alignment = label_widget.alignment()
        assert alignment & Qt.AlignmentFlag.AlignCenter


class TestMessagePanel:
    """Tests for MessagePanel placeholder widget."""

    def test_message_panel_creation(self, qapp: QApplication) -> None:
        """Test message panel can be instantiated without parent."""
        panel = MessagePanel()
        assert panel is not None
        assert isinstance(panel, QWidget)

    def test_message_panel_with_parent(self, qapp: QApplication) -> None:
        """Test message panel accepts and sets parent correctly."""
        parent = QWidget()
        panel = MessagePanel(parent)
        assert panel.parent() == parent

    def test_message_panel_has_layout(self, qapp: QApplication) -> None:
        """Test message panel has a vertical box layout."""
        panel = MessagePanel()
        layout = panel.layout()
        assert layout is not None
        assert isinstance(layout, QVBoxLayout)

    def test_message_panel_has_placeholder_label(self, qapp: QApplication) -> None:
        """Test message panel displays placeholder text.

        Note: Layout structure is [QLineEdit (search), QLabel (placeholder)]
        since E06-F02-T03 added search input.
        """
        panel = MessagePanel()
        layout = panel.layout()
        assert layout is not None
        # Layout has 2 items: search input (index 0) + placeholder label (index 1)
        assert layout.count() >= 2
        label_item = layout.itemAt(1)  # Placeholder label is at index 1
        assert label_item is not None
        label_widget = label_item.widget()
        assert isinstance(label_widget, QLabel)
        assert "Message" in label_widget.text()
        assert "E04-F03" in label_widget.text()

    def test_message_panel_label_centered(self, qapp: QApplication) -> None:
        """Test placeholder label is center-aligned.

        Note: Layout structure is [QLineEdit (search), QLabel (placeholder)]
        since E06-F02-T03 added search input.
        """
        panel = MessagePanel()
        layout = panel.layout()
        assert layout is not None
        label_item = layout.itemAt(1)  # Placeholder label is at index 1
        assert label_item is not None
        label_widget = label_item.widget()
        assert isinstance(label_widget, QLabel)
        alignment = label_widget.alignment()
        assert alignment & Qt.AlignmentFlag.AlignCenter

    def test_message_panel_has_search_input(self, qapp: QApplication) -> None:
        """Test message panel has search input for Find action (E06-F02-T03)."""
        from PySide6.QtWidgets import QLineEdit

        panel = MessagePanel()
        # The search_input should be accessible as an attribute
        assert hasattr(panel, "search_input")
        assert isinstance(panel.search_input, QLineEdit)

    def test_message_panel_focus_search_input_method(self, qapp: QApplication) -> None:
        """Test message panel has focus_search_input method (E06-F02-T03)."""
        panel = MessagePanel()
        assert hasattr(panel, "focus_search_input")
        assert callable(panel.focus_search_input)


class TestPanelPackageExports:
    """Tests for panel package __init__.py exports."""

    def test_hierarchy_panel_exported(self) -> None:
        """Test HierarchyPanel is exported from panels package."""
        from ink.presentation.panels import HierarchyPanel as HP

        assert HP is HierarchyPanel

    def test_property_panel_exported(self) -> None:
        """Test PropertyPanel is exported from panels package."""
        from ink.presentation.panels import PropertyPanel as PP

        assert PP is PropertyPanel

    def test_message_panel_exported(self) -> None:
        """Test MessagePanel is exported from panels package."""
        from ink.presentation.panels import MessagePanel as MP

        assert MP is MessagePanel
