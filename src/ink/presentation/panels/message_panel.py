"""Message panel widget for log and search results display.

This module provides the MessagePanel class, a placeholder widget that
will be replaced with a full search/log panel in E04-F03.

Design Decisions:
    - Minimal placeholder with centered text for clear identification
    - Inherits from QWidget as placeholder is simpler than full view
    - Clear reference to future implementation epic in placeholder text
    - Styled text to appear as placeholder, not active content
    - Provides focus_search_input() method for Edit > Find action (E06-F02-T03)

See Also:
    - Spec E06-F01-T03 for dock widget requirements
    - Spec E04-F03 for full message panel implementation
    - Spec E06-F02-T03 for Edit menu Find action integration
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QVBoxLayout, QWidget


class MessagePanel(QWidget):
    """Message log and search results panel.

    Placeholder for MVP main window setup. This widget displays centered
    text indicating the panel purpose and referencing the epic where full
    implementation will occur.

    The message panel will eventually show:
    - Search query input and results list
    - Application log messages
    - Status updates and notifications
    - Navigation history

    Provides a search input field at the top for the Edit > Find action
    (E06-F02-T03) to focus when invoked. This provides basic search
    infrastructure that will be enhanced in E05-F01.

    Attributes:
        search_input: QLineEdit for search queries (placeholder for E05-F01).

    Example:
        >>> from ink.presentation.panels import MessagePanel
        >>> panel = MessagePanel()
        >>> panel.focus_search_input()  # Set focus to search field
        >>> panel.show()

    Notes:
        Will be replaced with full search/log panel in E04-F03.
        The replacement will maintain the same class name and import path
        to avoid breaking changes to InkMainWindow.
    """

    # Type hint for search input widget
    search_input: QLineEdit

    # Placeholder text with implementation reference
    _PLACEHOLDER_TEXT: str = "Message Panel\n(Implementation: E04-F03)"

    # Style for placeholder appearance - gray color indicates inactive
    _PLACEHOLDER_STYLE: str = "QLabel { color: #666; padding: 10px; }"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize message panel placeholder.

        Creates a simple centered label with placeholder text indicating
        the panel purpose and future implementation epic.

        Args:
            parent: Parent widget, typically InkMainWindow. When parent
                is destroyed, this panel is automatically cleaned up.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup placeholder UI with search input and centered label.

        Creates a vertical box layout containing:
        1. Search input field at the top for Edit > Find action (E06-F02-T03)
        2. Placeholder label indicating future implementation

        The layout structure:
            QVBoxLayout
                ├── QLineEdit (search input - for Ctrl+F focus)
                └── QLabel (centered, styled placeholder text)

        Design Decision:
            The search input is added here to support the Edit > Find action
            (E06-F02-T03) before the full search panel is implemented in E05-F01.
            This provides basic search infrastructure that will be enhanced later.
        """
        # Create layout - QVBoxLayout allows vertical expansion
        layout = QVBoxLayout(self)

        # =====================================================================
        # Search Input (E06-F02-T03)
        # Provides input field for Edit > Find action (Ctrl+F) to focus.
        # This is placeholder infrastructure for E05-F01 search panel.
        # =====================================================================
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search cells, nets, or ports...")
        self.search_input.setClearButtonEnabled(True)
        layout.addWidget(self.search_input)

        # Create placeholder label with multi-line text
        placeholder = QLabel(self._PLACEHOLDER_TEXT, self)

        # Center the text horizontally and vertically
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Apply gray color style to indicate placeholder status
        placeholder.setStyleSheet(self._PLACEHOLDER_STYLE)

        # Add label to layout - it will expand to fill available space
        layout.addWidget(placeholder)

    def focus_search_input(self) -> None:
        """Set focus to the search input field.

        Called by InkMainWindow._on_find() when the user triggers
        Edit > Find (Ctrl+F). This provides quick keyboard access
        to search functionality.

        Behavior:
            1. Sets keyboard focus to the search input field
            2. Selects any existing text for easy replacement

        This allows the user to immediately start typing their search
        query after pressing Ctrl+F.

        See Also:
            - E06-F02-T03: Edit menu Find action implementation
            - E05-F01: Full search panel implementation (future)
        """
        # Set keyboard focus to the search input
        self.search_input.setFocus()

        # Select all existing text so user can type to replace
        # This is the standard behavior for find dialogs
        self.search_input.selectAll()
