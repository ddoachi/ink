"""Identification infrastructure for sequential cell detection.

This module provides implementations for detecting sequential elements
(latches, flip-flops) in gate-level netlists.

Available Classes:
    TopologyBasedLatchIdentifier: Topology-based latch/flip-flop identification
        using feedback loop detection as the primary method.

See Also:
    - ink.domain.services.latch_identifier: Protocol definition
    - Spec E01-F04-T02 for requirements
"""

from ink.infrastructure.identification.topology_latch_identifier import (
    TopologyBasedLatchIdentifier,
)

__all__ = ["TopologyBasedLatchIdentifier"]
