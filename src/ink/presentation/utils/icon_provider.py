"""Icon loading utility with system theme fallback support.

This module provides a consistent API for loading toolbar icons, preferring
system icon themes when available and falling back to bundled SVG resources
when themes are not installed. This ensures toolbar buttons always display
appropriate icons regardless of the user's system configuration.

Design Decisions:
    - Static methods: No state needed, simple utility class
    - Theme-first: Prefer native look when theme available
    - Resource fallback: Guarantee icons always available
    - Logging: Debug messages for troubleshooting icon issues

Usage:
    >>> from ink.presentation.utils.icon_provider import IconProvider
    >>> icon = IconProvider.get_icon("zoom-in")
    >>> action.setIcon(icon)

See Also:
    - Spec E06-F03-T04 for icon resources requirements
    - resources/resources.qrc for resource definitions
    - resources/icons/README.md for icon sources and licenses
"""

from __future__ import annotations

import logging
from typing import ClassVar

from PySide6.QtCore import QFile
from PySide6.QtGui import QIcon

# Import resources to register them with Qt's resource system.
# This must happen before any :/icons/* paths can be used.
# The import registers resources as a side effect.
from ink.presentation import resources_rc  # noqa: F401

logger = logging.getLogger(__name__)


class IconProvider:
    """Provides icons with system theme fallback to bundled resources.

    This class implements a two-tier icon loading strategy:
    1. First, attempt to load from system icon theme (freedesktop.org standard)
    2. If theme unavailable, fall back to bundled SVG resources

    All icons are guaranteed to load (either from theme or resource),
    ensuring toolbar buttons always have visual representation.

    The class uses static methods since no instance state is needed -
    it's purely a utility for loading icons with fallback logic.

    Attributes:
        ICON_MAP: Mapping from freedesktop icon names to Qt resource paths.

    Example:
        >>> icon = IconProvider.get_icon("document-open")
        >>> action.setIcon(icon)
        >>> assert not icon.isNull()

    See Also:
        - Spec E06-F03-T04 for icon requirements
        - resources/icons/README.md for icon attribution
    """

    # Icon name mapping: freedesktop.org name -> Qt resource path.
    # All paths use the :/icons/ prefix which refers to the <qresource prefix="icons">
    # section in resources.qrc. The actual file paths are relative to the .qrc location.
    ICON_MAP: ClassVar[dict[str, str]] = {
        "document-open": ":/icons/icons/document-open.svg",
        "edit-undo": ":/icons/icons/edit-undo.svg",
        "edit-redo": ":/icons/icons/edit-redo.svg",
        "edit-find": ":/icons/icons/edit-find.svg",
        "zoom-in": ":/icons/icons/zoom-in.svg",
        "zoom-out": ":/icons/icons/zoom-out.svg",
        "zoom-fit-best": ":/icons/icons/zoom-fit-best.svg",
    }

    @staticmethod
    def get_icon(name: str) -> QIcon:
        """Get icon by name with automatic theme fallback.

        Attempts to load icon from system theme first (for native look).
        If theme icon is not available, falls back to bundled SVG resource.

        The method handles several edge cases:
        - QIcon.fromTheme() may return non-null but empty icon (no sizes)
        - Resource files may be missing if not properly compiled
        - Unknown icon names gracefully return null icons

        Args:
            name: Icon name following freedesktop.org conventions
                  (e.g., "document-open", "edit-undo", "zoom-in").

        Returns:
            QIcon instance. Will be a valid icon from either theme or
            resource. May return null icon only if both sources fail
            (should not happen with valid icon names from ICON_MAP).

        Example:
            >>> icon = IconProvider.get_icon("zoom-in")
            >>> assert not icon.isNull()
            >>> pixmap = icon.pixmap(24, 24)
        """
        # Phase 1: Try system theme (preferred for native appearance).
        # This respects the user's desktop environment theme.
        icon = QIcon.fromTheme(name)

        # Validate theme icon: fromTheme() may return non-null but empty icon.
        # An icon with no available sizes is effectively useless, so we need
        # to check availableSizes() to verify the icon actually loaded.
        if not icon.isNull() and icon.availableSizes():
            logger.debug("Loaded icon '%s' from system theme", name)
            return icon

        # Phase 2: Fallback to bundled resource.
        # This ensures icons work even without a system theme.
        resource_path = IconProvider.ICON_MAP.get(name)
        if resource_path:
            if QFile.exists(resource_path):
                icon = QIcon(resource_path)
                if not icon.isNull():
                    logger.debug(
                        "Loaded icon '%s' from resource %s", name, resource_path
                    )
                    return icon
                logger.warning(
                    "Resource exists but failed to load: %s", resource_path
                )
            else:
                logger.warning("Resource file not found: %s", resource_path)
        else:
            logger.warning("No resource mapping for icon: %s", name)

        # Both sources failed - return null icon.
        # This should not happen with valid icon names from ICON_MAP,
        # but we handle it gracefully for unknown icon names.
        logger.error("Icon '%s' not found in theme or resources", name)
        return QIcon()

    @staticmethod
    def has_theme_icon(name: str) -> bool:
        """Check if system icon theme provides the specified icon.

        Useful for diagnostics and detecting theme availability.
        The check verifies both that the icon exists and that it
        has available sizes (some themes return empty icons).

        Args:
            name: Icon name to check following freedesktop.org conventions.

        Returns:
            True if icon available in system theme with valid sizes,
            False otherwise.

        Example:
            >>> if IconProvider.has_theme_icon("zoom-in"):
            ...     print("System theme is available")
        """
        icon = QIcon.fromTheme(name)
        has_icon = not icon.isNull() and len(icon.availableSizes()) > 0
        return has_icon

    @staticmethod
    def get_available_icons() -> list[str]:
        """Get list of all available icon names.

        Returns the list of icon names that are guaranteed to load
        via get_icon() (either from theme or bundled resources).

        Returns:
            List of icon names that can be loaded via get_icon().

        Example:
            >>> icons = IconProvider.get_available_icons()
            >>> print(f"Available icons: {len(icons)}")
            Available icons: 7
        """
        return list(IconProvider.ICON_MAP.keys())
