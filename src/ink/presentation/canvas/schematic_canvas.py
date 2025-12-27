"""Schematic canvas widget for schematic visualization.

This module provides the SchematicCanvas widget, which serves as the central
workspace area for displaying schematic diagrams. Currently implemented as
a placeholder that displays informational text; will be replaced with full
QGraphicsView-based rendering in E02 (Rendering epic).

Design Decisions:
    - Extends QWidget (not QGraphicsView) for this placeholder phase
    - Uses QVBoxLayout for simple centered placeholder layout
    - Zero margins ensure canvas fills entire central area without gaps
    - Light gray background distinguishes canvas from window chrome
    - Parent parameter follows Qt ownership model for memory management

Architecture Notes:
    - Lives in presentation layer (no domain logic)
    - Will be replaced by QGraphicsView subclass in E02
    - Interface (parent parameter, basic widget behavior) will remain stable

See Also:
    - Spec E06-F01-T02 for detailed requirements
    - E02 (Rendering) for future QGraphicsView implementation
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SchematicCanvas(QWidget):
    """Central canvas widget for schematic visualization.

    This is a placeholder implementation for the main window setup.
    It displays informational text indicating where the schematic
    rendering will appear once E02 is implemented.

    The placeholder provides:
    - Visual indication of canvas area boundaries
    - Informational text for developers/testers
    - Proper Qt parent-child relationship for memory management

    Future replacement (E02):
    - Will become QGraphicsView subclass
    - Will contain QGraphicsScene with cell, pin, net items
    - Will support zoom, pan, selection, highlighting

    Attributes:
        _PLACEHOLDER_TEXT: Text displayed in the placeholder label.
        _BACKGROUND_COLOR: Background color for the placeholder (#f0f0f0).
        _TEXT_COLOR: Text color for the placeholder (#666666).

    Args:
        parent: Parent widget (typically InkMainWindow). When parent is
            deleted, this widget is automatically deleted (Qt ownership).

    Example:
        >>> from ink.presentation.canvas import SchematicCanvas
        >>> canvas = SchematicCanvas()
        >>> canvas.show()

        With parent (recommended for memory management):
        >>> from ink.presentation.main_window import InkMainWindow
        >>> window = InkMainWindow()
        >>> canvas = SchematicCanvas(parent=window)
    """

    # Placeholder configuration constants
    # Centralized here for easy modification and testing
    _PLACEHOLDER_TEXT: str = "Schematic Canvas Area\n(Rendering implementation: E02)"
    _BACKGROUND_COLOR: str = "#f0f0f0"  # Light gray - neutral canvas background
    _TEXT_COLOR: str = "#666666"  # Dark gray - readable but not prominent
    _FONT_SIZE: str = "16px"  # Readable at default window size
    _PADDING: str = "20px"  # Comfortable padding around text

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the schematic canvas.

        Sets up the placeholder UI with a centered label displaying
        informational text. The layout uses zero margins to ensure
        the canvas fills the entire central area of the main window.

        Args:
            parent: Parent widget (typically InkMainWindow). Defaults to None
                for standalone use, but should be set for proper memory
                management in production.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure the placeholder user interface.

        Creates a vertical layout with a centered label showing placeholder
        text. The layout has zero margins to ensure the canvas fills the
        entire available space without gaps.

        Layout structure:
            SchematicCanvas (QWidget)
            └── QVBoxLayout (no margins)
                └── QLabel (centered, styled placeholder text)
        """
        # Create layout with zero margins
        # Zero margins are critical - they ensure the canvas fills
        # the entire central area without visible borders or gaps
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create and style placeholder label
        # Label shows informational text until E02 implements rendering
        placeholder = self._create_placeholder_label()
        layout.addWidget(placeholder)

    def _create_placeholder_label(self) -> QLabel:
        """Create the styled placeholder label.

        Returns:
            QLabel configured with placeholder text, center alignment,
            and styling for visual distinction.
        """
        label = QLabel(self._PLACEHOLDER_TEXT, self)

        # Center alignment provides clear visual indication
        # of canvas area boundaries
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Apply styling for visual distinction
        # - Light gray background: neutral, doesn't distract
        # - Dark gray text: readable but indicates placeholder status
        # - Larger font: visible from distance, easy to read
        # - Padding: comfortable text positioning
        label.setStyleSheet(f"""
            QLabel {{
                background-color: {self._BACKGROUND_COLOR};
                color: {self._TEXT_COLOR};
                font-size: {self._FONT_SIZE};
                padding: {self._PADDING};
            }}
        """)

        return label

    # =========================================================================
    # View Control Methods (E06-F03-T02)
    # =========================================================================
    # These methods provide the canvas API for toolbar view controls.
    # Currently no-op for placeholder; will have real implementation in E02.

    def zoom_in(self, factor: float = 1.2) -> None:
        """Zoom in by scaling factor.

        Increases the view scale by the given factor (default 1.2 = 20% increase).
        In the placeholder implementation, this is a no-op.

        Args:
            factor: Scale multiplier (default 1.2).

        Note:
            Placeholder implementation for E06-F03-T02 toolbar integration.
            Full implementation will be in E02 (Rendering epic) when this
            becomes a QGraphicsView subclass.

        See Also:
            - E02: Full rendering implementation with actual zoom
            - E06-F03-T02: Toolbar view controls
        """
        # Placeholder: No-op until E02 implements QGraphicsView with self.scale()

    def zoom_out(self, factor: float = 1.2) -> None:
        """Zoom out by inverse scaling factor.

        Decreases the view scale by the inverse of the given factor
        (default 1.2 = ~17% decrease).

        Args:
            factor: Scale divisor (default 1.2).

        Note:
            Placeholder implementation for E06-F03-T02 toolbar integration.
            Full implementation will be in E02 (Rendering epic).

        See Also:
            - E02: Full rendering implementation with actual zoom
            - E06-F03-T02: Toolbar view controls
        """
        # Placeholder: No-op until E02 implements QGraphicsView with self.scale()

    def fit_view(self) -> None:
        """Fit all visible items in view.

        Centers the scene bounding rect in the viewport while preserving
        the aspect ratio.

        Note:
            Placeholder implementation for E06-F03-T02 toolbar integration.
            Full implementation will be in E02 (Rendering epic).

        See Also:
            - E02: Full rendering implementation with actual fit
            - E06-F03-T02: Toolbar view controls
        """
        # Placeholder: No-op until E02 implements QGraphicsView with self.fitInView()
