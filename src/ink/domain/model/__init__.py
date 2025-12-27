"""Domain model entities for the Ink schematic viewer.

This module contains the core domain entities for circuit design representation,
following Domain-Driven Design principles.

Entities:
    Cell: Gate-level cell instance (e.g., INV_X1, DFF_X1)
    Pin: Connection point on a cell
    Net: Wire connecting multiple pins
    Port: Top-level I/O of the design
    Design: Root aggregate containing all entities
"""

from ink.domain.model.cell import Cell
from ink.domain.model.design import Design
from ink.domain.model.net import Net
from ink.domain.model.pin import Pin
from ink.domain.model.port import Port

__all__ = [
    "Cell",
    "Design",
    "Net",
    "Pin",
    "Port",
]
