"""Topology-based latch/flip-flop identification.

This module provides the TopologyBasedLatchIdentifier class, which implements
the LatchIdentifier protocol for detecting sequential elements in netlists.

Detection Priority (highest to lowest reliability):
    1. Feedback loop in registered subcircuit topology (naming-independent)
    2. Explicit annotation via register_sequential_cells()
    3. Pin signature analysis (relies on standard pin naming)
    4. Pattern matching on cell type name (least reliable)

The key insight is that sequential elements (latches, flip-flops) are
characterized by feedback loops in their internal topology. This structural
property is independent of naming conventions and provides the most reliable
detection method.

See Also:
    - Spec E01-F04-T02 for requirements
    - LatchIdentifier protocol in domain/services/latch_identifier.py
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ink.domain.services.latch_identifier import (
    DetectionStrategy,
    SequentialDetectionResult,
)

if TYPE_CHECKING:
    from collections.abc import Set

# Pin signature patterns for sequential detection (used as heuristic fallback)
CLOCK_PIN_PATTERNS = {"CLK", "CK", "CP", "CLOCK", "GCLK", "CLKB", "CKB", "PHI", "PHI1", "PHI2"}
DATA_INPUT_PATTERNS = {"D", "DI", "DATA", "SI", "SE", "SN", "SD"}
DATA_OUTPUT_PATTERNS = {"Q", "QN", "QB", "QI", "DO", "QO"}
SET_RESET_PATTERNS = {
    "SET", "SETB", "RST", "RSTB", "RESET", "RESETB", "RN", "SN", "CDN", "SDN", "CLR", "PRE"
}
ENABLE_PATTERNS = {"EN", "ENB", "ENABLE", "TE", "TI", "G", "GN", "GATE"}

# Fallback name patterns (lowest priority - least reliable)
FALLBACK_NAME_PATTERNS = ["*DFF*", "*LATCH*", "*FF*", "*FLOP*", "*REG*"]


@dataclass
class PinSignature:
    """Analyzed pin signature of a cell."""

    has_clock: bool
    has_data_input: bool
    has_data_output: bool
    has_set_reset: bool
    has_enable: bool
    clock_pins: set[str]
    data_pins: set[str]


class TopologyBasedLatchIdentifier:
    """Topology-based latch/flip-flop identification.

    Detection Priority (highest to lowest reliability):
    1. Feedback loop in registered subcircuit topology (naming-independent)
    2. Explicit annotation via register_sequential_cells()
    3. Pin signature analysis (relies on standard pin naming)
    4. Pattern matching on cell type name (least reliable)
    """

    def __init__(
        self,
        enable_feedback_detection: bool = True,
        enable_pin_signature: bool = True,
        enable_pattern_fallback: bool = True,
        fallback_patterns: list[str] | None = None,
        case_sensitive: bool = False,
    ) -> None:
        """Initialize topology-based latch identifier.

        Args:
            enable_feedback_detection: Enable feedback loop detection (PRIMARY)
            enable_pin_signature: Enable pin-based detection (SECONDARY)
            enable_pattern_fallback: Enable name pattern fallback (LOWEST)
            fallback_patterns: Custom fallback patterns
            case_sensitive: Case sensitivity for pattern matching
        """
        self._enable_feedback = enable_feedback_detection
        self._enable_pin_signature = enable_pin_signature
        self._enable_fallback = enable_pattern_fallback
        self._fallback_patterns = fallback_patterns or list(FALLBACK_NAME_PATTERNS)
        self._case_sensitive = case_sensitive

        # Cache for subcircuit topologies (cell_type -> has_feedback)
        self._topology_cache: dict[str, bool] = {}

        # Explicit annotations (cell_type -> True)
        self._explicit_sequential: set[str] = set()

        # Cache for detection results (cache_key -> result)
        self._detection_cache: dict[str, SequentialDetectionResult] = {}

    def is_sequential(self, cell_type: str, pin_names: Set[str] | None = None) -> bool:
        """Check if cell is sequential using topology analysis."""
        result = self.detect_with_reason(cell_type, pin_names)
        return result.is_sequential

    def detect_with_reason(
        self, cell_type: str, pin_names: Set[str] | None = None
    ) -> SequentialDetectionResult:
        """Detect with detailed reasoning, using priority-based strategies."""
        pin_names = pin_names or set()

        # Check cache first
        cache_key = f"{cell_type}:{','.join(sorted(pin_names))}"
        if cache_key in self._detection_cache:
            return self._detection_cache[cache_key]

        result = self._detect_impl(cell_type, pin_names)
        self._detection_cache[cache_key] = result
        return result

    def _detect_impl(
        self, cell_type: str, pin_names: Set[str]
    ) -> SequentialDetectionResult:
        """Internal detection implementation with strategy priority."""
        # Strategy 1: Feedback Loop Detection (HIGHEST PRIORITY - naming independent)
        if self._enable_feedback and cell_type in self._topology_cache:
            has_feedback = self._topology_cache[cell_type]
            if has_feedback:
                return SequentialDetectionResult(
                    is_sequential=True,
                    strategy=DetectionStrategy.FEEDBACK_LOOP,
                    confidence=0.99,  # Highest confidence - structural proof
                    reason=f"Detected feedback loop in subcircuit '{cell_type}' internal topology",
                )

        # Strategy 2: Explicit Annotation
        normalized_type = cell_type if self._case_sensitive else cell_type.upper()
        if normalized_type in self._explicit_sequential:
            return SequentialDetectionResult(
                is_sequential=True,
                strategy=DetectionStrategy.EXPLICIT,
                confidence=0.95,  # High confidence - user explicitly marked
                reason=f"Cell type '{cell_type}' explicitly registered as sequential",
            )

        # Strategy 3: Pin Signature Analysis (if pins provided)
        if self._enable_pin_signature and pin_names:
            signature = self._analyze_pin_signature(pin_names)
            if signature.has_clock and signature.has_data_output:
                confidence = 0.80 if signature.has_data_input else 0.70
                return SequentialDetectionResult(
                    is_sequential=True,
                    strategy=DetectionStrategy.PIN_SIGNATURE,
                    confidence=confidence,
                    reason=f"Detected clock pin(s): {signature.clock_pins}, "
                    f"data output(s): {signature.data_pins}",
                )

        # Strategy 4: Pattern Fallback (LOWEST priority)
        if self._enable_fallback:
            test_type = cell_type if self._case_sensitive else cell_type.upper()
            for pattern in self._fallback_patterns:
                test_pattern = pattern if self._case_sensitive else pattern.upper()
                if fnmatch.fnmatch(test_type, test_pattern):
                    return SequentialDetectionResult(
                        is_sequential=True,
                        strategy=DetectionStrategy.PATTERN_MATCH,
                        confidence=0.50,  # Low confidence - just name matching
                        reason=f"Cell type '{cell_type}' matches pattern '{pattern}' (name-based)",
                    )

        # No detection - combinational cell
        return SequentialDetectionResult(
            is_sequential=False,
            strategy=DetectionStrategy.UNKNOWN,
            confidence=0.80,
            reason=f"No sequential characteristics detected in '{cell_type}'",
        )

    def _analyze_pin_signature(self, pin_names: Set[str]) -> PinSignature:
        """Analyze pin names to identify sequential characteristics."""
        normalized = {p.upper() for p in pin_names}

        clock_pins = normalized & CLOCK_PIN_PATTERNS
        data_input_pins = normalized & DATA_INPUT_PATTERNS
        data_output_pins = normalized & DATA_OUTPUT_PATTERNS
        set_reset_pins = normalized & SET_RESET_PATTERNS
        enable_pins = normalized & ENABLE_PATTERNS

        return PinSignature(
            has_clock=bool(clock_pins),
            has_data_input=bool(data_input_pins),
            has_data_output=bool(data_output_pins),
            has_set_reset=bool(set_reset_pins),
            has_enable=bool(enable_pins),
            clock_pins=clock_pins,
            data_pins=data_input_pins | data_output_pins,
        )

    def register_subcircuit_topology(
        self, cell_type: str, internal_connections: list[tuple[str, str]]
    ) -> None:
        """Register subcircuit topology for feedback detection (PRIMARY method)."""
        has_feedback = self._detect_feedback_loop(internal_connections)
        self._topology_cache[cell_type] = has_feedback
        # Invalidate detection cache for this cell type
        self._invalidate_cache_for_type(cell_type)

    def register_sequential_cells(self, cell_types: Set[str]) -> None:
        """Explicitly register cell types as sequential (user annotation)."""
        for cell_type in cell_types:
            normalized = cell_type if self._case_sensitive else cell_type.upper()
            self._explicit_sequential.add(normalized)
            self._invalidate_cache_for_type(cell_type)

    def _invalidate_cache_for_type(self, cell_type: str) -> None:
        """Invalidate detection cache entries for a cell type."""
        to_remove = [k for k in self._detection_cache if k.startswith(f"{cell_type}:")]
        for key in to_remove:
            del self._detection_cache[key]

    def _detect_feedback_loop(
        self, connections: list[tuple[str, str]]
    ) -> bool:
        """Detect feedback loops using DFS cycle detection.

        This is the core algorithm for naming-independent sequential detection.
        A feedback loop indicates bistable storage (latch/flip-flop).
        """
        if not connections:
            return False

        # Build adjacency list
        graph: dict[str, list[str]] = {}
        for src, dst in connections:
            if src not in graph:
                graph[src] = []
            graph[src].append(dst)

        # DFS cycle detection (standard algorithm)
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True  # Back edge found = cycle

            rec_stack.remove(node)
            return False

        return any(node not in visited and has_cycle(node) for node in graph)

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._detection_cache.clear()
        self._topology_cache.clear()
        self._explicit_sequential.clear()
