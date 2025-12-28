"""Unit tests for InkMainWindow file and object count status display.

Tests verify the file status and object count display meets all requirements
from spec E06-F04-T04:
- update_file_status() method updates file_label text and tooltip
- update_object_count_status() method updates object_count_label text
- _update_view_counts() helper queries expansion state and updates counts
- File name displays base name only (not full path)
- Full file path shown in tooltip on file label hover
- "No file loaded" shown when file_path is None
- Object counts display format "Cells: N / Nets: M"
- Signal connections handle missing services gracefully
- Counts show 0 when expansion state not available

These tests follow TDD methodology:
- RED phase: Tests written first, expecting failures
- GREEN phase: Implementation to pass all tests
- REFACTOR phase: Code cleanup while tests pass

See Also:
    - Spec E06-F04-T04 for file and object count display requirements
    - Spec E06-F04-T01 for status bar setup (upstream dependency)
    - E01-F02 for file service signals
    - E03-F01 for expansion service signals
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QSettings

from ink.infrastructure.persistence.app_settings import AppSettings
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


@pytest.fixture
def main_window(qtbot: QtBot, app_settings: AppSettings) -> InkMainWindow:
    """Create InkMainWindow instance for testing.

    Args:
        qtbot: Pytest-qt bot for widget management.
        app_settings: Application settings instance.

    Returns:
        InkMainWindow instance registered with qtbot.
    """
    window = InkMainWindow(app_settings)
    qtbot.addWidget(window)
    return window


# =============================================================================
# Test Classes - update_file_status() Method
# =============================================================================


class TestUpdateFileStatusMethodExists:
    """Tests for update_file_status() method existence and signature."""

    def test_update_file_status_method_exists(self, main_window: InkMainWindow) -> None:
        """Test that update_file_status method exists on InkMainWindow.

        The method should accept an optional file_path string parameter
        and update the file_label text and tooltip.
        """
        assert hasattr(main_window, "update_file_status")
        assert callable(main_window.update_file_status)

    def test_update_file_status_accepts_string(self, main_window: InkMainWindow) -> None:
        """Test that update_file_status accepts a string parameter.

        The method should accept file_path as a string representing
        the absolute path to the loaded file.
        """
        # Should not raise an exception
        main_window.update_file_status("/path/to/design.ckt")

    def test_update_file_status_accepts_none(self, main_window: InkMainWindow) -> None:
        """Test that update_file_status accepts None parameter.

        The method should accept None to indicate no file is loaded.
        """
        # Should not raise an exception
        main_window.update_file_status(None)


class TestUpdateFileStatusFormatting:
    """Tests for file status display formatting with file path."""

    def test_update_file_status_shows_basename(self, main_window: InkMainWindow) -> None:
        """File status should show only the base name (not full path).

        Given "/home/user/project/design.ckt", displays "File: design.ckt".
        """
        file_path = "/home/user/project/design.ckt"
        main_window.update_file_status(file_path)
        assert main_window.file_label.text() == "File: design.ckt"

    def test_update_file_status_tooltip_shows_full_path(
        self, main_window: InkMainWindow
    ) -> None:
        """File label tooltip should show full path on hover.

        The tooltip provides access to the complete file path for reference.
        """
        file_path = "/home/user/project/design.ckt"
        main_window.update_file_status(file_path)
        assert main_window.file_label.toolTip() == file_path

    def test_update_file_status_handles_deep_path(
        self, main_window: InkMainWindow
    ) -> None:
        """File status should handle deeply nested file paths.

        The base name extraction should work regardless of path depth.
        """
        file_path = "/home/user/projects/chip/rev2/netlists/top/design.ckt"
        main_window.update_file_status(file_path)
        assert main_window.file_label.text() == "File: design.ckt"
        assert main_window.file_label.toolTip() == file_path

    def test_update_file_status_handles_various_extensions(
        self, main_window: InkMainWindow
    ) -> None:
        """File status should display files with different extensions.

        Supports .ckt, .cdl, and .sp extensions.
        """
        # Test .ckt extension
        main_window.update_file_status("/path/to/circuit.ckt")
        assert main_window.file_label.text() == "File: circuit.ckt"

        # Test .cdl extension
        main_window.update_file_status("/path/to/netlist.cdl")
        assert main_window.file_label.text() == "File: netlist.cdl"

        # Test .sp extension
        main_window.update_file_status("/path/to/spice.sp")
        assert main_window.file_label.text() == "File: spice.sp"


class TestUpdateFileStatusNoFile:
    """Tests for file status display when no file is loaded."""

    def test_update_file_status_none_shows_placeholder(
        self, main_window: InkMainWindow
    ) -> None:
        """File status should show 'No file loaded' when path is None.

        This is the initial state and the state after file is closed.
        """
        main_window.update_file_status(None)
        assert main_window.file_label.text() == "No file loaded"

    def test_update_file_status_none_clears_tooltip(
        self, main_window: InkMainWindow
    ) -> None:
        """File label tooltip should be empty when no file is loaded.

        No tooltip needed when there's no file to display path for.
        """
        # First set a file to have a tooltip
        main_window.update_file_status("/path/to/design.ckt")
        assert main_window.file_label.toolTip() != ""

        # Then clear with None
        main_window.update_file_status(None)
        assert main_window.file_label.toolTip() == ""

    def test_initial_state_shows_no_file_loaded(
        self, main_window: InkMainWindow
    ) -> None:
        """Initial file status should show 'No file loaded'.

        Before any file is opened, the status bar shows placeholder text.
        """
        # Window just initialized, no update_file_status called
        assert main_window.file_label.text() == "No file loaded"


class TestUpdateFileStatusEdgeCases:
    """Tests for file status edge cases."""

    def test_update_file_status_unicode_filename(
        self, main_window: InkMainWindow
    ) -> None:
        """File status should handle unicode characters in filename.

        Path library handles unicode correctly.
        """
        file_path = "/home/用户/项目/设计.ckt"
        main_window.update_file_status(file_path)
        assert main_window.file_label.text() == "File: 设计.ckt"
        assert main_window.file_label.toolTip() == file_path

    def test_update_file_status_long_filename(
        self, main_window: InkMainWindow
    ) -> None:
        """File status should handle very long filenames.

        The full name is displayed; widget width handles truncation.
        """
        long_name = "very_long_circuit_design_name_for_project_revision_3.ckt"
        file_path = f"/path/to/{long_name}"
        main_window.update_file_status(file_path)
        assert main_window.file_label.text() == f"File: {long_name}"

    def test_update_file_status_spaces_in_path(
        self, main_window: InkMainWindow
    ) -> None:
        """File status should handle spaces in path and filename.

        Spaces are common in user-created directory and file names.
        """
        file_path = "/home/user/My Projects/Circuit Design/top level.ckt"
        main_window.update_file_status(file_path)
        assert main_window.file_label.text() == "File: top level.ckt"
        assert main_window.file_label.toolTip() == file_path


# =============================================================================
# Test Classes - update_object_count_status() Method
# =============================================================================


class TestUpdateObjectCountStatusMethodExists:
    """Tests for update_object_count_status() method existence and signature."""

    def test_update_object_count_status_method_exists(
        self, main_window: InkMainWindow
    ) -> None:
        """Test that update_object_count_status method exists on InkMainWindow.

        The method should accept cell_count and net_count integer parameters
        and update the object_count_label text.
        """
        assert hasattr(main_window, "update_object_count_status")
        assert callable(main_window.update_object_count_status)

    def test_update_object_count_status_accepts_integers(
        self, main_window: InkMainWindow
    ) -> None:
        """Test that update_object_count_status accepts two integer parameters.

        The method should accept cell_count and net_count as integers.
        """
        # Should not raise an exception
        main_window.update_object_count_status(45, 67)


class TestUpdateObjectCountStatusFormatting:
    """Tests for object count status display formatting."""

    def test_update_object_count_status_format(
        self, main_window: InkMainWindow
    ) -> None:
        """Object count status should format as 'Cells: N / Nets: M'.

        This is the standard display format for visible object counts.
        """
        main_window.update_object_count_status(45, 67)
        assert main_window.object_count_label.text() == "Cells: 45 / Nets: 67"

    def test_update_object_count_status_zeros(
        self, main_window: InkMainWindow
    ) -> None:
        """Object count status should show zeros when no objects visible.

        This is the initial state before any file is loaded or expanded.
        """
        main_window.update_object_count_status(0, 0)
        assert main_window.object_count_label.text() == "Cells: 0 / Nets: 0"

    def test_update_object_count_status_single_items(
        self, main_window: InkMainWindow
    ) -> None:
        """Object count status should handle single items correctly.

        Format remains consistent even with count of 1.
        """
        main_window.update_object_count_status(1, 1)
        assert main_window.object_count_label.text() == "Cells: 1 / Nets: 1"

    def test_update_object_count_status_large_counts(
        self, main_window: InkMainWindow
    ) -> None:
        """Object count status should handle large counts.

        Large designs may have thousands of visible cells and nets.
        """
        main_window.update_object_count_status(10000, 15000)
        assert main_window.object_count_label.text() == "Cells: 10000 / Nets: 15000"

    def test_update_object_count_status_asymmetric(
        self, main_window: InkMainWindow
    ) -> None:
        """Object count status should handle asymmetric cell/net counts.

        It's common to have different numbers of cells vs nets.
        """
        main_window.update_object_count_status(100, 50)
        assert main_window.object_count_label.text() == "Cells: 100 / Nets: 50"

        main_window.update_object_count_status(50, 100)
        assert main_window.object_count_label.text() == "Cells: 50 / Nets: 100"

    def test_initial_object_count_status(self, main_window: InkMainWindow) -> None:
        """Initial object count should show 'Cells: 0 / Nets: 0'.

        Before any file is loaded, counts are zero.
        """
        # Window just initialized, no update called
        assert main_window.object_count_label.text() == "Cells: 0 / Nets: 0"


class TestUpdateObjectCountStatusUpdates:
    """Tests for object count status update behavior."""

    def test_object_count_updates_sequentially(
        self, main_window: InkMainWindow
    ) -> None:
        """Object count should track sequential updates.

        Multiple calls to update_object_count_status should each update display.
        """
        main_window.update_object_count_status(10, 20)
        assert main_window.object_count_label.text() == "Cells: 10 / Nets: 20"

        main_window.update_object_count_status(25, 35)
        assert main_window.object_count_label.text() == "Cells: 25 / Nets: 35"

        main_window.update_object_count_status(0, 0)
        assert main_window.object_count_label.text() == "Cells: 0 / Nets: 0"

    def test_object_count_updates_immediately(
        self, main_window: InkMainWindow
    ) -> None:
        """Object count should update immediately on method call.

        No delay or deferred processing should be required.
        """
        initial_text = main_window.object_count_label.text()
        assert initial_text == "Cells: 0 / Nets: 0"

        main_window.update_object_count_status(42, 84)

        # Should update immediately (no processEvents needed)
        assert main_window.object_count_label.text() == "Cells: 42 / Nets: 84"


# =============================================================================
# Test Classes - _update_view_counts() Helper Method
# =============================================================================


class TestUpdateViewCountsMethodExists:
    """Tests for _update_view_counts() helper method existence."""

    def test_update_view_counts_method_exists(
        self, main_window: InkMainWindow
    ) -> None:
        """Test that _update_view_counts method exists on InkMainWindow.

        This private helper method queries expansion state and updates counts.
        """
        assert hasattr(main_window, "_update_view_counts")
        assert callable(main_window._update_view_counts)


class TestUpdateViewCountsBehavior:
    """Tests for _update_view_counts() behavior with expansion state."""

    def test_update_view_counts_no_expansion_state(
        self, main_window: InkMainWindow
    ) -> None:
        """Counts should be 0 when expansion_state is not available.

        Before any design is loaded, expansion_state doesn't exist.
        """
        # Ensure no expansion_state attribute
        if hasattr(main_window, "expansion_state"):
            delattr(main_window, "expansion_state")

        main_window._update_view_counts()
        assert main_window.object_count_label.text() == "Cells: 0 / Nets: 0"

    def test_update_view_counts_expansion_state_none(
        self, main_window: InkMainWindow
    ) -> None:
        """Counts should be 0 when expansion_state is None.

        After file is closed, expansion_state may be set to None.
        """
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "expansion_state", None)

        main_window._update_view_counts()
        assert main_window.object_count_label.text() == "Cells: 0 / Nets: 0"

    def test_update_view_counts_with_expansion_state(
        self, main_window: InkMainWindow
    ) -> None:
        """Counts should reflect expansion_state visible cells and nets.

        The helper queries visible_cells and visible_nets from expansion_state.
        """
        # Create mock expansion state with visible objects
        mock_state = Mock()
        mock_state.visible_cells = {"cell1", "cell2", "cell3", "cell4", "cell5"}
        mock_state.visible_nets = {"net1", "net2", "net3"}
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "expansion_state", mock_state)

        main_window._update_view_counts()
        assert main_window.object_count_label.text() == "Cells: 5 / Nets: 3"

    def test_update_view_counts_empty_sets(
        self, main_window: InkMainWindow
    ) -> None:
        """Counts should be 0 when visible sets are empty.

        After collapsing all cells, the sets become empty.
        """
        mock_state = Mock()
        mock_state.visible_cells = set()
        mock_state.visible_nets = set()
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "expansion_state", mock_state)

        main_window._update_view_counts()
        assert main_window.object_count_label.text() == "Cells: 0 / Nets: 0"

    def test_update_view_counts_large_sets(
        self, main_window: InkMainWindow
    ) -> None:
        """Counts should handle large visible sets.

        Large designs may have thousands of visible objects.
        """
        mock_state = Mock()
        mock_state.visible_cells = {f"cell{i}" for i in range(5000)}
        mock_state.visible_nets = {f"net{i}" for i in range(7500)}
        # Use setattr to bypass mypy (testing pattern for dependency injection)
        setattr(main_window, "expansion_state", mock_state)

        main_window._update_view_counts()
        assert main_window.object_count_label.text() == "Cells: 5000 / Nets: 7500"


# =============================================================================
# Test Classes - Signal Connection Behavior
# =============================================================================


class TestConnectStatusSignalsGracefulHandling:
    """Tests for _connect_status_signals() graceful handling of missing services."""

    def test_connect_signals_no_file_service(
        self, main_window: InkMainWindow
    ) -> None:
        """Signal connection should handle missing file_service gracefully.

        The file_service may not be initialized during early development.
        """
        # Ensure no file_service
        if hasattr(main_window, "file_service"):
            delattr(main_window, "file_service")

        # Should not raise an exception
        main_window._connect_status_signals()

    def test_connect_signals_no_expansion_service(
        self, main_window: InkMainWindow
    ) -> None:
        """Signal connection should handle missing expansion_service gracefully.

        The expansion_service may not be initialized during early development.
        """
        # Ensure no expansion_service
        if hasattr(main_window, "expansion_service"):
            delattr(main_window, "expansion_service")

        # Should not raise an exception
        main_window._connect_status_signals()


# =============================================================================
# Test Classes - Combined File and Object Status Updates
# =============================================================================


class TestCombinedStatusUpdates:
    """Tests for combined file and object status updates."""

    def test_file_and_object_status_independent(
        self, main_window: InkMainWindow
    ) -> None:
        """File status and object count status should update independently.

        Updating one should not affect the other.
        """
        # Update file status
        main_window.update_file_status("/path/to/design.ckt")
        initial_object_count = main_window.object_count_label.text()

        # Verify file status changed but object count unchanged
        assert main_window.file_label.text() == "File: design.ckt"
        assert main_window.object_count_label.text() == initial_object_count

        # Update object counts
        main_window.update_object_count_status(100, 200)

        # Verify object count changed but file status unchanged
        assert main_window.object_count_label.text() == "Cells: 100 / Nets: 200"
        assert main_window.file_label.text() == "File: design.ckt"

    def test_clear_file_resets_counts(self, main_window: InkMainWindow) -> None:
        """Clearing file status should be independent of object counts.

        File status None doesn't automatically clear counts (separate concern).
        """
        # Set both statuses
        main_window.update_file_status("/path/to/design.ckt")
        main_window.update_object_count_status(50, 75)

        # Clear file status
        main_window.update_file_status(None)

        # File cleared, but counts should remain (separate update)
        assert main_window.file_label.text() == "No file loaded"
        assert main_window.object_count_label.text() == "Cells: 50 / Nets: 75"
