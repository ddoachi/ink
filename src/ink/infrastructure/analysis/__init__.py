"""Infrastructure analysis module for transistor topology extraction.

This module provides services for analyzing transistor-level subcircuit definitions
to extract signal flow graphs. The primary use case is detecting sequential elements
(latches, flip-flops) by identifying feedback loops in the internal topology.

Components:
    - TopologyAnalyzer: Protocol for topology analysis services
    - TransistorInstance: Dataclass representing a transistor in a subcircuit
    - CellInstance: Dataclass representing a subcircuit instance
    - SubcircuitDefinition: Dataclass representing a parsed subcircuit
    - SignalFlowGraph: Dataclass representing extracted signal flow

    - TransistorPatternRecognizer: Recognizes common transistor patterns
    - TransistorTopologyAnalyzer: Main implementation of TopologyAnalyzer

See Also:
    - Spec E01-F04-T04 for requirements
    - TopologyBasedLatchIdentifier for integration
"""

from ink.infrastructure.analysis.topology_analyzer import (
    CellInstance,
    SignalFlowGraph,
    SubcircuitDefinition,
    TopologyAnalyzer,
    TransistorInstance,
)
from ink.infrastructure.analysis.transistor_patterns import (
    RecognizedStructure,
    StructureType,
    TransistorPatternRecognizer,
)
from ink.infrastructure.analysis.transistor_topology_analyzer import (
    TransistorTopologyAnalyzer,
)

__all__ = [
    "CellInstance",
    "RecognizedStructure",
    "SignalFlowGraph",
    "StructureType",
    "SubcircuitDefinition",
    "TopologyAnalyzer",
    "TransistorInstance",
    "TransistorPatternRecognizer",
    "TransistorTopologyAnalyzer",
]
