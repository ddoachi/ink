"""Dialog components for the Ink presentation layer.

This package contains dialog windows for user interaction, including:
- KeyboardShortcutsDialog: Shows all keyboard shortcuts organized by category
- NetClassificationDialog: Edits power/ground net classification settings

Design Decisions:
    - Dialogs are separate from the main window for modularity
    - Each dialog is a self-contained class with its own layout
    - Dialogs use standard Qt dialog patterns (QDialog base class)

See Also:
    - E06-F02-T04: View and Help menu actions requiring dialogs
    - E01-F01-T06: Net classification configuration
"""

from ink.presentation.dialogs.net_classification_dialog import (
    NetClassificationDialog,
)
from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

__all__ = ["KeyboardShortcutsDialog", "NetClassificationDialog"]
