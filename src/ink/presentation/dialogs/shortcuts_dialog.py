"""Keyboard shortcuts dialog for the Ink application.

This module provides the KeyboardShortcutsDialog class that displays all
available keyboard shortcuts organized by category (File, Edit, View, etc.).

The dialog is accessible via Help > Keyboard Shortcuts or F1 shortcut.

Design Decisions:
    - Uses QTextBrowser for rich HTML content with tables
    - Organized by menu category for easy reference
    - Close button at bottom for easy dismissal
    - Minimum size of 500x400 ensures readability

See Also:
    - Spec E06-F02-T04 for keyboard shortcuts dialog requirements
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QPushButton, QTextBrowser, QVBoxLayout, QWidget


class KeyboardShortcutsDialog(QDialog):
    """Dialog showing all keyboard shortcuts.

    Displays keyboard shortcuts organized by category:
    - File Menu: Open, Exit
    - Edit Menu: Undo, Redo, Find
    - View Menu: Zoom In, Zoom Out, Fit View
    - Canvas Interaction: Double-click, right-click, scroll
    - Help: F1 for this dialog

    The dialog uses HTML tables for clean formatting and is styled
    to be readable and professional.

    Attributes:
        browser: QTextBrowser displaying the shortcuts HTML content.
        close_btn: QPushButton to dismiss the dialog.

    Example:
        >>> from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog
        >>> dialog = KeyboardShortcutsDialog(parent_window)
        >>> dialog.exec()

    See Also:
        - E06-F02-T04: Help menu Keyboard Shortcuts action
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the keyboard shortcuts dialog.

        Args:
            parent: Optional parent widget (typically the main window).
        """
        super().__init__(parent)

        # Set dialog properties
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(500, 400)

        # Create layout
        layout = QVBoxLayout(self)

        # Create text browser for HTML content
        # QTextBrowser is read-only by default and supports rich HTML
        browser = QTextBrowser()
        browser.setHtml(self._get_shortcuts_html())
        browser.setOpenExternalLinks(False)  # Prevent clicking links
        layout.addWidget(browser)

        # Create close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _get_shortcuts_html(self) -> str:
        """Generate HTML content for the shortcuts display.

        Returns:
            HTML string with all keyboard shortcuts organized by category.

        The content is structured with:
        - Main heading
        - Category headings (h3)
        - Tables with two columns: shortcut and description
        - Consistent styling for readability
        """
        return """
        <style>
            h2 { color: #333; margin-bottom: 16px; }
            h3 {
                color: #555;
                margin-top: 20px;
                margin-bottom: 8px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 4px;
            }
            table { border-collapse: collapse; width: 100%; margin-bottom: 12px; }
            td { padding: 6px 12px; }
            td:first-child { font-weight: bold; width: 140px; color: #0066cc; }
            td:last-child { color: #444; }
            tr:nth-child(even) { background-color: #f8f8f8; }
        </style>

        <h2>Keyboard Shortcuts</h2>

        <h3>File Menu</h3>
        <table>
            <tr><td>Ctrl+O</td><td>Open netlist file</td></tr>
            <tr><td>Ctrl+Q</td><td>Exit application</td></tr>
        </table>

        <h3>Edit Menu</h3>
        <table>
            <tr><td>Ctrl+Z</td><td>Undo last action</td></tr>
            <tr><td>Ctrl+Shift+Z</td><td>Redo last undone action</td></tr>
            <tr><td>Ctrl+F</td><td>Find (open search panel)</td></tr>
        </table>

        <h3>View Menu</h3>
        <table>
            <tr><td>Ctrl+=</td><td>Zoom in</td></tr>
            <tr><td>Ctrl+-</td><td>Zoom out</td></tr>
            <tr><td>Ctrl+0</td><td>Fit view to content</td></tr>
            <tr><td>Ctrl+Shift+H</td><td>Toggle Hierarchy panel</td></tr>
            <tr><td>Ctrl+Shift+P</td><td>Toggle Properties panel</td></tr>
            <tr><td>Ctrl+Shift+M</td><td>Toggle Messages panel</td></tr>
            <tr><td>Ctrl+Shift+R</td><td>Reset panel layout</td></tr>
        </table>

        <h3>Canvas Interaction</h3>
        <table>
            <tr><td>Double-click cell</td><td>Expand fanout/fanin</td></tr>
            <tr><td>Right-click</td><td>Context menu</td></tr>
            <tr><td>Mouse wheel</td><td>Zoom in/out</td></tr>
            <tr><td>Middle-click drag</td><td>Pan view</td></tr>
        </table>

        <h3>Help</h3>
        <table>
            <tr><td>F1</td><td>Show this help dialog</td></tr>
        </table>
        """
