# E06-F04-T03 - Zoom Level Display: Implementation Narrative

## Document Information
- **Task**: E06-F04-T03 - Zoom Level Display
- **Status**: Completed
- **Created**: 2025-12-27
- **ClickUp Task ID**: 86evzm35g

---

## 1. Introduction and Context

### 1.1 The Problem We're Solving

When users navigate a large schematic, they need immediate awareness of their current view scale. Questions like "Am I zoomed in enough to see component details?" or "How far zoomed out am I?" should have an instantly visible answer without requiring user action.

The status bar's zoom display provides this passive awareness by showing the current zoom level as a percentage, updating in real-time as the user zooms in and out.

### 1.2 Why This Matters

Without zoom level display:
- Users can't tell if they're viewing at 100% (actual size) or some other scale
- No feedback during zoom operations (wheel scroll, button clicks)
- Difficult to return to a specific zoom level after navigating
- Professional applications like Cadence, Synopsys tools all show zoom level

This implementation connects the schematic canvas to the status bar using Qt's signal/slot mechanism, enabling automatic updates whenever zoom changes.

### 1.3 Dependencies

| Dependency | Status | Purpose |
|------------|--------|---------|
| E06-F04-T01 (Status Bar Setup) | ✅ Completed | Provides `zoom_label` widget |
| E02-F02 (Schematic Canvas) | Future | Will emit `zoom_changed` on user actions |

---

## 2. The Solution Architecture

### 2.1 High-Level Design

The solution uses Qt's signal/slot pattern to decouple the canvas (signal emitter) from the main window (slot handler):

```
┌─────────────────────┐     zoom_changed(float)     ┌─────────────────────┐
│  SchematicCanvas    │ ─────────────────────────▶  │  InkMainWindow      │
│                     │                              │                     │
│  zoom_changed       │     Signal: 150.0            │  update_zoom_status │
│  = Signal(float)    │ ─────────────────────────▶  │  (150.0)            │
│                     │                              │                     │
│  (Future: set_zoom) │                              │  zoom_label.setText │
│                     │                              │  ("Zoom: 150%")     │
└─────────────────────┘                              └─────────────────────┘
```

**Key Design Decisions:**

1. **Signal Emits Percentage**: The `zoom_changed` signal emits zoom as a percentage (150.0 for 150%), not as a factor (1.5). This simplifies the display logic since no conversion is needed.

2. **Integer Display**: Zoom is displayed without decimal places ("Zoom: 150%" not "Zoom: 150.5%"). Python's `:.0f` format specifier provides correct rounding.

3. **Graceful Degradation**: The connection code uses `hasattr` checks to handle cases where the canvas doesn't exist or doesn't have the signal (e.g., placeholder canvas).

### 2.2 Signal/Slot Connection Flow

```
Application Startup:
    InkMainWindow.__init__()
        ├── _setup_central_widget()     → Creates schematic_canvas
        ├── _setup_status_bar()          → Creates zoom_label with "Zoom: 100%"
        └── _connect_status_signals()    → Connects zoom_changed → update_zoom_status

Runtime (when zoom changes):
    User Action (scroll wheel, button click)
        → Canvas.set_zoom(1.5)           [Future implementation]
        → zoom_percent = 1.5 * 100.0
        → zoom_changed.emit(150.0)
        → update_zoom_status(150.0)
        → zoom_label.setText("Zoom: 150%")
```

---

## 3. Implementation Walkthrough

### 3.1 Adding the Signal to SchematicCanvas

**File**: `src/ink/presentation/canvas/schematic_canvas.py:27`

```python
from PySide6.QtCore import Qt, Signal  # Added Signal import
```

**File**: `src/ink/presentation/canvas/schematic_canvas.py:77-86`

```python
# ==========================================================================
# Qt Signals
# ==========================================================================
# Signals must be defined as class attributes, not instance attributes.
# Qt's meta-object system processes these at class definition time.

# Zoom level change signal
# Emits the zoom percentage as a float (e.g., 150.0 for 150%)
# Connected to InkMainWindow.update_zoom_status() for status bar updates
zoom_changed = Signal(float)
```

**Why Class Attribute?**

Qt signals are processed by the meta-object compiler (moc) at class definition time. Defining them as instance attributes in `__init__` would fail because:
1. The signal wouldn't be registered in the class's QMetaObject
2. Connections wouldn't work properly
3. Signal emission would raise AttributeError

### 3.2 The Update Method

**File**: `src/ink/presentation/main_window.py:1037-1061`

```python
def update_zoom_status(self, zoom_percent: float) -> None:
    """Update zoom level in status bar.

    Updates the zoom_label text to show the current zoom level as a
    percentage. The value is rounded to the nearest integer for display
    (no decimal places).

    This method is connected to SchematicCanvas.zoom_changed signal
    for automatic updates when the user zooms in/out.

    Args:
        zoom_percent: Current zoom level as percentage (e.g., 150.0 for 150%).
            Expected range is 10.0 to 1000.0 (10% to 1000%).

    Example:
        >>> window.update_zoom_status(150.0)  # Shows "Zoom: 150%"
        >>> window.update_zoom_status(75.5)   # Shows "Zoom: 76%" (rounded)
    """
    # Format zoom percentage as integer (no decimal places)
    # Using :.0f rounds to nearest integer
    self.zoom_label.setText(f"Zoom: {zoom_percent:.0f}%")
```

**Why `:.0f` Format?**

The `:.0f` format specifier:
- `.0` means zero decimal places
- `f` means floating-point format
- Provides banker's rounding (round half to even): 150.5 → 150, 151.5 → 152

This is preferable to `int()` which truncates rather than rounds.

### 3.3 Signal Connection

**File**: `src/ink/presentation/main_window.py:1063-1091`

```python
def _connect_status_signals(self) -> None:
    """Connect canvas signals to status bar update methods.

    Establishes signal/slot connections between the schematic canvas
    and status bar update methods. This enables real-time status bar
    updates when canvas state changes (zoom, selection, etc.).

    Signal Connections:
        - schematic_canvas.zoom_changed → update_zoom_status

    This method handles the case where the canvas may not yet be
    initialized or may not have the expected signals. It uses hasattr
    checks to avoid AttributeError exceptions.
    """
    # Connect zoom changes from canvas to status update
    # Check for signal existence to handle placeholder canvas gracefully
    if hasattr(self, "schematic_canvas") and hasattr(
        self.schematic_canvas, "zoom_changed"
    ):
        self.schematic_canvas.zoom_changed.connect(self.update_zoom_status)
```

**Why Double hasattr Check?**

1. `hasattr(self, "schematic_canvas")`: Handles case where method is called before canvas initialization
2. `hasattr(self.schematic_canvas, "zoom_changed")`: Handles case where canvas doesn't have the signal (future-proofing)

### 3.4 Initialization Integration

**File**: `src/ink/presentation/main_window.py:181-195`

```python
# Setup UI components BEFORE restoring geometry
self._setup_window()
self._setup_central_widget()    # Creates schematic_canvas
self._setup_dock_widgets()
self._setup_status_bar()        # Creates zoom_label
self._setup_menus()
self._setup_toolbar()

# Connect canvas signals to status bar updates (E06-F04-T03)
# Must be called after both canvas and status bar are created
self._connect_status_signals()

# Restore geometry AFTER all widgets are created
self._restore_geometry()
```

**Why This Order?**

The connection must happen:
- AFTER `_setup_central_widget()` (creates canvas with signal)
- AFTER `_setup_status_bar()` (creates zoom_label to update)
- BEFORE `_restore_geometry()` (in case geometry restoration triggers zoom)

---

## 4. The Data Flow

### 4.1 Zoom Update Flow

```python
# Example: User scrolls mouse wheel to zoom to 150%

# 1. Canvas receives wheel event (future E02 implementation)
def wheelEvent(self, event: QWheelEvent):
    delta = event.angleDelta().y()
    new_zoom = self.zoom_factor + (delta / 1200.0)  # Example calculation
    self.set_zoom(new_zoom)

# 2. Canvas updates zoom and emits signal
def set_zoom(self, zoom_factor: float):
    self.zoom_factor = max(0.1, min(10.0, zoom_factor))  # Clamp 10%-1000%
    zoom_percent = self.zoom_factor * 100.0
    self.zoom_changed.emit(zoom_percent)  # Emit 150.0

# 3. Main window receives signal and updates status bar
def update_zoom_status(self, zoom_percent: float):
    self.zoom_label.setText(f"Zoom: {zoom_percent:.0f}%")  # "Zoom: 150%"
```

### 4.2 Rounding Examples

| Input Value | Calculation | Display |
|-------------|-------------|---------|
| `100.0` | `f"{100.0:.0f}%"` | "Zoom: 100%" |
| `150.7` | `f"{150.7:.0f}%"` | "Zoom: 151%" |
| `75.3` | `f"{75.3:.0f}%"` | "Zoom: 75%" |
| `99.5` | `f"{99.5:.0f}%"` | "Zoom: 100%" (banker's) |
| `100.5` | `f"{100.5:.0f}%"` | "Zoom: 100%" (banker's) |
| `101.5` | `f"{101.5:.0f}%"` | "Zoom: 102%" (banker's) |

---

## 5. Testing Strategy

### 5.1 TDD Approach

We followed strict TDD methodology:

**RED Phase**: Wrote 24 tests that all failed (except initial 100% test)
```
FAILED tests/unit/presentation/test_main_window_zoom_status.py::TestUpdateZoomStatusMethod::test_update_zoom_status_method_exists
FAILED tests/integration/presentation/test_zoom_status_integration.py::TestCanvasZoomSignal::test_canvas_has_zoom_changed_signal
... (22 more failures)
```

**GREEN Phase**: Implemented just enough code to pass all tests
```
============================= 24 passed in 1.52s =============================
```

**REFACTOR Phase**: Formatted code with ruff, added comprehensive documentation

### 5.2 Unit Tests

**File**: `tests/unit/presentation/test_main_window_zoom_status.py`

| Test Class | Purpose |
|------------|---------|
| `TestUpdateZoomStatusMethod` | Method exists and accepts float |
| `TestZoomStatusFormatting` | Correct format for various zoom levels |
| `TestZoomStatusUpdates` | Sequential and immediate updates work |
| `TestZoomStatusEdgeCases` | Boundary values and rounding |

**Key Test Example**:

```python
def test_update_zoom_status_formats_integer_round_up(
    self, main_window: InkMainWindow
) -> None:
    """Zoom status should round up fractional percentages >= 0.5."""
    main_window.update_zoom_status(150.7)
    assert main_window.zoom_label.text() == "Zoom: 151%"
```

### 5.3 Integration Tests

**File**: `tests/integration/presentation/test_zoom_status_integration.py`

| Test Class | Purpose |
|------------|---------|
| `TestCanvasZoomSignal` | Signal exists on canvas class |
| `TestZoomSignalConnection` | Signal emission triggers status update |
| `TestZoomStatusInitialization` | Initial 100% zoom on startup |
| `TestConnectStatusSignalsMethod` | Connection method handles edge cases |
| `TestZoomUpdateTriggers` | Various zoom scenarios work |

**Key Test Example**:

```python
def test_zoom_signal_connected(self, main_window: InkMainWindow) -> None:
    """Test that zoom_changed signal triggers status update."""
    # Emit zoom changed signal with 150%
    main_window.schematic_canvas.zoom_changed.emit(150.0)

    # Status should update
    assert main_window.zoom_label.text() == "Zoom: 150%"
```

---

## 6. Edge Cases and Error Handling

### 6.1 Canvas Not Initialized

```python
# _connect_status_signals handles missing canvas
if hasattr(self, "schematic_canvas") and hasattr(
    self.schematic_canvas, "zoom_changed"
):
    # Only connect if both exist
    self.schematic_canvas.zoom_changed.connect(self.update_zoom_status)
```

### 6.2 Extreme Zoom Values

| Scenario | Input | Output | Notes |
|----------|-------|--------|-------|
| Minimum zoom | `10.0` | "Zoom: 10%" | Canvas should clamp |
| Maximum zoom | `1000.0` | "Zoom: 1000%" | Canvas should clamp |
| Below minimum | `5.0` | "Zoom: 5%" | Displays but canvas should prevent |
| Above maximum | `1500.0` | "Zoom: 1500%" | Displays but canvas should prevent |

### 6.3 Rapid Zoom Changes

Qt's signal/slot mechanism handles rapid emissions gracefully:
- Each emission is processed in order
- The final zoom value is displayed
- No queuing or debouncing needed

---

## 7. Future Integration Points

### 7.1 E02-F02: Schematic Canvas Implementation

When the full canvas is implemented, it will emit `zoom_changed` in these scenarios:

```python
class SchematicCanvas(QGraphicsView):
    zoom_changed = Signal(float)

    def wheelEvent(self, event):
        """Mouse wheel zoom."""
        # Calculate new zoom...
        self.zoom_changed.emit(new_zoom * 100.0)

    def zoom_in(self):
        """Zoom In button/Ctrl++ action."""
        # Calculate new zoom...
        self.zoom_changed.emit(new_zoom * 100.0)

    def fit_to_view(self):
        """Fit-to-View/Ctrl+0 action."""
        # Calculate fit zoom...
        self.zoom_changed.emit(fit_zoom * 100.0)
```

### 7.2 Related Status Updates

The same `_connect_status_signals` pattern will be used for:
- **E06-F04-T02**: Selection status (`selection_changed` → `update_selection_status`)
- **E06-F04-T04**: Object counts (`objects_changed` → `update_object_count_status`)

---

## 8. Debugging Guide

### 8.1 Zoom Not Updating

**Symptom**: Zoom label stays at "Zoom: 100%" when zooming

**Checklist**:
1. Is `zoom_changed` signal defined on canvas class?
   ```python
   assert hasattr(canvas.__class__, 'zoom_changed')
   ```
2. Is signal connected?
   ```python
   # Check if slot is connected (Qt doesn't expose this easily)
   # Best: Add debug print in update_zoom_status
   ```
3. Is signal being emitted?
   ```python
   # Add debug: print(f"Emitting zoom_changed: {zoom_percent}")
   self.zoom_changed.emit(zoom_percent)
   ```

### 8.2 Incorrect Zoom Display

**Symptom**: Wrong zoom percentage shown

**Possible Causes**:
1. Emitting zoom factor (1.5) instead of percentage (150.0)
2. Rounding issue in calculation
3. Signal emitting before label exists

---

## 9. Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-27 | 1.0 | Claude | Initial implementation narrative |
