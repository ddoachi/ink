"""Hierarchy panel widget for design object tree navigation.

This module provides the HierarchyPanel class, a placeholder widget that
will be replaced with a full QTreeView-based hierarchy browser in E04-F01.

Design Decisions:
    - Minimal placeholder with centered text for clear identification
    - Inherits from QWidget (not QTreeView) as placeholder is simpler
    - Clear reference to future implementation epic in placeholder text
    - Styled text to appear as placeholder, not active content

See Also:
    - Spec E06-F01-T03 for dock widget requirements
    - Spec E04-F01 for full hierarchy panel implementation
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class HierarchyPanel(QWidget):
    """Design hierarchy and object tree panel.

    Placeholder for MVP main window setup. This widget displays centered
    text indicating the panel purpose and referencing the epic where full
    implementation will occur.

    The hierarchy panel will eventually show:
    - Design object tree (cells, nets, ports)
    - Expandable/collapsible hierarchy
    - Click-to-navigate functionality
    - Search and filter capabilities

    Attributes:
        None (placeholder has no meaningful state)

    Example:
        >>> from ink.presentation.panels import HierarchyPanel
        >>> panel = HierarchyPanel()
        >>> panel.show()

    Notes:
        Will be replaced with QTreeView in E04-F01 (Object Tree).
        The replacement will maintain the same class name and import path
        to avoid breaking changes to InkMainWindow.
    """

    # Placeholder text with implementation reference
    _PLACEHOLDER_TEXT: str = "Hierarchy Panel\n(Implementation: E04-F01)"

    # Style for placeholder appearance - gray color indicates inactive
    _PLACEHOLDER_STYLE: str = "QLabel { color: #666; padding: 10px; }"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize hierarchy panel placeholder.

        Creates a simple centered label with placeholder text indicating
        the panel purpose and future implementation epic.

        Args:
            parent: Parent widget, typically InkMainWindow. When parent
                is destroyed, this panel is automatically cleaned up.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup placeholder UI with centered label.

        Creates a vertical box layout containing a single centered label
        with placeholder text. The label is styled to appear as inactive
        placeholder content rather than functional UI.

        The layout structure:
            QVBoxLayout
                └── QLabel (centered, styled placeholder text)
        """
        # Create layout - QVBoxLayout allows vertical expansion
        layout = QVBoxLayout(self)

        # Create placeholder label with multi-line text
        placeholder = QLabel(self._PLACEHOLDER_TEXT, self)

        # Center the text horizontally and vertically
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Apply gray color style to indicate placeholder status
        placeholder.setStyleSheet(self._PLACEHOLDER_STYLE)

        # Add label to layout - it will expand to fill available space
        layout.addWidget(placeholder)
