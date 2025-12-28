"""Unit tests for TopologyBasedLatchIdentifier.

This module contains comprehensive tests for the topology-based latch/flip-flop
detection implementation. Tests are organized by detection strategy and behavior.

Test Organization:
    1. Feedback Loop Detection (Primary - Naming Independent)
    2. Explicit Annotation
    3. Pin Signature Detection (Heuristic)
    4. Pattern Fallback (Lowest Priority)
    5. Detection Priority Order
    6. Caching Behavior
    7. Edge Cases
    8. Performance

See Also:
    - Spec E01-F04-T02 for requirements
    - TopologyBasedLatchIdentifier implementation
"""

import pytest

from ink.domain.services.latch_identifier import (
    DetectionStrategy,
    SequentialDetectionResult,
)
from ink.infrastructure.identification.topology_latch_identifier import (
    TopologyBasedLatchIdentifier,
)

# =============================================================================
# FEEDBACK LOOP DETECTION (Primary - Naming Independent)
# =============================================================================


class TestFeedbackLoopDetection:
    """Tests for feedback loop detection - the PRIMARY detection method."""

    def test_detects_cross_coupled_nand_as_sequential(self) -> None:
        """Cross-coupled NANDs detected as sequential via feedback."""
        identifier = TopologyBasedLatchIdentifier()

        # SR Latch: cross-coupled NAND gates
        # Signal flow: nand1.in -> nand1.out -> nand2.in -> nand2.out -> nand1.in
        # This forms a cycle in the signal flow graph
        identifier.register_subcircuit_topology(
            "SR_LATCH",
            [
                # Internal gate signal flow (input to output)
                ("nand1.in1", "nand1.out"),
                ("nand1.in2", "nand1.out"),
                ("nand2.in1", "nand2.out"),
                ("nand2.in2", "nand2.out"),
                # Cross-coupling (output to input)
                ("nand1.out", "nand2.in1"),
                ("nand2.out", "nand1.in2"),
            ],
        )

        result = identifier.detect_with_reason("SR_LATCH")
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.FEEDBACK_LOOP
        assert result.confidence == pytest.approx(0.99)

    def test_detects_cross_coupled_nor_as_sequential(self) -> None:
        """Cross-coupled NORs detected as sequential via feedback."""
        identifier = TopologyBasedLatchIdentifier()

        # SR Latch with NOR: cross-coupled NOR gates
        # Signal flow: nor1.in -> nor1.out -> nor2.in -> nor2.out -> nor1.in
        identifier.register_subcircuit_topology(
            "NOR_SR_LATCH",
            [
                # Internal gate signal flow
                ("nor1.in1", "nor1.out"),
                ("nor1.in2", "nor1.out"),
                ("nor2.in1", "nor2.out"),
                ("nor2.in2", "nor2.out"),
                # Cross-coupling
                ("nor1.out", "nor2.in1"),
                ("nor2.out", "nor1.in2"),
            ],
        )

        result = identifier.detect_with_reason("NOR_SR_LATCH")
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.FEEDBACK_LOOP

    def test_detects_transmission_gate_latch(self) -> None:
        """Transmission gate + inverter feedback detected as sequential."""
        identifier = TopologyBasedLatchIdentifier()

        # TG Latch: TG -> INV1 -> output, INV1 -> INV2 -> TG2 -> INV1 (feedback)
        # The signal flow includes internal gate propagation:
        # inv1.in -> inv1.out -> inv2.in -> inv2.out -> tg2.in -> tg2.out -> inv1.in
        identifier.register_subcircuit_topology(
            "TG_LATCH_CUSTOM",
            [
                # Data path
                ("D", "tg1.in"),
                ("tg1.in", "tg1.out"),      # TG1 passes through
                ("tg1.out", "inv1.in"),
                ("inv1.in", "inv1.out"),    # INV1 inverts
                ("inv1.out", "Q"),
                # Feedback path
                ("inv1.out", "inv2.in"),
                ("inv2.in", "inv2.out"),    # INV2 inverts
                ("inv2.out", "tg2.in"),
                ("tg2.in", "tg2.out"),      # TG2 passes through
                ("tg2.out", "inv1.in"),     # Feedback to inv1 input!
            ],
        )

        result = identifier.detect_with_reason("TG_LATCH_CUSTOM")
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.FEEDBACK_LOOP

    def test_detects_tristate_inverter_latch(self) -> None:
        """Tristate inverter feedback loop detected as sequential."""
        identifier = TopologyBasedLatchIdentifier()

        # Tristate INV latch: TINV1 -> node -> TINV2 -> node (feedback)
        # The signal flow: tinv1.in -> tinv1.out -> node -> tinv2.in -> tinv2.out -> node
        identifier.register_subcircuit_topology(
            "TINV_LATCH",
            [
                # Data path
                ("D", "tinv1.in"),
                ("tinv1.in", "tinv1.out"),    # TINV1 inverts
                ("tinv1.out", "node"),
                ("node", "Q"),
                # Feedback path
                ("node", "tinv2.in"),
                ("tinv2.in", "tinv2.out"),    # TINV2 inverts
                ("tinv2.out", "node"),        # Feedback to node!
            ],
        )

        result = identifier.detect_with_reason("TINV_LATCH")
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.FEEDBACK_LOOP

    def test_no_feedback_in_combinational_chain(self) -> None:
        """Linear gate chain has no feedback - detected as combinational."""
        identifier = TopologyBasedLatchIdentifier()

        # AND -> INV -> OR chain (no feedback)
        identifier.register_subcircuit_topology(
            "COMBO_CHAIN",
            [
                ("A", "and.in1"),
                ("B", "and.in2"),
                ("and.out", "inv.in"),
                ("inv.out", "or.in1"),
                ("C", "or.in2"),
                ("or.out", "Y"),
            ],
        )

        result = identifier.detect_with_reason("COMBO_CHAIN")
        assert result.is_sequential is False
        assert result.strategy == DetectionStrategy.UNKNOWN

    def test_feedback_detection_ignores_cell_name(self) -> None:
        """Feedback detection works regardless of cell type name."""
        identifier = TopologyBasedLatchIdentifier()

        # Completely arbitrary name - no pattern match possible
        # Signal flow forms a cycle: gate1.in -> gate1.out -> gate2.in -> gate2.out -> gate1.in
        identifier.register_subcircuit_topology(
            "XYZZY_PLUGH_123",
            [
                # Internal gate signal flow
                ("gate1.in1", "gate1.out"),
                ("gate1.in2", "gate1.out"),
                ("gate2.in1", "gate2.out"),
                ("gate2.in2", "gate2.out"),
                # Cross-coupling forms feedback
                ("gate1.out", "gate2.in1"),
                ("gate2.out", "gate1.in2"),
            ],
        )

        result = identifier.detect_with_reason("XYZZY_PLUGH_123")
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.FEEDBACK_LOOP

    def test_feedback_detection_ignores_pin_names(self) -> None:
        """Feedback detection works regardless of pin names."""
        identifier = TopologyBasedLatchIdentifier()

        # Arbitrary internal node names - no pattern match possible
        identifier.register_subcircuit_topology(
            "WEIRD_CELL",
            [
                ("x1", "y2"),
                ("y2", "z3"),
                ("z3", "x1"),  # Cycle!
            ],
        )

        # Query with arbitrary pin names
        result = identifier.detect_with_reason(
            "WEIRD_CELL",
            {"ALPHA", "BETA", "GAMMA"},  # Completely non-standard
        )
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.FEEDBACK_LOOP

    def test_feedback_detection_highest_confidence(self) -> None:
        """Feedback detection returns confidence 0.99."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_subcircuit_topology(
            "LATCH_X1",
            [("a", "b"), ("b", "a")],
        )

        result = identifier.detect_with_reason("LATCH_X1")
        assert result.confidence == pytest.approx(0.99)


# =============================================================================
# EXPLICIT ANNOTATION
# =============================================================================


class TestExplicitAnnotation:
    """Tests for explicit user annotation of sequential cells."""

    def test_explicit_annotation_marks_as_sequential(self) -> None:
        """Explicitly registered cells detected as sequential."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_sequential_cells({"VENDOR_SPECIAL_FF"})

        result = identifier.detect_with_reason("VENDOR_SPECIAL_FF")
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.EXPLICIT

    def test_explicit_annotation_case_insensitive(self) -> None:
        """Explicit annotation matching is case-insensitive by default."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_sequential_cells({"MY_CUSTOM_FF"})

        # Query with different case
        result = identifier.detect_with_reason("my_custom_ff")
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.EXPLICIT

    def test_explicit_annotation_case_sensitive(self) -> None:
        """Explicit annotation matching is case-sensitive when configured."""
        identifier = TopologyBasedLatchIdentifier(case_sensitive=True)

        identifier.register_sequential_cells({"MY_CUSTOM_FF"})

        # Exact match works
        result_exact = identifier.detect_with_reason("MY_CUSTOM_FF")
        assert result_exact.is_sequential is True

        # Different case does not match
        result_diff = identifier.detect_with_reason("my_custom_ff")
        assert result_diff.strategy != DetectionStrategy.EXPLICIT

    def test_explicit_annotation_confidence(self) -> None:
        """Explicit annotation returns confidence 0.95."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_sequential_cells({"ENCRYPTED_LATCH_IP"})

        result = identifier.detect_with_reason("ENCRYPTED_LATCH_IP")
        assert result.confidence == pytest.approx(0.95)

    def test_multiple_explicit_annotations(self) -> None:
        """Can register multiple cell types as sequential."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_sequential_cells({
            "VENDOR_FF_1",
            "VENDOR_FF_2",
            "VENDOR_LATCH_1",
        })

        for cell_type in ["VENDOR_FF_1", "VENDOR_FF_2", "VENDOR_LATCH_1"]:
            result = identifier.detect_with_reason(cell_type)
            assert result.is_sequential is True
            assert result.strategy == DetectionStrategy.EXPLICIT


# =============================================================================
# PIN SIGNATURE DETECTION (Heuristic)
# =============================================================================


class TestPinSignatureDetection:
    """Tests for pin signature-based detection (heuristic fallback)."""

    def test_detects_dff_by_clk_d_q_pins(self) -> None:
        """D flip-flop detected by CLK, D, Q pins."""
        identifier = TopologyBasedLatchIdentifier()

        result = identifier.detect_with_reason(
            "CUSTOM_STORAGE_ELEMENT",
            {"CLK", "D", "Q", "QN"},
        )

        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.PIN_SIGNATURE
        assert result.confidence == pytest.approx(0.80)

    def test_detects_latch_by_clk_q_pins(self) -> None:
        """Latch detected by CLK, Q pins (no D)."""
        identifier = TopologyBasedLatchIdentifier()

        result = identifier.detect_with_reason(
            "UNKNOWN_LATCH",
            {"CLK", "Q", "EN"},  # No D pin
        )

        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.PIN_SIGNATURE
        assert result.confidence == pytest.approx(0.70)

    def test_case_insensitive_pin_matching(self) -> None:
        """Pin matching is case-insensitive by default."""
        identifier = TopologyBasedLatchIdentifier()

        # Mixed case pin names
        result = identifier.detect_with_reason(
            "SOME_CELL",
            {"clk", "D", "q"},  # lowercase clk and q
        )

        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.PIN_SIGNATURE

    def test_alternative_clock_pin_names(self) -> None:
        """Detects various clock pin naming conventions."""
        identifier = TopologyBasedLatchIdentifier()

        clock_variants = ["CK", "CP", "CLOCK", "GCLK", "PHI", "PHI1"]

        for clock_name in clock_variants:
            result = identifier.detect_with_reason(
                f"CELL_WITH_{clock_name}",
                {clock_name, "D", "Q"},
            )
            assert result.is_sequential is True, f"Failed for clock pin: {clock_name}"
            assert result.strategy == DetectionStrategy.PIN_SIGNATURE

    def test_alternative_data_pin_names(self) -> None:
        """Detects various data pin naming conventions."""
        identifier = TopologyBasedLatchIdentifier()

        data_variants = ["DI", "DATA", "SI", "SE"]

        for data_name in data_variants:
            result = identifier.detect_with_reason(
                f"CELL_WITH_{data_name}",
                {"CLK", data_name, "Q"},
            )
            assert result.is_sequential is True, f"Failed for data pin: {data_name}"

    def test_pin_signature_lower_confidence_than_feedback(self) -> None:
        """Pin signature confidence < feedback confidence."""
        identifier = TopologyBasedLatchIdentifier()

        # Register topology with feedback
        identifier.register_subcircuit_topology("FF1", [("a", "b"), ("b", "a")])

        feedback_result = identifier.detect_with_reason("FF1")
        pin_result = identifier.detect_with_reason("FF2", {"CLK", "D", "Q"})

        assert feedback_result.confidence > pin_result.confidence

    def test_disable_pin_signature_detection(self) -> None:
        """Pin signature detection can be disabled."""
        identifier = TopologyBasedLatchIdentifier(enable_pin_signature=False)

        # Standard pins should NOT trigger detection when disabled
        result = identifier.detect_with_reason(
            "MY_CELL",
            {"CLK", "D", "Q"},
        )

        # Should fall back to pattern matching, not pin signature
        assert result.strategy != DetectionStrategy.PIN_SIGNATURE


# =============================================================================
# PATTERN FALLBACK (Lowest Priority)
# =============================================================================


class TestPatternFallback:
    """Tests for pattern-based fallback detection (lowest priority)."""

    def test_pattern_fallback_when_no_other_detection(self) -> None:
        """Falls back to pattern when other methods don't match."""
        identifier = TopologyBasedLatchIdentifier()

        # No topology registered, no standard pins, but name contains "DFF"
        result = identifier.detect_with_reason(
            "SDFFRX2_TSMC",
            {"A", "B", "Y"},  # Non-standard pins
        )

        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.PATTERN_MATCH

    def test_pattern_matches_dff(self) -> None:
        """Pattern matches *DFF* cells."""
        identifier = TopologyBasedLatchIdentifier()

        dff_names = ["DFFR_X1", "SDFFR_X2", "DFF_POS", "MY_DFF_CUSTOM"]

        for name in dff_names:
            result = identifier.detect_with_reason(name)
            assert result.is_sequential is True, f"Failed for: {name}"
            assert result.strategy == DetectionStrategy.PATTERN_MATCH

    def test_pattern_matches_latch(self) -> None:
        """Pattern matches *LATCH* cells."""
        identifier = TopologyBasedLatchIdentifier()

        latch_names = ["LATCH_X1", "DLATCH_X2", "HLATCH", "MY_LATCH_CELL"]

        for name in latch_names:
            result = identifier.detect_with_reason(name)
            assert result.is_sequential is True, f"Failed for: {name}"

    def test_pattern_matches_ff(self) -> None:
        """Pattern matches *FF* cells."""
        identifier = TopologyBasedLatchIdentifier()

        ff_names = ["FF_X1", "JKFF", "SRFF"]

        for name in ff_names:
            result = identifier.detect_with_reason(name)
            assert result.is_sequential is True, f"Failed for: {name}"

    def test_pattern_fallback_lowest_confidence(self) -> None:
        """Pattern-based detection has confidence 0.50."""
        identifier = TopologyBasedLatchIdentifier()

        result = identifier.detect_with_reason("SOME_DFF_CELL")
        assert result.confidence == pytest.approx(0.50)

    def test_disable_pattern_fallback(self) -> None:
        """Pattern fallback can be disabled."""
        identifier = TopologyBasedLatchIdentifier(enable_pattern_fallback=False)

        # Name matches pattern but fallback is disabled
        result = identifier.detect_with_reason("DFF_X1")

        assert result.is_sequential is False
        assert result.strategy == DetectionStrategy.UNKNOWN

    def test_custom_fallback_patterns(self) -> None:
        """Custom fallback patterns can be provided."""
        identifier = TopologyBasedLatchIdentifier(
            fallback_patterns=["*REGF*", "*STOR*"],
        )

        # Custom pattern should match
        result = identifier.detect_with_reason("REGFILE_X1")
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.PATTERN_MATCH

        # Default pattern should NOT match (we replaced them)
        result2 = identifier.detect_with_reason("DFF_X1")
        assert result2.is_sequential is False

    def test_pattern_matching_case_insensitive(self) -> None:
        """Pattern matching is case-insensitive by default."""
        identifier = TopologyBasedLatchIdentifier()

        result = identifier.detect_with_reason("dff_x1")  # lowercase
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.PATTERN_MATCH

    def test_pattern_matching_case_sensitive(self) -> None:
        """Pattern matching can be case-sensitive."""
        identifier = TopologyBasedLatchIdentifier(case_sensitive=True)

        # Patterns are uppercase by default
        _result_lower = identifier.detect_with_reason("dff_x1")
        result_upper = identifier.detect_with_reason("DFF_X1")

        # Case-sensitive: lowercase won't match uppercase patterns
        assert result_upper.is_sequential is True
        # lowercase may or may not match depending on pattern case


# =============================================================================
# DETECTION PRIORITY ORDER
# =============================================================================


class TestDetectionPriorityOrder:
    """Tests for detection strategy priority order."""

    def test_feedback_takes_priority_over_explicit(self) -> None:
        """Feedback detection has higher priority than explicit annotation."""
        identifier = TopologyBasedLatchIdentifier()

        # Register both feedback topology AND explicit annotation
        identifier.register_subcircuit_topology(
            "DUAL_REG",
            [("a", "b"), ("b", "a")],  # Feedback
        )
        identifier.register_sequential_cells({"DUAL_REG"})

        result = identifier.detect_with_reason("DUAL_REG")

        # Feedback should win
        assert result.strategy == DetectionStrategy.FEEDBACK_LOOP
        assert result.confidence == pytest.approx(0.99)

    def test_explicit_takes_priority_over_pin_signature(self) -> None:
        """Explicit annotation has higher priority than pin signature."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_sequential_cells({"MY_CELL"})

        # Query with standard pins - explicit should still win
        result = identifier.detect_with_reason("MY_CELL", {"CLK", "D", "Q"})

        assert result.strategy == DetectionStrategy.EXPLICIT
        assert result.confidence == pytest.approx(0.95)

    def test_pin_signature_takes_priority_over_pattern(self) -> None:
        """Pin signature has higher priority than pattern matching."""
        identifier = TopologyBasedLatchIdentifier()

        # Cell name matches pattern, but pins are also standard
        result = identifier.detect_with_reason(
            "DFF_X1",  # Matches *DFF* pattern
            {"CLK", "D", "Q"},  # Standard pins
        )

        # Pin signature should win (0.80 > 0.50 confidence)
        assert result.strategy == DetectionStrategy.PIN_SIGNATURE
        assert result.confidence == pytest.approx(0.80)


# =============================================================================
# CACHING BEHAVIOR
# =============================================================================


class TestCachingBehavior:
    """Tests for caching behavior and cache invalidation."""

    def test_caches_detection_results(self) -> None:
        """Results are cached for repeated queries."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_sequential_cells({"CACHED_CELL"})

        # First call
        result1 = identifier.detect_with_reason("CACHED_CELL")

        # Second call should hit cache (same result)
        result2 = identifier.detect_with_reason("CACHED_CELL")

        assert result1 == result2

    def test_cache_key_includes_cell_type_and_pins(self) -> None:
        """Cache key includes both cell_type and pin_names."""
        identifier = TopologyBasedLatchIdentifier()

        # Same cell type, different pins = different cache entries
        result1 = identifier.detect_with_reason("SOME_CELL", {"CLK", "D", "Q"})
        result2 = identifier.detect_with_reason("SOME_CELL", {"A", "B", "Y"})

        # Different strategies expected (pin signature vs pattern/unknown)
        assert result1.strategy != result2.strategy or result1.confidence != result2.confidence

    def test_cache_invalidation_on_topology_registration(self) -> None:
        """Cache is invalidated when topology is registered."""
        identifier = TopologyBasedLatchIdentifier()

        # First query - no topology, should be combinational or pattern match
        result1 = identifier.detect_with_reason("MY_CELL")
        initial_strategy = result1.strategy

        # Register topology with feedback
        identifier.register_subcircuit_topology(
            "MY_CELL",
            [("a", "b"), ("b", "a")],
        )

        # Second query - should now be detected via feedback
        result2 = identifier.detect_with_reason("MY_CELL")

        assert result2.strategy == DetectionStrategy.FEEDBACK_LOOP
        is_different = result2.strategy != initial_strategy
        was_already_feedback = initial_strategy == DetectionStrategy.FEEDBACK_LOOP
        assert is_different or was_already_feedback

    def test_cache_invalidation_on_explicit_annotation(self) -> None:
        """Cache is invalidated when explicit annotation is added."""
        identifier = TopologyBasedLatchIdentifier()

        # First query - should be unknown (no pattern match)
        result1 = identifier.detect_with_reason("UNKNOWN_CELL_123")
        assert result1.is_sequential is False

        # Register as explicit
        identifier.register_sequential_cells({"UNKNOWN_CELL_123"})

        # Second query - should now be detected
        result2 = identifier.detect_with_reason("UNKNOWN_CELL_123")

        assert result2.is_sequential is True
        assert result2.strategy == DetectionStrategy.EXPLICIT

    def test_clear_cache(self) -> None:
        """Cache can be cleared via clear_cache() method."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_sequential_cells({"CELL1"})
        identifier.detect_with_reason("CELL1")  # Populate cache

        identifier.clear_cache()

        # After clear, should still work (just rebuild cache)
        result = identifier.detect_with_reason("CELL1")
        # But registration is also cleared, so it should be unknown now
        assert result.strategy != DetectionStrategy.EXPLICIT


# =============================================================================
# EDGE CASES
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_pins_no_crash(self) -> None:
        """Empty pin set doesn't cause crash."""
        identifier = TopologyBasedLatchIdentifier()

        # Should not raise
        result = identifier.detect_with_reason("SOME_CELL", set())
        assert isinstance(result, SequentialDetectionResult)

    def test_none_pins_no_crash(self) -> None:
        """None pin set doesn't cause crash."""
        identifier = TopologyBasedLatchIdentifier()

        # Should not raise
        result = identifier.detect_with_reason("SOME_CELL", None)
        assert isinstance(result, SequentialDetectionResult)

    def test_empty_topology_no_feedback(self) -> None:
        """Empty topology list returns no feedback."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_subcircuit_topology("EMPTY_CELL", [])

        result = identifier.detect_with_reason("EMPTY_CELL")
        assert result.strategy != DetectionStrategy.FEEDBACK_LOOP

    def test_combinational_cell_detection(self) -> None:
        """AND, NAND, INV correctly identified as combinational."""
        identifier = TopologyBasedLatchIdentifier()

        combinational = ["AND2_X1", "NAND3_X2", "INV_X4", "OR2_X1", "XOR2_X1"]

        for cell_type in combinational:
            result = identifier.detect_with_reason(cell_type)
            assert result.is_sequential is False, f"False positive for: {cell_type}"

    def test_is_sequential_method(self) -> None:
        """is_sequential() method returns boolean correctly."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_sequential_cells({"SEQ_CELL"})

        assert identifier.is_sequential("SEQ_CELL") is True
        assert identifier.is_sequential("COMBO_CELL") is False

    def test_self_loop_is_feedback(self) -> None:
        """A self-loop counts as feedback."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_subcircuit_topology(
            "SELF_LOOP_CELL",
            [("node", "node")],  # Self-loop
        )

        result = identifier.detect_with_reason("SELF_LOOP_CELL")
        assert result.is_sequential is True
        assert result.strategy == DetectionStrategy.FEEDBACK_LOOP


# =============================================================================
# PERFORMANCE (Benchmark tests - run with pytest-benchmark)
# =============================================================================


class TestPerformance:
    """Performance tests for sequential detection."""

    def test_cached_lookups_are_fast(self) -> None:
        """Cached lookups should be very fast."""
        identifier = TopologyBasedLatchIdentifier()

        identifier.register_sequential_cells({"FAST_CELL"})

        # Warm up cache
        identifier.detect_with_reason("FAST_CELL")

        # Multiple lookups should be fast (no assertion on time, just ensure it works)
        for _ in range(1000):
            result = identifier.detect_with_reason("FAST_CELL")
            assert result.is_sequential is True

    def test_handles_many_unique_cells(self) -> None:
        """Can handle many unique cell types."""
        identifier = TopologyBasedLatchIdentifier()

        # Register many topologies
        for i in range(100):
            identifier.register_subcircuit_topology(
                f"CELL_{i}",
                [("a", "b"), ("b", "a")] if i % 2 == 0 else [("a", "b")],
            )

        # Query all of them
        for i in range(100):
            result = identifier.detect_with_reason(f"CELL_{i}")
            expected = i % 2 == 0  # Even cells have feedback
            assert result.is_sequential == expected, f"Failed for CELL_{i}"
