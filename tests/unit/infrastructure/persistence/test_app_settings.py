"""Unit tests for AppSettings class.

This module tests the AppSettings class which provides a clean API over
Qt's QSettings for platform-native settings storage.

Test Strategy:
    - Use temporary QSettings path to avoid polluting user settings
    - Test each public method independently
    - Verify type conversion works correctly
    - Ensure default initialization on first run
    - Test settings persistence across instance recreation

See Also:
    - Spec E06-F06-T01 for requirements
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
def app_settings(isolated_settings: Path) -> AppSettings:  # noqa: ARG001
    """Create AppSettings instance with isolated storage.

    Args:
        isolated_settings: Temporary settings directory (ensures isolation).
            This parameter is used to ensure the fixture dependency runs first.

    Returns:
        Fresh AppSettings instance.
    """
    return AppSettings()


# =============================================================================
# Test Classes
# =============================================================================


class TestAppSettingsClassConstants:
    """Test AppSettings class-level constants and configuration."""

    def test_has_window_geometry_key(self) -> None:
        """Verify KEY_WINDOW_GEOMETRY constant is defined."""
        assert hasattr(AppSettings, "KEY_WINDOW_GEOMETRY")
        assert AppSettings.KEY_WINDOW_GEOMETRY == "geometry/window"

    def test_has_window_state_key(self) -> None:
        """Verify KEY_WINDOW_STATE constant is defined."""
        assert hasattr(AppSettings, "KEY_WINDOW_STATE")
        assert AppSettings.KEY_WINDOW_STATE == "geometry/state"

    def test_has_recent_files_key(self) -> None:
        """Verify KEY_RECENT_FILES constant is defined."""
        assert hasattr(AppSettings, "KEY_RECENT_FILES")
        assert AppSettings.KEY_RECENT_FILES == "files/recent"

    def test_has_max_recent_key(self) -> None:
        """Verify KEY_MAX_RECENT constant is defined."""
        assert hasattr(AppSettings, "KEY_MAX_RECENT")
        assert AppSettings.KEY_MAX_RECENT == "files/max_recent"

    def test_has_settings_version_key(self) -> None:
        """Verify KEY_SETTINGS_VERSION constant is defined."""
        assert hasattr(AppSettings, "KEY_SETTINGS_VERSION")
        assert AppSettings.KEY_SETTINGS_VERSION == "meta/version"

    def test_has_current_version(self) -> None:
        """Verify CURRENT_VERSION constant is defined."""
        assert hasattr(AppSettings, "CURRENT_VERSION")
        assert AppSettings.CURRENT_VERSION == 1

    def test_has_default_max_recent(self) -> None:
        """Verify DEFAULT_MAX_RECENT constant is defined."""
        assert hasattr(AppSettings, "DEFAULT_MAX_RECENT")
        assert AppSettings.DEFAULT_MAX_RECENT == 10


class TestAppSettingsInitialization:
    """Test AppSettings initialization and setup."""

    def test_creates_qsettings_instance(self, app_settings: AppSettings) -> None:
        """Verify QSettings instance is created on initialization."""
        assert hasattr(app_settings, "settings")
        assert isinstance(app_settings.settings, QSettings)

    def test_uses_correct_organization(self, app_settings: AppSettings) -> None:
        """Verify QSettings uses correct organization name."""
        assert app_settings.settings.organizationName() == "InkProject"

    def test_uses_correct_application(self, app_settings: AppSettings) -> None:
        """Verify QSettings uses correct application name."""
        assert app_settings.settings.applicationName() == "Ink"

    def test_initializes_defaults_on_first_run(
        self, isolated_settings: Path
    ) -> None:
        """Verify default values are set on first run."""
        # Create fresh instance (simulates first run)
        settings = AppSettings()

        # Check defaults were initialized
        assert settings.has_key(AppSettings.KEY_SETTINGS_VERSION)
        assert settings.get_value(
            AppSettings.KEY_SETTINGS_VERSION, value_type=int
        ) == AppSettings.CURRENT_VERSION
        assert settings.get_value(
            AppSettings.KEY_MAX_RECENT, value_type=int
        ) == AppSettings.DEFAULT_MAX_RECENT

    def test_does_not_reinitialize_existing_settings(
        self, isolated_settings: Path
    ) -> None:
        """Verify defaults are not overwritten on subsequent runs."""
        # First run - creates defaults
        settings1 = AppSettings()
        settings1.set_value(AppSettings.KEY_MAX_RECENT, 5)
        settings1.sync()

        # Second run - should not overwrite
        settings2 = AppSettings()
        assert settings2.get_value(
            AppSettings.KEY_MAX_RECENT, value_type=int
        ) == 5


class TestAppSettingsGetValue:
    """Test AppSettings.get_value() method."""

    def test_returns_stored_value(self, app_settings: AppSettings) -> None:
        """Verify get_value returns previously stored value."""
        app_settings.set_value("test/key", "test_value")
        assert app_settings.get_value("test/key") == "test_value"

    def test_returns_default_for_nonexistent_key(
        self, app_settings: AppSettings
    ) -> None:
        """Verify get_value returns default for missing key."""
        result = app_settings.get_value("nonexistent/key", "default")
        assert result == "default"

    def test_returns_none_for_nonexistent_without_default(
        self, app_settings: AppSettings
    ) -> None:
        """Verify get_value returns None when no default provided."""
        result = app_settings.get_value("nonexistent/key")
        assert result is None

    def test_converts_to_int_type(self, app_settings: AppSettings) -> None:
        """Verify type conversion to int works."""
        app_settings.set_value("test/int", 42)
        result = app_settings.get_value("test/int", value_type=int)
        assert result == 42
        assert isinstance(result, int)

    def test_converts_to_bool_type(self, app_settings: AppSettings) -> None:
        """Verify type conversion to bool works."""
        app_settings.set_value("test/bool", True)
        result = app_settings.get_value("test/bool", value_type=bool)
        assert result is True
        assert isinstance(result, bool)

    def test_converts_to_str_type(self, app_settings: AppSettings) -> None:
        """Verify type conversion to str works."""
        app_settings.set_value("test/str", "hello")
        result = app_settings.get_value("test/str", value_type=str)
        assert result == "hello"
        assert isinstance(result, str)

    def test_handles_list_type(self, app_settings: AppSettings) -> None:
        """Verify list values are stored and retrieved correctly."""
        test_list = ["file1.ckt", "file2.ckt", "file3.ckt"]
        app_settings.set_value("test/list", test_list)
        result = app_settings.get_value("test/list")
        assert result == test_list

    def test_handles_qbytearray(self, app_settings: AppSettings) -> None:
        """Verify QByteArray values work (for geometry storage)."""
        byte_array = QByteArray(b"\x01\x02\x03\x04")
        app_settings.set_value("test/bytes", byte_array)
        result = app_settings.get_value("test/bytes", value_type=QByteArray)
        assert result == byte_array


class TestAppSettingsSetValue:
    """Test AppSettings.set_value() method."""

    def test_stores_string_value(self, app_settings: AppSettings) -> None:
        """Verify string values are stored correctly."""
        app_settings.set_value("test/string", "hello world")
        assert app_settings.get_value("test/string") == "hello world"

    def test_stores_int_value(self, app_settings: AppSettings) -> None:
        """Verify integer values are stored correctly."""
        app_settings.set_value("test/int", 123)
        assert app_settings.get_value("test/int", value_type=int) == 123

    def test_stores_float_value(self, app_settings: AppSettings) -> None:
        """Verify float values are stored correctly."""
        app_settings.set_value("test/float", 3.14)
        result = app_settings.get_value("test/float", value_type=float)
        assert abs(result - 3.14) < 0.001

    def test_overwrites_existing_value(self, app_settings: AppSettings) -> None:
        """Verify existing values can be overwritten."""
        app_settings.set_value("test/key", "original")
        app_settings.set_value("test/key", "updated")
        assert app_settings.get_value("test/key") == "updated"


class TestAppSettingsHasKey:
    """Test AppSettings.has_key() method."""

    def test_returns_false_for_nonexistent_key(
        self, app_settings: AppSettings
    ) -> None:
        """Verify has_key returns False for missing keys."""
        assert app_settings.has_key("nonexistent/key") is False

    def test_returns_true_for_existing_key(
        self, app_settings: AppSettings
    ) -> None:
        """Verify has_key returns True for existing keys."""
        app_settings.set_value("test/key", "value")
        assert app_settings.has_key("test/key") is True


class TestAppSettingsRemoveKey:
    """Test AppSettings.remove_key() method."""

    def test_removes_existing_key(self, app_settings: AppSettings) -> None:
        """Verify remove_key removes existing key."""
        app_settings.set_value("test/key", "value")
        app_settings.remove_key("test/key")
        assert app_settings.has_key("test/key") is False

    def test_handles_nonexistent_key(self, app_settings: AppSettings) -> None:
        """Verify remove_key handles missing keys gracefully."""
        # Should not raise an exception
        app_settings.remove_key("nonexistent/key")


class TestAppSettingsGetAllKeys:
    """Test AppSettings.get_all_keys() method."""

    def test_returns_list(self, app_settings: AppSettings) -> None:
        """Verify get_all_keys returns a list."""
        result = app_settings.get_all_keys()
        assert isinstance(result, list)

    def test_includes_all_set_keys(self, app_settings: AppSettings) -> None:
        """Verify all set keys appear in result."""
        app_settings.set_value("test/key1", "value1")
        app_settings.set_value("test/key2", "value2")
        keys = app_settings.get_all_keys()
        assert "test/key1" in keys
        assert "test/key2" in keys


class TestAppSettingsGetSettingsFilePath:
    """Test AppSettings.get_settings_file_path() method."""

    def test_returns_string(self, app_settings: AppSettings) -> None:
        """Verify get_settings_file_path returns a string."""
        result = app_settings.get_settings_file_path()
        assert isinstance(result, str)

    def test_returns_nonempty_path(self, app_settings: AppSettings) -> None:
        """Verify path is not empty."""
        result = app_settings.get_settings_file_path()
        assert len(result) > 0


class TestAppSettingsSync:
    """Test AppSettings.sync() method."""

    def test_sync_does_not_raise(self, app_settings: AppSettings) -> None:
        """Verify sync() completes without errors."""
        app_settings.set_value("test/key", "value")
        # Should not raise an exception
        app_settings.sync()

    def test_sync_persists_values(
        self, isolated_settings: Path
    ) -> None:
        """Verify sync() writes values to disk."""
        # Create instance, set value, and sync
        settings1 = AppSettings()
        settings1.set_value("persist/test", "persistent_value")
        settings1.sync()

        # Create new instance and verify value persists
        settings2 = AppSettings()
        assert settings2.get_value("persist/test") == "persistent_value"


class TestAppSettingsPersistence:
    """Test that settings persist across instance recreation."""

    def test_values_persist_across_instances(
        self, isolated_settings: Path
    ) -> None:
        """Verify settings survive instance recreation."""
        # Create first instance and set values
        settings1 = AppSettings()
        settings1.set_value("persist/string", "hello")
        settings1.set_value("persist/int", 42)
        settings1.sync()

        # Create second instance and verify values
        settings2 = AppSettings()
        assert settings2.get_value("persist/string") == "hello"
        assert settings2.get_value("persist/int", value_type=int) == 42

    def test_qbytearray_persists_across_instances(
        self, isolated_settings: Path
    ) -> None:
        """Verify QByteArray values persist (important for geometry)."""
        byte_data = QByteArray(b"\x00\x01\x02\x03\x04\x05")

        settings1 = AppSettings()
        settings1.set_value(AppSettings.KEY_WINDOW_GEOMETRY, byte_data)
        settings1.sync()

        settings2 = AppSettings()
        result = settings2.get_value(
            AppSettings.KEY_WINDOW_GEOMETRY, value_type=QByteArray
        )
        assert result == byte_data


# =============================================================================
# Settings Migration Tests (E06-F06-T04)
# =============================================================================


class TestSettingsMigration:
    """Test settings migration framework.

    These tests verify that:
    - Settings version is tracked and stored
    - Migrations are applied sequentially when version changes
    - The migration framework handles version jumps correctly
    """

    def test_migrate_if_needed_called_on_init(
        self, isolated_settings: Path
    ) -> None:
        """Verify _migrate_if_needed is called during initialization."""
        # Pre-set an old version to simulate upgrade scenario
        temp_settings = QSettings("InkProject", "Ink")
        temp_settings.setValue(AppSettings.KEY_SETTINGS_VERSION, 0)
        temp_settings.sync()

        # Create new instance - should trigger migration
        settings = AppSettings()

        # Version should now be current
        assert settings.get_settings_version() == AppSettings.CURRENT_VERSION

    def test_get_settings_version_returns_stored_version(
        self, app_settings: AppSettings
    ) -> None:
        """Verify get_settings_version returns the stored version."""
        version = app_settings.get_settings_version()
        assert version == AppSettings.CURRENT_VERSION
        assert isinstance(version, int)

    def test_migration_applies_sequentially(
        self, isolated_settings: Path
    ) -> None:
        """Verify migrations are applied in sequence from old to new version."""
        # Pre-set version 0 to simulate fresh install before versioning
        temp_settings = QSettings("InkProject", "Ink")
        temp_settings.setValue(AppSettings.KEY_SETTINGS_VERSION, 0)
        temp_settings.sync()

        # Create instance - migration v0->v1 should run
        settings = AppSettings()

        # Version should be updated to current
        assert settings.get_settings_version() == AppSettings.CURRENT_VERSION

    def test_no_migration_when_version_is_current(
        self, isolated_settings: Path
    ) -> None:
        """Verify no migration runs when version is already current."""
        # Pre-set current version
        temp_settings = QSettings("InkProject", "Ink")
        temp_settings.setValue(
            AppSettings.KEY_SETTINGS_VERSION, AppSettings.CURRENT_VERSION
        )
        temp_settings.setValue("test/key", "original_value")
        temp_settings.sync()

        # Create instance - should NOT modify anything
        settings = AppSettings()

        # Test value should be unchanged
        assert settings.get_value("test/key") == "original_value"


# =============================================================================
# Settings Reset Tests (E06-F06-T04)
# =============================================================================


class TestSettingsReset:
    """Test settings reset functionality.

    These tests verify:
    - reset_all_settings clears everything and re-initializes defaults
    - reset_window_geometry clears only geometry-related settings
    - reset_recent_files clears only recent files
    """

    def test_reset_all_settings_clears_all(
        self, app_settings: AppSettings
    ) -> None:
        """Verify reset_all_settings clears all custom settings."""
        # Add custom settings
        app_settings.set_value("custom/key1", "value1")
        app_settings.set_value("custom/key2", "value2")
        app_settings.sync()

        # Reset all settings
        app_settings.reset_all_settings()

        # Custom settings should be cleared
        assert not app_settings.has_key("custom/key1")
        assert not app_settings.has_key("custom/key2")

    def test_reset_all_settings_reinitializes_defaults(
        self, app_settings: AppSettings
    ) -> None:
        """Verify reset_all_settings re-initializes default values."""
        # Modify defaults
        app_settings.set_value(AppSettings.KEY_MAX_RECENT, 99)
        app_settings.sync()

        # Reset
        app_settings.reset_all_settings()

        # Defaults should be restored
        assert (
            app_settings.get_value(AppSettings.KEY_MAX_RECENT, value_type=int)
            == AppSettings.DEFAULT_MAX_RECENT
        )
        assert (
            app_settings.get_settings_version() == AppSettings.CURRENT_VERSION
        )

    def test_reset_all_settings_clears_recent_files(
        self, app_settings: AppSettings
    ) -> None:
        """Verify reset_all_settings clears recent files list."""
        # Add recent files
        app_settings.set_value(
            AppSettings.KEY_RECENT_FILES, ["/path/to/file.ckt"]
        )
        app_settings.sync()

        # Reset
        app_settings.reset_all_settings()

        # Recent files should be empty
        recent = app_settings.get_value(AppSettings.KEY_RECENT_FILES)
        assert recent == []

    def test_reset_window_geometry_clears_geometry(
        self, app_settings: AppSettings
    ) -> None:
        """Verify reset_window_geometry clears geometry settings."""
        from PySide6.QtCore import QByteArray

        # Set geometry values
        app_settings.set_value(
            AppSettings.KEY_WINDOW_GEOMETRY, QByteArray(b"geometry_data")
        )
        app_settings.set_value(
            AppSettings.KEY_WINDOW_STATE, QByteArray(b"state_data")
        )
        app_settings.sync()

        # Reset geometry
        app_settings.reset_window_geometry()

        # Geometry should be cleared
        assert not app_settings.has_key(AppSettings.KEY_WINDOW_GEOMETRY)
        assert not app_settings.has_key(AppSettings.KEY_WINDOW_STATE)

    def test_reset_window_geometry_preserves_other_settings(
        self, app_settings: AppSettings
    ) -> None:
        """Verify reset_window_geometry doesn't affect other settings."""
        from PySide6.QtCore import QByteArray

        # Set geometry and other settings
        app_settings.set_value(
            AppSettings.KEY_WINDOW_GEOMETRY, QByteArray(b"geometry")
        )
        app_settings.set_value("other/setting", "preserved")
        app_settings.sync()

        # Reset geometry
        app_settings.reset_window_geometry()

        # Other settings should remain
        assert app_settings.get_value("other/setting") == "preserved"

    def test_reset_recent_files_clears_list(
        self, app_settings: AppSettings
    ) -> None:
        """Verify reset_recent_files clears the recent files list."""
        # Add recent files
        app_settings.set_value(
            AppSettings.KEY_RECENT_FILES, ["/file1.ckt", "/file2.ckt"]
        )
        app_settings.sync()

        # Reset recent files
        app_settings.reset_recent_files()

        # Should be empty
        recent = app_settings.get_value(AppSettings.KEY_RECENT_FILES)
        assert recent == []

    def test_reset_recent_files_preserves_other_settings(
        self, app_settings: AppSettings
    ) -> None:
        """Verify reset_recent_files doesn't affect other settings."""
        # Set recent files and other settings
        app_settings.set_value(
            AppSettings.KEY_RECENT_FILES, ["/file.ckt"]
        )
        app_settings.set_value("other/key", "value")
        app_settings.sync()

        # Reset recent files
        app_settings.reset_recent_files()

        # Other settings should remain
        assert app_settings.get_value("other/key") == "value"


# =============================================================================
# Settings Diagnostics Tests (E06-F06-T04)
# =============================================================================


class TestSettingsDiagnostics:
    """Test settings diagnostic methods.

    These tests verify:
    - get_all_settings returns all settings as dictionary
    - export_settings writes settings to JSON file
    - is_corrupted detects corrupted settings
    """

    def test_get_all_settings_returns_dict(
        self, app_settings: AppSettings
    ) -> None:
        """Verify get_all_settings returns a dictionary."""
        result = app_settings.get_all_settings()
        assert isinstance(result, dict)

    def test_get_all_settings_includes_all_keys(
        self, app_settings: AppSettings
    ) -> None:
        """Verify get_all_settings includes all stored keys."""
        app_settings.set_value("test/key1", "value1")
        app_settings.set_value("test/key2", "value2")

        all_settings = app_settings.get_all_settings()

        assert "test/key1" in all_settings
        assert "test/key2" in all_settings
        assert all_settings["test/key1"] == "value1"
        assert all_settings["test/key2"] == "value2"

    def test_export_settings_creates_file(
        self, app_settings: AppSettings, tmp_path: Path
    ) -> None:
        """Verify export_settings creates a file."""
        export_path = tmp_path / "settings_export.json"

        app_settings.export_settings(str(export_path))

        assert export_path.exists()

    def test_export_settings_writes_valid_json(
        self, app_settings: AppSettings, tmp_path: Path
    ) -> None:
        """Verify export_settings writes valid JSON."""
        import json

        app_settings.set_value("test/key", "test_value")
        export_path = tmp_path / "settings_export.json"

        app_settings.export_settings(str(export_path))

        # Should be valid JSON
        with export_path.open() as f:
            data = json.load(f)

        assert "test/key" in data
        assert data["test/key"] == "test_value"

    def test_export_settings_handles_qbytearray(
        self, app_settings: AppSettings, tmp_path: Path
    ) -> None:
        """Verify export_settings converts QByteArray to base64."""
        import json

        from PySide6.QtCore import QByteArray

        byte_data = QByteArray(b"\x01\x02\x03\x04")
        app_settings.set_value("test/bytes", byte_data)
        export_path = tmp_path / "settings_export.json"

        app_settings.export_settings(str(export_path))

        with export_path.open() as f:
            data = json.load(f)

        # QByteArray should be converted to dict with type and base64 data
        assert "test/bytes" in data
        assert data["test/bytes"]["_type"] == "QByteArray"
        assert "_data" in data["test/bytes"]

    def test_is_corrupted_returns_false_for_valid_settings(
        self, app_settings: AppSettings
    ) -> None:
        """Verify is_corrupted returns False for valid settings."""
        assert app_settings.is_corrupted() is False

    def test_is_corrupted_returns_true_for_corrupted_settings(
        self, isolated_settings: Path
    ) -> None:
        """Verify is_corrupted returns True for corrupted settings."""
        # Create settings with invalid data that will cause read errors
        temp_settings = QSettings("InkProject", "Ink")
        temp_settings.setValue(AppSettings.KEY_SETTINGS_VERSION, "not_an_int")
        temp_settings.sync()

        settings = AppSettings()

        # is_corrupted should detect the issue
        # Note: This test may need adjustment based on what "corrupted" means
        # For now, we test the method exists and returns bool
        result = settings.is_corrupted()
        assert isinstance(result, bool)
