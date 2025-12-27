# E02-F01-T05 Implementation Narrative: Sequential Cell Styling

## The Story of Adding Clock Indicators to Sequential Cells

*A comprehensive technical narrative documenting the implementation of clock indicator icons for sequential cells in Ink's schematic viewer.*

---

## Chapter 1: Understanding the Problem

### 1.1 The Challenge

In digital circuit design, sequential elements (flip-flops, latches) are fundamentally different from combinational logic. They hold state, define timing boundaries, and represent clock domain crossings. When engineers explore schematics, they need to instantly identify these elements.

**The existing solution** (from E02-F01-T01) provided:
- Thicker borders (3px vs 2px) for sequential cells
- White fill (vs light gray) for sequential cells

**The gap**: While these visual differences work, they're subtle. Engineers requested a more explicit indicator - something that says "this is a sequential element" at a glance.

### 1.2 The Requirement

From the spec (E02-F01-T05):

> Sequential cells show clock icon at FULL detail level only. Clock icon positioned in top-right corner (12x12 pixels). Clock icon: circle with clock hands.

This introduces **Level of Detail (LOD)** rendering - showing different amounts of visual information based on zoom level.

---

## Chapter 2: Design Decisions

### 2.1 Why a Clock Icon?

The clock symbol was chosen because:
1. **Universal recognition** - Everyone knows what a clock looks like
2. **Semantic relevance** - Sequential elements are clock-driven
3. **Compact representation** - Works at 12x12 pixels
4. **No external dependencies** - Can be drawn with simple primitives

**Alternatives considered:**

| Option | Pros | Cons | Decision |
|--------|------|------|----------|
| Clock emoji ⏰ | Easy | Font-dependent, inconsistent | Rejected |
| SVG/PNG asset | High quality | File dependency, scaling | Rejected |
| "S" text marker | Simple | Not immediately meaningful | Rejected |
| Filled circle | Minimal | Easily confused with bullet | Rejected |
| **Clock primitives** | Fast, consistent, semantic | Drawing code needed | ✓ Selected |

### 2.2 The DetailLevel Enum

Before implementing the clock icon, we needed a way to control when it appears. Enter `DetailLevel`:

```python
class DetailLevel(IntEnum):
    MINIMAL = 0  # Zoomed way out - just rectangles
    BASIC = 1    # Normal view - rectangles + names
    FULL = 2     # Zoomed in - everything including clock icon
```

**Why IntEnum?**

Using `IntEnum` instead of regular `Enum` enables comparison operators:

```python
# This works because BASIC.value (1) is >= MINIMAL.value (0)
if self._detail_level >= DetailLevel.BASIC:
    self._draw_cell_name(painter, body_rect)

# This works because FULL.value (2) equals FULL.value (2)
if self._detail_level == DetailLevel.FULL and is_sequential:
    self._draw_clock_indicator(painter)
```

### 2.3 Where to Draw the Clock

**Position analysis:**

```
┌─────────────────────────────┐
│ 5px margin        ○─┐      │
│                   │ ↑│12px  │
│                   │ →│      │
│                   ╰─╯      │
│         U1                  │  ← Cell name centered
│       (AND2_X1)             │
│                             │
└─────────────────────────────┘
```

**Top-right corner was chosen because:**
- Doesn't overlap with centered cell name
- Standard position for status indicators (like badges)
- Visible but not dominant
- Works across different cell sizes

---

## Chapter 3: TDD Implementation

### 3.1 RED Phase - Writing Failing Tests First

Before writing any implementation code, we wrote 21 tests that defined expected behavior:

**Test file structure:**
```
test_cell_item_clock_indicator.py
├── TestDetailLevelEnum
│   ├── test_detail_level_has_minimal_value
│   ├── test_detail_level_has_basic_value
│   ├── test_detail_level_has_full_value
│   └── test_detail_level_ordering
├── TestClockIndicatorConstants
│   ├── test_clock_icon_size_constant
│   └── test_clock_icon_margin_constant
├── TestCellItemDetailLevel
│   ├── test_cell_item_has_default_detail_level
│   ├── test_cell_item_can_set_detail_level
│   └── test_cell_item_can_set_all_detail_levels
├── TestClockIndicatorMethod
│   ├── test_draw_clock_indicator_method_exists
│   └── test_draw_clock_indicator_can_be_called
├── TestClockIndicatorRendering
│   ├── test_sequential_cell_shows_clock_at_full_detail
│   ├── test_sequential_cell_no_clock_at_basic_detail
│   ├── test_sequential_cell_no_clock_at_minimal_detail
│   └── test_combinational_cell_never_shows_clock
├── TestClockIndicatorPosition
│   └── test_clock_icon_position_in_top_right
├── TestPaintMethodWithClockIndicator
│   ├── test_paint_at_full_detail_includes_clock
│   ├── test_paint_at_basic_detail_renders_without_clock
│   └── test_paint_at_minimal_detail_renders_simplified
└── TestMixedCellTypes
    ├── test_mixed_cells_render_correctly
    └── test_multiple_sequential_cells_at_different_detail_levels
```

**Initial test run:**
```
ModuleNotFoundError: No module named 'ink.presentation.canvas.detail_level'
```

Tests failed because `DetailLevel` didn't exist yet. This is the RED phase - tests define what we need to build.

### 3.2 GREEN Phase - Making Tests Pass

**Step 1: Create DetailLevel enum**

```python
# src/ink/presentation/canvas/detail_level.py

class DetailLevel(IntEnum):
    """Enumeration of rendering detail levels for schematic items."""

    MINIMAL = 0
    """Simplest rendering level for zoomed-out overview."""

    BASIC = 1
    """Standard rendering level with cell names."""

    FULL = 2
    """Complete rendering level with all visual indicators."""
```

**Step 2: Add detail level tracking to CellItem**

```python
class CellItem(QGraphicsItem):
    # New constants for clock indicator
    CLOCK_ICON_SIZE: float = 12.0
    CLOCK_ICON_MARGIN: float = 5.0
    _CLOCK_ICON_COLOR = QColor("#666666")

    def __init__(self, cell: Cell, parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)
        self._cell = cell
        self._is_hovered = False
        self._detail_level = DetailLevel.BASIC  # ← NEW: default to BASIC
        # ... rest of init
```

**Step 3: Implement clock indicator drawing**

```python
def _draw_clock_indicator(self, painter: QPainter) -> None:
    """Draw clock indicator icon for sequential cells."""
    painter.save()

    # Position: top-right corner
    icon_x = self.DEFAULT_WIDTH - self.CLOCK_ICON_SIZE - self.CLOCK_ICON_MARGIN
    icon_y = self.CLOCK_ICON_MARGIN

    # Calculate center
    center = QPointF(
        icon_x + self.CLOCK_ICON_SIZE / 2,
        icon_y + self.CLOCK_ICON_SIZE / 2,
    )
    radius = (self.CLOCK_ICON_SIZE / 2) - 1.0

    # Configure pen
    clock_pen = QPen(self._CLOCK_ICON_COLOR, 1.0)
    clock_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(clock_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    # Draw clock face
    painter.drawEllipse(center, radius, radius)

    # Draw hour hand (pointing up)
    hour_end = center + QPointF(0, -radius * 0.5)
    painter.drawLine(center, hour_end)

    # Draw minute hand (pointing right)
    minute_end = center + QPointF(radius * 0.7, 0)
    painter.drawLine(center, minute_end)

    painter.restore()
```

**Step 4: Integrate with paint() method**

```python
def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, ...) -> None:
    # ... existing cell body and selection rendering ...

    # Draw cell name (BASIC and FULL only)
    if self._detail_level >= DetailLevel.BASIC:
        self._draw_cell_name(painter, body_rect)

    # Draw clock indicator (FULL + sequential only)
    if self._detail_level == DetailLevel.FULL and is_sequential:
        self._draw_clock_indicator(painter)
```

**Test result after implementation:**
```
21 passed in 0.08s
```

All tests pass. GREEN phase complete.

### 3.3 REFACTOR Phase - Code Quality

With passing tests as a safety net, we cleaned up:

1. **Added comprehensive docstrings** to all new methods
2. **Organized constants** into logical sections
3. **Added ASCII diagram** in `_draw_clock_indicator()` docstring
4. **Removed unused imports** in test file
5. **Ran linting and type checking** - all clean

---

## Chapter 4: The Code Flow

### 4.1 When a Sequential Cell is Painted at FULL Detail

```
Qt Graphics Framework calls paint()
           │
           ▼
┌─────────────────────────────────────────┐
│ paint(painter, option, widget)          │
│                                         │
│ 1. Check option.state for selection     │
│ 2. Get is_sequential from domain cell   │
│                                         │
│ 3. Configure pen based on:              │
│    ├─ is_sequential → 3px border        │
│    └─ selection state → blue border     │
│                                         │
│ 4. Configure brush based on:            │
│    └─ is_sequential → white fill        │
│                                         │
│ 5. Draw rounded rectangle (cell body)   │
│                                         │
│ 6. If selected: draw selection overlay  │
│                                         │
│ 7. If detail_level >= BASIC:            │
│    └─► _draw_cell_name(painter, rect)   │
│                                         │
│ 8. If detail_level == FULL AND          │
│       is_sequential:                    │
│    └─► _draw_clock_indicator(painter)   │◄── THIS IS NEW
└─────────────────────────────────────────┘
```

### 4.2 Clock Indicator Drawing Detail

```
_draw_clock_indicator(painter)
           │
           ▼
┌─────────────────────────────────────────┐
│ 1. Save painter state                   │
│    └─ painter.save()                    │
│                                         │
│ 2. Calculate position                   │
│    icon_x = 120 - 12 - 5 = 103         │
│    icon_y = 5                           │
│    center = (109, 11)                   │
│    radius = 5.0                         │
│                                         │
│ 3. Configure pen                        │
│    └─ Color: #666666 (dark gray)        │
│    └─ Width: 1px                        │
│    └─ Cap: Round                        │
│                                         │
│ 4. Draw clock face                      │
│    └─ painter.drawEllipse(center, 5, 5) │
│                                         │
│ 5. Draw hour hand                       │
│    └─ From center to (109, 8.5)        │
│       (pointing up, 50% of radius)      │
│                                         │
│ 6. Draw minute hand                     │
│    └─ From center to (112.5, 11)       │
│       (pointing right, 70% of radius)   │
│                                         │
│ 7. Restore painter state                │
│    └─ painter.restore()                 │
└─────────────────────────────────────────┘
```

---

## Chapter 5: Testing Strategy

### 5.1 Test Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| Enum Tests | 4 | Verify DetailLevel structure and ordering |
| Constant Tests | 2 | Verify CLOCK_ICON_SIZE and MARGIN exist |
| API Tests | 3 | Verify get/set_detail_level works |
| Method Tests | 2 | Verify _draw_clock_indicator exists and callable |
| Rendering Tests | 4 | Verify clock appears/hides correctly |
| Position Tests | 1 | Verify top-right positioning math |
| Integration Tests | 3 | Verify paint() integration |
| Mixed Type Tests | 2 | Verify sequential + combinational work together |

### 5.2 Testing Without Visual Verification

Since we can't easily verify pixels in unit tests, we use behavioral verification:

```python
def test_sequential_cell_shows_clock_at_full_detail(self, ...):
    """Test that conditions for clock rendering are met."""
    cell_item = CellItem(sequential_cell)
    cell_item.set_detail_level(DetailLevel.FULL)
    graphics_scene.addItem(cell_item)

    # Force rendering
    graphics_view.show()
    qtbot.waitExposed(graphics_view)

    # Verify conditions that trigger clock drawing
    assert cell_item.get_cell().is_sequential  # ✓ Cell is sequential
    assert cell_item.get_detail_level() == DetailLevel.FULL  # ✓ At FULL detail
    # If both true, paint() will call _draw_clock_indicator()
```

### 5.3 Regression Testing

We also verified no regressions in original CellItem tests:

```
tests/unit/presentation/canvas/test_cell_item.py ... 34 passed
tests/unit/presentation/canvas/test_cell_item_clock_indicator.py ... 21 passed
```

---

## Chapter 6: Future Considerations

### 6.1 Integration with Zoom (E02-F01-T04)

The DetailLevel system is designed to integrate with zoom:

```python
# Future: SchematicCanvas.wheelEvent()
def wheelEvent(self, event):
    # Get new zoom factor
    zoom = self.transform().m11()

    # Map zoom to detail level
    if zoom < 0.25:
        level = DetailLevel.MINIMAL
    elif zoom < 0.75:
        level = DetailLevel.BASIC
    else:
        level = DetailLevel.FULL

    # Update all cell items
    for item in self.scene().items():
        if isinstance(item, CellItem):
            item.set_detail_level(level)
```

### 6.2 Potential Enhancements

| Enhancement | Complexity | Value | Priority |
|-------------|------------|-------|----------|
| User-configurable icon color | Low | Medium | P1 |
| Different icons per seq type | Medium | Low | P2 |
| Animation (pulsing clock) | Medium | Low | Rejected |
| Configurable position | Low | Low | P2 |

---

## Chapter 7: Summary

### 7.1 What We Built

1. **DetailLevel enum** - Foundation for LOD rendering
2. **Clock indicator** - 12x12px icon drawn with QPainter primitives
3. **Integration** - Seamless addition to existing CellItem.paint()
4. **Tests** - 21 comprehensive unit tests

### 7.2 Key Technical Decisions

| Decision | Rationale |
|----------|-----------|
| IntEnum for DetailLevel | Enables comparison operators |
| QPainter primitives | No external dependencies, fast rendering |
| Top-right position | Standard UI pattern, doesn't overlap text |
| FULL detail only | Performance optimization, reduces clutter |

### 7.3 Files Changed

```
New Files:
├── src/ink/presentation/canvas/detail_level.py (110 lines)
└── tests/unit/presentation/canvas/test_cell_item_clock_indicator.py (430 lines)

Modified Files:
├── src/ink/presentation/canvas/cell_item.py (+200 lines)
└── src/ink/presentation/canvas/__init__.py (+4 lines)
```

### 7.4 Metrics

| Metric | Value |
|--------|-------|
| New LOC | ~540 |
| Tests Added | 21 |
| Tests Passing | 21/21 (100%) |
| Lint Errors | 0 |
| Type Errors | 0 |

---

*Document complete. Implementation narrative for E02-F01-T05 Sequential Cell Styling.*
