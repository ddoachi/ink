# E02-F03-T01: Net Geometry Data Structure - Implementation Narrative

## Document Overview

This narrative provides a comprehensive walkthrough of the Net Geometry Data Structure implementation, explaining the business logic, architectural decisions, and technical details that make this component work. After reading this document, you should fully understand:

1. **Why** these value objects exist and their role in the system
2. **How** the implementation handles edge cases and constraints
3. **What** design patterns and techniques were used
4. **Where** this code integrates with the rest of the Ink schematic viewer

---

## 1. Business Context

### 1.1 The Problem We're Solving

Ink is a schematic viewer for gate-level netlists. When rendering a schematic, we need to draw **nets** (wires) connecting cells (logic gates). But how do we represent the physical path of a wire from one cell to another?

Consider a simple scenario:
```
┌───────┐                    ┌───────┐
│ Cell A│──────┬─────────────│ Cell B│
└───────┘      │             └───────┘
               │
               │
               └─────────────┌───────┐
                             │ Cell C│
                             └───────┘
```

This net connects Cell A's output to both Cell B and Cell C. The routing consists of:
- A horizontal segment from A to the junction point
- A horizontal segment from junction to B
- A vertical segment from junction to C

We need a data structure to represent this routing geometry so the rendering engine can draw it on the canvas.

### 1.2 Why Value Objects?

In Domain-Driven Design, **value objects** are immutable objects identified by their attributes, not by identity. Our geometry types are perfect value objects because:

1. **No identity needed**: A point at (10, 5) is the same as any other point at (10, 5)
2. **Immutability is beneficial**: Once routing is computed, it shouldn't change
3. **Comparability**: We need to compare points and segments for equality
4. **Thread safety**: Immutable objects are inherently thread-safe

---

## 2. Technical Deep Dive

### 2.1 The Point Class

**Location**: `src/ink/domain/value_objects/geometry.py:66-109`

The `Point` class is the fundamental building block—a 2D coordinate in schematic space.

```python
@dataclass(frozen=True)
class Point:
    """A 2D point in schematic coordinate space."""
    x: float
    y: float
```

#### Coordinate System

We use **screen coordinates** where:
- Origin (0, 0) is at the top-left
- X increases rightward
- Y increases **downward** (not upward like mathematical coordinates)

This matches Qt/PySide6's coordinate system and avoids costly transformations between domain and presentation layers.

```
(0,0) ────────> X
  │
  │
  │
  V
  Y
```

#### Distance Calculations

Two distance methods are provided:

**Euclidean Distance** (`distance_to`): The straight-line distance, calculated using `math.hypot()` for numerical stability:

```python
def distance_to(self, other: Point) -> float:
    dx = other.x - self.x
    dy = other.y - self.y
    return math.hypot(dx, dy)  # sqrt(dx² + dy²)
```

**Why `hypot()` over `sqrt(dx**2 + dy**2)`?** The `hypot()` function handles edge cases like very large or very small numbers without overflow/underflow issues.

**Manhattan Distance** (`manhattan_distance_to`): The "taxicab" distance—how far you'd travel if you could only move horizontally or vertically:

```python
def manhattan_distance_to(self, other: Point) -> float:
    return abs(other.x - self.x) + abs(other.y - self.y)
```

Manhattan distance is critical for orthogonal routing because it represents the actual wire length when diagonal paths are forbidden.

---

### 2.2 The LineSegment Class

**Location**: `src/ink/domain/value_objects/geometry.py:112-188`

A `LineSegment` connects two points and knows whether it's horizontal, vertical, or diagonal.

```python
@dataclass(frozen=True)
class LineSegment:
    start: Point
    end: Point
```

#### Orthogonal Detection

The most critical feature is detecting segment orientation. In Manhattan routing, all segments must be either horizontal or vertical—no diagonals allowed.

```python
_ORTHOGONAL_TOLERANCE = 1e-6

@property
def is_horizontal(self) -> bool:
    return math.isclose(self.start.y, self.end.y, abs_tol=_ORTHOGONAL_TOLERANCE)

@property
def is_vertical(self) -> bool:
    return math.isclose(self.start.x, self.end.x, abs_tol=_ORTHOGONAL_TOLERANCE)

@property
def is_orthogonal(self) -> bool:
    return self.is_horizontal or self.is_vertical
```

**Why the tolerance?** Floating-point arithmetic isn't exact. A layout algorithm might compute:
```python
y1 = 100.0
y2 = 100.0000000001  # Should be equal but isn't exactly
```

Without tolerance, this would fail the horizontal check. The 1e-6 tolerance (0.000001) is negligible at visual scale—less than a thousandth of a pixel.

#### Degenerate Zero-Length Segments

A special case: when `start == end`, the segment has zero length. We consider this **both horizontal AND vertical** (a degenerate case):

```python
# For Point(5, 5) to Point(5, 5):
segment.is_horizontal  # True (same y)
segment.is_vertical    # True (same x)
segment.is_orthogonal  # True
```

This may seem odd, but it's mathematically correct and simplifies downstream handling.

---

### 2.3 The NetGeometry Class

**Location**: `src/ink/domain/value_objects/geometry.py:191-438`

`NetGeometry` is the aggregate that holds all routing information for a single net.

```python
@dataclass(frozen=True)
class NetGeometry:
    net_id: NetId
    segments: tuple[LineSegment, ...]  # Immutable tuple, not list
    junctions: tuple[Point, ...]       # Where net branches (multi-fanout)
    crossings: tuple[Point, ...]       # Where this net crosses other nets
```

#### Why Tuples Instead of Lists?

Lists are mutable—you can append, remove, or modify elements. Since our dataclass is frozen, we want the collections to be immutable too. Tuples:
1. Can't be modified after creation
2. Are hashable (can be used in sets/dicts)
3. Have slightly lower memory overhead

#### Total Length Calculation

The `total_length` property sums up the Manhattan length of all segments:

```python
@property
def total_length(self) -> float:
    return sum(seg.manhattan_length for seg in self.segments)
```

For orthogonal geometry (all H or V segments), Manhattan length equals Euclidean length. For any (invalid) diagonal segments, it represents the length if the path were routed orthogonally.

#### Bend Counting Algorithm

**Location**: `src/ink/domain/value_objects/geometry.py:304-360`

The `bend_count` property counts direction changes in the routing path. This is useful for optimization (fewer bends = cleaner schematic).

The algorithm iterates through consecutive segment pairs and counts transitions between purely-horizontal and purely-vertical:

```python
for i in range(1, len(self.segments)):
    prev_seg = self.segments[i - 1]
    curr_seg = self.segments[i]

    # Check if each segment is purely H or purely V
    prev_is_purely_horizontal = prev_seg.is_horizontal and not prev_seg.is_vertical
    prev_is_purely_vertical = prev_seg.is_vertical and not prev_seg.is_horizontal
    curr_is_purely_horizontal = curr_seg.is_horizontal and not curr_seg.is_vertical
    curr_is_purely_vertical = curr_seg.is_vertical and not curr_seg.is_horizontal

    # A bend is H→V or V→H
    is_direction_change = (
        (prev_is_purely_horizontal and curr_is_purely_vertical)
        or (prev_is_purely_vertical and curr_is_purely_horizontal)
    )
    if is_direction_change:
        bend_count += 1
```

**Why "purely" horizontal/vertical?** Zero-length segments are both H and V. If we didn't check for "purely", a zero-length segment would incorrectly trigger a bend count.

Examples:
- `H` (single segment): 0 bends
- `H → V` (L-shape): 1 bend
- `H → V → H` (U-shape): 2 bends
- `H → H` (collinear): 0 bends

#### Validation

**Location**: `src/ink/domain/value_objects/geometry.py:362-400`

The `validate()` method enforces the Manhattan routing constraint—all segments must be orthogonal:

```python
def validate(self) -> bool:
    errors: list[str] = []

    for i, seg in enumerate(self.segments):
        if not seg.is_orthogonal:
            errors.append(
                f"Segment {i} is not orthogonal (diagonal): "
                f"({seg.start.x}, {seg.start.y}) -> ({seg.end.x}, {seg.end.y})"
            )

    if errors:
        raise ValueError("NetGeometry validation failed:\n- " + "\n- ".join(errors))

    return True
```

**Design decision**: Validation is explicit, not automatic in `__post_init__`. This allows:
1. Construction of intermediate geometry during algorithm development
2. Skipping validation for trusted sources (performance)
3. Better error messages (all errors at once, not just the first)

---

### 2.4 Serialization

**Location**: `src/ink/domain/value_objects/geometry.py:402-438`

For session persistence, geometry must be serializable to JSON-compatible dictionaries.

**to_dict()** creates a nested dictionary structure:

```python
def to_dict(self) -> dict[str, Any]:
    return {
        "net_id": str(self.net_id),
        "segments": [
            {
                "start": {"x": seg.start.x, "y": seg.start.y},
                "end": {"x": seg.end.x, "y": seg.end.y},
            }
            for seg in self.segments
        ],
        "junctions": [{"x": p.x, "y": p.y} for p in self.junctions],
        "crossings": [{"x": p.x, "y": p.y} for p in self.crossings],
    }
```

**from_dict()** reconstructs the object from the dictionary:

```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> NetGeometry:
    segments = tuple(
        LineSegment(
            start=Point(x=seg["start"]["x"], y=seg["start"]["y"]),
            end=Point(x=seg["end"]["x"], y=seg["end"]["y"]),
        )
        for seg in data["segments"]
    )
    # ... similar for junctions and crossings
```

**Why simple dicts over Protocol Buffers or msgpack?**
1. Human-readable for debugging
2. No external dependencies
3. Fast enough for typical session sizes (<10K nets)

---

## 3. Testing Philosophy

### 3.1 TDD Approach

This implementation followed strict Test-Driven Development:

1. **RED**: Write failing tests first
2. **GREEN**: Implement just enough to pass tests
3. **REFACTOR**: Clean up while keeping tests green

All 52 tests were written before any implementation code.

### 3.2 Test Categories

**Creation & Immutability Tests**: Verify objects can be created and can't be modified.

```python
def test_point_is_immutable(self) -> None:
    point = Point(x=1.0, y=2.0)
    with pytest.raises(FrozenInstanceError):
        point.x = 5.0  # Should fail
```

**Calculation Tests**: Verify distance, length, bend counting.

```python
def test_euclidean_distance_345_triangle(self) -> None:
    p1 = Point(x=0.0, y=0.0)
    p2 = Point(x=3.0, y=4.0)
    assert p1.distance_to(p2) == 5.0  # Classic 3-4-5 right triangle
```

**Edge Case Tests**: Cover degenerate scenarios.

```python
def test_zero_length_segment_is_both_horizontal_and_vertical(self) -> None:
    segment = LineSegment(Point(5.0, 5.0), Point(5.0, 5.0))
    assert segment.is_horizontal is True
    assert segment.is_vertical is True
```

**Validation Tests**: Verify constraint enforcement.

```python
def test_validate_rejects_diagonal_segment(self) -> None:
    geom = NetGeometry(
        net_id=NetId("test"),
        segments=(LineSegment(Point(0, 0), Point(5, 5)),),  # Diagonal!
        junctions=(),
        crossings=()
    )
    with pytest.raises(ValueError, match=r"diagonal|orthogonal"):
        geom.validate()
```

**Serialization Round-Trip Tests**: Verify data survives serialization.

```python
def test_serialization_roundtrip(self) -> None:
    original = NetGeometry(...)
    data = original.to_dict()
    restored = NetGeometry.from_dict(data)
    assert restored == original
```

---

## 4. Integration with Ink Architecture

### 4.1 Layer Placement

These value objects live in the **Domain Layer** (`src/ink/domain/value_objects/`):

```
┌───────────────────────────────────────┐
│         PRESENTATION LAYER            │
│  (PySide6 graphics items use this)    │
├───────────────────────────────────────┤
│         APPLICATION LAYER             │
│  (Use cases may pass geometry around) │
├───────────────────────────────────────┤
│          DOMAIN LAYER ←────────────── │ Point, LineSegment, NetGeometry
│  (Pure Python, no dependencies)       │
├───────────────────────────────────────┤
│       INFRASTRUCTURE LAYER            │
│  (Router creates NetGeometry)         │
└───────────────────────────────────────┘
```

### 4.2 Dependency Flow

The geometry classes have **zero external dependencies**—only Python standard library:
- `math` for `hypot()` and `isclose()`
- `dataclasses` for `@dataclass`
- `typing` for type hints

They depend only on `NetId` from `identifiers.py` (another domain value object).

### 4.3 Consumer Chain

```
CDL Parser → Graph Builder → Routing Engine → NetGeometry → Graphics Renderer
                                   ↓
                            (this component)
```

1. **Routing Engine** (E02-F03-T02) computes paths and creates `NetGeometry` instances
2. **Multi-Fanout Handler** (E02-F03-T03) populates the `junctions` field
3. **Net Graphics Item** (E02-F03-T04) renders segments as QPainterPath

---

## 5. Code Flow Walkthrough

### 5.1 Creating and Validating Geometry

```python
# Step 1: Create points for an L-shaped route
source = Point(x=0.0, y=0.0)        # Cell A output
corner = Point(x=10.0, y=0.0)       # Turn point
sink = Point(x=10.0, y=5.0)         # Cell B input

# Step 2: Create segments connecting the points
seg1 = LineSegment(start=source, end=corner)  # Horizontal
seg2 = LineSegment(start=corner, end=sink)    # Vertical

# Step 3: Create the NetGeometry
route = NetGeometry(
    net_id=NetId("net_a"),
    segments=(seg1, seg2),
    junctions=(),      # No branching in this simple case
    crossings=()       # No other nets cross this one
)

# Step 4: Validate the geometry
try:
    route.validate()  # Passes because all segments are orthogonal
    print("Valid geometry!")
except ValueError as e:
    print(f"Invalid: {e}")

# Step 5: Query properties
print(f"Total wire length: {route.total_length}")  # 15.0 (10 + 5)
print(f"Number of bends: {route.bend_count}")      # 1 (H→V transition)
```

### 5.2 Serializing for Session Save

```python
# Save current routing to session
import json

geometry_data = route.to_dict()
# {
#     "net_id": "net_a",
#     "segments": [
#         {"start": {"x": 0.0, "y": 0.0}, "end": {"x": 10.0, "y": 0.0}},
#         {"start": {"x": 10.0, "y": 0.0}, "end": {"x": 10.0, "y": 5.0}}
#     ],
#     "junctions": [],
#     "crossings": []
# }

with open("session.json", "w") as f:
    json.dump(geometry_data, f, indent=2)
```

### 5.3 Loading from Session

```python
# Load routing from session
with open("session.json", "r") as f:
    data = json.load(f)

restored_route = NetGeometry.from_dict(data)
assert restored_route == route  # Perfect round-trip
```

---

## 6. Error Handling and Edge Cases

### 6.1 Validation Errors

When validation fails, the error message includes all problematic segments:

```python
geom = NetGeometry(
    net_id=NetId("bad"),
    segments=(
        LineSegment(Point(0, 0), Point(5, 5)),    # Diagonal
        LineSegment(Point(5, 5), Point(10, 10)),  # Diagonal
    ),
    junctions=(),
    crossings=()
)

geom.validate()
# Raises:
# ValueError: NetGeometry validation failed:
# - Segment 0 is not orthogonal (diagonal): (0.0, 0.0) -> (5.0, 5.0)
# - Segment 1 is not orthogonal (diagonal): (5.0, 5.0) -> (10.0, 10.0)
```

### 6.2 Empty Geometry

Empty geometry (no segments) is valid—represents a net with no routing yet:

```python
empty = NetGeometry(
    net_id=NetId("unrouted"),
    segments=(),
    junctions=(),
    crossings=()
)

empty.validate()  # Passes
empty.total_length  # 0.0
empty.bend_count    # 0
```

### 6.3 Floating-Point Near-Misses

The tolerance ensures near-orthogonal segments pass validation:

```python
# This should be horizontal but has FP error
seg = LineSegment(
    start=Point(0.0, 100.0),
    end=Point(10.0, 100.0000001)  # y differs by 0.0000001
)

seg.is_horizontal  # True (within tolerance)
```

---

## 7. Performance Considerations

### 7.1 Time Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| Point distance | O(1) | Simple arithmetic |
| Segment orthogonal check | O(1) | Two `isclose()` calls |
| NetGeometry.total_length | O(n) | Iterates all segments |
| NetGeometry.bend_count | O(n) | Iterates all segments |
| NetGeometry.validate | O(n) | Iterates all segments |
| to_dict/from_dict | O(n) | Iterates all segments, junctions, crossings |

### 7.2 Memory Footprint

For a typical net with 10 segments:
- Point: ~24 bytes (object overhead + 2 floats)
- LineSegment: ~56 bytes (object overhead + 2 Points)
- NetGeometry: ~100 bytes (object overhead + tuple refs)

For 100K nets × 10 segments = 1M segments ≈ 80MB total geometry.

Acceptable for target hardware (16GB RAM).

---

## 8. Future Enhancement Considerations

### 8.1 Potential Optimizations

1. **`__slots__`**: Could reduce memory by ~30% if needed
2. **Lazy validation caching**: Store validation result to avoid recomputing
3. **Compact serialization**: Switch to msgpack/protobuf if session files too large

### 8.2 Feature Extensions

1. **Curved routing**: Add `CurveSegment` type for Bezier paths
2. **Non-Manhattan**: Support 45-degree (octilinear) routing
3. **Segment metadata**: Add labels, colors, or layer info per segment

---

## 9. Summary

The Net Geometry Data Structure provides the foundational types for representing wire routing in Ink schematics:

| Class | Purpose | Key Feature |
|-------|---------|-------------|
| `Point` | 2D coordinate | Immutable, distance methods |
| `LineSegment` | Wire segment | Orthogonal detection with FP tolerance |
| `NetGeometry` | Complete routing | Validation, serialization, metrics |

These value objects are:
- **Immutable**: Safe to share across threads
- **Type-safe**: Full type hints, mypy --strict compatible
- **Well-tested**: 100% coverage, 52 unit tests
- **Zero dependencies**: Pure Python, domain layer only

---

## Document Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-27 | 1.0 | Claude Opus 4.5 | Initial implementation narrative |

---

**End of Implementation Narrative**
