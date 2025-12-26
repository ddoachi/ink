#!/usr/bin/env python3
"""Temporary runner script for testing InkMainWindow.

This script will be replaced by src/ink/main.py in task E06-F01-T04.

Usage:
    uv run python run.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.main_window import InkMainWindow


def main() -> int:
    """Run the Ink application."""
    app = QApplication(sys.argv)
    settings = AppSettings()
    window = InkMainWindow(settings)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
