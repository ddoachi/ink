"""CDL parsing infrastructure for Ink.

This module provides lexical analysis, parsing, and normalization for CDL
(Circuit Description Language) netlist files. CDL is a SPICE-like format
used to describe gate-level netlists.

Main Components:
- CDLLexer: Tokenizes CDL files into logical line tokens
- LineType: Enumeration of CDL line types (SUBCKT, ENDS, INSTANCE, etc.)
- CDLToken: Data class representing a tokenized line
- NetNormalizer: Normalizes and classifies net names
- SubcircuitParser: Parses .SUBCKT/.ENDS blocks into SubcircuitDefinition objects
- InstanceParser: Parses X-prefixed instance lines into CellInstance objects
"""

from ink.infrastructure.parsing.cdl_lexer import CDLLexer, CDLToken, LineType
from ink.infrastructure.parsing.instance_parser import InstanceParser
from ink.infrastructure.parsing.net_normalizer import NetNormalizer
from ink.infrastructure.parsing.subcircuit_parser import SubcircuitParser

__all__ = [
    "CDLLexer",
    "CDLToken",
    "InstanceParser",
    "LineType",
    "NetNormalizer",
    "SubcircuitParser",
]
