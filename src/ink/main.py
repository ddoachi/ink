"""Ink - Incremental Schematic Viewer application entry point.

This module provides the main entry point for the Ink application. It handles:
- Logging configuration with standardized format
- High-DPI display support configuration
- QApplication initialization with proper metadata
- Main window creation and display
- Qt event loop management
- Graceful shutdown with appropriate exit codes

The initialization sequence is carefully ordered to ensure:
1. Logging is available for all subsequent operations
2. High-DPI is configured before QApplication (Qt requirement)
3. Application metadata is set before any settings access
4. Main window is created after all configuration
5. Exit codes are properly propagated to shell

Design Decisions:
    - Separate main() function enables testing and programmatic use
    - Logging to stdout for visibility during development
    - PassThrough scaling policy for accurate fractional DPI
    - Exit code 1 for initialization failures

See Also:
    - E06-F01-T04 spec for requirements
    - E06-F01-T01 for InkMainWindow
    - docs/architecture/README.md for system architecture
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ink.infrastructure.persistence.app_settings import AppSettings
from ink.presentation.main_window import InkMainWindow


def setup_logging() -> None:
    """Configure application logging with standardized format.

    Sets up logging to stdout with INFO level and a format that includes:
    - Timestamp with milliseconds for debugging timing issues
    - Logger name to identify log source module
    - Log level for filtering and importance
    - Log message with actual content

    This should be called early in application startup to ensure
    all subsequent operations have logging available.

    Example output:
        2025-12-27 10:30:15,234 - ink.main - INFO - Starting Ink application
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def configure_high_dpi() -> None:
    """Configure high-DPI display support.

    Must be called BEFORE creating QApplication. This function sets up:
    - PassThrough scaling policy for accurate fractional scaling (1.5x, 1.75x)
    - This avoids rounding artifacts on displays with non-integer scale factors

    High-DPI support ensures Ink looks crisp on:
    - 4K displays (200% scaling)
    - 5K displays (typically 200% or more)
    - Fractional scaling (125%, 150%, 175%)

    Calling this after QApplication creation has no effect (Qt limitation).

    See Also:
        - Qt High DPI documentation: https://doc.qt.io/qt-6/highdpi.html
    """
    # Set rounding policy before QApplication is created
    # PassThrough gives the most accurate scaling without rounding
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )


def main() -> int:
    """Application entry point - initializes and runs Ink.

    This is the main function that:
    1. Sets up logging for visibility into startup
    2. Configures high-DPI support (before QApplication)
    3. Creates QApplication with command-line arguments
    4. Sets application metadata for Qt settings storage
    5. Creates and shows the main window
    6. Starts the Qt event loop
    7. Returns exit code for shell integration

    Returns:
        Exit code: 0 for successful exit, 1 for initialization failure.

    Example:
        >>> # Run application
        >>> exit_code = main()
        >>> sys.exit(exit_code)

    Raises:
        No exceptions raised - all are caught and logged.
        Errors result in exit code 1 instead.
    """
    # Step 1: Setup logging first for visibility into all operations
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Ink application")

    # Step 2: Configure high-DPI BEFORE QApplication creation (Qt requirement)
    configure_high_dpi()

    # Step 3: Create Qt application instance
    # sys.argv is passed for potential Qt command-line argument parsing
    app = QApplication(sys.argv)

    # Step 4: Set application metadata
    # These are used by Qt for:
    # - Settings file location: ~/.config/InkProject/Ink.conf
    # - Desktop integration (window grouping, taskbar)
    # - Future: About dialog, system notifications
    app.setApplicationName("Ink")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("InkProject")
    app.setOrganizationDomain("github.com/inkproject")

    logger.info(f"Ink version {app.applicationVersion()}")

    # Step 5: Create and show main window
    try:
        # Create settings manager for window state persistence
        app_settings = AppSettings()

        # Create main window with settings injection
        window = InkMainWindow(app_settings)
        window.show()
        logger.info("Main window displayed")
    except Exception as e:
        # Log the error with full traceback for debugging
        logger.critical(f"Failed to create main window: {e}", exc_info=True)
        return 1

    # Step 6: Start event loop
    logger.info("Starting Qt event loop")
    exit_code = app.exec()

    # Step 7: Log exit and return code
    logger.info(f"Application exiting with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    # Allow running directly: python src/ink/main.py
    sys.exit(main())
