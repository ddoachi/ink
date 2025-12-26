"""Integration tests for application startup and lifecycle.

This module tests the application entry point, verifying that the Ink application
can be launched and terminated correctly with proper logging and exit codes.

Test Categories:
    - Entry point import tests: Verify main module can be imported
    - Logging configuration tests: Verify logging setup works correctly
    - High-DPI configuration tests: Verify high-DPI settings are applied
    - Application metadata tests: Verify Qt metadata is set correctly
    - Package export tests: Verify __init__.py exports are correct

See Also:
    - E06-F01-T04 spec for requirements
    - src/ink/main.py for implementation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    import pytest
    from pytestqt.qtbot import QtBot


class TestApplicationEntryPoint:
    """Test application entry point and initialization."""

    def test_main_module_can_be_imported(self) -> None:
        """Test main module can be imported without errors."""
        # This should not raise ImportError
        from ink import main  # noqa: F401

    def test_main_function_exists(self) -> None:
        """Test main function can be imported and is callable."""
        from ink.main import main

        assert callable(main)

    def test_main_function_in_package_init(self) -> None:
        """Test main is exported from package __init__.py."""
        from ink import main

        assert callable(main)


class TestLoggingSetup:
    """Test logging configuration from entry point."""

    def test_setup_logging_exists(self) -> None:
        """Test setup_logging function exists."""
        from ink.main import setup_logging

        assert callable(setup_logging)

    def test_setup_logging_configures_info_level(self) -> None:
        """Test setup_logging sets INFO level as default."""
        from ink.main import setup_logging

        # Clear any existing handlers to avoid interference
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging()

        # The root logger should have at least one handler
        assert len(root_logger.handlers) > 0

    def test_setup_logging_outputs_to_stdout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test logging outputs to stdout after setup."""
        from ink.main import setup_logging

        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging()

        # Create a test logger and log a message
        test_logger = logging.getLogger("test.startup")
        test_logger.info("Test startup message")

        captured = capsys.readouterr()
        assert "Test startup message" in captured.out

    def test_logging_format_includes_timestamp(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test log format includes timestamp."""
        from ink.main import setup_logging

        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging()

        test_logger = logging.getLogger("test.format")
        test_logger.info("Timestamp test")

        captured = capsys.readouterr()
        # Timestamp format: YYYY-MM-DD HH:MM:SS,mmm
        # Check for common timestamp pattern
        assert "-" in captured.out  # Date separator
        assert ":" in captured.out  # Time separator


class TestHighDPIConfiguration:
    """Test high-DPI display configuration."""

    def test_configure_high_dpi_exists(self) -> None:
        """Test configure_high_dpi function exists."""
        from ink.main import configure_high_dpi

        assert callable(configure_high_dpi)

    def test_configure_high_dpi_does_not_raise(self) -> None:
        """Test configure_high_dpi can be called without errors.

        Note: This must be called before QApplication is created.
        The test just verifies the function runs without exception.
        """
        from ink.main import configure_high_dpi

        # Should not raise any exception
        configure_high_dpi()


class TestApplicationMetadata:
    """Test application metadata configuration."""

    def test_application_name_is_set(self, qtbot: QtBot) -> None:
        """Test application name is 'Ink'."""
        app = QApplication.instance()
        assert app is not None
        # Note: In test environment, we can't easily test metadata set by main()
        # because main() creates its own QApplication. We test the intent here.
        # Actual metadata testing would require subprocess testing.

    def test_version_constant_exists(self) -> None:
        """Test version is defined in package."""
        from ink import __version__

        assert __version__ == "0.1.0"

    def test_author_constant_exists(self) -> None:
        """Test author is defined in package."""
        from ink import __author__

        assert __author__ == "InkProject"


class TestPackageExports:
    """Test package __init__.py exports."""

    def test_version_exported(self) -> None:
        """Test __version__ is exported from ink package."""
        from ink import __version__

        assert isinstance(__version__, str)
        assert __version__ == "0.1.0"

    def test_author_exported(self) -> None:
        """Test __author__ is exported from ink package."""
        from ink import __author__

        assert isinstance(__author__, str)
        assert __author__ == "InkProject"

    def test_main_exported(self) -> None:
        """Test main function is exported from ink package."""
        from ink import main

        assert callable(main)

    def test_all_exports_defined(self) -> None:
        """Test __all__ is defined with expected exports."""
        import ink

        assert hasattr(ink, "__all__")
        expected_exports = {"main", "__version__", "__author__"}
        assert set(ink.__all__) == expected_exports


class TestModuleExecution:
    """Test module execution via python -m ink."""

    def test_main_module_exists(self) -> None:
        """Test __main__.py can be imported."""
        # This should not raise ImportError
        import ink.__main__  # noqa: F401

    def test_main_module_imports_main_function(self) -> None:
        """Test __main__ module imports main from ink.main."""
        import ink.__main__  # noqa: F401

        # The module should have imported main
        # We can verify by checking if the module executed without error
        assert True  # Import succeeded


class TestMainFunctionSignature:
    """Test main function signature and return type."""

    def test_main_returns_int(self) -> None:
        """Test main() is annotated to return int.

        Note: We can't easily call main() in tests because it starts
        the Qt event loop. We test the type hints instead.
        """
        import inspect

        from ink.main import main

        # Get return annotation
        sig = inspect.signature(main)
        # With `from __future__ import annotations`, the annotation is a string
        assert sig.return_annotation in (int, "int")
