"""Unit tests for AppSettings window geometry persistence methods.

This module tests the window geometry persistence features added to AppSettings
for spec E06-F06-T02 - Window Geometry Persistence.

Test Strategy:
    - Test save/load methods for window geometry (size, position)
    - Test save/load methods for window state (dock widget layout)
    - Test has_* methods for checking if geometry/state exists
    - Test type safety (QByteArray handling)
    - Test graceful handling of missing or invalid data

TDD Phase: RED
    These tests are written BEFORE implementation to define expected behavior.
    All tests should FAIL initially, then PASS after implementation.

See Also:
    - Spec E06-F06-T02 for requirements
    - src/ink/infrastructure/persistence/app_settings.py for implementation
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QByteArray, QSettings

from ink.infrastructure.persistence.app_settings import AppSettings

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


# =============================================================================
# Module-level Fixtures
# =============================================================================


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide isolated QSettings storage for each test.

    This fixture:
    1. Creates a temporary directory for settings
    2. Configures QSettings to use this directory
    3. Clears any existing settings
    4. Yields the path for test use

    This ensures complete test isolation - no test can affect another.

    Args:
        tmp_path: Pytest-provided temporary directory (unique per test).

    Yields:
        Path to temporary settings directory.
    """
    settings_path = tmp_path / "settings"
    settings_path.mkdir()

    # Configure QSettings to use temporary path for INI format
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    # Clear any existing settings to ensure test isolation
    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.clear()
    temp_settings.sync()

    yield settings_path


@pytest.fixture
def app_settings(isolated_settings: Path) -> AppSettings:
    """Create AppSettings instance with isolated storage.

    Args:
        isolated_settings: Temporary settings directory (ensures isolation).
            This parameter is used to ensure the fixture dependency runs first.

    Returns:
        Fresh AppSettings instance.
    """
    return AppSettings()


# =============================================================================
# Test Classes for Window Geometry Methods
# =============================================================================


class TestSaveWindowGeometry:
    """Tests for AppSettings.save_window_geometry() method."""

    def test_save_window_geometry_method_exists(self, app_settings: AppSettings) -> None:
        """Verify save_window_geometry method is defined."""
        assert hasattr(app_settings, "save_window_geometry")
        assert callable(app_settings.save_window_geometry)

    def test_save_window_geometry_accepts_qbytearray(self, app_settings: AppSettings) -> None:
        """Verify save_window_geometry accepts QByteArray parameter."""
        geometry = QByteArray(b"\x01\x02\x03\x04")
        # Should not raise an exception
        app_settings.save_window_geometry(geometry)

    def test_save_window_geometry_persists_value(self, app_settings: AppSettings) -> None:
        """Verify save_window_geometry stores the geometry data."""
        geometry = QByteArray(b"test_geometry_data")
        app_settings.save_window_geometry(geometry)

        # Verify value is stored under correct key
        stored = app_settings.get_value(AppSettings.KEY_WINDOW_GEOMETRY, value_type=QByteArray)
        assert stored == geometry


class TestLoadWindowGeometry:
    """Tests for AppSettings.load_window_geometry() method."""

    def test_load_window_geometry_method_exists(self, app_settings: AppSettings) -> None:
        """Verify load_window_geometry method is defined."""
        assert hasattr(app_settings, "load_window_geometry")
        assert callable(app_settings.load_window_geometry)

    def test_load_window_geometry_returns_none_when_not_saved(
        self, app_settings: AppSettings
    ) -> None:
        """Verify load_window_geometry returns None when no geometry is saved."""
        result = app_settings.load_window_geometry()
        assert result is None

    def test_load_window_geometry_returns_saved_value(self, app_settings: AppSettings) -> None:
        """Verify load_window_geometry returns previously saved geometry."""
        geometry = QByteArray(b"saved_geometry_data")
        app_settings.save_window_geometry(geometry)

        result = app_settings.load_window_geometry()
        assert result == geometry

    def test_load_window_geometry_returns_qbytearray_type(self, app_settings: AppSettings) -> None:
        """Verify load_window_geometry returns QByteArray type."""
        geometry = QByteArray(b"geometry_bytes")
        app_settings.save_window_geometry(geometry)

        result = app_settings.load_window_geometry()
        assert isinstance(result, QByteArray)

    def test_load_window_geometry_returns_none_for_invalid_data(
        self, app_settings: AppSettings
    ) -> None:
        """Verify load_window_geometry returns None for non-QByteArray data."""
        # Simulate corrupted/invalid data by setting a string directly
        app_settings.set_value(AppSettings.KEY_WINDOW_GEOMETRY, "invalid_string")

        result = app_settings.load_window_geometry()
        assert result is None


class TestSaveWindowState:
    """Tests for AppSettings.save_window_state() method."""

    def test_save_window_state_method_exists(self, app_settings: AppSettings) -> None:
        """Verify save_window_state method is defined."""
        assert hasattr(app_settings, "save_window_state")
        assert callable(app_settings.save_window_state)

    def test_save_window_state_accepts_qbytearray(self, app_settings: AppSettings) -> None:
        """Verify save_window_state accepts QByteArray parameter."""
        state = QByteArray(b"\x05\x06\x07\x08")
        # Should not raise an exception
        app_settings.save_window_state(state)

    def test_save_window_state_persists_value(self, app_settings: AppSettings) -> None:
        """Verify save_window_state stores the state data."""
        state = QByteArray(b"test_state_data")
        app_settings.save_window_state(state)

        # Verify value is stored under correct key
        stored = app_settings.get_value(AppSettings.KEY_WINDOW_STATE, value_type=QByteArray)
        assert stored == state


class TestLoadWindowState:
    """Tests for AppSettings.load_window_state() method."""

    def test_load_window_state_method_exists(self, app_settings: AppSettings) -> None:
        """Verify load_window_state method is defined."""
        assert hasattr(app_settings, "load_window_state")
        assert callable(app_settings.load_window_state)

    def test_load_window_state_returns_none_when_not_saved(self, app_settings: AppSettings) -> None:
        """Verify load_window_state returns None when no state is saved."""
        result = app_settings.load_window_state()
        assert result is None

    def test_load_window_state_returns_saved_value(self, app_settings: AppSettings) -> None:
        """Verify load_window_state returns previously saved state."""
        state = QByteArray(b"saved_state_data")
        app_settings.save_window_state(state)

        result = app_settings.load_window_state()
        assert result == state

    def test_load_window_state_returns_qbytearray_type(self, app_settings: AppSettings) -> None:
        """Verify load_window_state returns QByteArray type."""
        state = QByteArray(b"state_bytes")
        app_settings.save_window_state(state)

        result = app_settings.load_window_state()
        assert isinstance(result, QByteArray)

    def test_load_window_state_returns_none_for_invalid_data(
        self, app_settings: AppSettings
    ) -> None:
        """Verify load_window_state returns None for non-QByteArray data."""
        # Simulate corrupted/invalid data by setting a string directly
        app_settings.set_value(AppSettings.KEY_WINDOW_STATE, "invalid_string")

        result = app_settings.load_window_state()
        assert result is None


class TestHasWindowGeometry:
    """Tests for AppSettings.has_window_geometry() method."""

    def test_has_window_geometry_method_exists(self, app_settings: AppSettings) -> None:
        """Verify has_window_geometry method is defined."""
        assert hasattr(app_settings, "has_window_geometry")
        assert callable(app_settings.has_window_geometry)

    def test_has_window_geometry_returns_false_when_not_saved(
        self, app_settings: AppSettings
    ) -> None:
        """Verify has_window_geometry returns False when no geometry exists."""
        result = app_settings.has_window_geometry()
        assert result is False

    def test_has_window_geometry_returns_true_after_save(self, app_settings: AppSettings) -> None:
        """Verify has_window_geometry returns True after saving geometry."""
        geometry = QByteArray(b"geometry_data")
        app_settings.save_window_geometry(geometry)

        result = app_settings.has_window_geometry()
        assert result is True


class TestHasWindowState:
    """Tests for AppSettings.has_window_state() method."""

    def test_has_window_state_method_exists(self, app_settings: AppSettings) -> None:
        """Verify has_window_state method is defined."""
        assert hasattr(app_settings, "has_window_state")
        assert callable(app_settings.has_window_state)

    def test_has_window_state_returns_false_when_not_saved(self, app_settings: AppSettings) -> None:
        """Verify has_window_state returns False when no state exists."""
        result = app_settings.has_window_state()
        assert result is False

    def test_has_window_state_returns_true_after_save(self, app_settings: AppSettings) -> None:
        """Verify has_window_state returns True after saving state."""
        state = QByteArray(b"state_data")
        app_settings.save_window_state(state)

        result = app_settings.has_window_state()
        assert result is True


class TestGeometryPersistence:
    """Tests for geometry persistence across AppSettings instances."""

    def test_window_geometry_persists_across_instances(self, isolated_settings: Path) -> None:
        """Verify window geometry survives instance recreation."""
        geometry = QByteArray(b"persistent_geometry")

        # Save with first instance
        settings1 = AppSettings()
        settings1.save_window_geometry(geometry)
        settings1.sync()

        # Load with second instance
        settings2 = AppSettings()
        result = settings2.load_window_geometry()

        assert result == geometry

    def test_window_state_persists_across_instances(self, isolated_settings: Path) -> None:
        """Verify window state survives instance recreation."""
        state = QByteArray(b"persistent_state")

        # Save with first instance
        settings1 = AppSettings()
        settings1.save_window_state(state)
        settings1.sync()

        # Load with second instance
        settings2 = AppSettings()
        result = settings2.load_window_state()

        assert result == state
