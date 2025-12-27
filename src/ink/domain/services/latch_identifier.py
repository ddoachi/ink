"""Domain service protocol for sequential element identification.

This module defines the LatchIdentifier protocol, which is the domain service
interface for identifying sequential elements (latches, flip-flops) in a netlist.

The protocol defines the contract that any implementation must satisfy. The actual
implementation (TopologyBasedLatchIdentifier) lives in the infrastructure layer.

Detection Strategies (Priority Order):
    1. Feedback Loop: Detect cross-coupled gates via cycle detection (highest reliability)
    2. Explicit Annotation: User-provided list of sequential cell types
    3. Pin Signature: Detect by characteristic pins (CLK, D, Q patterns)
    4. Pattern Matching: Fallback using glob patterns on cell type names (lowest)

Architecture:
    This protocol lives in the domain layer with no external dependencies.
    It follows the DDD pattern of defining interfaces in the domain layer
    while implementations reside in the infrastructure layer.

See Also:
    - TopologyBasedLatchIdentifier in infrastructure/identification/
    - Spec E01-F04-T02 for requirements
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Set


class DetectionStrategy(Enum):
    """Strategy used to detect sequential elements (ordered by reliability).

    The strategies are listed in order of decreasing reliability:
    - FEEDBACK_LOOP: Most reliable - detects structural feedback
    - EXPLICIT: High reliability - user-provided annotations
    - PIN_SIGNATURE: Medium reliability - relies on pin naming conventions
    - PATTERN_MATCH: Low reliability - relies on cell naming conventions
    - UNKNOWN: Could not determine strategy
    """

    FEEDBACK_LOOP = "feedback_loop"
    EXPLICIT = "explicit"
    PIN_SIGNATURE = "pin_signature"
    PATTERN_MATCH = "pattern_match"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SequentialDetectionResult:
    """Result of sequential element detection with reasoning.

    This value object encapsulates the result of a sequential element
    detection query, including the detection method used and a human-readable
    explanation.

    Attributes:
        is_sequential: True if the cell was detected as sequential
        strategy: The detection strategy that was used
        confidence: Confidence level from 0.0 to 1.0
        reason: Human-readable explanation of the detection
    """

    is_sequential: bool
    strategy: DetectionStrategy
    confidence: float
    reason: str


class LatchIdentifier(Protocol):
    """Domain service protocol for identifying sequential elements by topology.

    This protocol defines the contract for sequential element detection.
    Implementations should support multiple detection strategies with
    configurable priority.

    The primary detection method is feedback loop analysis, which is
    naming-independent and provides the highest reliability.
    """

    def is_sequential(self, cell_type: str, pin_names: Set[str] | None = None) -> bool:
        """Check if a cell type represents a sequential element.

        Detection priority:
        1. Feedback loop in registered topology (highest reliability)
        2. Explicit annotation
        3. Pin signature analysis (if pin_names provided)
        4. Pattern matching on cell_type (lowest reliability)

        Args:
            cell_type: Cell type name (e.g., "DFFR_X1", "MY_CUSTOM_FF")
            pin_names: Optional set of pin names for signature analysis

        Returns:
            True if cell is detected as sequential, False otherwise
        """
        ...

    def detect_with_reason(
        self, cell_type: str, pin_names: Set[str] | None = None
    ) -> SequentialDetectionResult:
        """Detect sequential element with detailed reasoning.

        Args:
            cell_type: Cell type name
            pin_names: Optional set of pin names for signature analysis

        Returns:
            SequentialDetectionResult with detection details
        """
        ...

    def register_subcircuit_topology(
        self, cell_type: str, internal_connections: list[tuple[str, str]]
    ) -> None:
        """Register internal topology of a subcircuit for feedback detection.

        This is the PRIMARY detection method - naming independent.

        Args:
            cell_type: Cell type name
            internal_connections: List of (from_node, to_node) internal wire connections
        """
        ...

    def register_sequential_cells(self, cell_types: Set[str]) -> None:
        """Explicitly register cell types as sequential (user annotation).

        Use when topology cannot be analyzed or as override.

        Args:
            cell_types: Set of cell type names to mark as sequential
        """
        ...
