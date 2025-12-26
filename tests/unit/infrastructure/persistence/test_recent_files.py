"""Unit tests for AppSettings recent files functionality.

This module tests the recent files management methods added to AppSettings
for tracking and persisting recently opened netlist files.

Test Strategy:
    - Use temporary QSettings path to avoid polluting user settings
    - Use temporary files to test file existence filtering
    - Test each recent files method independently
    - Verify ordering, deduplication, and max size limits
    - Test auto-removal of non-existent files

TDD Phase: RED - These tests define the expected behavior before implementation.

See Also:
    - Spec E06-F06-T03 for requirements
    - src/ink/infrastructure/persistence/app_settings.py for implementation
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings

from ink.infrastructure.persistence.app_settings import AppSettings

if TYPE_CHECKING:
    from collections.abc import Generator


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


@pytest.fixture
def temp_files(tmp_path: Path) -> list[str]:
    """Create temporary test files for recent files testing.

    Creates 15 temporary .ckt files with content. This exceeds the default
    maximum of 10 recent files to test trimming behavior.

    Args:
        tmp_path: Pytest-provided temporary directory.

    Returns:
        List of absolute file paths as strings.
    """
    files = []
    for i in range(15):
        file = tmp_path / f"test{i}.ckt"
        file.write_text(f"* Netlist content {i}\n")
        files.append(str(file))
    return files


# =============================================================================
# Test Classes for Recent Files Methods
# =============================================================================


class TestAddRecentFile:
    """Test AppSettings.add_recent_file() method."""

    def test_add_single_file(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test adding a single file to recent files list."""
        app_settings.add_recent_file(temp_files[0])

        recent = app_settings.get_recent_files()
        assert len(recent) == 1
        assert recent[0] == temp_files[0]

    def test_add_multiple_files_newest_first(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that most recently added file is first in list."""
        app_settings.add_recent_file(temp_files[0])
        app_settings.add_recent_file(temp_files[1])
        app_settings.add_recent_file(temp_files[2])

        recent = app_settings.get_recent_files()
        assert recent[0] == temp_files[2]  # Most recent
        assert recent[1] == temp_files[1]
        assert recent[2] == temp_files[0]  # Oldest

    def test_duplicate_moves_to_front(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that re-adding existing file moves it to front without duplicating."""
        app_settings.add_recent_file(temp_files[0])
        app_settings.add_recent_file(temp_files[1])
        app_settings.add_recent_file(temp_files[2])
        app_settings.add_recent_file(temp_files[0])  # Re-add first file

        recent = app_settings.get_recent_files()
        assert len(recent) == 3  # No duplicate
        assert recent[0] == temp_files[0]  # Moved to front
        assert recent[1] == temp_files[2]
        assert recent[2] == temp_files[1]

    def test_respects_max_files_limit(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that list is trimmed to max size."""
        # Add 15 files (default max is 10)
        for file in temp_files:
            app_settings.add_recent_file(file)

        recent = app_settings.get_recent_files()
        assert len(recent) == 10  # Trimmed to max
        # Most recent file (temp_files[14]) should be first
        assert recent[0] == temp_files[14]
        # Oldest kept file should be temp_files[5]
        assert recent[9] == temp_files[5]

    def test_stores_absolute_path(
        self, app_settings: AppSettings, tmp_path: Path
    ) -> None:
        """Test that file paths are stored as absolute paths."""
        file = tmp_path / "test.ckt"
        file.write_text("* content\n")

        app_settings.add_recent_file(str(file))

        recent = app_settings.get_recent_files()
        assert len(recent) == 1
        # Path should be absolute
        assert Path(recent[0]).is_absolute()


class TestGetRecentFiles:
    """Test AppSettings.get_recent_files() method."""

    def test_returns_empty_list_when_no_files(
        self, app_settings: AppSettings
    ) -> None:
        """Test that empty list is returned when no recent files exist."""
        recent = app_settings.get_recent_files()
        assert isinstance(recent, list)
        assert len(recent) == 0

    def test_returns_list_of_strings(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that returned list contains string paths."""
        app_settings.add_recent_file(temp_files[0])

        recent = app_settings.get_recent_files()
        assert all(isinstance(f, str) for f in recent)

    def test_filters_nonexistent_files(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that non-existent files are automatically removed."""
        app_settings.add_recent_file(temp_files[0])
        app_settings.add_recent_file(temp_files[1])

        # Delete one of the files
        Path(temp_files[0]).unlink()

        recent = app_settings.get_recent_files()
        assert len(recent) == 1
        assert recent[0] == temp_files[1]

    def test_updates_stored_list_when_files_removed(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that stored list is updated when files are filtered."""
        app_settings.add_recent_file(temp_files[0])
        app_settings.add_recent_file(temp_files[1])
        app_settings.sync()

        # Delete one file
        Path(temp_files[0]).unlink()

        # Get files (should filter and update stored list)
        app_settings.get_recent_files()

        # Verify stored list was updated by creating new instance
        new_settings = AppSettings()
        recent = new_settings.get_recent_files()
        assert len(recent) == 1
        assert recent[0] == temp_files[1]

    def test_preserves_order(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that file order is preserved (newest first)."""
        for i in range(5):
            app_settings.add_recent_file(temp_files[i])

        recent = app_settings.get_recent_files()
        assert recent == [
            temp_files[4],
            temp_files[3],
            temp_files[2],
            temp_files[1],
            temp_files[0],
        ]


class TestClearRecentFiles:
    """Test AppSettings.clear_recent_files() method."""

    def test_clears_all_files(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that clear removes all recent files."""
        app_settings.add_recent_file(temp_files[0])
        app_settings.add_recent_file(temp_files[1])

        app_settings.clear_recent_files()

        recent = app_settings.get_recent_files()
        assert len(recent) == 0

    def test_clear_when_empty_does_nothing(
        self, app_settings: AppSettings
    ) -> None:
        """Test that clearing empty list doesn't cause errors."""
        # Should not raise
        app_settings.clear_recent_files()

        recent = app_settings.get_recent_files()
        assert len(recent) == 0


class TestGetMaxRecentFiles:
    """Test AppSettings.get_max_recent_files() method."""

    def test_returns_default_value(self, app_settings: AppSettings) -> None:
        """Test that default max is returned."""
        max_recent = app_settings.get_max_recent_files()
        assert max_recent == AppSettings.DEFAULT_MAX_RECENT
        assert max_recent == 10

    def test_returns_int(self, app_settings: AppSettings) -> None:
        """Test that returned value is an integer."""
        max_recent = app_settings.get_max_recent_files()
        assert isinstance(max_recent, int)


class TestSetMaxRecentFiles:
    """Test AppSettings.set_max_recent_files() method."""

    def test_changes_max_value(self, app_settings: AppSettings) -> None:
        """Test that max value can be changed."""
        app_settings.set_max_recent_files(5)

        max_recent = app_settings.get_max_recent_files()
        assert max_recent == 5

    def test_trims_existing_list(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that changing max trims existing list."""
        # Add 10 files
        for i in range(10):
            app_settings.add_recent_file(temp_files[i])

        # Reduce max to 5
        app_settings.set_max_recent_files(5)

        recent = app_settings.get_recent_files()
        assert len(recent) == 5
        # Should keep the 5 most recent (files 9, 8, 7, 6, 5)
        assert recent[0] == temp_files[9]
        assert recent[4] == temp_files[5]

    def test_rejects_zero_max(self, app_settings: AppSettings) -> None:
        """Test that max < 1 raises ValueError."""
        with pytest.raises(ValueError, match="max_count must be >= 1"):
            app_settings.set_max_recent_files(0)

    def test_rejects_negative_max(self, app_settings: AppSettings) -> None:
        """Test that negative max raises ValueError."""
        with pytest.raises(ValueError, match="max_count must be >= 1"):
            app_settings.set_max_recent_files(-1)

    def test_persists_max_setting(self, isolated_settings: Path) -> None:
        """Test that max setting persists across instances."""
        settings1 = AppSettings()
        settings1.set_max_recent_files(15)
        settings1.sync()

        settings2 = AppSettings()
        assert settings2.get_max_recent_files() == 15


class TestRecentFilesPersistence:
    """Test that recent files persist across AppSettings instances."""

    def test_files_persist_across_instances(
        self, isolated_settings: Path, tmp_path: Path
    ) -> None:
        """Test that recent files survive instance recreation."""
        # Create test files
        files = []
        for i in range(3):
            file = tmp_path / f"persist{i}.ckt"
            file.write_text(f"* content {i}\n")
            files.append(str(file))

        # Add files in first instance
        settings1 = AppSettings()
        for f in files:
            settings1.add_recent_file(f)
        settings1.sync()

        # Verify in new instance
        settings2 = AppSettings()
        recent = settings2.get_recent_files()
        assert len(recent) == 3
        assert recent[0] == files[2]  # Most recent
        assert recent[2] == files[0]  # Oldest

    def test_order_persists_after_move_to_front(
        self, isolated_settings: Path, tmp_path: Path
    ) -> None:
        """Test that order changes persist after duplicate re-add."""
        files = []
        for i in range(3):
            file = tmp_path / f"order{i}.ckt"
            file.write_text(f"* content {i}\n")
            files.append(str(file))

        # Add files
        settings1 = AppSettings()
        for f in files:
            settings1.add_recent_file(f)

        # Move first file to front
        settings1.add_recent_file(files[0])
        settings1.sync()

        # Verify order in new instance
        settings2 = AppSettings()
        recent = settings2.get_recent_files()
        assert recent[0] == files[0]  # Moved to front


class TestRecentFilesEdgeCases:
    """Test edge cases for recent files functionality."""

    def test_handles_empty_string_path(
        self, app_settings: AppSettings, temp_files: list[str]
    ) -> None:
        """Test that empty strings are filtered out from stored list."""
        app_settings.add_recent_file(temp_files[0])

        # Manually set list with empty string (simulates corruption)
        app_settings.set_value(
            AppSettings.KEY_RECENT_FILES,
            [temp_files[0], "", temp_files[1]]
        )

        recent = app_settings.get_recent_files()
        # Empty string should be filtered out, and temp_files[1] doesn't exist yet
        # Actually temp_files[1] exists in temp_files fixture, so check existence
        assert "" not in recent

    def test_handles_path_with_spaces(
        self, app_settings: AppSettings, tmp_path: Path
    ) -> None:
        """Test that paths with spaces are handled correctly."""
        file = tmp_path / "my design file.ckt"
        file.write_text("* content\n")

        app_settings.add_recent_file(str(file))

        recent = app_settings.get_recent_files()
        assert len(recent) == 1
        assert " " in recent[0]
        assert Path(recent[0]).exists()

    def test_handles_unicode_path(
        self, app_settings: AppSettings, tmp_path: Path
    ) -> None:
        """Test that unicode characters in paths are handled."""
        file = tmp_path / "设计_ファイル.ckt"
        file.write_text("* content\n")

        app_settings.add_recent_file(str(file))

        recent = app_settings.get_recent_files()
        assert len(recent) == 1
        assert Path(recent[0]).exists()
