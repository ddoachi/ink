# E02-F01-T02: Pin Graphics Item - Implementation Narrative

## 1. Executive Summary

This document provides a comprehensive walkthrough of implementing `PinItem`, a custom `QGraphicsItem` subclass that renders pins (connection points) on cell symbols in Ink's schematic canvas. The implementation followed Test-Driven Development (TDD) methodology, resulting in a robust, well-tested graphics component.

**Key Achievements**:
- Implemented `PinItem` class with 450+ lines of thoroughly documented code
- Created 39 unit tests covering all acceptance criteria
- Established pattern for parent-child graphics items
- Accurate connection point calculation for net routing

---

## 2. Problem Context

### 2.1 Business Need

Pins are the fundamental connection points in a schematic. They serve multiple critical functions:

1. **Visual Communication**: Show where signals enter and exit cells
2. **Direction Indication**: Display arrows showing signal flow (input/output/inout)
3. **Net Attachment**: Provide precise coordinates for net routing
4. **Name Display**: Show pin names for identification

### 2.2 Technical Challenge

The implementation needed to address:

1. **Parent-Child Relationship**: Pins must be children of cells for coordinate inheritance
2. **Coordinate Transformation**: Connection points must be in scene coordinates
3. **Detail Levels**: Three LOD levels matching CellItem's system
4. **Direction Arrows**: Different arrow styles for input/output/inout

---

## 3. Solution Architecture

### 3.1 Class Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                          QGraphicsItem                              │
│                         (Qt Framework)                              │
└────────────────────────────────────────────────────────────────────┘
                                  △
                                  │ inherits
                                  │
┌────────────────────────────────────────────────────────────────────┐
│                           PinItem                                   │
│                    (Presentation Layer)                             │
├────────────────────────────────────────────────────────────────────┤
│ Class Constants:                                                    │
│   PIN_RADIUS = 3.0           # Pin circle radius                   │
│   ARROW_SIZE = 8.0           # Arrow length                        │
│   LABEL_OFFSET = 5.0         # Distance from pin to label          │
│   LABEL_FONT_SIZE = 8        # Font size in points                 │
│   PIN_COLOR = #333333        # Dark gray                           │
│   _LABEL_COLOR = #000000     # Black                               │
├────────────────────────────────────────────────────────────────────┤
│ Instance Attributes:                                                │
│   _pin: Pin                  # Domain entity reference              │
│   _detail_level: DetailLevel # Current LOD                          │
├────────────────────────────────────────────────────────────────────┤
│ Required Methods (QGraphicsItem):                                   │
│   boundingRect() -> QRectF                                         │
│   paint(painter, option, widget)                                   │
├────────────────────────────────────────────────────────────────────┤
│ Public API:                                                         │
│   get_connection_point() -> QPointF  # For net routing              │
│   set_detail_level(level)            # For zoom LOD                 │
│   get_pin() -> Pin                   # Domain entity access         │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ child of
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                           CellItem                                  │
│                    (Parent Graphics Item)                           │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ references
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                             Pin                                     │
│                        (Domain Layer)                               │
├────────────────────────────────────────────────────────────────────┤
│   id: PinId                                                         │
│   name: str                                                         │
│   direction: PinDirection (INPUT/OUTPUT/INOUT)                     │
│   net_id: NetId | None                                             │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 Coordinate System Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Scene Coordinates                            │
│                                                                      │
│   CellItem.pos() = (100, 200)                                       │
│   ┌───────────────────────────────────────────────────────────┐     │
│   │                    CellItem                                │     │
│   │                                                            │     │
│   │   PinItem.pos() = (0, 20) [relative to parent]             │     │
│   │   ●                                                        │     │
│   │                                                            │     │
│   │   PinItem.get_connection_point() = (100, 220) [scene]      │     │
│   │                                                            │     │
│   └───────────────────────────────────────────────────────────┘     │
│                                                                      │
│   How it works:                                                      │
│   1. PinItem calls mapToScene(QPointF(0, 0))                        │
│   2. Qt transforms (0, 0) through parent chain                       │
│   3. Result: parent.pos() + pin.pos() = (100+0, 200+20) = (100, 220)│
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Implementation Walkthrough

### 4.1 TDD RED Phase - Writing Failing Tests

The first step was writing comprehensive tests for all required functionality:

```python
# tests/unit/presentation/canvas/test_pin_item.py

class TestPinItemCreation:
    """Tests for PinItem instantiation and basic properties."""

    def test_pin_item_can_be_created(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that PinItem can be instantiated with a Pin entity and parent."""
        pin_item = PinItem(input_pin, parent_cell_item)
        assert pin_item is not None

    def test_pin_item_has_parent_cell_item(
        self, qtbot: QtBot, input_pin: Pin, parent_cell_item: CellItem
    ) -> None:
        """Test that PinItem is a child of the parent CellItem."""
        pin_item = PinItem(input_pin, parent_cell_item)
        assert pin_item.parentItem() is parent_cell_item
```

**Test Categories**:
1. **Creation** (5 tests): Constructor, subclass, pin reference, parent, default level
2. **Constants** (3 tests): PIN_RADIUS, ARROW_SIZE, LABEL_OFFSET
3. **Bounding Rect** (5 tests): Return type, MINIMAL, BASIC, FULL, long names
4. **Detail Level** (4 tests): MINIMAL hides, BASIC/FULL show, triggers update
5. **Connection Point** (5 tests): Return type, origin, pin/parent positions, movement
6. **Direction Arrows** (3 tests): Input, output, inout directions
7. **Paint** (6 tests): Method, all detail levels, all directions
8. **Scene Integration** (3 tests): Scene items, multiple pins, visibility
9. **Edge Cases** (3 tests): Floating pin, empty name, same level
10. **Performance** (2 tests): Creation speed, calculation speed

### 4.2 TDD GREEN Phase - Implementation

#### 4.2.1 Class Structure

```python
# src/ink/presentation/canvas/pin_item.py

class PinItem(QGraphicsItem):
    """QGraphicsItem representing a pin on a cell symbol."""

    # Geometry constants
    PIN_RADIUS: float = 3.0
    ARROW_SIZE: float = 8.0
    LABEL_OFFSET: float = 5.0
    LABEL_FONT_SIZE: int = 8

    # Color constants
    PIN_COLOR = QColor("#333333")
    _LABEL_COLOR = QColor("#000000")
```

#### 4.2.2 Constructor with Parent-Child Relationship

```python
def __init__(
    self, pin: Pin, parent_cell_item: QGraphicsItem
) -> None:
    """Initialize pin graphics item.

    The key insight is passing parent_cell_item to super().__init__().
    This establishes the parent-child relationship automatically.
    """
    # Initialize as child of parent cell item
    super().__init__(parent_cell_item)  # <-- Critical!

    # Store domain entity reference
    self._pin = pin

    # Default to FULL detail level
    self._detail_level = DetailLevel.FULL
```

#### 4.2.3 Bounding Rect with Detail Level Awareness

```python
def boundingRect(self) -> QRectF:
    """Return bounding rectangle based on detail level.

    The bounding rect must adapt to detail level:
    - MINIMAL: Empty (hidden, nothing to render)
    - BASIC: Small (just the pin circle)
    - FULL: Large (circle + label + arrow)
    """
    # MINIMAL: Empty bounds
    if self._detail_level == DetailLevel.MINIMAL:
        return QRectF()

    # BASIC: Just the pin circle
    if self._detail_level == DetailLevel.BASIC:
        return QRectF(
            -self.PIN_RADIUS, -self.PIN_RADIUS,
            self.PIN_RADIUS * 2, self.PIN_RADIUS * 2
        )

    # FULL: Include label and arrow extents
    bounds = QRectF(-self.PIN_RADIUS, -self.PIN_RADIUS,
                    self.PIN_RADIUS * 2, self.PIN_RADIUS * 2)

    # Expand based on direction
    arrow_extent = self.ARROW_SIZE + 2
    label_extent = self._estimate_label_width() + self.LABEL_OFFSET

    if self._pin.direction == PinDirection.INPUT:
        bounds.adjust(-label_extent, -5, arrow_extent, 5)
    elif self._pin.direction == PinDirection.OUTPUT:
        bounds.adjust(-arrow_extent, -5, label_extent, 5)
    else:  # INOUT
        extent = max(arrow_extent, label_extent)
        bounds.adjust(-extent, -5, extent, 5)

    return bounds
```

#### 4.2.4 Paint Method with All Detail Levels

```python
def paint(self, painter: QPainter, _option, _widget=None) -> None:
    """Render pin with appropriate detail level.

    Rendering progression:
    1. MINIMAL: Return immediately (nothing rendered)
    2. BASIC: Draw pin circle only
    3. FULL: Draw circle, then label, then direction arrow
    """
    # MINIMAL: Don't render
    if self._detail_level == DetailLevel.MINIMAL:
        return

    # BASIC and FULL: Draw pin circle
    painter.setPen(QPen(self.PIN_COLOR, 1))
    painter.setBrush(QBrush(self.PIN_COLOR))
    painter.drawEllipse(QPointF(0, 0), self.PIN_RADIUS, self.PIN_RADIUS)

    # BASIC: Stop here
    if self._detail_level == DetailLevel.BASIC:
        return

    # FULL: Draw label and arrow
    self._draw_label(painter)
    self._draw_direction_arrow(painter)
```

#### 4.2.5 Direction Arrow Rendering

```python
def _draw_input_arrow(self, painter: QPainter) -> None:
    """Draw arrow pointing into cell (rightward →).

    Arrow is drawn as a polyline from base to tip with barbs.
    """
    base_x = self.PIN_RADIUS + 2  # Start after pin circle

    # Create arrow as polyline: base → tip → barbs
    arrow = QPolygonF([
        QPointF(base_x, 0),                          # Base
        QPointF(base_x + self.ARROW_SIZE, 0),        # Tip
        QPointF(base_x + self.ARROW_SIZE - 3, -3),   # Upper barb
        QPointF(base_x + self.ARROW_SIZE, 0),        # Back to tip
        QPointF(base_x + self.ARROW_SIZE - 3, 3),    # Lower barb
    ])
    painter.drawPolyline(arrow)
```

#### 4.2.6 Connection Point Calculation

```python
def get_connection_point(self) -> QPointF:
    """Return the scene coordinate for net attachment.

    This is the most critical method for integration with net routing.
    Uses Qt's mapToScene() to handle all coordinate transformations.
    """
    # Pin center is at item origin (0, 0)
    item_pos = QPointF(0, 0)

    # Convert to scene coordinates
    # This automatically handles:
    # - Pin's position relative to parent cell
    # - Parent cell's position in scene
    # - Any transformations in the chain
    scene_pos = self.mapToScene(item_pos)

    return scene_pos
```

### 4.3 TDD REFACTOR Phase

After all tests passed, refactoring focused on:

1. **Type consistency**: Changed `label_y = 4` to `label_y = 4.0` for consistent float types
2. **Documentation**: Added comprehensive docstrings to all methods
3. **Code organization**: Grouped related methods together

---

## 5. Key Implementation Details

### 5.1 Parent-Child Coordinate Transformation

The most important aspect of PinItem is the parent-child relationship:

```python
# When creating a PinItem:
cell_item = CellItem(cell)
cell_item.setPos(100.0, 200.0)  # Cell at (100, 200) in scene

pin_item = PinItem(pin, cell_item)  # Parent-child established
pin_item.setPos(0.0, 20.0)  # Pin at (0, 20) relative to cell

# When calculating connection point:
connection_pt = pin_item.get_connection_point()
# Returns: (100, 220) in scene coordinates

# Why it works:
# mapToScene(0, 0) traverses the parent chain:
#   PinItem local (0, 0)
#   + PinItem pos (0, 20)
#   + CellItem pos (100, 200)
#   = Scene (100, 220)
```

### 5.2 Detail Level State Management

```python
def set_detail_level(self, level: DetailLevel) -> None:
    """Set the level of detail based on zoom.

    Critical behaviors:
    1. Skip if level unchanged (optimization)
    2. Update visibility based on level
    3. Trigger repaint for visual update
    """
    # Optimization: skip if no change
    if self._detail_level == level:
        return

    self._detail_level = level

    # MINIMAL = hidden, others = visible
    self.setVisible(level != DetailLevel.MINIMAL)

    # Trigger repaint
    self.update()
```

### 5.3 Label Positioning Strategy

```python
def _draw_label(self, painter: QPainter) -> None:
    """Position labels based on pin direction.

    Strategy:
    - INPUT pins are on left edge → label goes left (outside cell)
    - OUTPUT pins are on right edge → label goes right (outside cell)
    - INOUT pins → label goes above to avoid ambiguity
    """
    if self._pin.direction == PinDirection.INPUT:
        # Label on left (outside cell)
        label_x = -self.LABEL_OFFSET - self._estimate_label_width()
        label_y = 4.0  # Baseline adjustment

    elif self._pin.direction == PinDirection.OUTPUT:
        # Label on right (outside cell)
        label_x = self.LABEL_OFFSET
        label_y = 4.0

    else:  # INOUT
        # Label above pin
        label_x = -self._estimate_label_width() / 2
        label_y = -self.LABEL_OFFSET
```

---

## 6. Testing Strategy

### 6.1 Test Fixtures

```python
@pytest.fixture
def input_pin() -> Pin:
    """Create an input pin for testing."""
    return Pin(
        id=PinId("U1.A"),
        name="A",
        direction=PinDirection.INPUT,
        net_id=NetId("net_001"),
    )

@pytest.fixture
def parent_cell_item(parent_cell: Cell) -> CellItem:
    """Create a parent CellItem for testing pin items."""
    return CellItem(parent_cell)
```

### 6.2 Critical Test Cases

**Connection Point Accuracy Test**:
```python
def test_connection_point_accounts_for_parent_position(
    self, qtbot, input_pin, parent_cell_item, graphics_scene
) -> None:
    """Test connection point when parent cell has position.

    This test validates the core coordinate transformation.
    """
    graphics_scene.addItem(parent_cell_item)
    parent_cell_item.setPos(100.0, 200.0)  # Cell at (100, 200)

    pin_item = PinItem(input_pin, parent_cell_item)
    pin_item.setPos(10.0, 20.0)  # Pin at (10, 20) relative

    connection_point = pin_item.get_connection_point()

    # Should be (110, 220) in scene coordinates
    assert connection_point.x() == pytest.approx(110.0, abs=0.1)
    assert connection_point.y() == pytest.approx(220.0, abs=0.1)
```

**Performance Test**:
```python
def test_pin_item_creation_is_fast(self, qtbot, input_pin, parent_cell_item):
    """Test that creating many pin items is reasonably fast."""
    import time
    start = time.perf_counter()

    for i in range(100):
        pin = Pin(id=PinId(f"U1.P{i}"), name=f"P{i}",
                  direction=PinDirection.INPUT, net_id=None)
        PinItem(pin, parent_cell_item)

    elapsed = time.perf_counter() - start

    # Should create 100 items in less than 0.5 seconds
    assert elapsed < 0.5
```

---

## 7. Integration Points

### 7.1 With CellItem (E02-F01-T01)

```python
# CellItem creates pins as children
cell_item = CellItem(cell)
scene.addItem(cell_item)

for pin in cell.pins:
    pin_item = PinItem(pin, parent_cell_item=cell_item)
    # Position set by SymbolLayoutCalculator (T03)
    pin_item.setPos(calculated_x, calculated_y)
```

### 7.2 With SymbolLayoutCalculator (E02-F01-T03)

```python
# T03 calculates pin positions
calculator = SymbolLayoutCalculator()
layouts = calculator.calculate_pin_layouts(cell)

for pin_id, layout in layouts.items():
    pin_item = PinItem(cell.get_pin(pin_id), cell_item)
    pin_item.setPos(layout.position)  # Relative to cell
```

### 7.3 With Net Router (E02-F03)

```python
# Router uses connection points to draw nets
start_point = start_pin_item.get_connection_point()  # Scene coords
end_point = end_pin_item.get_connection_point()      # Scene coords
net_path = router.route(start_point, end_point)
```

### 7.4 With Zoom LOD (E02-F01-T04)

```python
# Canvas updates detail level on zoom
def on_zoom_changed(self, zoom_factor: float):
    level = DetailLevel.from_zoom(zoom_factor)
    for item in self.scene().items():
        if isinstance(item, PinItem):
            item.set_detail_level(level)
```

---

## 8. Error Handling

### 8.1 Empty Pin Names

```python
def _draw_label(self, painter: QPainter) -> None:
    # Skip if pin name is empty
    if not self._pin.name:
        return
    # ... draw label
```

### 8.2 Detail Level Optimization

```python
def set_detail_level(self, level: DetailLevel) -> None:
    # Skip if level hasn't changed
    if self._detail_level == level:
        return
    # ... update level
```

---

## 9. Performance Considerations

### 9.1 Creation Performance

- 100 PinItems created in < 0.5 seconds
- Simple constructor with minimal initialization
- No expensive computations in constructor

### 9.2 Rendering Performance

- MINIMAL level: No rendering at all
- BASIC level: Single `drawEllipse` call
- FULL level: Circle + label + arrow (3 draw operations)

### 9.3 Connection Point Calculation

- 1000 calculations in < 0.1 seconds
- Uses Qt's optimized `mapToScene` method
- No caching needed (fast enough without)

---

## 10. Code Flow Examples

### 10.1 Creating a Pin on a Cell

```python
# 1. Create domain entities
cell = Cell(id=CellId("U1"), name="U1", cell_type="AND2_X1",
            pin_ids=[PinId("U1.A"), PinId("U1.Y")], is_sequential=False)
pin = Pin(id=PinId("U1.A"), name="A", direction=PinDirection.INPUT,
          net_id=NetId("net_001"))

# 2. Create graphics items
cell_item = CellItem(cell)
cell_item.setPos(100.0, 200.0)
scene.addItem(cell_item)

# 3. Create pin as child of cell
pin_item = PinItem(pin, cell_item)  # Parent-child relationship
pin_item.setPos(0.0, 20.0)          # Relative to cell

# 4. Pin is automatically in scene (child of cell_item)
assert pin_item in scene.items()

# 5. Connection point is in scene coordinates
pt = pin_item.get_connection_point()  # Returns (100, 220)
```

### 10.2 Zoom Level Change

```python
# User zooms out to 20%
zoom_factor = 0.2

# Canvas calculates detail level
level = DetailLevel.MINIMAL  # Below 25% threshold

# Update all pins
for item in scene.items():
    if isinstance(item, PinItem):
        item.set_detail_level(level)
        # Pin becomes invisible
        # boundingRect returns empty
        # paint returns immediately
```

---

## 11. Debugging Tips

### 11.1 Checking Connection Points

```python
# Debug: Print connection points
for item in scene.items():
    if isinstance(item, PinItem):
        pt = item.get_connection_point()
        print(f"Pin {item.get_pin().name}: ({pt.x()}, {pt.y()})")
```

### 11.2 Visualizing Pin Bounds

```python
# Debug: Draw bounding rect
def paint(self, painter, option, widget):
    super().paint(painter, option, widget)
    # Draw debug bounds in red
    painter.setPen(QPen(QColor("red"), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRect(self.boundingRect())
```

### 11.3 Checking Parent-Child Chain

```python
# Debug: Verify parent chain
pin_item = PinItem(pin, cell_item)
assert pin_item.parentItem() is cell_item
assert pin_item.scene() is cell_item.scene()
```

---

## 12. File Structure

```
src/ink/presentation/canvas/
├── __init__.py          # Module exports
├── cell_item.py         # CellItem (parent)
├── pin_item.py          # PinItem (this implementation)
└── detail_level.py      # DetailLevel enum

tests/unit/presentation/canvas/
├── test_cell_item.py    # CellItem tests
└── test_pin_item.py     # PinItem tests (39 tests)
```

---

## 13. Summary

The `PinItem` implementation successfully provides:

1. **Visual Representation**: Pins as circles with direction arrows
2. **Detail Levels**: MINIMAL/BASIC/FULL matching CellItem's LOD
3. **Connection Points**: Accurate scene coordinates for routing
4. **Parent-Child Integration**: Coordinate inheritance from CellItem

**Key Design Decisions**:
- Use Qt's parent-child mechanism for coordinate transformation
- Use `mapToScene()` for connection point calculation
- Position labels based on direction (outside cell boundary)
- Simple polyline arrows for direction indication

**Test Coverage**: 39 tests covering all acceptance criteria

---

## 14. References

- **Spec**: [E02-F01-T02.spec.md](./E02-F01-T02.spec.md)
- **Pre-docs**: [E02-F01-T02.pre-docs.md](./E02-F01-T02.pre-docs.md)
- **Post-docs**: [E02-F01-T02.post-docs.md](./E02-F01-T02.post-docs.md)
- **Qt Documentation**: [QGraphicsItem Parent-Child](https://doc.qt.io/qt-6/qgraphicsitem.html#parent-child-relationship)
- **Qt Documentation**: [mapToScene](https://doc.qt.io/qt-6/qgraphicsitem.html#mapToScene)
