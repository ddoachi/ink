# E06-F03-T02: View Control Tools - Implementation Narrative

## Overview

This document provides a comprehensive narrative of implementing View Control Tools for the Ink schematic viewer's toolbar. It tells the complete story of how zoom in, zoom out, and fit view functionality was added using Test-Driven Development (TDD).

---

## 1. The Problem We Solved

### 1.1 User Pain Point

When exploring large schematics, users need quick access to view manipulation controls. Without toolbar buttons:

- **Menu navigation interrupts workflow** - Users must navigate File → View → Zoom In
- **Keyboard shortcuts are not discoverable** - New users don't know Ctrl+= zooms in
- **Mouse wheel zoom has no "fit view" equivalent** - Can't quickly reset to see all content
- **No visual cues for available operations** - Users don't know what's possible

### 1.2 The Solution

Three toolbar buttons with keyboard shortcuts:

```
┌─────────────────────────────────────────────┐
│ [🔍-] [🔍+] [⊡]  │  ... other tools ...    │
│  Zoom   Zoom  Fit                           │
│  Out    In    View                          │
└─────────────────────────────────────────────┘
```

| Button | Shortcut | Function |
|--------|----------|----------|
| Zoom Out | Ctrl+- | Decrease view scale |
| Zoom In | Ctrl+= | Increase view scale |
| Fit View | Ctrl+0 | Show all content |

---

## 2. The TDD Journey

### 2.1 Phase 1: RED - Writing Failing Tests

We started by defining what success looks like. Before writing any implementation code, we wrote 13 tests that specify exactly how the view controls should behave.

#### Test Class Structure

```python
class TestViewControlActions:
    """Tests for view control toolbar actions - E06-F03-T02."""

    def test_view_actions_created(self, qtbot, app_settings):
        """Test view control actions are added to toolbar."""

    def test_view_actions_order(self, qtbot, app_settings):
        """Test view actions appear in correct order."""

    def test_view_action_shortcuts(self, qtbot, app_settings):
        """Test view actions have correct keyboard shortcuts."""

    def test_view_action_tooltips(self, qtbot, app_settings):
        """Test tooltips include action name and keyboard shortcut."""

    def test_zoom_in_triggered(self, qtbot, app_settings):
        """Test zoom in action calls canvas.zoom_in()."""

    def test_zoom_out_triggered(self, qtbot, app_settings):
        """Test zoom out action calls canvas.zoom_out()."""

    def test_fit_view_triggered(self, qtbot, app_settings):
        """Test fit view action calls canvas.fit_view()."""

    def test_view_actions_without_canvas(self, qtbot, app_settings):
        """Test view actions don't crash when canvas is missing."""

    def test_view_actions_without_zoom_methods(self, qtbot, app_settings):
        """Test view actions don't crash when canvas lacks zoom methods."""

    def test_view_actions_always_enabled(self, qtbot, app_settings):
        """Test view actions are always enabled."""

    def test_add_view_actions_method_exists(self, qtbot, app_settings):
        """Test that _add_view_actions() method exists."""

    def test_view_action_handlers_exist(self, qtbot, app_settings):
        """Test that action handler methods exist."""

    def test_toolbar_has_separator_after_view_actions(self, qtbot, app_settings):
        """Test visual separator is added after view control group."""
```

#### Initial Test Run Result

```
FAILED tests/.../test_main_window.py::TestViewControlActions::test_view_actions_created
FAILED tests/.../test_main_window.py::TestViewControlActions::test_view_actions_order
... (13 failures) ...
============================== 13 failed ==============================
```

This is exactly what we wanted! The tests fail because the functionality doesn't exist yet.

### 2.2 Phase 2: GREEN - Making Tests Pass

Now we implement the minimum code to make all tests pass.

#### Step 1: Add Required Imports

```python
# src/ink/presentation/main_window.py
from PySide6.QtGui import QAction, QIcon, QKeySequence
```

We needed `QAction` for toolbar actions, `QIcon` for loading system theme icons, and `QKeySequence` for keyboard shortcuts.

#### Step 2: Create the View Actions Method

```python
def _add_view_actions(self, toolbar: QToolBar) -> None:
    """Add view-related toolbar actions."""

    # Zoom Out (decrease first, conventional order)
    zoom_out_action = QAction(
        QIcon.fromTheme("zoom-out"),
        "Zoom Out",
        self,
    )
    zoom_out_action.setToolTip("Zoom out (Ctrl+-)")
    zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
    zoom_out_action.triggered.connect(self._on_zoom_out)
    toolbar.addAction(zoom_out_action)

    # Zoom In (increase second)
    zoom_in_action = QAction(
        QIcon.fromTheme("zoom-in"),
        "Zoom In",
        self,
    )
    zoom_in_action.setToolTip("Zoom in (Ctrl+=)")
    zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
    zoom_in_action.triggered.connect(self._on_zoom_in)
    toolbar.addAction(zoom_in_action)

    # Fit View (special operation last)
    fit_view_action = QAction(
        QIcon.fromTheme("zoom-fit-best"),
        "Fit View",
        self,
    )
    fit_view_action.setToolTip("Fit view to content (Ctrl+0)")
    fit_view_action.setShortcut(QKeySequence("Ctrl+0"))
    fit_view_action.triggered.connect(self._on_fit_view)
    toolbar.addAction(fit_view_action)
```

**Design Decision: Button Order**

We chose Zoom Out → Zoom In → Fit View because:
1. Decrease before increase is industry convention
2. Fit View is a "special" operation, so it goes last
3. Matches user mental model from browser and CAD tools

#### Step 3: Create Action Handlers

```python
def _on_zoom_in(self) -> None:
    """Handle zoom in action."""
    if (
        hasattr(self, "schematic_canvas")
        and self.schematic_canvas
        and hasattr(self.schematic_canvas, "zoom_in")
    ):
        self.schematic_canvas.zoom_in()

def _on_zoom_out(self) -> None:
    """Handle zoom out action."""
    if (
        hasattr(self, "schematic_canvas")
        and self.schematic_canvas
        and hasattr(self.schematic_canvas, "zoom_out")
    ):
        self.schematic_canvas.zoom_out()

def _on_fit_view(self) -> None:
    """Handle fit view action."""
    if (
        hasattr(self, "schematic_canvas")
        and self.schematic_canvas
        and hasattr(self.schematic_canvas, "fit_view")
    ):
        self.schematic_canvas.fit_view()
```

**Why Three Checks?**

1. `hasattr(self, "schematic_canvas")` - Attribute may not exist if called during partial initialization
2. `self.schematic_canvas` - Attribute may be explicitly set to `None`
3. `hasattr(self.schematic_canvas, "zoom_in")` - Canvas may be a mock or stub without the method

This defensive pattern ensures the action never crashes, regardless of canvas state.

#### Step 4: Call from Setup Toolbar

```python
def _setup_toolbar(self) -> None:
    """Create and configure the main toolbar."""
    # ... existing toolbar setup ...

    # View Group (E06-F03-T02): Zoom and view controls
    self._add_view_actions(self._toolbar)
    self._toolbar.addSeparator()
```

#### Step 5: Add Canvas Placeholder Methods

Even though SchematicCanvas is a placeholder, we added the zoom methods for integration:

```python
# src/ink/presentation/canvas/schematic_canvas.py

def zoom_in(self, factor: float = 1.2) -> None:
    """Zoom in by scaling factor."""
    # Placeholder: No-op until E02 implements QGraphicsView

def zoom_out(self, factor: float = 1.2) -> None:
    """Zoom out by inverse scaling factor."""
    # Placeholder: No-op until E02 implements QGraphicsView

def fit_view(self) -> None:
    """Fit all visible items in view."""
    # Placeholder: No-op until E02 implements QGraphicsView
```

#### Test Result After Implementation

```
============================== 13 passed ==============================
```

All tests pass! GREEN phase complete.

### 2.3 Phase 3: REFACTOR - Quality Improvements

With passing tests as our safety net, we improved code quality:

1. **Ran ruff linter** - Fixed commented-out code warnings
2. **Ran mypy** - Verified all type hints correct
3. **Formatted with ruff format** - Consistent code style
4. **Ran full test suite** - 438 tests pass

---

## 3. Code Flow Walkthrough

### 3.1 User Clicks "Zoom In" Button

Here's what happens when a user clicks the Zoom In toolbar button:

```
┌───────────────────────────────────────────────────────────────────┐
│ User clicks [🔍+] button                                          │
└─────────────────────────────┬─────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ Qt emits triggered() signal on zoom_in_action                     │
│   QAction.triggered.connect(self._on_zoom_in)                     │
└─────────────────────────────┬─────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ _on_zoom_in() handler called                                      │
│                                                                   │
│   def _on_zoom_in(self) -> None:                                  │
│       if (                                                        │
│           hasattr(self, "schematic_canvas")  # ✓ attribute exists │
│           and self.schematic_canvas          # ✓ not None         │
│           and hasattr(self.schematic_canvas, "zoom_in")  # ✓ has  │
│       ):                                                          │
│           self.schematic_canvas.zoom_in()    # ◀── Call canvas    │
└─────────────────────────────┬─────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ SchematicCanvas.zoom_in() executed                                │
│                                                                   │
│   (Currently placeholder - no-op)                                 │
│   (E02 will implement: self.scale(1.2, 1.2))                      │
└───────────────────────────────────────────────────────────────────┘
```

### 3.2 User Presses Ctrl+=

The keyboard shortcut triggers the same flow:

```
┌───────────────────────────────────────────────────────────────────┐
│ User presses Ctrl+=                                               │
└─────────────────────────────┬─────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ Qt matches shortcut to zoom_in_action                             │
│   zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)     │
└─────────────────────────────┬─────────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────────┐
│ Qt emits triggered() signal                                       │
│   (Same path as button click)                                     │
└───────────────────────────────────────────────────────────────────┘
```

---

## 4. Integration Points

### 4.1 Toolbar Infrastructure (E06-F03-T01)

Our view actions plug into the toolbar created by E06-F03-T01:

```python
# _setup_toolbar() creates:
self._toolbar = QToolBar("Main Toolbar", self)
self._toolbar.setObjectName("MainToolBar")
self._toolbar.setIconSize(QSize(24, 24))
self._toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
self.addToolBar(self._toolbar)

# We add to it:
self._add_view_actions(self._toolbar)
self._toolbar.addSeparator()
```

### 4.2 Schematic Canvas (E02 - Future)

Currently SchematicCanvas is a placeholder. When E02 implements the real canvas:

```python
# Current (placeholder):
class SchematicCanvas(QWidget):
    def zoom_in(self, factor: float = 1.2) -> None:
        pass  # No-op

# Future (E02 implementation):
class SchematicCanvas(QGraphicsView):
    def zoom_in(self, factor: float = 1.2) -> None:
        self.scale(factor, factor)  # Actually scales the view

    def zoom_out(self, factor: float = 1.2) -> None:
        self.scale(1.0 / factor, 1.0 / factor)

    def fit_view(self) -> None:
        self.fitInView(
            self.scene().itemsBoundingRect(),
            Qt.AspectRatioMode.KeepAspectRatio
        )
```

Our handlers will work without modification because they call the same methods.

### 4.3 Icon Resources (E06-F03-T04 - Future)

We use `QIcon.fromTheme()` for system icons:

```python
QIcon.fromTheme("zoom-in")   # Works on most Linux systems
QIcon.fromTheme("zoom-out")
QIcon.fromTheme("zoom-fit-best")
```

E06-F03-T04 will add fallback icons for systems without theme icons.

---

## 5. Testing Strategy

### 5.1 Test Structure

We organized tests to cover all acceptance criteria:

```
TestViewControlActions
├── test_view_actions_created         # Actions exist in toolbar
├── test_view_actions_order           # Correct order: Out → In → Fit
├── test_view_action_shortcuts        # Qt standard keys work
├── test_view_action_tooltips         # Tooltips show shortcuts
├── test_zoom_in_triggered            # Mock canvas receives call
├── test_zoom_out_triggered           # Mock canvas receives call
├── test_fit_view_triggered           # Mock canvas receives call
├── test_view_actions_without_canvas  # No crash when canvas = None
├── test_view_actions_without_zoom_methods  # No crash when methods missing
├── test_view_actions_always_enabled  # Always clickable
├── test_add_view_actions_method_exists     # Public interface exists
├── test_view_action_handlers_exist         # Handler methods exist
└── test_toolbar_has_separator_after_view_actions  # Visual grouping
```

### 5.2 Mock Usage

For testing canvas integration without a real canvas:

```python
def test_zoom_in_triggered(self, qtbot, app_settings):
    from unittest.mock import Mock

    window = InkMainWindow(app_settings)
    mock_canvas = Mock()
    window.schematic_canvas = mock_canvas

    # Trigger the action
    toolbar = window.findChild(QToolBar, "MainToolBar")
    actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}
    actions["Zoom In"].trigger()

    # Verify canvas method was called
    mock_canvas.zoom_in.assert_called_once()
```

### 5.3 Graceful Degradation Tests

Testing that actions don't crash with missing components:

```python
def test_view_actions_without_canvas(self, qtbot, app_settings):
    window = InkMainWindow(app_settings)
    window.schematic_canvas = None  # Explicitly None

    # Should not raise exception
    toolbar = window.findChild(QToolBar, "MainToolBar")
    actions = {a.text(): a for a in toolbar.actions() if not a.isSeparator()}

    actions["Zoom In"].trigger()   # No crash
    actions["Zoom Out"].trigger()  # No crash
    actions["Fit View"].trigger()  # No crash
```

---

## 6. Design Decisions Explained

### 6.1 Why QKeySequence.StandardKey Instead of String?

```python
# We use:
zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)

# Not:
zoom_in_action.setShortcut(QKeySequence("Ctrl+="))
```

**Reason**: `StandardKey.ZoomIn` is platform-aware:
- Linux/Windows: Ctrl+=
- macOS: Cmd+=

Using the standard key ensures consistent behavior across platforms.

### 6.2 Why Custom Ctrl+0 for Fit View?

Qt doesn't have a `StandardKey.FitView` because it's application-specific. We chose `Ctrl+0` because:

1. Industry convention (Figma, Sketch, many CAD tools)
2. "0" mentally maps to "zero zoom" or "reset"
3. Easy to remember and type

### 6.3 Why Tooltips Include Shortcuts?

```python
zoom_in_action.setToolTip("Zoom in (Ctrl+=)")
```

**Reason**: Discoverability. Users learn keyboard shortcuts by hovering over buttons. This is UX best practice from tools like VS Code, Figma, and Adobe products.

### 6.4 Why No Action Enable/Disable Logic?

Unlike undo/redo which requires state (undo stack non-empty), view controls are always applicable:
- Zoom in always possible (until max zoom)
- Zoom out always possible (until min zoom)
- Fit view always possible (even empty canvas)

Simpler code, better UX.

---

## 7. Troubleshooting Guide

### 7.1 Icons Not Appearing

**Symptom**: Toolbar shows text only, no icons

**Cause**: System lacks icon theme

**Solution**: E06-F03-T04 will add fallback icons. For now, install an icon theme:
```bash
sudo apt install adwaita-icon-theme
```

### 7.2 Shortcuts Not Working

**Symptom**: Ctrl+= doesn't zoom in

**Possible Causes**:
1. Focus not on main window
2. Another action captured the shortcut
3. Window manager intercepts shortcut

**Debugging**:
```python
# Check action shortcut is set correctly:
toolbar = window.findChild(QToolBar, "MainToolBar")
for action in toolbar.actions():
    if action.text() == "Zoom In":
        print(f"Shortcut: {action.shortcut().toString()}")
```

### 7.3 Canvas Methods Not Called

**Symptom**: Clicking button does nothing

**Possible Causes**:
1. `schematic_canvas` is None
2. Canvas doesn't have zoom methods

**Debugging**:
```python
# Check canvas state:
print(f"Canvas exists: {hasattr(window, 'schematic_canvas')}")
print(f"Canvas value: {window.schematic_canvas}")
print(f"Has zoom_in: {hasattr(window.schematic_canvas, 'zoom_in')}")
```

---

## 8. Summary

This implementation added view control tools to Ink's toolbar using a disciplined TDD approach:

1. **13 failing tests** defined the expected behavior
2. **Implementation** made all tests pass with minimal code
3. **Refactoring** improved quality with tests as safety net
4. **Documentation** captured learnings for future developers

The view controls are ready for integration when E02 implements the real SchematicCanvas with actual zoom functionality.

---

## Document Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-27 | 1.0 | Claude Opus 4.5 | Initial implementation narrative |

---

**End of Implementation Narrative**
