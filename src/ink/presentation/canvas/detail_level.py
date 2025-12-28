"""Detail level enum for Level of Detail (LOD) rendering.

This module defines the DetailLevel enum which controls the level of detail
used when rendering schematic elements. Different detail levels allow the
rendering system to optimize performance by showing less detail when zoomed
out, and full detail when zoomed in.

Architecture Notes:
    - DetailLevel is a presentation-layer concept (no domain impact)
    - Used by CellItem, NetItem, and other graphics items
    - Level selection is typically driven by zoom factor in SchematicCanvas

Usage:
    Each graphics item can have its detail level set independently, allowing
    for smooth transitions as the user zooms in and out. The typical mapping:

    - MINIMAL: Zoom < 25% - Simple solid rectangle, no text
    - BASIC: 25% <= Zoom < 75% - Rectangle with cell name
    - FULL: Zoom >= 75% - Full detail with all visual indicators

Example:
    >>> from ink.presentation.canvas.detail_level import DetailLevel
    >>> from ink.presentation.canvas.cell_item import CellItem
    >>>
    >>> # Set detail level based on zoom factor
    >>> cell_item = CellItem(cell)
    >>> cell_item.set_detail_level(DetailLevel.FULL)
    >>>
    >>> # Check current detail level
    >>> if cell_item.get_detail_level() == DetailLevel.FULL:
    ...     print("Showing full details including clock indicator")

See Also:
    - Spec E02-F01-T04 for zoom-based LOD requirements
    - Spec E02-F01-T05 for sequential cell clock indicator (FULL only)
"""

from __future__ import annotations

from enum import IntEnum

# =============================================================================
# Zoom Threshold Constants (E02-F01-T04)
# =============================================================================
# These define the zoom level boundaries for detail level transitions.
# Defined at module level to avoid mypy issues with Enum member annotations.

MINIMAL_THRESHOLD: float = 0.25
"""Zoom threshold for MINIMAL level. Below this: show minimal detail."""

FULL_THRESHOLD: float = 0.75
"""Zoom threshold for FULL level. At or above this: show full detail."""


class DetailLevel(IntEnum):
    """Enumeration of rendering detail levels for schematic items.

    DetailLevel controls how much visual information is rendered for
    schematic elements. Higher values indicate more detail. The enum
    uses IntEnum for easy comparison operations (MINIMAL < BASIC < FULL).

    Detail Level Behavior:
        MINIMAL (0):
            - Zoomed out view (< 25% zoom)
            - Simple solid fill rectangle
            - No text labels
            - No visual indicators (icons, symbols)
            - Fastest rendering for overview

        BASIC (1):
            - Standard view (25% - 75% zoom)
            - Rectangle with border styling
            - Cell name displayed
            - Sequential cell distinction (border width, fill color)
            - No optional indicators (clock icon hidden)
            - Good balance of detail and performance

        FULL (2):
            - Zoomed in view (>= 75% zoom)
            - All visual elements rendered
            - Cell name with full text (no elision if possible)
            - Clock indicator for sequential cells
            - Pin labels and details visible
            - Highest fidelity rendering

    Attributes:
        MINIMAL: Simplest rendering for zoomed-out overview (value: 0)
        BASIC: Standard rendering with cell names (value: 1)
        FULL: Complete rendering with all visual indicators (value: 2)

    Example:
        >>> # Compare detail levels
        >>> DetailLevel.MINIMAL < DetailLevel.BASIC
        True
        >>> DetailLevel.FULL > DetailLevel.BASIC
        True
        >>>
        >>> # Use in conditional rendering
        >>> if detail_level >= DetailLevel.BASIC:
        ...     draw_cell_name()
        >>> if detail_level == DetailLevel.FULL:
        ...     draw_clock_indicator()
    """

    MINIMAL = 0
    """Simplest rendering level for zoomed-out overview.

    At this level, cells are rendered as simple colored rectangles without
    any text or visual indicators. This provides the fastest rendering for
    navigation and overview purposes.
    """

    BASIC = 1
    """Standard rendering level with cell names.

    At this level, cells show their instance name and have visual distinction
    between sequential and combinational cells (border width, fill color).
    This is the default rendering level.
    """

    FULL = 2
    """Complete rendering level with all visual indicators.

    At this level, all visual elements are rendered including:
    - Cell instance name
    - Sequential cell distinction (border, fill)
    - Clock indicator icon for sequential cells
    - Pin details when visible

    This level provides the highest fidelity for detailed work.
    """

    # =========================================================================
    # Factory Method - Zoom-Based LOD Selection (E02-F01-T04)
    # =========================================================================

    @classmethod
    def from_zoom(cls, zoom_factor: float) -> DetailLevel:
        """Determine the appropriate detail level based on zoom factor.

        This factory method maps zoom levels to detail levels using the
        following thresholds:
        - MINIMAL: zoom_factor < 0.25 (less than 25%)
        - BASIC: 0.25 <= zoom_factor < 0.75 (25% to 75%)
        - FULL: zoom_factor >= 0.75 (75% and above)

        The thresholds are chosen to provide:
        - Optimal performance when zoomed out (MINIMAL reduces rendering)
        - Balanced detail at moderate zoom (BASIC shows cell names)
        - Full information when zoomed in (FULL shows all details)

        Args:
            zoom_factor: Current zoom level where 1.0 = 100%.
                Values range from ~0.1 (10%) to ~5.0 (500%).
                Negative or very small values are treated as MINIMAL.

        Returns:
            DetailLevel: The appropriate detail level for the given zoom.

        Example:
            >>> DetailLevel.from_zoom(0.1)
            DetailLevel.MINIMAL
            >>> DetailLevel.from_zoom(0.5)
            DetailLevel.BASIC
            >>> DetailLevel.from_zoom(1.0)
            DetailLevel.FULL

        Note:
            This method is called frequently during zoom animations, so it
            must be efficient. Simple threshold comparisons ensure O(1)
            performance.

        See Also:
            - Spec E02-F01-T04 for zoom LOD requirements
            - SchematicCanvas._apply_zoom() for usage context
        """
        # Handle edge cases: negative or very small values → MINIMAL
        # This provides graceful degradation for invalid zoom values
        if zoom_factor < MINIMAL_THRESHOLD:
            return cls.MINIMAL

        # Mid-range zoom: 25% to 75% → BASIC detail
        # Shows cell names but not full pin details
        if zoom_factor < FULL_THRESHOLD:
            return cls.BASIC

        # High zoom: 75% and above → FULL detail
        # Shows all visual elements including clock indicators and pin arrows
        return cls.FULL
