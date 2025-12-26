"""Integration tests for InkMainWindow with SchematicCanvas.

Tests verify the integration between main window and central canvas widget
as specified in E06-F01-T02:
- Main window has canvas as central widget
- Canvas parent is correctly set to main window
- Canvas fills the central area properly
- Schematic canvas attribute is accessible

These integration tests verify components work together correctly.

See Also:
    - Spec E06-F01-T02 for central widget requirements
    - Spec E06-F06-T03 for recent files menu requirements
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.canvas import SchematicCanvas
from ink.presentation.main_window import InkMainWindow

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from pytestqt.qtbot import QtBot


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide isolated QSettings storage for each test.

    Args:
        tmp_path: Pytest-provided temporary directory (unique per test).

    Yields:
        Path to temporary settings directory.
    """
    settings_path = tmp_path / "settings"
    settings_path.mkdir()

    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.clear()
    temp_settings.sync()

    yield settings_path


@pytest.fixture
def app_settings(isolated_settings: Path) -> AppSettings:
    """Create AppSettings instance with isolated storage.

    Args:
        isolated_settings: Temporary settings directory (ensures isolation).

    Returns:
        Fresh AppSettings instance.
    """
    return AppSettings()


# =============================================================================
# Test Classes
# =============================================================================


class TestMainWindowCentralWidget:
    """Tests for central widget integration."""

    def test_main_window_has_central_widget(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test main window has a central widget set.

        Central widget is required for QMainWindow to display primary content.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        central = window.centralWidget()

        assert central is not None

    def test_central_widget_is_schematic_canvas(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test central widget is a SchematicCanvas instance.

        SchematicCanvas is the designated primary workspace for schematics.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        central = window.centralWidget()

        assert isinstance(central, SchematicCanvas)

    def test_schematic_canvas_attribute_exists(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test main window has schematic_canvas attribute.

        Attribute provides direct access to canvas for signal connections.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert hasattr(window, "schematic_canvas")
        assert window.schematic_canvas is not None

    def test_central_widget_matches_attribute(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test centralWidget() returns same object as schematic_canvas.

        Both access methods should reference the same canvas instance.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        assert window.centralWidget() is window.schematic_canvas


class TestCanvasParentRelationship:
    """Tests for Qt parent-child relationship."""

    def test_canvas_parent_is_main_window(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test canvas parent is set to main window.

        Qt ownership: parent automatically deletes children on destruction.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Note: centralWidget's parent is the window, verified via parent()
        assert window.schematic_canvas.parent() == window

    def test_canvas_is_child_of_main_window(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test canvas appears in main window's children.

        Verifies proper Qt object hierarchy.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        # Canvas should be findable as child
        canvases = window.findChildren(SchematicCanvas)

        assert len(canvases) == 1
        assert canvases[0] is window.schematic_canvas


class TestCanvasVisibility:
    """Tests for canvas visibility in main window."""

    def test_canvas_visible_when_window_shown(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test canvas becomes visible when main window is shown.

        Central widget should automatically become visible with parent.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        window.show()
        qtbot.waitExposed(window)

        assert window.schematic_canvas.isVisible()

    def test_canvas_geometry_is_reasonable(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test canvas has non-zero dimensions when window is shown.

        Canvas should expand to fill available central area.
        """
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        window.show()
        qtbot.waitExposed(window)

        canvas = window.schematic_canvas

        # Canvas should have meaningful size (at least 100x100)
        assert canvas.width() > 100
        assert canvas.height() > 100
