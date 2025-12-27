"""Domain model entities for the Ink schematic viewer.

This module contains the core domain entities (aggregates) for circuit design
representation, following Domain-Driven Design principles.

Entities:
    Design: Root aggregate containing cells, nets, and ports.
"""

from ink.domain.model.design import Design

__all__ = ["Design"]
