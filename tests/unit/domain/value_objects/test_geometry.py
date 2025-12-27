"""Unit tests for geometry value objects.

This module tests the geometry value objects used for net routing representation:
- Point: 2D coordinate with distance calculations
- LineSegment: Line connecting two points with orthogonal detection
- NetGeometry: Complete routing geometry for a net

These tests follow TDD (Test-Driven Development) approach, with tests written
before implementation to define expected behavior.

Test Coverage Goals:
    - 90%+ line coverage
    - 100% branch coverage for critical paths (validation, serialization)
    - Edge cases: zero-length segments, empty geometry, FP precision
"""

from dataclasses import FrozenInstanceError

import pytest

from ink.domain.value_objects.identifiers import NetId


class TestPoint:
    """Test suite for Point value object.

    The Point class represents a 2D coordinate in schematic space.
    It is immutable and provides distance calculation methods.
    """

    def test_point_creation(self) -> None:
        """Point should be created with x and y coordinates."""
        from ink.domain.value_objects.geometry import Point

        point = Point(x=10.0, y=20.0)
        assert point.x == 10.0
        assert point.y == 20.0

    def test_point_is_immutable(self) -> None:
        """Point should be frozen (immutable)."""
        from ink.domain.value_objects.geometry import Point

        point = Point(x=1.0, y=2.0)
        with pytest.raises(FrozenInstanceError):
            point.x = 5.0  # type: ignore[misc]

    def test_point_equality(self) -> None:
        """Points with same coordinates should be equal."""
        from ink.domain.value_objects.geometry import Point

        p1 = Point(x=3.0, y=4.0)
        p2 = Point(x=3.0, y=4.0)
        assert p1 == p2

    def test_point_inequality(self) -> None:
        """Points with different coordinates should not be equal."""
        from ink.domain.value_objects.geometry import Point

        p1 = Point(x=3.0, y=4.0)
        p2 = Point(x=5.0, y=6.0)
        assert p1 != p2

    def test_point_hashable(self) -> None:
        """Point should be usable as dictionary key."""
        from ink.domain.value_objects.geometry import Point

        p = Point(x=1.0, y=2.0)
        d = {p: "test"}
        assert d[p] == "test"

    def test_euclidean_distance_345_triangle(self) -> None:
        """Euclidean distance for 3-4-5 right triangle should be 5."""
        from ink.domain.value_objects.geometry import Point

        p1 = Point(x=0.0, y=0.0)
        p2 = Point(x=3.0, y=4.0)
        assert p1.distance_to(p2) == 5.0

    def test_euclidean_distance_same_point(self) -> None:
        """Distance from a point to itself should be 0."""
        from ink.domain.value_objects.geometry import Point

        p = Point(x=5.0, y=10.0)
        assert p.distance_to(p) == 0.0

    def test_euclidean_distance_symmetry(self) -> None:
        """Distance should be symmetric: d(p1,p2) == d(p2,p1)."""
        from ink.domain.value_objects.geometry import Point

        p1 = Point(x=1.0, y=2.0)
        p2 = Point(x=7.0, y=9.0)
        assert p1.distance_to(p2) == p2.distance_to(p1)

    def test_euclidean_distance_negative_coords(self) -> None:
        """Distance calculation should handle negative coordinates."""
        from ink.domain.value_objects.geometry import Point

        p1 = Point(x=-3.0, y=-4.0)
        p2 = Point(x=0.0, y=0.0)
        assert p1.distance_to(p2) == 5.0

    def test_manhattan_distance_basic(self) -> None:
        """Manhattan distance for (0,0) to (3,4) should be 7."""
        from ink.domain.value_objects.geometry import Point

        p1 = Point(x=0.0, y=0.0)
        p2 = Point(x=3.0, y=4.0)
        assert p1.manhattan_distance_to(p2) == 7.0

    def test_manhattan_distance_same_point(self) -> None:
        """Manhattan distance from a point to itself should be 0."""
        from ink.domain.value_objects.geometry import Point

        p = Point(x=5.0, y=10.0)
        assert p.manhattan_distance_to(p) == 0.0

    def test_manhattan_distance_symmetry(self) -> None:
        """Manhattan distance should be symmetric."""
        from ink.domain.value_objects.geometry import Point

        p1 = Point(x=1.0, y=2.0)
        p2 = Point(x=7.0, y=9.0)
        assert p1.manhattan_distance_to(p2) == p2.manhattan_distance_to(p1)

    def test_manhattan_distance_negative_coords(self) -> None:
        """Manhattan distance should handle negative coordinates."""
        from ink.domain.value_objects.geometry import Point

        p1 = Point(x=-3.0, y=-4.0)
        p2 = Point(x=0.0, y=0.0)
        assert p1.manhattan_distance_to(p2) == 7.0

    def test_point_repr(self) -> None:
        """Point should have a readable string representation."""
        from ink.domain.value_objects.geometry import Point

        p = Point(x=3.0, y=4.0)
        # dataclass provides default repr
        assert "3.0" in repr(p) and "4.0" in repr(p)


class TestLineSegment:
    """Test suite for LineSegment value object.

    LineSegment connects two Points and provides orthogonal detection
    (horizontal/vertical) which is critical for Manhattan routing.
    """

    def test_segment_creation(self) -> None:
        """LineSegment should be created with start and end points."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        start = Point(x=0.0, y=0.0)
        end = Point(x=10.0, y=0.0)
        segment = LineSegment(start=start, end=end)

        assert segment.start == start
        assert segment.end == end

    def test_segment_is_immutable(self) -> None:
        """LineSegment should be frozen (immutable)."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=10.0, y=0.0)
        )
        with pytest.raises(FrozenInstanceError):
            segment.start = Point(x=5.0, y=5.0)  # type: ignore[misc]

    def test_horizontal_segment_detection(self) -> None:
        """Segment with same y coordinates should be horizontal."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=100.0),
            end=Point(x=50.0, y=100.0)
        )
        assert segment.is_horizontal is True
        assert segment.is_vertical is False

    def test_vertical_segment_detection(self) -> None:
        """Segment with same x coordinates should be vertical."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=100.0, y=0.0),
            end=Point(x=100.0, y=50.0)
        )
        assert segment.is_horizontal is False
        assert segment.is_vertical is True

    def test_diagonal_segment_not_orthogonal(self) -> None:
        """Diagonal segment should not be horizontal or vertical."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=10.0, y=10.0)
        )
        assert segment.is_horizontal is False
        assert segment.is_vertical is False
        assert segment.is_orthogonal is False

    def test_horizontal_segment_is_orthogonal(self) -> None:
        """Horizontal segment should be orthogonal."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=10.0, y=0.0)
        )
        assert segment.is_orthogonal is True

    def test_vertical_segment_is_orthogonal(self) -> None:
        """Vertical segment should be orthogonal."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=0.0, y=10.0)
        )
        assert segment.is_orthogonal is True

    def test_horizontal_with_floating_point_tolerance(self) -> None:
        """Horizontal detection should tolerate floating point error."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        # y differs by tiny amount due to FP arithmetic
        segment = LineSegment(
            start=Point(x=0.0, y=100.0),
            end=Point(x=10.0, y=100.0000001)
        )
        assert segment.is_horizontal is True

    def test_vertical_with_floating_point_tolerance(self) -> None:
        """Vertical detection should tolerate floating point error."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        # x differs by tiny amount due to FP arithmetic
        segment = LineSegment(
            start=Point(x=100.0, y=0.0),
            end=Point(x=100.0000001, y=50.0)
        )
        assert segment.is_vertical is True

    def test_euclidean_length_horizontal(self) -> None:
        """Euclidean length of horizontal segment."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=10.0, y=0.0)
        )
        assert segment.length == 10.0

    def test_euclidean_length_vertical(self) -> None:
        """Euclidean length of vertical segment."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=0.0, y=5.0)
        )
        assert segment.length == 5.0

    def test_euclidean_length_diagonal(self) -> None:
        """Euclidean length of diagonal segment (3-4-5 triangle)."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=3.0, y=4.0)
        )
        assert segment.length == 5.0

    def test_manhattan_length_horizontal(self) -> None:
        """Manhattan length of horizontal segment equals euclidean length."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=10.0, y=0.0)
        )
        assert segment.manhattan_length == 10.0

    def test_manhattan_length_vertical(self) -> None:
        """Manhattan length of vertical segment equals euclidean length."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=0.0, y=5.0)
        )
        assert segment.manhattan_length == 5.0

    def test_manhattan_length_diagonal(self) -> None:
        """Manhattan length of diagonal segment is sum of dx and dy."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=3.0, y=4.0)
        )
        assert segment.manhattan_length == 7.0  # |3| + |4|

    def test_zero_length_segment(self) -> None:
        """Zero-length segment (start == end) should have length 0."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=5.0, y=5.0),
            end=Point(x=5.0, y=5.0)
        )
        assert segment.length == 0.0
        assert segment.manhattan_length == 0.0

    def test_zero_length_segment_is_both_horizontal_and_vertical(self) -> None:
        """Zero-length segment is degenerate: both horizontal and vertical."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        segment = LineSegment(
            start=Point(x=5.0, y=5.0),
            end=Point(x=5.0, y=5.0)
        )
        # Both are true for degenerate case (same x means vertical, same y means horizontal)
        assert segment.is_horizontal is True
        assert segment.is_vertical is True
        assert segment.is_orthogonal is True

    def test_segment_equality(self) -> None:
        """Segments with same start/end should be equal."""
        from ink.domain.value_objects.geometry import LineSegment, Point

        s1 = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=10.0, y=0.0)
        )
        s2 = LineSegment(
            start=Point(x=0.0, y=0.0),
            end=Point(x=10.0, y=0.0)
        )
        assert s1 == s2


class TestNetGeometry:
    """Test suite for NetGeometry value object.

    NetGeometry contains all routing information for a single net:
    - segments: Line segments forming the routing path
    - junctions: Points where multi-fanout nets branch
    - crossings: Points where this net crosses other nets
    """

    def test_net_geometry_creation(self) -> None:
        """NetGeometry should be created with net_id, segments, junctions, crossings."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),
            ),
            junctions=(),
            crossings=()
        )
        assert geom.net_id == NetId("test_net")
        assert len(geom.segments) == 1
        assert len(geom.junctions) == 0
        assert len(geom.crossings) == 0

    def test_net_geometry_is_immutable(self) -> None:
        """NetGeometry should be frozen (immutable)."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),
            ),
            junctions=(),
            crossings=()
        )
        with pytest.raises(FrozenInstanceError):
            geom.net_id = NetId("another")  # type: ignore[misc]

    def test_validate_passes_for_orthogonal_segments(self) -> None:
        """Validation should pass for all orthogonal segments."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),  # Horizontal
                LineSegment(
                    start=Point(x=10.0, y=0.0),
                    end=Point(x=10.0, y=5.0)
                ),  # Vertical
            ),
            junctions=(),
            crossings=()
        )
        assert geom.validate() is True

    def test_validate_rejects_diagonal_segment(self) -> None:
        """Validation should reject diagonal (non-orthogonal) segments."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=5.0, y=5.0)
                ),  # Diagonal!
            ),
            junctions=(),
            crossings=()
        )
        with pytest.raises(ValueError, match=r"diagonal|orthogonal"):
            geom.validate()

    def test_validate_rejects_multiple_diagonal_segments(self) -> None:
        """Validation should report all diagonal segments."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=5.0, y=5.0)
                ),  # Diagonal
                LineSegment(
                    start=Point(x=5.0, y=5.0),
                    end=Point(x=10.0, y=10.0)
                ),  # Diagonal
            ),
            junctions=(),
            crossings=()
        )
        with pytest.raises(ValueError) as exc_info:
            geom.validate()
        # Error message should mention both segments
        error_msg = str(exc_info.value)
        assert "0" in error_msg  # Segment index 0
        assert "1" in error_msg  # Segment index 1

    def test_validate_passes_empty_geometry(self) -> None:
        """Validation should pass for empty geometry (no segments)."""
        from ink.domain.value_objects.geometry import NetGeometry

        geom = NetGeometry(
            net_id=NetId("empty_net"),
            segments=(),
            junctions=(),
            crossings=()
        )
        assert geom.validate() is True

    def test_total_length_single_horizontal_segment(self) -> None:
        """Total length of single horizontal segment."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),
            ),
            junctions=(),
            crossings=()
        )
        assert geom.total_length == 10.0

    def test_total_length_l_shape(self) -> None:
        """Total length of L-shaped routing (horizontal + vertical)."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),  # 10 units
                LineSegment(
                    start=Point(x=10.0, y=0.0),
                    end=Point(x=10.0, y=5.0)
                ),  # 5 units
            ),
            junctions=(),
            crossings=()
        )
        assert geom.total_length == 15.0

    def test_total_length_empty_geometry(self) -> None:
        """Total length of empty geometry should be 0."""
        from ink.domain.value_objects.geometry import NetGeometry

        geom = NetGeometry(
            net_id=NetId("empty_net"),
            segments=(),
            junctions=(),
            crossings=()
        )
        assert geom.total_length == 0.0

    def test_bend_count_single_segment(self) -> None:
        """Single segment has no bends."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),
            ),
            junctions=(),
            crossings=()
        )
        assert geom.bend_count == 0

    def test_bend_count_l_shape(self) -> None:
        """L-shape (horizontal then vertical) has 1 bend."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),  # Horizontal
                LineSegment(
                    start=Point(x=10.0, y=0.0),
                    end=Point(x=10.0, y=5.0)
                ),  # Vertical
            ),
            junctions=(),
            crossings=()
        )
        assert geom.bend_count == 1

    def test_bend_count_u_shape(self) -> None:
        """U-shape (H-V-H) has 2 bends."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=5.0, y=0.0)
                ),  # Horizontal
                LineSegment(
                    start=Point(x=5.0, y=0.0),
                    end=Point(x=5.0, y=10.0)
                ),  # Vertical
                LineSegment(
                    start=Point(x=5.0, y=10.0),
                    end=Point(x=10.0, y=10.0)
                ),  # Horizontal
            ),
            junctions=(),
            crossings=()
        )
        assert geom.bend_count == 2

    def test_bend_count_same_direction_no_bend(self) -> None:
        """Two consecutive segments in same direction (H-H) is not a bend."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=5.0, y=0.0)
                ),  # Horizontal
                LineSegment(
                    start=Point(x=5.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),  # Horizontal (same direction)
            ),
            junctions=(),
            crossings=()
        )
        assert geom.bend_count == 0

    def test_bend_count_empty_geometry(self) -> None:
        """Empty geometry has 0 bends."""
        from ink.domain.value_objects.geometry import NetGeometry

        geom = NetGeometry(
            net_id=NetId("empty_net"),
            segments=(),
            junctions=(),
            crossings=()
        )
        assert geom.bend_count == 0

    def test_serialization_to_dict(self) -> None:
        """NetGeometry should serialize to dictionary."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        geom = NetGeometry(
            net_id=NetId("test_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),
            ),
            junctions=(Point(x=10.0, y=0.0),),
            crossings=(Point(x=5.0, y=0.0),)
        )

        data = geom.to_dict()

        assert data["net_id"] == "test_net"
        assert len(data["segments"]) == 1
        assert data["segments"][0]["start"]["x"] == 0.0
        assert data["segments"][0]["start"]["y"] == 0.0
        assert data["segments"][0]["end"]["x"] == 10.0
        assert data["segments"][0]["end"]["y"] == 0.0
        assert len(data["junctions"]) == 1
        assert data["junctions"][0]["x"] == 10.0
        assert len(data["crossings"]) == 1
        assert data["crossings"][0]["x"] == 5.0

    def test_deserialization_from_dict(self) -> None:
        """NetGeometry should deserialize from dictionary."""
        from ink.domain.value_objects.geometry import NetGeometry

        data = {
            "net_id": "test_net",
            "segments": [
                {
                    "start": {"x": 0.0, "y": 0.0},
                    "end": {"x": 10.0, "y": 0.0}
                }
            ],
            "junctions": [{"x": 10.0, "y": 0.0}],
            "crossings": [{"x": 5.0, "y": 0.0}]
        }

        geom = NetGeometry.from_dict(data)

        assert geom.net_id == NetId("test_net")
        assert len(geom.segments) == 1
        assert geom.segments[0].start.x == 0.0
        assert geom.segments[0].end.x == 10.0
        assert len(geom.junctions) == 1
        assert geom.junctions[0].x == 10.0
        assert len(geom.crossings) == 1
        assert geom.crossings[0].x == 5.0

    def test_serialization_roundtrip(self) -> None:
        """Serialization roundtrip should preserve all data."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        original = NetGeometry(
            net_id=NetId("roundtrip_net"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=10.0, y=0.0)
                ),
                LineSegment(
                    start=Point(x=10.0, y=0.0),
                    end=Point(x=10.0, y=5.0)
                ),
            ),
            junctions=(Point(x=10.0, y=0.0),),
            crossings=(Point(x=5.0, y=0.0), Point(x=7.5, y=0.0))
        )

        data = original.to_dict()
        restored = NetGeometry.from_dict(data)

        assert restored == original

    def test_serialization_empty_geometry(self) -> None:
        """Empty geometry should serialize and deserialize correctly."""
        from ink.domain.value_objects.geometry import NetGeometry

        original = NetGeometry(
            net_id=NetId("empty_net"),
            segments=(),
            junctions=(),
            crossings=()
        )

        data = original.to_dict()
        restored = NetGeometry.from_dict(data)

        assert restored == original
        assert len(restored.segments) == 0
        assert len(restored.junctions) == 0
        assert len(restored.crossings) == 0

    def test_net_geometry_with_junctions(self) -> None:
        """NetGeometry should store junction points for multi-fanout."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        junction = Point(x=10.0, y=5.0)
        geom = NetGeometry(
            net_id=NetId("clock"),
            segments=(
                # Source to junction
                LineSegment(
                    start=Point(x=0.0, y=0.0),
                    end=Point(x=0.0, y=5.0)
                ),
                LineSegment(
                    start=Point(x=0.0, y=5.0),
                    end=Point(x=10.0, y=5.0)
                ),
                # Junction to sink 1
                LineSegment(
                    start=Point(x=10.0, y=5.0),
                    end=Point(x=10.0, y=10.0)
                ),
                # Junction to sink 2
                LineSegment(
                    start=Point(x=10.0, y=5.0),
                    end=Point(x=15.0, y=5.0)
                ),
            ),
            junctions=(junction,),
            crossings=()
        )

        assert len(geom.junctions) == 1
        assert geom.junctions[0] == junction

    def test_net_geometry_with_crossings(self) -> None:
        """NetGeometry should store crossing points."""
        from ink.domain.value_objects.geometry import LineSegment, NetGeometry, Point

        crossing = Point(x=5.0, y=5.0)
        geom = NetGeometry(
            net_id=NetId("data"),
            segments=(
                LineSegment(
                    start=Point(x=0.0, y=5.0),
                    end=Point(x=10.0, y=5.0)
                ),
            ),
            junctions=(),
            crossings=(crossing,)
        )

        assert len(geom.crossings) == 1
        assert geom.crossings[0] == crossing
