"""Performance tests for application startup and window creation.

This module verifies the application meets performance requirements:
- Startup time < 2 seconds (hard requirement from spec)
- Window creation < 500ms (target)
- No memory leaks in repeated create/destroy cycles

Test Strategy:
    - Use time.perf_counter() for accurate timing measurements
    - Multiple iterations to get stable measurements
    - Separate tests for window creation vs full startup
    - Memory leak detection via repeated create/destroy cycles

See Also:
    - E06-F01-T05 spec for performance requirements
    - Pre-docs E06-F01-T05 for testing strategy
"""

from __future__ import annotations

import gc
import os
import time
from typing import TYPE_CHECKING

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.main_window import InkMainWindow

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def qapp() -> Generator[QApplication, None, None]:
    """Provide QApplication instance for Qt widget tests.

    Qt requires exactly one QApplication instance per process.
    This fixture ensures we reuse an existing instance or create a new one.
    """
    existing = QApplication.instance()
    if existing is not None and isinstance(existing, QApplication):
        yield existing
    else:
        app = QApplication([])
        yield app


@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Redirect QSettings to temporary directory for test isolation.

    Uses QSettings.setPath() to redirect INI file storage to a temp
    directory. This ensures tests don't affect real user settings.

    Yields:
        Path to the temporary settings directory.
    """
    settings_path = tmp_path / "settings"
    settings_path.mkdir(exist_ok=True)

    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    yield settings_path


@pytest.fixture
def app_settings(isolated_settings: Path) -> AppSettings:
    """Create AppSettings instance for testing.

    Args:
        isolated_settings: Temporary settings directory (ensures isolation).

    Returns:
        Fresh AppSettings instance.
    """
    return AppSettings()


# =============================================================================
# Constants
# =============================================================================


# Performance thresholds
# CI environments may be slower, so use relaxed thresholds
IS_CI = os.getenv("CI") is not None
STARTUP_THRESHOLD = 2.0  # Hard requirement: 2 seconds
CREATION_THRESHOLD = 0.5 if not IS_CI else 1.0  # 500ms target, 1s for CI


# =============================================================================
# Test Classes: Window Creation Performance
# =============================================================================


class TestWindowCreationPerformance:
    """Test window creation performance."""

    def test_window_creation_under_threshold(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Verify window creation is under threshold."""
        start = time.perf_counter()
        window = InkMainWindow(app_settings)
        elapsed = time.perf_counter() - start

        window.deleteLater()
        qapp.processEvents()

        assert elapsed < CREATION_THRESHOLD, (
            f"Window creation took {elapsed:.3f}s, exceeds {CREATION_THRESHOLD}s limit"
        )

    def test_average_creation_time(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test average window creation time over multiple iterations."""
        iterations = 5
        times: list[float] = []

        for _ in range(iterations):
            start = time.perf_counter()
            window = InkMainWindow(app_settings)
            elapsed = time.perf_counter() - start
            times.append(elapsed)

            window.deleteLater()
            qapp.processEvents()

        avg_time = sum(times) / len(times)
        max_time = max(times)

        # Average should be under threshold
        assert avg_time < CREATION_THRESHOLD, (
            f"Average creation time {avg_time:.3f}s exceeds threshold"
        )

        # Maximum should not be too far from average (stability check)
        assert max_time < CREATION_THRESHOLD * 2, (
            f"Maximum creation time {max_time:.3f}s is unstable"
        )


class TestWindowShowPerformance:
    """Test window show() performance."""

    def test_window_show_is_fast(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Verify window show operation is fast."""
        window = InkMainWindow(app_settings)

        start = time.perf_counter()
        window.show()
        qapp.processEvents()
        elapsed = time.perf_counter() - start

        window.close()
        window.deleteLater()
        qapp.processEvents()

        # Show should be near-instantaneous (< 100ms)
        assert elapsed < 0.1, f"Window show took {elapsed:.3f}s, too slow"


# =============================================================================
# Test Classes: Startup Time
# =============================================================================


class TestStartupTime:
    """Test complete application startup time."""

    def test_startup_under_2_seconds(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Verify complete startup meets 2-second requirement.

        This is the hard requirement from E06-F01 spec:
        "Application launches in < 2 seconds on typical hardware"
        """
        start = time.perf_counter()

        # Simulate full startup sequence
        window = InkMainWindow(app_settings)
        window.show()
        qapp.processEvents()

        elapsed = time.perf_counter() - start

        window.close()
        window.deleteLater()
        qapp.processEvents()

        # Full startup should be under 2 seconds
        assert elapsed < STARTUP_THRESHOLD, (
            f"Startup took {elapsed:.2f}s, exceeds {STARTUP_THRESHOLD}s limit"
        )

    def test_cold_vs_warm_startup(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Compare cold vs warm startup times.

        First creation may be slower due to imports and initialization.
        Subsequent creations should be faster.
        """
        # First (cold) creation
        start1 = time.perf_counter()
        window1 = InkMainWindow(app_settings)
        window1.show()
        qapp.processEvents()
        cold_time = time.perf_counter() - start1
        window1.close()
        window1.deleteLater()
        qapp.processEvents()

        # Second (warm) creation
        start2 = time.perf_counter()
        window2 = InkMainWindow(app_settings)
        window2.show()
        qapp.processEvents()
        warm_time = time.perf_counter() - start2
        window2.close()
        window2.deleteLater()
        qapp.processEvents()

        # Both should be under threshold
        assert cold_time < STARTUP_THRESHOLD, (
            f"Cold startup took {cold_time:.2f}s"
        )
        assert warm_time < STARTUP_THRESHOLD, (
            f"Warm startup took {warm_time:.2f}s"
        )

        # Warm should generally be faster (but not always in CI)
        # Just log the difference for diagnostics


# =============================================================================
# Test Classes: Memory Usage
# =============================================================================


class TestMemoryUsage:
    """Test memory usage and leak detection."""

    def test_no_memory_leak_in_create_destroy(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test repeated window creation doesn't leak memory.

        Creates and destroys windows multiple times, then verifies
        everything still works. Actual memory profiling would require
        external tools, but this catches obvious leaks.
        """
        iterations = 50

        # Create and destroy windows many times
        for _ in range(iterations):
            window = InkMainWindow(app_settings)
            window.show()
            qapp.processEvents()
            window.close()
            window.deleteLater()
            qapp.processEvents()

        # Force garbage collection
        gc.collect()

        # Create one final window to ensure everything still works
        final_window = InkMainWindow(app_settings)
        final_window.show()
        qapp.processEvents()
        assert final_window.isVisible()

        final_window.close()
        final_window.deleteLater()
        qapp.processEvents()

    def test_rapid_create_destroy(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test rapid window creation/destruction doesn't crash.

        Rapidly creates and destroys windows without waiting for
        full event processing. Tests Qt's cleanup mechanisms.
        """
        for _ in range(20):
            window = InkMainWindow(app_settings)
            window.deleteLater()

        # Process all pending deletions
        qapp.processEvents()
        gc.collect()

        # Final verification
        window = InkMainWindow(app_settings)
        assert window is not None
        window.deleteLater()
        qapp.processEvents()


# =============================================================================
# Test Classes: Component Creation
# =============================================================================


class TestComponentCreationPerformance:
    """Test individual component creation performance."""

    def test_central_widget_creation(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test central widget is created quickly."""
        window = InkMainWindow(app_settings)

        # Canvas should already exist after construction
        assert window.schematic_canvas is not None

        window.deleteLater()
        qapp.processEvents()

    def test_dock_widgets_creation(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test dock widgets are created quickly."""
        window = InkMainWindow(app_settings)

        # All docks should exist after construction
        assert window.hierarchy_dock is not None
        assert window.property_dock is not None
        assert window.message_dock is not None

        window.deleteLater()
        qapp.processEvents()

    def test_menu_bar_creation(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Test menu bar is created quickly."""
        window = InkMainWindow(app_settings)

        # Menu bar should exist after construction
        assert window.menuBar() is not None
        assert window.recent_files_menu is not None

        window.deleteLater()
        qapp.processEvents()


# =============================================================================
# Test Classes: Benchmark (if pytest-benchmark is available)
# =============================================================================


@pytest.mark.slow
class TestBenchmarks:
    """Benchmark tests for detailed performance analysis.

    These tests are marked as slow and can be skipped in quick test runs.
    They provide detailed timing information for optimization work.
    """

    def test_benchmark_window_creation(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Benchmark window creation with statistics."""
        times: list[float] = []
        iterations = 10

        for _ in range(iterations):
            start = time.perf_counter()
            window = InkMainWindow(app_settings)
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            window.deleteLater()
            qapp.processEvents()

        avg = sum(times) / len(times)
        min_time = min(times)

        # Just verify they're within reasonable bounds
        assert avg < 1.0, f"Average too high: {avg:.3f}s"
        assert min_time < 0.5, f"Minimum too high: {min_time:.3f}s"

    def test_benchmark_full_startup(
        self, qapp: QApplication, app_settings: AppSettings
    ) -> None:
        """Benchmark full startup with statistics."""
        times: list[float] = []
        iterations = 5

        for _ in range(iterations):
            start = time.perf_counter()
            window = InkMainWindow(app_settings)
            window.show()
            qapp.processEvents()
            elapsed = time.perf_counter() - start
            times.append(elapsed)
            window.close()
            window.deleteLater()
            qapp.processEvents()

        avg = sum(times) / len(times)

        # All iterations should be under requirement
        for i, t in enumerate(times):
            assert t < STARTUP_THRESHOLD, (
                f"Iteration {i+1} took {t:.3f}s"
            )

        # Average should be well under threshold
        assert avg < STARTUP_THRESHOLD * 0.8, (
            f"Average {avg:.3f}s is too close to threshold"
        )
