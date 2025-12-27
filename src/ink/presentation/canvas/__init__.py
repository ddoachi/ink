"""Canvas widgets for schematic visualization.

This package provides the canvas components for rendering and interacting
with schematic diagrams. The central component is SchematicCanvas, which
serves as the primary workspace for schematic visualization.

Current implementation (E06-F01-T02):
    - SchematicCanvas: Placeholder widget for main window central area

E02 - Rendering Epic Components:
    - CellItem (E02-F01-T01): QGraphicsItem for cell symbol rendering
    - SymbolLayoutCalculator (E02-F01-T03): Pin position calculation
    - DetailLevel (E02-F01-T05): Level of Detail enum for rendering optimization

Future implementation (E02 - Rendering):
    - Full QGraphicsView-based rendering with QGraphicsScene
    - Pin and net visualization
    - Zoom and pan functionality
    - Selection and highlighting

Example:
    >>> from ink.presentation.canvas import SchematicCanvas, CellItem, DetailLevel
    >>> canvas = SchematicCanvas()
    >>> canvas.show()
"""

from ink.presentation.canvas.cell_item import CellItem
from ink.presentation.canvas.detail_level import DetailLevel
from ink.presentation.canvas.schematic_canvas import SchematicCanvas
from ink.presentation.canvas.symbol_layout_calculator import (
    PinLayout,
    SymbolLayoutCalculator,
)

__all__ = [
    "CellItem",
    "DetailLevel",
    "PinLayout",
    "SchematicCanvas",
    "SymbolLayoutCalculator",
]
