"""Canvas widgets for schematic visualization.

This package provides the canvas components for rendering and interacting
with schematic diagrams. The central component is SchematicCanvas, which
serves as the primary workspace for schematic visualization.

Current implementation (E06-F01-T02):
    - SchematicCanvas: Placeholder widget for main window central area

Future implementation (E02 - Rendering):
    - Full QGraphicsView-based rendering with QGraphicsScene
    - Cell, pin, and net visualization
    - Zoom and pan functionality
    - Selection and highlighting

Example:
    >>> from ink.presentation.canvas import SchematicCanvas
    >>> canvas = SchematicCanvas()
    >>> canvas.show()
"""

from ink.presentation.canvas.schematic_canvas import SchematicCanvas

__all__ = ["SchematicCanvas"]
