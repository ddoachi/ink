"""Presentation layer utilities for the Ink schematic viewer.

This package provides utility classes and functions used across the
presentation layer, including icon management and other UI helpers.

Exports:
    IconProvider: Icon loading utility with theme fallback support.

See Also:
    - Spec E06-F03-T04 for icon resources requirements
"""

from ink.presentation.utils.icon_provider import IconProvider

__all__ = ["IconProvider"]
