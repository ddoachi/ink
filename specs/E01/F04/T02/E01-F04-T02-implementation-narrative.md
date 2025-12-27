# Implementation Narrative: E01-F04-T02 - Latch Detector Service

## Background

The original spec (v0.1) proposed a name-based approach for detecting sequential elements, using patterns like `*DFF*` and `*LATCH*`. However, during pre-implementation discussions, we identified that:

1. **Cell type names vary across vendors** - `DFF_X1`, `DFFR_X2`, `MYFF_CUSTOM`, etc.
2. **Pin names are also non-standard** - `CLK` vs `CK` vs `PHI` vs `CP1`
3. **Custom cells may not follow any naming convention**

This led to the key insight: **sequential elements are characterized by feedback loops in their internal topology**, which is a structural property independent of naming.

## TDD Journey

### Phase 1: RED - Writing Failing Tests

Started by analyzing the revised spec (v0.3) which defined:
- `LatchIdentifier` protocol with `is_sequential()` and `detect_with_reason()` methods
- `DetectionStrategy` enum with priority-ordered strategies
- `SequentialDetectionResult` dataclass for detailed detection output

Created 45 comprehensive tests covering:
- Feedback loop detection for various latch topologies (SR, TG, Tristate)
- Explicit annotation behavior
- Pin signature detection heuristics
- Pattern fallback mechanisms
- Detection priority order
- Caching and cache invalidation
- Edge cases (empty pins, empty topology, self-loops)

**Key insight during test writing**: The test cases for cross-coupled gates initially modeled only inter-gate connections:
```python
# Initial (incorrect) model
[("nand1.out", "nand2.in1"), ("nand2.out", "nand1.in2")]
```

This doesn't form a graph-theoretic cycle! Had to revise tests to include internal signal flow:
```python
# Corrected model with internal gate propagation
[
    ("nand1.in1", "nand1.out"),  # Internal signal flow
    ("nand1.in2", "nand1.out"),
    ("nand2.in1", "nand2.out"),
    ("nand2.in2", "nand2.out"),
    ("nand1.out", "nand2.in1"),  # Cross-coupling
    ("nand2.out", "nand1.in2"),
]
```

### Phase 2: GREEN - Making Tests Pass

Implemented `TopologyBasedLatchIdentifier` with:

1. **DFS Cycle Detection**: Standard algorithm using visited set and recursion stack
   ```python
   def _detect_feedback_loop(self, connections):
       # Build adjacency list
       graph = {}
       for src, dst in connections:
           graph.setdefault(src, []).append(dst)

       # DFS with recursion stack for back-edge detection
       visited, rec_stack = set(), set()
       def has_cycle(node):
           visited.add(node)
           rec_stack.add(node)
           for neighbor in graph.get(node, []):
               if neighbor not in visited:
                   if has_cycle(neighbor):
                       return True
               elif neighbor in rec_stack:
                   return True  # Back edge = cycle
           rec_stack.remove(node)
           return False

       return any(node not in visited and has_cycle(node) for node in graph)
   ```

2. **Priority-Based Detection**: Checks strategies in order (feedback > explicit > pin > pattern)

3. **Two-Level Caching**:
   - Topology cache: `cell_type -> has_feedback`
   - Detection cache: `cache_key -> SequentialDetectionResult`
   - Cache invalidation when topology or annotations are registered

### Phase 3: REFACTOR - Cleanup

Fixed linting issues identified by ruff:
- Line length (broke up long set definition)
- Removed blank line after docstring
- Simplified nested if statements to single condition
- Used `any()` instead of for-loop with early return

Updated package `__init__.py` files with proper exports.

## Key Learnings

1. **Graph-Theoretic Cycle Detection Requires Complete Signal Flow**: Simply listing inter-gate connections isn't enough. Must include internal gate propagation edges.

2. **Separation of Concerns Matters**: E01-F04-T02 handles the detection algorithm (cycle detection). E01-F04-T04 handles transistor pattern recognition. This separation makes both tasks cleaner.

3. **Confidence Levels Are Meaningful**:
   - 99% for feedback (structural proof)
   - 95% for explicit (user certainty)
   - 70-80% for pin signature (heuristic)
   - 50% for pattern (name-based guess)

## Future Work

- E01-F04-T04 will provide the transistor topology analyzer that extracts internal connections from SPICE netlists
- Integration with CDL parser to automatically register subcircuit topologies
- Performance benchmarking with 100K+ cell designs
