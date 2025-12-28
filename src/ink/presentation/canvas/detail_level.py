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
