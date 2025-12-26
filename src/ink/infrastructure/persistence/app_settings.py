r"""Application settings manager using QSettings.

This module provides the AppSettings class which wraps Qt's QSettings
to provide a clean, type-safe API for platform-native settings storage.

Design Decisions:
    - Uses QSettings for platform-native storage (INI on Linux, Registry on Windows,
      plist on macOS) which provides automatic persistence without file handling
    - Settings keys use hierarchical namespacing (e.g., "geometry/window") for
      organization and to prevent collisions
    - Type conversion is handled through the optional value_type parameter to
      ensure correct Python types are returned
    - Default values are initialized on first run to ensure consistent state

Storage Locations:
    - Linux: ~/.config/InkProject/Ink.conf (INI format)
    - Windows: HKEY_CURRENT_USER\Software\InkProject\Ink (Registry)
    - macOS: ~/Library/Preferences/com.InkProject.Ink.plist

See Also:
    - Spec E06-F06-T01 for detailed requirements
    - Qt QSettings documentation for platform behavior details
    - E06-F06-T02 (Window Geometry Persistence) - uses this class
    - E06-F06-T03 (Recent Files Management) - uses this class
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QSettings


class AppSettings:
    """Application settings manager using QSettings.

    Provides centralized access to persisted application settings
    using Qt's platform-native storage mechanism. This class wraps
    QSettings to provide a cleaner, more Pythonic API with type
    conversion support.

    The class handles:
    - Platform-native storage (automatic per-OS behavior)
    - Type conversion for common Python types
    - Default value initialization on first run
    - Hierarchical key organization

    Attributes:
        KEY_WINDOW_GEOMETRY: Key for storing window geometry (position/size).
        KEY_WINDOW_STATE: Key for storing window state (maximized, etc.).
        KEY_RECENT_FILES: Key for storing list of recently opened files.
        KEY_MAX_RECENT: Key for maximum number of recent files to track.
        KEY_SETTINGS_VERSION: Key for settings schema version (for migrations).
        CURRENT_VERSION: Current settings schema version.
        DEFAULT_MAX_RECENT: Default maximum number of recent files.
        settings: Underlying QSettings instance for direct access if needed.

    Example:
        >>> from ink.infrastructure.persistence.app_settings import AppSettings
        >>> settings = AppSettings()
        >>> settings.set_value("user/name", "John")
        >>> name = settings.get_value("user/name")
        >>> print(name)
        John

    See Also:
        - E06-F06-T02: Window geometry persistence using KEY_WINDOW_GEOMETRY
        - E06-F06-T03: Recent files using KEY_RECENT_FILES
        - E06-F06-T04: Settings migration using KEY_SETTINGS_VERSION
    """

    # =========================================================================
    # Settings Keys - Organized by Category
    # =========================================================================
    # Using hierarchical keys (category/name) for organization and to prevent
    # collisions. This matches QSettings convention and makes debugging easier
    # when viewing the settings file directly.

    # Window geometry keys - for restoring window position/size/state
    KEY_WINDOW_GEOMETRY: str = "geometry/window"
    KEY_WINDOW_STATE: str = "geometry/state"

    # File management keys - for recent files list
    KEY_RECENT_FILES: str = "files/recent"
    KEY_MAX_RECENT: str = "files/max_recent"

    # Metadata keys - for versioning and migration support
    KEY_SETTINGS_VERSION: str = "meta/version"

    # =========================================================================
    # Constants
    # =========================================================================

    # Current settings schema version - increment when making breaking changes
    # to settings structure that require migration. See E06-F06-T04 for
    # migration implementation.
    CURRENT_VERSION: int = 1

    # Default maximum number of recent files to display in File menu.
    # 10 is a common default that balances usefulness with menu length.
    DEFAULT_MAX_RECENT: int = 10

    def __init__(self) -> None:
        r"""Initialize settings with platform-native storage.

        Creates a QSettings instance configured for the InkProject/Ink
        application. QSettings automatically determines the appropriate
        storage location based on the operating system:

        - Linux: ~/.config/InkProject/Ink.conf (INI format)
        - Windows: Registry HKEY_CURRENT_USER\Software\InkProject\Ink
        - macOS: ~/Library/Preferences/com.InkProject.Ink.plist

        On first run, default values are initialized to ensure consistent
        application state. This is detected by checking for the presence
        of the KEY_SETTINGS_VERSION key.
        """
        # Create QSettings with organization and application names.
        # These names determine the storage location path.
        self.settings = QSettings("InkProject", "Ink")

        # Initialize default values on first run
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default settings on first run.

        This method is called during __init__ to set up default values
        when the application runs for the first time (detected by the
        absence of KEY_SETTINGS_VERSION).

        Default values include:
        - Settings version for migration tracking
        - Maximum recent files count
        - Empty recent files list

        This ensures the application has a consistent initial state and
        that all expected keys exist, preventing None checks throughout
        the codebase.
        """
        # Check if this is first run by looking for version key
        if not self.has_key(self.KEY_SETTINGS_VERSION):
            # First run - set all default values
            self.set_value(self.KEY_SETTINGS_VERSION, self.CURRENT_VERSION)
            self.set_value(self.KEY_MAX_RECENT, self.DEFAULT_MAX_RECENT)
            self.set_value(self.KEY_RECENT_FILES, [])

            # Force write to disk to ensure defaults persist even if
            # application crashes before normal shutdown
            self.sync()

    def get_value(
        self, key: str, default: Any = None, value_type: type | None = None
    ) -> Any:
        """Get a setting value with optional type conversion.

        Retrieves the value associated with the given key. If the key
        doesn't exist, returns the specified default value. If value_type
        is provided, QSettings will attempt to convert the stored value
        to that type.

        Args:
            key: Settings key (e.g., "geometry/window"). Uses hierarchical
                 naming with "/" as separator.
            default: Default value to return if key doesn't exist.
                     Defaults to None.
            value_type: Expected Python type for conversion (e.g., int, bool,
                        str, QByteArray). If None, returns value as-is.

        Returns:
            The setting value, or default if key doesn't exist.
            Type depends on value_type parameter and stored data.

        Example:
            >>> settings = AppSettings()
            >>> settings.set_value("user/age", 25)
            >>> age = settings.get_value("user/age", value_type=int)
            >>> print(age, type(age))
            25 <class 'int'>

        Note:
            For QByteArray (used for window geometry/state), always specify
            value_type=QByteArray to ensure correct deserialization.
        """
        if value_type is not None:
            # Use QSettings type conversion when type is specified
            # This is important for int/bool which may be stored as strings
            return self.settings.value(key, default, type=value_type)
        return self.settings.value(key, default)

    def set_value(self, key: str, value: Any) -> None:
        """Set a setting value.

        Stores the given value under the specified key. QSettings handles
        serialization automatically for common types (str, int, bool, list,
        QByteArray, etc.).

        Args:
            key: Settings key (e.g., "geometry/window"). Uses hierarchical
                 naming with "/" as separator.
            value: Value to store. Must be a type supported by QSettings:
                   - Basic types: str, int, float, bool
                   - Collections: list (will be serialized)
                   - Qt types: QByteArray, QSize, QPoint, etc.

        Example:
            >>> settings = AppSettings()
            >>> settings.set_value("user/name", "Alice")
            >>> settings.set_value("window/width", 1024)
            >>> settings.set_value("recent/files", ["a.ckt", "b.ckt"])

        Note:
            Values are not immediately written to disk. Call sync() to
            force immediate write, or rely on automatic write on
            QSettings destruction or application exit.
        """
        self.settings.setValue(key, value)

    def has_key(self, key: str) -> bool:
        """Check if a setting key exists.

        Useful for determining whether a setting has been explicitly set,
        as opposed to relying on default values.

        Args:
            key: Settings key to check.

        Returns:
            True if the key exists in settings, False otherwise.

        Example:
            >>> settings = AppSettings()
            >>> settings.has_key("nonexistent")
            False
            >>> settings.set_value("test", "value")
            >>> settings.has_key("test")
            True
        """
        return self.settings.contains(key)

    def remove_key(self, key: str) -> None:
        """Remove a setting key.

        Deletes the key and its associated value from settings.
        If the key doesn't exist, this method does nothing (no error).

        This can be used to reset a specific setting to its default
        value on next access.

        Args:
            key: Settings key to remove.

        Example:
            >>> settings = AppSettings()
            >>> settings.set_value("temp/value", 123)
            >>> settings.remove_key("temp/value")
            >>> settings.has_key("temp/value")
            False
        """
        self.settings.remove(key)

    def get_all_keys(self) -> list[str]:
        """Get all setting keys.

        Returns a list of all keys currently stored in settings.
        Useful for debugging, migration, or settings export.

        Returns:
            List of all setting keys as strings.

        Example:
            >>> settings = AppSettings()
            >>> settings.set_value("a", 1)
            >>> settings.set_value("b", 2)
            >>> keys = settings.get_all_keys()
            >>> "a" in keys and "b" in keys
            True
        """
        return list(self.settings.allKeys())

    def get_settings_file_path(self) -> str:
        """Get path to settings file.

        Returns the absolute path where settings are stored. This is
        useful for debugging, support, and backup purposes.

        Note that on Windows, this returns a registry path which is
        not a file path. On Linux and macOS, it's an actual file path.

        Returns:
            Absolute path to settings storage location.

        Example:
            >>> settings = AppSettings()
            >>> path = settings.get_settings_file_path()
            >>> print(path)  # On Linux
            /home/user/.config/InkProject/Ink.conf
        """
        return self.settings.fileName()

    def sync(self) -> None:
        """Force write settings to disk.

        Normally Qt handles settings persistence automatically when the
        QSettings object is destroyed or the application exits cleanly.
        This method forces an immediate write, which is useful when:

        - You want to ensure settings survive a crash
        - You're making critical settings changes
        - You need settings available to another process immediately

        Example:
            >>> settings = AppSettings()
            >>> settings.set_value("important/setting", "value")
            >>> settings.sync()  # Ensure it's written immediately
        """
        self.settings.sync()

    # =========================================================================
    # Recent Files Management Methods
    # =========================================================================
    # These methods manage the list of recently opened files, providing:
    # - Adding files to the list (with move-to-front for duplicates)
    # - Retrieving the list (with automatic filtering of non-existent files)
    # - Clearing the list
    # - Configuring maximum list size

    def add_recent_file(self, file_path: str) -> None:
        """Add a file to the recent files list.

        The file is added to the front of the list (most recent first).
        If the file already exists in the list, it is moved to the front
        instead of creating a duplicate. The list is automatically trimmed
        to respect the maximum recent files limit.

        This method normalizes the path to an absolute path before storing
        to ensure consistent matching across sessions.

        Args:
            file_path: Path to the file (relative or absolute). Will be
                       converted to an absolute path.

        Example:
            >>> settings = AppSettings()
            >>> settings.add_recent_file("/path/to/design.ckt")
            >>> recent = settings.get_recent_files()
            >>> "/path/to/design.ckt" in recent
            True

        See Also:
            - get_recent_files: Retrieve the current list
            - clear_recent_files: Clear all entries
            - get_max_recent_files: Get the maximum list size
        """
        # Normalize to absolute path for consistent storage
        # This resolves relative paths and symlinks
        normalized_path = str(Path(file_path).resolve())

        # Get current list of recent files
        recent = self._get_raw_recent_files()

        # Remove if already exists (will re-add at front to update position)
        if normalized_path in recent:
            recent.remove(normalized_path)

        # Insert at front (newest first)
        recent.insert(0, normalized_path)

        # Trim to maximum allowed size
        max_recent = self.get_max_recent_files()
        recent = recent[:max_recent]

        # Persist the updated list
        self.set_value(self.KEY_RECENT_FILES, recent)

    def get_recent_files(self) -> list[str]:
        """Get the list of recently opened files.

        Returns a list of file paths ordered by most recently opened first.
        Non-existent files are automatically filtered out and the stored
        list is updated if any files were removed.

        This lazy cleanup approach means:
        - No background tasks are needed to maintain the list
        - Files deleted outside the app are cleaned up on next access
        - The UI always shows only files that can be opened

        Returns:
            List of absolute file paths as strings, newest first.
            Empty list if no recent files exist.

        Example:
            >>> settings = AppSettings()
            >>> recent = settings.get_recent_files()
            >>> for path in recent:
            ...     print(path)
            /home/user/projects/latest.ckt
            /home/user/projects/previous.ckt

        See Also:
            - add_recent_file: Add a file to the list
            - clear_recent_files: Clear all entries
        """
        # Get raw list from storage
        files = self._get_raw_recent_files()

        # Filter out non-existent files
        # This handles files that were deleted outside the application
        existing_files = [f for f in files if Path(f).exists()]

        # If any files were removed, update the stored list to keep it clean
        # This prevents the list from accumulating dead entries over time
        if len(existing_files) < len(files):
            self.set_value(self.KEY_RECENT_FILES, existing_files)

        return existing_files

    def _get_raw_recent_files(self) -> list[str]:
        """Get the raw recent files list without existence filtering.

        This internal method retrieves the stored list and ensures all
        entries are valid strings, but does not check file existence.
        Used by add_recent_file to avoid unnecessary file system checks.

        Returns:
            List of stored file paths as strings.
        """
        files = self.get_value(self.KEY_RECENT_FILES, [], value_type=list)

        # Ensure all entries are non-empty strings
        # This handles potential corruption or type coercion issues
        return [str(f) for f in files if f]

    def clear_recent_files(self) -> None:
        """Clear the recent files list.

        Removes all entries from the recent files list. This operation
        is immediate and persists on next sync.

        Example:
            >>> settings = AppSettings()
            >>> settings.add_recent_file("design.ckt")
            >>> settings.clear_recent_files()
            >>> len(settings.get_recent_files())
            0

        See Also:
            - get_recent_files: Retrieve the current list
            - add_recent_file: Add files back to the list
        """
        self.set_value(self.KEY_RECENT_FILES, [])

    def get_max_recent_files(self) -> int:
        """Get the maximum number of recent files to remember.

        This limit determines how many files are kept in the recent files
        list. When the limit is exceeded, the oldest files are removed.

        Returns:
            Maximum number of recent files (default: 10).

        Example:
            >>> settings = AppSettings()
            >>> max_files = settings.get_max_recent_files()
            >>> print(max_files)
            10

        See Also:
            - set_max_recent_files: Change the maximum
            - DEFAULT_MAX_RECENT: The default value constant
        """
        result = self.get_value(
            self.KEY_MAX_RECENT,
            self.DEFAULT_MAX_RECENT,
            value_type=int,
        )
        return int(result) if result is not None else self.DEFAULT_MAX_RECENT

    def set_max_recent_files(self, max_count: int) -> None:
        """Set the maximum number of recent files to remember.

        Changes the limit for the recent files list. If the current list
        exceeds the new limit, it is immediately trimmed to fit.

        Args:
            max_count: New maximum count. Must be >= 1.

        Raises:
            ValueError: If max_count is less than 1.

        Example:
            >>> settings = AppSettings()
            >>> settings.set_max_recent_files(5)
            >>> settings.get_max_recent_files()
            5

        See Also:
            - get_max_recent_files: Get the current maximum
        """
        if max_count < 1:
            msg = "max_count must be >= 1"
            raise ValueError(msg)

        self.set_value(self.KEY_MAX_RECENT, max_count)

        # Trim existing list if it now exceeds the new maximum
        # This ensures immediate consistency with the new setting
        recent = self._get_raw_recent_files()
        if len(recent) > max_count:
            self.set_value(self.KEY_RECENT_FILES, recent[:max_count])
