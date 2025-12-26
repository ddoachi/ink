"""Pytest configuration and shared fixtures for Ink tests.

This module provides Qt-specific fixtures required for testing PySide6 widgets.
The pytest-qt plugin handles QApplication lifecycle automatically.

Environment Configuration:
    Sets QT_QPA_PLATFORM=offscreen for headless testing in CI/server environments.
    This allows Qt widget tests to run without a display server (X11/Wayland).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

# Set Qt to offscreen mode for headless testing
# This must be done before any Qt imports in test modules
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot


@pytest.fixture(scope="session")
def qapp_args() -> list[str]:
    """Provide command-line arguments for QApplication.

    Returns:
        Empty list for default Qt application behavior.
    """
    return []


@pytest.fixture
def qtbot_with_logging(qtbot: QtBot) -> QtBot:
    """QtBot fixture with enhanced logging for debugging.

    Args:
        qtbot: The pytest-qt QtBot fixture.

    Returns:
        The same QtBot instance (passthrough for now).
    """
    return qtbot
