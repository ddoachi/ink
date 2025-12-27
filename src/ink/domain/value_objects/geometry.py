"""Geometry value objects for net routing representation.

This module defines immutable value objects for representing routing geometry
in the schematic domain layer. These structures are used by the routing engine
(infrastructure layer) and consumed by the presentation layer for rendering.

Key Concepts:
    - Point: A 2D coordinate in schematic space (screen coordinates: Y increases downward)
    - LineSegment: A connection between two points with orthogonal detection
    - NetGeometry: Complete routing information for a single net

Coordinate System:
    The coordinate system follows screen/Qt conventions:
    - Origin (0, 0) at top-left
    - X increases rightward
    - Y increases downward
    - Units: logical pixels (not scaled by zoom)

Orthogonal Routing:
    This module enforces Manhattan (orthogonal) routing where all segments
    must be either horizontal or vertical. Diagonal segments are rejected
    by validation. A tolerance of 1e-6 is used for floating-point comparisons
    to handle arithmetic precision issues from layout algorithms.

Example:
    >>> from ink.domain.value_objects.geometry import Point, LineSegment, NetGeometry
    >>> from ink.domain.value_objects.identifiers import NetId
    >>>
    >>> # Create an L-shaped route
    >>> route = NetGeometry(
    ...     net_id=NetId("net_a"),
    ...     segments=(
    ...         LineSegment(Point(0.0, 0.0), Point(10.0, 0.0)),  # Horizontal
    ...         LineSegment(Point(10.0, 0.0), Point(10.0, 5.0)), # Vertical
    ...     ),
    ...     junctions=(),
    ...     crossings=()
    ... )
    >>> route.validate()  # Returns True
    True
    >>> route.total_length  # 10 + 5 = 15
    15.0
    >>> route.bend_count  # One direction change
    1

Note:
    All value objects are immutable (frozen=True) to ensure thread safety
    and prevent accidental modifications during the rendering pipeline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ink.domain.value_objects.identifiers import NetId

# Tolerance for floating-point comparisons in orthogonal detection.
# Layout algorithms may produce coordinates like 100.0000001 due to FP arithmetic.
# 1e-6 is negligible at visual scale (< 0.001 pixels).
_ORTHOGONAL_TOLERANCE = 1e-6


@dataclass(frozen=True)
class Point:
    """A 2D point in schematic coordinate space.

    Represents an immutable coordinate in the schematic canvas. Used for
    defining segment endpoints, junction locations, and crossing points.

    The coordinate system follows screen conventions:
    - X increases rightward (positive to the right)
    - Y increases downward (positive downward)

    Attributes:
        x: Horizontal position (increases rightward).
        y: Vertical position (increases downward).

    Example:
        >>> p1 = Point(x=0.0, y=0.0)
        >>> p2 = Point(x=3.0, y=4.0)
        >>> p1.distance_to(p2)
        5.0
        >>> p1.manhattan_distance_to(p2)
        7.0
    """

    x: float
    y: float

    def distance_to(self, other: Point) -> float:
        """Calculate Euclidean distance to another point.

        The Euclidean distance is the straight-line distance between two points,
        computed as sqrt((x2-x1)^2 + (y2-y1)^2).

        Args:
            other: The target point to measure distance to.

        Returns:
            The Euclidean (straight-line) distance between self and other.
            Always non-negative. Returns 0.0 if points are identical.

        Example:
            >>> p1 = Point(0.0, 0.0)
            >>> p2 = Point(3.0, 4.0)
            >>> p1.distance_to(p2)  # 3-4-5 right triangle
            5.0
        """
        # Using math.hypot for numerical stability with large/small values
        dx = other.x - self.x
        dy = other.y - self.y
        return math.hypot(dx, dy)

    def manhattan_distance_to(self, other: Point) -> float:
        """Calculate Manhattan (taxicab) distance to another point.

        The Manhattan distance is the sum of absolute differences in x and y,
        representing the distance if only orthogonal movement is allowed
        (like navigating a city grid).

        Args:
            other: The target point to measure distance to.

        Returns:
            The Manhattan distance: |x2-x1| + |y2-y1|.
            Always non-negative. Returns 0.0 if points are identical.

        Example:
            >>> p1 = Point(0.0, 0.0)
            >>> p2 = Point(3.0, 4.0)
            >>> p1.manhattan_distance_to(p2)
            7.0
        """
        return abs(other.x - self.x) + abs(other.y - self.y)


@dataclass(frozen=True)
class LineSegment:
    """A line segment connecting two points.

    Represents an immutable directed line segment from start to end.
    Provides properties for detecting segment orientation (horizontal,
    vertical, orthogonal) which is critical for Manhattan routing validation.

    The segment direction is significant for rendering (arrows, etc.),
    though for length calculations the direction doesn't matter.

    Attributes:
        start: The starting point of the segment.
        end: The ending point of the segment.

    Example:
        >>> seg = LineSegment(Point(0.0, 0.0), Point(10.0, 0.0))
        >>> seg.is_horizontal
        True
        >>> seg.is_vertical
        False
        >>> seg.length
        10.0

    Note:
        Orthogonal detection uses a tolerance of 1e-6 to handle
        floating-point precision issues from layout algorithms.
    """

    start: Point
    end: Point

    @property
    def is_horizontal(self) -> bool:
        """Check if segment is horizontal (same y coordinate).

        A segment is considered horizontal if the y coordinates of start
        and end are equal within floating-point tolerance (1e-6).

        Returns:
            True if the segment is horizontal (or zero-length).

        Note:
            Zero-length segments (start == end) are considered both
            horizontal AND vertical (degenerate case).
        """
        return math.isclose(self.start.y, self.end.y, abs_tol=_ORTHOGONAL_TOLERANCE)

    @property
    def is_vertical(self) -> bool:
        """Check if segment is vertical (same x coordinate).

        A segment is considered vertical if the x coordinates of start
        and end are equal within floating-point tolerance (1e-6).

        Returns:
            True if the segment is vertical (or zero-length).

        Note:
            Zero-length segments (start == end) are considered both
            horizontal AND vertical (degenerate case).
        """
        return math.isclose(self.start.x, self.end.x, abs_tol=_ORTHOGONAL_TOLERANCE)

    @property
    def is_orthogonal(self) -> bool:
        """Check if segment is orthogonal (horizontal or vertical).

        Manhattan routing requires all segments to be orthogonal.
        This property is used by NetGeometry.validate() to enforce
        the orthogonal constraint.

        Returns:
            True if segment is horizontal OR vertical.
            Diagonal segments return False.
        """
        return self.is_horizontal or self.is_vertical

    @property
    def length(self) -> float:
        """Calculate Euclidean length of the segment.

        Returns:
            The straight-line distance from start to end.
            Returns 0.0 for zero-length segments.
        """
        return self.start.distance_to(self.end)

    @property
    def manhattan_length(self) -> float:
        """Calculate Manhattan length of the segment.

        The Manhattan length is the sum of absolute differences in x and y.
        For orthogonal segments, this equals the Euclidean length.
        For diagonal segments, this represents the minimum distance
        if only orthogonal movement were allowed.

        Returns:
            The Manhattan distance from start to end: |dx| + |dy|.
        """
        return self.start.manhattan_distance_to(self.end)


@dataclass(frozen=True)
class NetGeometry:
    """Complete routing geometry for a net.

    Contains all information needed to render a net on the schematic canvas,
    including line segments, junction points (for multi-fanout), and crossing
    indicators (where nets visually intersect).

    This is the primary data structure passed from the routing engine
    (infrastructure) to the graphics layer (presentation).

    Attributes:
        net_id: Identifier linking this geometry to the logical net.
        segments: Ordered tuple of line segments forming the routing path.
            For connected paths, segments[i].end should equal segments[i+1].start.
        junctions: Points where the net branches (multi-fanout topology).
            Rendered as filled dots to indicate electrical connection.
        crossings: Points where this net crosses other nets.
            Rendered as crossing symbols (hops/bridges) for visual clarity.

    Example:
        >>> # L-shaped route from source to sink
        >>> geom = NetGeometry(
        ...     net_id=NetId("data[0]"),
        ...     segments=(
        ...         LineSegment(Point(0, 0), Point(10, 0)),   # Horizontal
        ...         LineSegment(Point(10, 0), Point(10, 5)),  # Vertical
        ...     ),
        ...     junctions=(),
        ...     crossings=()
        ... )
        >>> geom.validate()
        True
        >>> geom.total_length
        15.0
        >>> geom.bend_count
        1

    Note:
        The validate() method must be called explicitly to check constraints.
        Construction does not automatically validate to allow intermediate
        states during routing algorithm development.
    """

    net_id: NetId
    segments: tuple[LineSegment, ...]
    junctions: tuple[Point, ...]
    crossings: tuple[Point, ...]

    @property
    def total_length(self) -> float:
        """Calculate total Manhattan length of all segments.

        For orthogonal (validated) geometry, this equals the sum of
        Euclidean lengths since each segment is horizontal or vertical.

        Returns:
            Sum of manhattan_length for all segments.
            Returns 0.0 for empty geometry.
        """
        return sum(seg.manhattan_length for seg in self.segments)

    @property
    def bend_count(self) -> int:
        """Count the number of direction changes (bends) in the routing.

        A bend occurs when a segment's orientation differs from the
        previous segment (e.g., horizontal followed by vertical).
        Consecutive segments in the same direction don't count as bends.

        Returns:
            Number of bends in the routing path.
            Single segment: 0 bends.
            L-shape (H→V or V→H): 1 bend.
            U-shape (H→V→H): 2 bends.
            Empty geometry: 0 bends.

        Note:
            This counts orientation changes, not endpoint connections.
            Two consecutive horizontal segments count as 0 bends even
            if they're visually at different y positions.
        """
        # Need at least 2 segments to have a bend (direction change)
        min_segments_for_bend = 2
        if len(self.segments) < min_segments_for_bend:
            return 0

        bend_count = 0
        for i in range(1, len(self.segments)):
            prev_seg = self.segments[i - 1]
            curr_seg = self.segments[i]

            # Determine orientation of each segment
            # A segment is "horizontal-ish" if horizontal, "vertical-ish" if vertical
            # For zero-length or near-zero, we consider it matches either
            prev_horizontal = prev_seg.is_horizontal
            prev_vertical = prev_seg.is_vertical
            curr_horizontal = curr_seg.is_horizontal
            curr_vertical = curr_seg.is_vertical

            # A bend occurs when orientation changes:
            # H→V, V→H counts as bend
            # H→H, V→V does not count as bend
            # For degenerate (both H and V), no bend
            prev_is_purely_horizontal = prev_horizontal and not prev_vertical
            prev_is_purely_vertical = prev_vertical and not prev_horizontal
            curr_is_purely_horizontal = curr_horizontal and not curr_vertical
            curr_is_purely_vertical = curr_vertical and not curr_horizontal

            # Check for direction change: H→V or V→H
            is_direction_change = (
                (prev_is_purely_horizontal and curr_is_purely_vertical)
                or (prev_is_purely_vertical and curr_is_purely_horizontal)
            )
            if is_direction_change:
                bend_count += 1
            # Degenerate cases (both H and V) or diagonal don't count as bend

        return bend_count

    def validate(self) -> bool:
        """Validate geometry constraints.

        Checks that all segments are orthogonal (horizontal or vertical).
        Diagonal segments violate the Manhattan routing constraint and
        will cause a ValueError to be raised.

        Returns:
            True if all constraints are satisfied.

        Raises:
            ValueError: If any segment is not orthogonal, with details
                about which segments failed validation.

        Example:
            >>> # Valid orthogonal geometry
            >>> geom = NetGeometry(NetId("net"), (
            ...     LineSegment(Point(0, 0), Point(10, 0)),  # OK
            ... ), (), ())
            >>> geom.validate()
            True

            >>> # Invalid diagonal segment
            >>> bad_geom = NetGeometry(NetId("net"), (
            ...     LineSegment(Point(0, 0), Point(5, 5)),  # Diagonal!
            ... ), (), ())
            >>> bad_geom.validate()
            Traceback (most recent call last):
                ...
            ValueError: NetGeometry validation failed:
            - Segment 0 is not orthogonal (diagonal): ...
        """
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

    def to_dict(self) -> dict[str, Any]:
        """Serialize geometry to a dictionary for persistence.

        Creates a JSON-serializable dictionary representation of this
        geometry, suitable for saving to session files.

        Returns:
            Dictionary with structure:
            {
                "net_id": str,
                "segments": [{"start": {"x": float, "y": float}, "end": {...}}, ...],
                "junctions": [{"x": float, "y": float}, ...],
                "crossings": [{"x": float, "y": float}, ...]
            }

        Example:
            >>> geom = NetGeometry(...)
            >>> data = geom.to_dict()
            >>> import json
            >>> json.dumps(data)  # Valid JSON
        """
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NetGeometry:
        """Deserialize geometry from a dictionary.

        Reconstructs a NetGeometry instance from a dictionary created
        by to_dict(). Used when loading session files.

        Args:
            data: Dictionary with net_id, segments, junctions, crossings.

        Returns:
            New NetGeometry instance with the deserialized data.

        Raises:
            KeyError: If required fields are missing from data.
            TypeError: If data structure is malformed.

        Example:
            >>> data = {"net_id": "net1", "segments": [...], ...}
            >>> geom = NetGeometry.from_dict(data)
        """
        segments = tuple(
            LineSegment(
                start=Point(x=seg["start"]["x"], y=seg["start"]["y"]),
                end=Point(x=seg["end"]["x"], y=seg["end"]["y"]),
            )
            for seg in data["segments"]
        )

        junctions = tuple(
            Point(x=p["x"], y=p["y"])
            for p in data.get("junctions", [])
        )

        crossings = tuple(
            Point(x=p["x"], y=p["y"])
            for p in data.get("crossings", [])
        )

        return cls(
            net_id=NetId(data["net_id"]),
            segments=segments,
            junctions=junctions,
            crossings=crossings,
        )
