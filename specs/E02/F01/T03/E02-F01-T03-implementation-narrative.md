# E02-F01-T03: Symbol Layout Calculator - Implementation Narrative

## Overview

This document tells the complete story of implementing the Symbol Layout Calculator for the Ink schematic viewer. It serves as both a technical reference and an educational guide for developers who need to understand, maintain, or extend this component.

---

## 1. The Problem We're Solving

### Business Context

In schematic visualization, cells (logic gates like AND, OR, flip-flops) need to display their pins (connection points) in an organized, readable manner. Without a proper layout algorithm:

- Pins would overlap or cluster randomly
- Input and output pins would be indistinguishable
- Net routing would fail to find proper connection endpoints
- The schematic would be unreadable for engineers

### Technical Challenge

Given a Cell with N pins of varying directions (INPUT, OUTPUT, INOUT), calculate:
1. Which edge each pin belongs to (left for inputs, right for outputs)
2. The exact (x, y) position relative to the cell's origin
3. The absolute scene coordinates for net routing

The algorithm must handle edge cases like:
- Cells with 1 pin (center it)
- Cells with 10+ pins (expand height)
- Unequal input/output counts (distribute each edge independently)

---

## 2. Architecture & Design

### Layer Placement

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                               │
│                                                                          │
│   ┌─────────────────┐     ┌────────────────────────────┐                │
│   │    CellItem     │────▶│  SymbolLayoutCalculator    │                │
│   │ (QGraphicsItem) │     │                            │                │
│   └─────────────────┘     │  - calculate_pin_layouts() │                │
│                           │  - adjust_cell_height()    │                │
│                           └────────────────────────────┘                │
│                                        │                                 │
│                                        ▼                                 │
│                           ┌────────────────────────────┐                │
│                           │        PinLayout           │                │
│                           │    (Value Object)          │                │
│                           └────────────────────────────┘                │
├─────────────────────────────────────────────────────────────────────────┤
│                          DOMAIN LAYER                                    │
│                                                                          │
│   ┌───────────────┐   ┌───────────────┐   ┌───────────────────────┐    │
│   │     Cell      │   │      Pin      │   │     PinDirection      │    │
│   │   (Entity)    │   │   (Entity)    │   │   (Value Object)      │    │
│   └───────────────┘   └───────────────┘   └───────────────────────┘    │
│                                                                          │
│   ┌───────────────────────────────────────────────────────────────┐    │
│   │                      Design (Aggregate)                        │    │
│   │                                                                 │    │
│   │   - get_pin(pin_id) -> Pin | None                              │    │
│   │   - Manages all cells, pins, nets                              │    │
│   └───────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why This Design?

**Q: Why is SymbolLayoutCalculator in the presentation layer?**

A: Layout calculation is purely a visualization concern. The domain doesn't care where pins are drawn - it only knows about connectivity. Keeping layout logic in presentation:
- Respects domain purity
- Allows different layout strategies without domain changes
- Makes testing easier (no Qt mocks needed for domain tests)

**Q: Why pass Design as a parameter instead of storing it?**

A: Stateless calculators are:
- Thread-safe (no shared state)
- Testable (inject mock designs)
- Cacheable (same inputs = same outputs)
- Memory-efficient (no retained references)

---

## 3. The Algorithm Explained

### Step-by-Step Pin Distribution

Let's trace through a real example: an AND2 gate with pins A, B (inputs) and Y (output).

```python
# Input data
cell = Cell(
    id=CellId("U1"),
    name="U1",
    cell_type="AND2_X1",
    pin_ids=[PinId("U1.A"), PinId("U1.B"), PinId("U1.Y")]
)

# Pins in design
pin_A = Pin(id="U1.A", direction=INPUT, ...)   # Input
pin_B = Pin(id="U1.B", direction=INPUT, ...)   # Input
pin_Y = Pin(id="U1.Y", direction=OUTPUT, ...)  # Output
```

**Phase 1: Separate by Direction**

```python
input_pins = [pin_A, pin_B]   # Left edge
output_pins = [pin_Y]         # Right edge
```

**Phase 2: Calculate Left Edge Positions (2 pins)**

```
Cell dimensions: 120 x 80
Margin: 10px top/bottom
Available height: 80 - 20 = 60px
Spacing: 60 / (2 + 1) = 20px

Pin A: y = 10 + 1*20 = 30px
Pin B: y = 10 + 2*20 = 50px
```

Visual:
```
     ┌───────────────────────┐
     │         10px          │  ← top margin
     ├─────────────────── ─ ─┤
     │                       │
     ● A (x=0, y=30)         │  ← first pin
     │         20px          │
     ├─────────────────── ─ ─┤
     │                       │
     ● B (x=0, y=50)         │  ← second pin
     │         20px          │
     ├─────────────────── ─ ─┤
     │         10px          │  ← bottom margin
     └───────────────────────┘
```

**Phase 3: Calculate Right Edge Positions (1 pin)**

```
Single pin → center at height/2 = 40px

Pin Y: y = 40px (centered)
```

**Final Layout**

```python
{
    "U1.A": PinLayout(pin_id="U1.A", position=(0, 30), side="left"),
    "U1.B": PinLayout(pin_id="U1.B", position=(0, 50), side="left"),
    "U1.Y": PinLayout(pin_id="U1.Y", position=(120, 40), side="right"),
}
```

### Why This Formula Works

The formula `y = margin + (index + 1) * spacing` creates N+1 gaps for N pins:

```
For 3 pins:
  Gap 0: margin to pin 0       (15px)
  Gap 1: pin 0 to pin 1        (15px)
  Gap 2: pin 1 to pin 2        (15px)
  Gap 3: pin 2 to margin       (15px)

  4 gaps × 15px = 60px = available height ✓
```

This is mathematically equivalent to dividing a line segment into equal parts, with pins at the division points.

---

## 4. Code Walkthrough

### PinLayout Value Object

```python
# src/ink/presentation/canvas/symbol_layout_calculator.py:55

@dataclass(frozen=True, slots=True)
class PinLayout:
    """Position information for a single pin on a cell symbol.

    Why frozen=True?
    - Immutability prevents bugs when layouts are shared
    - Enables hash-based caching in the future
    - Guarantees thread safety

    Why slots=True?
    - Reduces memory footprint (no __dict__)
    - Faster attribute access
    """
    pin_id: str              # "U1.A" - matches Pin.id
    position: QPointF        # Relative to cell origin (0,0)
    connection_point: QPointF # Absolute scene coordinates
    side: str                # "left" | "right" | "top" | "bottom"
```

### Main Calculation Method

```python
# src/ink/presentation/canvas/symbol_layout_calculator.py:169

def calculate_pin_layouts(
    self,
    cell: Cell,
    design: Design,
    cell_scene_pos: QPointF | None = None,
) -> dict[str, PinLayout]:
    """
    The main entry point. This method:

    1. Handles defaults (scene_pos = (0,0) if None)
    2. Separates pins by direction
    3. Delegates to _distribute_pins_on_edge for each edge
    4. Calculates connection points in scene coordinates
    5. Returns complete layout dictionary
    """
    if cell_scene_pos is None:
        cell_scene_pos = QPointF(0.0, 0.0)

    # Early return for cells with no pins
    if not cell.pin_ids:
        return {}

    # Phase 1: Separate pins by direction
    input_pins: list[Pin] = []
    output_pins: list[Pin] = []

    for pin_id in cell.pin_ids:
        pin = design.get_pin(pin_id)
        if pin is None:
            continue  # Graceful handling of missing pins

        if pin.direction == PinDirection.INPUT:
            input_pins.append(pin)
        else:  # OUTPUT or INOUT
            output_pins.append(pin)

    # Phase 2: Create cell rectangle for calculations
    cell_rect = QRectF(0, 0, self._cell_width, self._cell_height)

    # Phase 3: Calculate layouts for each edge
    result: dict[str, PinLayout] = {}

    # Left edge (INPUT pins)
    for layout in self._distribute_pins_on_edge(input_pins, "left", cell_rect):
        connection_point = QPointF(
            cell_scene_pos.x() + layout.position.x(),
            cell_scene_pos.y() + layout.position.y(),
        )
        result[layout.pin_id] = PinLayout(
            pin_id=layout.pin_id,
            position=layout.position,
            connection_point=connection_point,
            side=layout.side,
        )

    # Right edge (OUTPUT and INOUT pins) - same pattern
    # ...

    return result
```

### Position Calculation Core

```python
# src/ink/presentation/canvas/symbol_layout_calculator.py:373

def _calculate_pin_position(
    self,
    edge_side: str,
    index: int,
    total_pins: int,
    cell_rect: QRectF,
) -> QPointF:
    """
    The mathematical core of the algorithm.

    For left edge:  x = 0
    For right edge: x = cell_width

    For single pin:     y = height / 2
    For multiple pins:  y = margin + (index + 1) * spacing
                        where spacing = available / (total + 1)
    """
    # X: edge-dependent
    x_pos = 0.0 if edge_side == "left" else cell_rect.width()

    # Y: pin-count-dependent
    if total_pins == 1:
        y_pos = cell_rect.height() / 2.0
    else:
        available_height = cell_rect.height() - (2 * self.PIN_MARGIN)
        spacing = available_height / (total_pins + 1)
        y_pos = self.PIN_MARGIN + (index + 1) * spacing

    return QPointF(x_pos, y_pos)
```

---

## 5. Test Strategy

### Test Organization

Tests are organized by concern, not by method:

```
test_symbol_layout_calculator.py
│
├── TestPinLayout                    # Value object behavior
│   ├── test_pin_layout_is_frozen_dataclass
│   ├── test_pin_layout_stores_all_fields
│   └── ...
│
├── TestSymbolLayoutCalculatorCreation  # Construction
│   ├── test_calculator_can_be_created_with_defaults
│   ├── test_calculator_uses_default_cell_width
│   └── ...
│
├── TestPinDirectionPlacement        # Direction → Edge mapping
│   ├── test_input_pins_placed_on_left_edge
│   ├── test_output_pins_placed_on_right_edge
│   └── ...
│
├── TestPinDistribution              # Even spacing algorithm
│   ├── test_single_input_centered_vertically
│   ├── test_two_inputs_evenly_distributed
│   └── ...
│
├── TestEdgeCases                    # Boundary conditions
│   ├── test_unequal_input_output_counts
│   ├── test_cell_with_no_pins
│   └── ...
│
└── TestLayoutIntegration            # Qt compatibility
    ├── test_layouts_compatible_with_qpointf
    └── test_layouts_within_cell_bounds
```

### Key Test Patterns

**Fixture-Based Setup**:
```python
@pytest.fixture
def simple_cell(design: Design) -> Cell:
    """Create a cell with known pin configuration for testing."""
    # Create pins with predictable IDs
    pin_a = Pin(id=PinId("U1.A"), direction=PinDirection.INPUT, ...)
    pin_b = Pin(id=PinId("U1.B"), direction=PinDirection.INPUT, ...)
    pin_y = Pin(id=PinId("U1.Y"), direction=PinDirection.OUTPUT, ...)

    design.add_pin(pin_a)
    design.add_pin(pin_b)
    design.add_pin(pin_y)

    return Cell(
        id=CellId("U1"),
        pin_ids=[PinId("U1.A"), PinId("U1.B"), PinId("U1.Y")],
        ...
    )
```

**Approximate Assertions for Float Math**:
```python
def test_two_inputs_evenly_distributed(self, design, simple_cell):
    layouts = calculator.calculate_pin_layouts(simple_cell, design)

    # Use pytest.approx for float comparison to handle precision
    assert y_positions[0] == pytest.approx(30.0, abs=0.1)
    assert y_positions[1] == pytest.approx(50.0, abs=0.1)
```

---

## 6. Integration Guide

### How CellItem Will Use This

```python
# Future usage in cell_item.py

class CellItem(QGraphicsItem):
    def __init__(self, cell: Cell, design: Design):
        super().__init__()
        self._cell = cell

        # Calculate pin layouts during construction
        calculator = SymbolLayoutCalculator()
        self._pin_layouts = calculator.calculate_pin_layouts(
            cell, design, cell_scene_pos=QPointF(0, 0)
        )

    def set_position(self, x: float, y: float) -> None:
        """When cell moves, update pin connection points."""
        self.setPos(x, y)

        # Recalculate connection points for net routing
        for layout in self._pin_layouts.values():
            layout.connection_point = QPointF(
                x + layout.position.x(),
                y + layout.position.y()
            )
```

### How Net Router Will Use This

```python
# Future usage in net_router.py

class NetRouter:
    def route_net(self, net: Net, scene: QGraphicsScene) -> None:
        """Route wires between pins using connection points."""
        # Get connection points from pin layouts
        points = []
        for pin_id in net.connected_pin_ids:
            cell_item = self._find_cell_item(pin_id)
            layout = cell_item._pin_layouts[str(pin_id)]
            points.append(layout.connection_point)

        # Create wire path through connection points
        path = self._calculate_orthogonal_path(points)
        self._draw_wire(path)
```

---

## 7. Common Tasks

### Adding Support for Top/Bottom Edges

If you need pins on top/bottom edges (e.g., for power pins):

```python
# In _calculate_pin_position:
if edge_side == "top":
    x_pos = PIN_MARGIN + (index + 1) * spacing  # Horizontal distribution
    y_pos = 0.0
elif edge_side == "bottom":
    x_pos = PIN_MARGIN + (index + 1) * spacing
    y_pos = cell_rect.height()
```

### Changing INOUT Pin Placement

Current behavior: INOUT pins go to right edge. To change:

```python
# In calculate_pin_layouts, modify the direction check:
if pin.direction == PinDirection.INPUT:
    input_pins.append(pin)
elif pin.direction == PinDirection.OUTPUT:
    output_pins.append(pin)
else:  # INOUT
    # Custom logic: could split between edges, go to both, etc.
    bidirectional_pins.append(pin)
```

### Adding Pin Sorting

To sort pins alphabetically by name:

```python
# In _distribute_pins_on_edge:
sorted_pins = sorted(pins, key=lambda p: p.name)
for i, pin in enumerate(sorted_pins):
    # ... position calculation
```

---

## 8. Troubleshooting

### Symptom: Pins Are All at Same Position

**Cause**: `total_pins` is 0 or 1 unexpectedly
**Debug**: Check that pins are being found in the design

```python
for pin_id in cell.pin_ids:
    pin = design.get_pin(pin_id)
    print(f"Pin {pin_id}: {pin}")  # Should not be None
```

### Symptom: Connection Points Are Wrong

**Cause**: `cell_scene_pos` not matching actual cell position
**Fix**: Ensure the position passed to `calculate_pin_layouts` matches `CellItem.pos()`

### Symptom: Height Adjustment Not Working

**Cause**: Check `adjust_cell_height_for_pins` is being called
**Note**: This method returns a value but doesn't modify the calculator - you must use the returned height

```python
height = calculator.adjust_cell_height_for_pins(10, 2)
calculator = SymbolLayoutCalculator(cell_height=height)  # New calculator with adjusted height
```

---

## 9. File Reference

| File | Lines | Purpose |
|------|-------|---------|
| `src/ink/presentation/canvas/symbol_layout_calculator.py` | 445 | Main implementation |
| `tests/unit/presentation/canvas/test_symbol_layout_calculator.py` | 700 | Unit tests |
| `src/ink/presentation/canvas/__init__.py` | 33 | Module exports |

---

## 10. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-28 | 1.0 | Claude | Initial implementation |

---

## Related Documentation

- [E02-F01-T03.spec.md](./E02-F01-T03.spec.md) - Original requirements
- [E02-F01-T03.post-docs.md](./E02-F01-T03.post-docs.md) - Quick reference
- [E02-F01-T01.spec.md](../T01/E02-F01-T01.spec.md) - CellItem (consumer)
