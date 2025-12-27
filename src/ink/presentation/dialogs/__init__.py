"""Dialog components for the Ink presentation layer.

This package contains dialog windows for user interaction, including:
- KeyboardShortcutsDialog: Shows all keyboard shortcuts organized by category

Design Decisions:
    - Dialogs are separate from the main window for modularity
    - Each dialog is a self-contained class with its own layout
    - Dialogs use standard Qt dialog patterns (QDialog base class)

See Also:
    - E06-F02-T04: View and Help menu actions requiring dialogs
"""

from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog

__all__ = ["KeyboardShortcutsDialog"]
