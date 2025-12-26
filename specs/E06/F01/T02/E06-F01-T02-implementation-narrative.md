# E06-F01-T02: Central Widget Setup - Implementation Narrative

## Overview

This document provides a comprehensive walkthrough of implementing the central widget setup for Ink's main window. It follows the TDD (Test-Driven Development) workflow and explains every decision, pattern, and implementation detail.

**Spec Reference**: [E06-F01-T02.spec.md](E06-F01-T02.spec.md)

---

## 1. Understanding the Problem

### The Central Widget Concept

In Qt's `QMainWindow` architecture, the **central widget** is a special area:

```
┌──────────────────────────────────────────────────────┐
│                    Menu Bar                           │
├──────────────────────────────────────────────────────┤
│                    Tool Bar                           │
├─────────┬──────────────────────────────┬─────────────┤
│         │                              │             │
│  Dock   │      CENTRAL WIDGET          │    Dock     │
│ Widget  │                              │   Widget    │
│  (Left) │  (SchematicCanvas lives      │   (Right)   │
│         │   here - the main            │             │
│         │   workspace area)            │             │
│         │                              │             │
├─────────┴──────────────────────────────┴─────────────┤
│                    Status Bar                         │
└──────────────────────────────────────────────────────┘
```

**Key Properties**:
- Occupies the largest area of the window
- Cannot be closed, moved, or undocked (unlike dock widgets)
- Automatically resizes with the window
- Qt manages its layout automatically

### Why a Placeholder?

The full schematic rendering is a complex feature (E02 - Rendering epic). This task focuses on:
1. Creating the widget container structure
2. Integrating it with `InkMainWindow`
3. Establishing the pattern for future replacement

---

## 2. TDD Workflow: RED Phase

### Writing Tests First

Before writing any implementation code, we define the expected behavior through tests.

#### Unit Tests for SchematicCanvas

**File**: `tests/unit/presentation/canvas/test_schematic_canvas.py`

```python
# Test 1: Basic instantiation
def test_canvas_can_be_created(self, qtbot: QtBot) -> None:
    canvas = SchematicCanvas()
    qtbot.addWidget(canvas)
    assert canvas is not None

# Test 2: Type inheritance
def test_canvas_is_qwidget_subclass(self, qtbot: QtBot) -> None:
    canvas = SchematicCanvas()
    qtbot.addWidget(canvas)
    assert isinstance(canvas, QWidget)

# Test 3: Parent handling
def test_canvas_accepts_parent_widget(self, qtbot: QtBot) -> None:
    parent = QWidget()
    qtbot.addWidget(parent)
    canvas = SchematicCanvas(parent=parent)
    assert canvas.parent() == parent
```

**Why these tests?**
- `test_canvas_can_be_created`: Ensures basic construction works
- `test_canvas_is_qwidget_subclass`: Verifies correct inheritance
- `test_canvas_accepts_parent_widget`: Tests Qt ownership model

#### Integration Tests for MainWindow

**File**: `tests/integration/presentation/test_main_window_canvas.py`

```python
# Test: Central widget is SchematicCanvas
def test_central_widget_is_schematic_canvas(self, qtbot: QtBot) -> None:
    window = InkMainWindow()
    qtbot.addWidget(window)
    central = window.centralWidget()
    assert isinstance(central, SchematicCanvas)

# Test: Direct attribute access
def test_schematic_canvas_attribute_exists(self, qtbot: QtBot) -> None:
    window = InkMainWindow()
    qtbot.addWidget(window)
    assert hasattr(window, "schematic_canvas")
    assert window.schematic_canvas is not None
```

**Why integration tests?**
- Verify that components work together correctly
- Test the actual Qt widget hierarchy
- Ensure the window displays properly

#### Running Tests (Expected Failure)

```bash
$ uv run python -m pytest tests/unit/presentation/canvas/ -v

E   ModuleNotFoundError: No module named 'ink.presentation.canvas'
```

This confirms RED phase - tests fail because the module doesn't exist yet.

---

## 3. TDD Workflow: GREEN Phase

### Step 1: Create Package Structure

**Directory Structure**:
```
src/ink/presentation/
├── __init__.py
├── main_window.py
└── canvas/           # NEW
    ├── __init__.py   # NEW
    └── schematic_canvas.py  # NEW
```

**File**: `src/ink/presentation/canvas/__init__.py`

```python
"""Canvas widgets for schematic visualization."""

from ink.presentation.canvas.schematic_canvas import SchematicCanvas

__all__ = ["SchematicCanvas"]
```

This provides clean imports: `from ink.presentation.canvas import SchematicCanvas`

### Step 2: Implement SchematicCanvas

**File**: `src/ink/presentation/canvas/schematic_canvas.py`

```python
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SchematicCanvas(QWidget):
    """Central canvas widget for schematic visualization."""

    _PLACEHOLDER_TEXT: str = "Schematic Canvas Area\n(Rendering implementation: E02)"
    _BACKGROUND_COLOR: str = "#f0f0f0"
    _TEXT_COLOR: str = "#666666"
    _FONT_SIZE: str = "16px"
    _PADDING: str = "20px"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the schematic canvas."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Configure the placeholder user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        placeholder = self._create_placeholder_label()
        layout.addWidget(placeholder)

    def _create_placeholder_label(self) -> QLabel:
        """Create the styled placeholder label."""
        label = QLabel(self._PLACEHOLDER_TEXT, self)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"""
            QLabel {{
                background-color: {self._BACKGROUND_COLOR};
                color: {self._TEXT_COLOR};
                font-size: {self._FONT_SIZE};
                padding: {self._PADDING};
            }}
        """)
        return label
```

**Key Implementation Details**:

1. **Class Constants**: Configuration values as class-level constants for testability
2. **Parent Parameter**: Follows Qt ownership model - parent deletes children
3. **Zero Margins**: `setContentsMargins(0, 0, 0, 0)` ensures canvas fills entire area
4. **Private Methods**: `_setup_ui()` and `_create_placeholder_label()` for clarity

### Step 3: Update InkMainWindow

**File**: `src/ink/presentation/main_window.py`

Add import:
```python
from ink.presentation.canvas import SchematicCanvas
```

Add class attribute for type hints:
```python
class InkMainWindow(QMainWindow):
    schematic_canvas: SchematicCanvas  # IDE/type checker support
```

Update `__init__`:
```python
def __init__(self) -> None:
    super().__init__()
    self._setup_window()
    self._setup_central_widget()  # NEW
```

Add central widget setup:
```python
def _setup_central_widget(self) -> None:
    """Create and configure the central schematic canvas."""
    self.schematic_canvas = SchematicCanvas(parent=self)
    self.setCentralWidget(self.schematic_canvas)
```

**Why `setCentralWidget()`?**
- Qt method that designates the primary content area
- Handles layout automatically
- Widget fills space between toolbars, docks, and status bar

### Step 4: Running Tests (Expected Pass)

```bash
$ uv run python -m pytest tests/ -v

============================== 31 passed ==============================
```

All tests pass - GREEN phase complete.

---

## 4. TDD Workflow: REFACTOR Phase

### Type Checking

Running mypy revealed an issue:

```bash
$ uv run mypy src/ tests/
error: Item "None" of "QLayout | None" has no attribute "contentsMargins"
```

**Problem**: `layout()` can return `None`, but we access `.contentsMargins()` directly.

**Solution**: Add assertion to narrow the type:

```python
def test_canvas_layout_has_no_margins(self, qtbot: QtBot) -> None:
    canvas = SchematicCanvas()
    qtbot.addWidget(canvas)

    layout = canvas.layout()
    assert layout is not None  # Type narrowing

    margins = layout.contentsMargins()
    # ... rest of test
```

### Code Quality Verification

```bash
# Linting
$ uv run ruff check src/ tests/ --fix
All checks passed!

# Type checking
$ uv run mypy src/ tests/
Success: no issues found in 10 source files

# Formatting
$ uv run ruff format src/ tests/
10 files left unchanged
```

---

## 5. Qt Patterns Explained

### Qt Ownership Model

```
InkMainWindow (parent)
    └── SchematicCanvas (child)
            └── QLabel (grandchild)
```

When `InkMainWindow` is deleted:
1. Qt automatically deletes `SchematicCanvas`
2. Which automatically deletes its `QLabel`

This prevents memory leaks without manual cleanup.

### QMainWindow Central Widget

```python
# Two ways to access the canvas:
window.schematic_canvas        # Direct attribute (faster, clearer)
window.centralWidget()         # Qt standard method

# They reference the same object:
assert window.schematic_canvas is window.centralWidget()
```

### Layout Zero Margins

```python
layout.setContentsMargins(0, 0, 0, 0)
#                         ↑  ↑  ↑  ↑
#                       left top right bottom
```

Without this, Qt adds default padding, creating visible gaps.

---

## 6. Testing Patterns Explained

### pytest-qt's `qtbot`

```python
def test_example(self, qtbot: QtBot) -> None:
    widget = QWidget()
    qtbot.addWidget(widget)  # Ensures cleanup after test
```

`qtbot.addWidget()` ensures Qt properly cleans up widgets after each test.

### Widget Visibility Testing

```python
def test_canvas_visible_when_window_shown(self, qtbot: QtBot) -> None:
    window = InkMainWindow()
    qtbot.addWidget(window)

    window.show()                    # Request window display
    qtbot.waitExposed(window)        # Wait for paint event

    assert window.schematic_canvas.isVisible()
```

`waitExposed()` ensures the window is actually painted before checking visibility.

---

## 7. Code Flow Diagram

```
Application Startup (future E06-F01-T04)
           │
           ▼
    InkMainWindow.__init__()
           │
           ├─── _setup_window()
           │         │
           │         ├── setWindowTitle()
           │         ├── resize()
           │         ├── setMinimumSize()
           │         └── setWindowFlags()
           │
           └─── _setup_central_widget()    ◄── NEW
                     │
                     ├── SchematicCanvas.__init__(parent=self)
                     │         │
                     │         └── _setup_ui()
                     │                  │
                     │                  ├── QVBoxLayout(self)
                     │                  ├── layout.setContentsMargins(0,0,0,0)
                     │                  ├── _create_placeholder_label()
                     │                  │         │
                     │                  │         ├── QLabel()
                     │                  │         ├── setAlignment(Center)
                     │                  │         └── setStyleSheet()
                     │                  │
                     │                  └── layout.addWidget(placeholder)
                     │
                     └── setCentralWidget(self.schematic_canvas)
```

---

## 8. Visual Result

When the application runs, the window displays:

```
┌──────────────────────────────────────────────────────────┐
│ Ink - Incremental Schematic Viewer                   - □ ✕│
├──────────────────────────────────────────────────────────┤
│                                                          │
│                                                          │
│                                                          │
│            ┌──────────────────────────────┐              │
│            │   Schematic Canvas Area      │              │
│            │ (Rendering implementation:   │              │
│            │           E02)               │              │
│            └──────────────────────────────┘              │
│                                                          │
│                                                          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

The placeholder clearly indicates:
1. This is the canvas area
2. Full rendering will come in E02

---

## 9. Future Replacement (E02)

When E02 (Rendering) is implemented, the placeholder will be replaced:

**Current (Placeholder)**:
```python
class SchematicCanvas(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Placeholder UI
```

**Future (Full Implementation)**:
```python
from PySide6.QtWidgets import QGraphicsView

class SchematicCanvas(QGraphicsView):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        # Full rendering setup
```

**What stays the same**:
- Class name: `SchematicCanvas`
- Constructor signature: `parent` parameter
- Package location: `ink.presentation.canvas`
- Window attribute: `window.schematic_canvas`

**What changes**:
- Base class: `QWidget` → `QGraphicsView`
- Internal implementation: Placeholder → Full rendering

---

## 10. Files Reference

| File | Line | Purpose |
|------|------|---------|
| `src/ink/presentation/canvas/__init__.py` | 1-23 | Package exports |
| `src/ink/presentation/canvas/schematic_canvas.py` | 1-114 | Canvas widget |
| `src/ink/presentation/main_window.py` | 126-149 | `_setup_central_widget()` |
| `tests/unit/presentation/canvas/test_schematic_canvas.py` | 1-147 | Unit tests |
| `tests/integration/presentation/test_main_window_canvas.py` | 1-93 | Integration tests |

---

## 11. Commit History

| Commit | Description |
|--------|-------------|
| `378766c` | `feat(presentation): implement SchematicCanvas as central widget [CU-86evzm333]` |

---

## 12. Summary

This implementation demonstrates:

1. **TDD Discipline**: Tests written before code, guiding implementation
2. **Qt Best Practices**: Ownership model, central widget pattern, proper styling
3. **Clean Architecture**: Canvas in presentation layer, no domain logic
4. **Incremental Development**: Placeholder enables future replacement
5. **Comprehensive Testing**: 18 tests covering all acceptance criteria
