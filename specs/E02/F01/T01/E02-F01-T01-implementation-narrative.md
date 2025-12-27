# E02-F01-T01: Cell Graphics Item - Implementation Narrative

## 1. Executive Summary

This document provides a comprehensive walkthrough of implementing `CellItem`, a custom `QGraphicsItem` subclass that renders cell symbols in Ink's schematic canvas. The implementation followed Test-Driven Development (TDD) methodology, resulting in a robust, well-tested graphics component.

**Key Achievements**:
- Implemented `CellItem` class with 469 lines of thoroughly documented code
- Created 34 unit tests covering all acceptance criteria
- Established patterns for future graphics items (Pin, Net)

---

## 2. Problem Context

### 2.1 Business Need

The schematic viewer needs to display gate-level cell instances as visual symbols. Each cell represents a logic gate (AND, OR, INV) or sequential element (DFF, LATCH) in the circuit. The visual representation must:

1. Show the cell as a recognizable symbol
2. Display the instance name for identification
3. Distinguish between combinational and sequential cells
4. Support user interaction (selection, hover)
5. Perform efficiently with thousands of cells

### 2.2 Technical Challenge

Qt's Graphics View Framework provides `QGraphicsItem` as the base for custom graphics. The challenge was to:

1. Implement required abstract methods (`boundingRect`, `paint`)
2. Handle visual states correctly (normal, selected, hover)
3. Integrate with the domain layer's `Cell` entity
4. Follow project architecture (DDD, Clean Architecture)

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
│                           CellItem                                  │
│                    (Presentation Layer)                             │
├────────────────────────────────────────────────────────────────────┤
│ Class Constants:                                                    │
│   DEFAULT_WIDTH = 120.0                                            │
│   DEFAULT_HEIGHT = 80.0                                            │
│   CORNER_RADIUS = 5.0                                              │
│   BORDER_WIDTH = 2.0                                               │
│   SEQUENTIAL_BORDER_WIDTH = 3.0                                    │
│   _FILL_COLOR_COMBINATIONAL = #F0F0F0                              │
│   _FILL_COLOR_SEQUENTIAL = #FFFFFF                                 │
│   _BORDER_COLOR_NORMAL = #333333                                   │
│   _BORDER_COLOR_SELECTED = #2196F3                                 │
│   _BORDER_COLOR_HOVER = #555555                                    │
├────────────────────────────────────────────────────────────────────┤
│ Instance Attributes:                                                │
│   _cell: Cell               # Domain entity reference              │
│   _is_hovered: bool         # Track hover state                    │
├────────────────────────────────────────────────────────────────────┤
│ Required Methods (QGraphicsItem):                                   │
│   boundingRect() -> QRectF                                         │
│   paint(painter, option, widget)                                   │
│   shape() -> QPainterPath                                          │
│   itemChange(change, value) -> object                              │
├────────────────────────────────────────────────────────────────────┤
│ Event Handlers:                                                     │
│   hoverEnterEvent(event)                                           │
│   hoverLeaveEvent(event)                                           │
├────────────────────────────────────────────────────────────────────┤
│ Public API:                                                         │
│   set_position(x, y)                                               │
│   get_cell() -> Cell                                               │
└────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ references
                                  ▼
┌────────────────────────────────────────────────────────────────────┐
│                             Cell                                    │
│                        (Domain Layer)                               │
├────────────────────────────────────────────────────────────────────┤
│   id: CellId                                                        │
│   name: str                                                         │
│   cell_type: str                                                    │
│   pin_ids: tuple[PinId, ...]                                       │
│   is_sequential: bool                                              │
└────────────────────────────────────────────────────────────────────┘
```

### 3.2 Data Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Cell (Domain)  │────▶│   CellItem      │────▶│  QGraphicsScene     │
│                 │     │  (Presentation)  │     │                     │
│  - id           │     │                  │     │  - items()          │
│  - name         │     │  boundingRect()  │     │  - addItem()        │
│  - cell_type    │     │  paint()         │     │  - itemAt()         │
│  - is_sequential│     │  shape()         │     │                     │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                                                            │
                                                            ▼
                                                 ┌─────────────────────┐
                                                 │  QGraphicsView      │
                                                 │                     │
                                                 │  Renders the scene  │
                                                 │  Handles user input │
                                                 └─────────────────────┘
```

---

## 4. Implementation Walkthrough

### 4.1 TDD RED Phase - Writing Failing Tests

The first step was writing comprehensive tests for all required functionality. Tests were organized into logical groups:

```python
# tests/unit/presentation/canvas/test_cell_item.py

class TestCellItemCreation:
    """Tests for CellItem instantiation and basic properties."""

    def test_cell_item_can_be_created(self, qtbot, combinational_cell):
        """Test that CellItem can be instantiated with a Cell entity."""
        cell_item = CellItem(combinational_cell)
        assert cell_item is not None

    def test_cell_item_is_qgraphics_item_subclass(self, qtbot, combinational_cell):
        """Test that CellItem inherits from QGraphicsItem."""
        cell_item = CellItem(combinational_cell)
        assert isinstance(cell_item, QGraphicsItem)
```

**Test Categories**:
1. **Creation** (4 tests): Constructor, subclass check, cell reference, parent support
2. **Constants** (5 tests): Verify all class constants have correct values
3. **Bounding Rect** (4 tests): Return type, dimensions, origin, sequential handling
4. **Position** (3 tests): set_position API, negative coords, initial origin
5. **Paint** (4 tests): Method existence, error-free execution, body/name rendering
6. **Visual States** (3 tests): Selectable flag, selection visual, hover events
7. **Sequential Distinction** (3 tests): Border widths, fill colors
8. **Shape** (3 tests): Return type, contains interior, excludes exterior
9. **Item Change** (2 tests): Selection and position change handling
10. **Scene Integration** (3 tests): Add to scene, multiple items, bounding rect

### 4.2 TDD GREEN Phase - Implementation

With tests defined, implementation followed the test requirements exactly.

#### 4.2.1 Class Structure

```python
# src/ink/presentation/canvas/cell_item.py

class CellItem(QGraphicsItem):
    """QGraphicsItem representing a cell symbol in the schematic canvas."""

    # Geometry constants
    DEFAULT_WIDTH: float = 120.0
    DEFAULT_HEIGHT: float = 80.0
    CORNER_RADIUS: float = 5.0
    BORDER_WIDTH: float = 2.0
    SEQUENTIAL_BORDER_WIDTH: float = 3.0

    # Color constants
    _FILL_COLOR_COMBINATIONAL = QColor("#F0F0F0")
    _FILL_COLOR_SEQUENTIAL = QColor("#FFFFFF")
    _BORDER_COLOR_NORMAL = QColor("#333333")
    _BORDER_COLOR_SELECTED = QColor("#2196F3")
    _BORDER_COLOR_HOVER = QColor("#555555")
    _TEXT_COLOR = QColor("#000000")
```

#### 4.2.2 Constructor

```python
def __init__(self, cell: Cell, parent: QGraphicsItem | None = None) -> None:
    super().__init__(parent)

    # Store domain entity reference
    self._cell = cell

    # Track hover state (Qt doesn't provide this directly)
    self._is_hovered = False

    # Configure Qt item flags
    self._setup_flags()

    # Enable caching for efficient rendering
    self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)
```

#### 4.2.3 Bounding Rect Calculation

```python
def boundingRect(self) -> QRectF:
    """Return the bounding rectangle for collision and rendering."""
    # Determine border width based on cell type
    border_width = (
        self.SEQUENTIAL_BORDER_WIDTH
        if self._cell.is_sequential
        else self.BORDER_WIDTH
    )

    # Pen is centered on path, so half extends outward
    # Add 1px margin for anti-aliasing
    margin = border_width / 2.0 + 1.0

    return QRectF(
        -margin,
        -margin,
        self.DEFAULT_WIDTH + 2 * margin,
        self.DEFAULT_HEIGHT + 2 * margin,
    )
```

#### 4.2.4 Paint Method

```python
def paint(
    self,
    painter: QPainter,
    option: QStyleOptionGraphicsItem,
    _widget: QWidget | None = None,
) -> None:
    """Render the cell symbol."""
    # Determine visual state
    is_selected = bool(option.state & QStyle.StateFlag.State_Selected)
    is_sequential = self._cell.is_sequential

    # Configure border
    border_width = self.SEQUENTIAL_BORDER_WIDTH if is_sequential else self.BORDER_WIDTH

    if is_selected:
        border_color = self._BORDER_COLOR_SELECTED
    elif self._is_hovered:
        border_color = self._BORDER_COLOR_HOVER
    else:
        border_color = self._BORDER_COLOR_NORMAL

    pen = QPen(border_color, border_width)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)

    # Configure fill
    fill_color = self._FILL_COLOR_SEQUENTIAL if is_sequential else self._FILL_COLOR_COMBINATIONAL
    painter.setBrush(QBrush(fill_color))

    # Draw cell body
    body_rect = QRectF(0, 0, self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)
    painter.drawRoundedRect(body_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

    # Draw selection highlight
    if is_selected:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._SELECTED_FILL_TINT))
        painter.drawRoundedRect(body_rect, self.CORNER_RADIUS, self.CORNER_RADIUS)

    # Draw cell name
    self._draw_cell_name(painter, body_rect)
```

#### 4.2.5 Text Elision for Long Names

```python
def _draw_cell_name(self, painter: QPainter, rect: QRectF) -> None:
    """Draw the cell instance name centered within the cell body."""
    # Configure font
    font = QFont()
    font.setPointSize(10)
    font.setFamily("sans-serif")
    painter.setFont(font)
    painter.setPen(QPen(self._TEXT_COLOR))

    cell_name = self._cell.name

    # Calculate if elision is needed
    font_metrics = painter.fontMetrics()
    text_width = font_metrics.horizontalAdvance(cell_name)
    text_padding = 8.0
    available_width = rect.width() - 2 * text_padding

    # Elide in middle for hierarchical names
    if text_width > available_width:
        cell_name = font_metrics.elidedText(
            cell_name,
            Qt.TextElideMode.ElideMiddle,
            int(available_width),
        )

    # Draw centered
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, cell_name)
```

### 4.3 TDD REFACTOR Phase

After all tests passed, refactoring focused on:

1. **Unused Parameters**: Added underscore prefix (`_widget`, `_event`) for Qt-required unused parameters
2. **Import Cleanup**: Removed unused imports from test file
3. **Type Comments**: Added explanation for PySide6 type stub limitation

---

## 5. Key Design Decisions

### 5.1 Why Store Cell Reference vs. Copy Properties

**Decision**: Store reference to `Cell` entity, not copy properties

**Rationale**:
- `Cell` is immutable (frozen dataclass), so no risk of external mutation
- Property access via `get_cell()` allows full domain data retrieval
- Avoids duplication of data between layers
- Supports future features (e.g., property panel showing cell details)

### 5.2 Why Track Hover State Manually

**Decision**: Use `_is_hovered` instance variable

**Rationale**:
- Qt doesn't provide direct hover state query
- `hoverEnterEvent`/`hoverLeaveEvent` only receive events, not current state
- Manual tracking enables clean state check in `paint()` method

### 5.3 Why Use DeviceCoordinateCache

**Decision**: Enable caching via `setCacheMode(DeviceCoordinateCache)`

**Rationale**:
- Cell appearance rarely changes (only on selection/hover)
- Caching avoids redrawing static content during scrolling
- `DeviceCoordinateCache` provides best quality/performance balance
- Can be disabled if needed for animated cells in future

---

## 6. Code Flow Examples

### 6.1 Creating and Displaying a Cell

```python
# 1. Create domain entity
from ink.domain.model.cell import Cell
from ink.domain.value_objects.identifiers import CellId, PinId

cell = Cell(
    id=CellId("U1"),
    name="U1",
    cell_type="AND2_X1",
    pin_ids=[PinId("U1.A"), PinId("U1.B"), PinId("U1.Y")],
    is_sequential=False,
)

# 2. Create graphics item
from ink.presentation.canvas.cell_item import CellItem

cell_item = CellItem(cell)

# 3. Position in scene
cell_item.set_position(100.0, 200.0)

# 4. Add to scene
from PySide6.QtWidgets import QGraphicsScene

scene = QGraphicsScene()
scene.addItem(cell_item)

# 5. View in graphics view (triggers paint)
from PySide6.QtWidgets import QGraphicsView

view = QGraphicsView(scene)
view.show()
```

### 6.2 Selection Flow

```
User clicks on CellItem
        │
        ▼
Qt detects click in item's shape()
        │
        ▼
Qt sets ItemSelectedChange on item
        │
        ▼
itemChange() called with new selection state
        │
        ▼
CellItem calls update() to trigger repaint
        │
        ▼
paint() called by Qt
        │
        ▼
paint() checks option.state for State_Selected
        │
        ▼
If selected: use blue border (#2196F3) + overlay
```

---

## 7. Testing Strategy

### 7.1 Test Fixtures

```python
@pytest.fixture
def combinational_cell() -> Cell:
    """Create a combinational cell for testing."""
    return Cell(
        id=CellId("U1"),
        name="U1",
        cell_type="AND2_X1",
        pin_ids=[PinId("U1.A"), PinId("U1.B"), PinId("U1.Y")],
        is_sequential=False,
    )

@pytest.fixture
def sequential_cell() -> Cell:
    """Create a sequential cell for testing."""
    return Cell(
        id=CellId("XFF1"),
        name="XFF1",
        cell_type="DFF_X1",
        pin_ids=[PinId("XFF1.D"), PinId("XFF1.CLK"), PinId("XFF1.Q")],
        is_sequential=True,
    )
```

### 7.2 Scene Integration Testing

```python
@pytest.fixture
def graphics_scene(qtbot) -> QGraphicsScene:
    """Create a scene for integration tests."""
    return QGraphicsScene()

@pytest.fixture
def graphics_view(qtbot, graphics_scene) -> QGraphicsView:
    """Create a view for rendering tests."""
    view = QGraphicsView(graphics_scene)
    qtbot.addWidget(view)
    return view

def test_paint_can_be_called_without_error(
    self, qtbot, combinational_cell, graphics_scene, graphics_view
):
    """Test that paint executes without exceptions."""
    cell_item = CellItem(combinational_cell)
    graphics_scene.addItem(cell_item)

    graphics_view.show()
    qtbot.waitExposed(graphics_view)

    # If we get here, paint worked
    assert True
```

---

## 8. Performance Considerations

### 8.1 Rendering Efficiency

| Optimization | Implementation | Impact |
|--------------|----------------|--------|
| Caching | `DeviceCoordinateCache` | Avoids redraw during pan/scroll |
| Minimal repaints | Only `update()` on state changes | Reduces paint calls |
| Simple geometry | Single `drawRoundedRect` call | Fast drawing |
| Accurate bounding rect | Includes border margin | Prevents overdraw |

### 8.2 Memory Footprint

| Component | Size | Notes |
|-----------|------|-------|
| CellItem instance | ~200 bytes | Plus QGraphicsItem overhead |
| Cell reference | 8 bytes | Pointer only, no copy |
| Color constants | Class-level | Shared across all instances |

---

## 9. Future Extensibility

### 9.1 Pin Graphics Items (E02-F01-T02)

```python
# Future: PinItem will be a child of CellItem
class PinItem(QGraphicsItem):
    def __init__(self, pin: Pin, parent: CellItem):
        super().__init__(parent)
        self._pin = pin
        # Position relative to parent CellItem
```

### 9.2 Level of Detail (E02-F01-T04)

```python
# Future: Add LOD support
def paint(self, painter, option, widget):
    lod = option.levelOfDetailFromTransform(painter.worldTransform())

    if lod < 0.5:
        # Simplified rendering at low zoom
        self._paint_simplified(painter)
    else:
        # Full rendering at high zoom
        self._paint_full(painter, option)
```

---

## 10. Troubleshooting Guide

### 10.1 Cell Not Visible

**Symptom**: CellItem added to scene but not visible
**Causes**:
1. Position outside view bounds → Check `set_position()` coordinates
2. Scene not connected to view → Verify `view.setScene(scene)`
3. Cell behind other items → Check z-order with `setZValue()`

### 10.2 Selection Not Working

**Symptom**: Clicking on cell doesn't select it
**Causes**:
1. `ItemIsSelectable` flag not set → Check `_setup_flags()` called
2. Scene not in selection mode → Verify `scene.setSelectionArea()`
3. `shape()` too small → Verify shape covers visible area

### 10.3 Hover Not Working

**Symptom**: No visual change on mouse hover
**Causes**:
1. Hover events not accepted → Check `acceptHoverEvents()` returns True
2. `_is_hovered` not updating → Verify `hoverEnterEvent`/`hoverLeaveEvent` called
3. No `update()` call → Ensure event handlers call `update()`

---

## 11. References

- **Spec**: [E02-F01-T01.spec.md](./E02-F01-T01.spec.md)
- **Post-Docs**: [E02-F01-T01.post-docs.md](./E02-F01-T01.post-docs.md)
- **Context Log**: [E02-F01-T01.context.md](./E02-F01-T01.context.md)
- **GitHub Issue**: [#61](https://github.com/ddoachi/ink/issues/61)
- **ClickUp Task**: `CU-86evzm2hc`
- **Qt Documentation**: [QGraphicsItem Class](https://doc.qt.io/qt-6/qgraphicsitem.html)
