# E06-F05-T01: Panel State Management - Implementation Narrative

## 1. Executive Summary

This document provides a comprehensive technical narrative of the Panel State Management implementation for the Ink schematic viewer. The implementation establishes a reactive state tracking system for dock widget panels using Qt's signal/slot mechanism, enabling programmatic control and future persistence capabilities.

**Key Achievements:**
- 74 tests passing (55 unit + 19 integration)
- Clean separation between structured state and Qt's opaque state blobs
- Full TDD workflow with RED-GREEN-REFACTOR cycles
- Integration with existing `InkMainWindow`

## 2. Problem Statement

### Business Context
The Ink schematic viewer uses three dock widget panels (Hierarchy, Properties, Messages) that users can show, hide, resize, and reposition. To provide a professional user experience, the application needs to:

1. Track panel visibility and position programmatically
2. Provide API for View menu toggle actions
3. Support state persistence across sessions
4. Handle panel state changes reactively

### Technical Challenge
Qt's dock widget system provides signals for state changes but doesn't offer a centralized state management API. The challenge was to create a clean abstraction layer that:
- Maintains synchronized state with Qt's internal representation
- Provides queryable state for application logic
- Emits custom signals for UI updates
- Supports state capture/restore for persistence

## 3. Architecture Design

### 3.1 Two-Tier State Architecture

The implementation uses a two-tier state storage approach:

```
┌─────────────────────────────────────────────────────────────┐
│                    PanelState (Tier 1)                       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  panels: dict[str, PanelInfo]                        │    │
│  │    "Hierarchy" → PanelInfo(visible=True, area=LEFT)  │    │
│  │    "Properties" → PanelInfo(visible=True, area=RIGHT)│    │
│  │    "Messages" → PanelInfo(visible=True, area=BOTTOM) │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Qt State Blobs (Tier 2)                             │    │
│  │    qt_state: QByteArray (from saveState())           │    │
│  │    qt_geometry: QByteArray (from saveGeometry())     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Why Two Tiers?**

| Tier 1: Structured State | Tier 2: Qt Blobs |
|--------------------------|------------------|
| Queryable at runtime | Opaque binary data |
| Enables application logic | Preserves complex layouts |
| Human-readable serialization | Perfect restoration |
| API-friendly | Qt-internal format |

### 3.2 Signal Flow Architecture

```
QDockWidget                  PanelStateManager               Application
     │                             │                              │
     │  visibilityChanged(bool)    │                              │
     ├────────────────────────────►│                              │
     │                             │  _on_visibility_changed()    │
     │                             ├──────┐                       │
     │                             │      │ Update panels dict    │
     │                             │◄─────┘                       │
     │                             │                              │
     │                             │  panel_visibility_changed    │
     │                             ├─────────────────────────────►│
     │                             │  state_changed               │
     │                             ├─────────────────────────────►│
     │                             │                              │
```

### 3.3 Class Hierarchy

```
PySide6.QtCore.QObject
         │
         └── PanelStateManager
                   │
                   ├── signals: state_changed, panel_visibility_changed, panel_area_changed
                   ├── state: PanelState
                   ├── _dock_widgets: dict[str, QDockWidget]
                   └── main_window: QMainWindow

@dataclass
PanelState
   ├── panels: dict[str, PanelInfo]
   ├── qt_state: QByteArray | None
   └── qt_geometry: QByteArray | None

@dataclass
PanelInfo
   ├── name: str
   ├── visible: bool
   ├── area: DockArea
   ├── is_floating: bool
   ├── geometry: PanelGeometry
   └── tab_group: str | None

@dataclass
PanelGeometry
   ├── width: int
   ├── height: int
   ├── x: int
   └── y: int

Enum(DockArea)
   ├── LEFT = Qt.DockWidgetArea.LeftDockWidgetArea
   ├── RIGHT = Qt.DockWidgetArea.RightDockWidgetArea
   ├── BOTTOM = Qt.DockWidgetArea.BottomDockWidgetArea
   └── FLOATING = -1
```

## 4. Implementation Details

### 4.1 Data Structures (`panel_state.py`)

#### DockArea Enum
```python
class DockArea(Enum):
    """Simplified dock area enum with Qt mappings."""
    LEFT = Qt.DockWidgetArea.LeftDockWidgetArea
    RIGHT = Qt.DockWidgetArea.RightDockWidgetArea
    BOTTOM = Qt.DockWidgetArea.BottomDockWidgetArea
    FLOATING = -1  # Custom value for undocked panels
```

**Design Decision:** TOP is excluded because Ink's UI only uses LEFT, RIGHT, and BOTTOM. TOP is reserved for toolbars in Qt's layout system.

#### PanelGeometry Dataclass
```python
@dataclass
class PanelGeometry:
    """Geometry with sensible defaults."""
    width: int = 0
    height: int = 0
    x: int = 0
    y: int = 0
```

**Design Decision:** All fields default to zero, enabling partial construction. For docked panels, only width/height matter. For floating panels, x/y capture screen position.

#### PanelInfo Dataclass
```python
@dataclass
class PanelInfo:
    """Complete panel metadata."""
    name: str
    visible: bool = True
    area: DockArea = DockArea.LEFT
    is_floating: bool = False
    geometry: PanelGeometry = field(default_factory=PanelGeometry)
    tab_group: str | None = None  # Future: tabbed panel support
```

**Design Decision:** Uses `field(default_factory=...)` for geometry to avoid the mutable default argument pitfall in Python.

### 4.2 State Manager (`panel_state_manager.py`)

#### Signal Definitions
```python
class PanelStateManager(QObject):
    # Emitted on any state change
    state_changed = Signal()

    # Emitted with (panel_name, visible)
    panel_visibility_changed = Signal(str, bool)

    # Emitted with (panel_name, DockArea)
    panel_area_changed = Signal(str, DockArea)
```

#### Panel Registration
```python
def register_panel(self, name: str, dock_widget: QDockWidget) -> None:
    # Store reference
    self._dock_widgets[name] = dock_widget

    # Capture initial state
    panel_info = PanelInfo(
        name=name,
        visible=dock_widget.isVisible(),
        area=self._get_dock_area(dock_widget),
        is_floating=dock_widget.isFloating(),
        geometry=self._get_panel_geometry(dock_widget),
    )
    self.state.panels[name] = panel_info

    # Connect signals
    self._connect_panel_signals(name, dock_widget)
```

**Signal Connection Implementation:**
```python
def _connect_panel_signals(self, name: str, dock_widget: QDockWidget) -> None:
    dock_widget.visibilityChanged.connect(
        lambda visible: self._on_visibility_changed(name, visible)
    )
    dock_widget.topLevelChanged.connect(
        lambda floating: self._on_floating_changed(name, floating)
    )
    dock_widget.dockLocationChanged.connect(
        lambda area: self._on_location_changed(name, area)
    )
```

**Design Decision:** Lambdas capture `name` by closure to identify which panel triggered the signal. This is necessary because Qt signals don't include source identification.

### 4.3 MainWindow Integration

```python
def _setup_dock_widgets(self) -> None:
    self._setup_hierarchy_dock()
    self._setup_property_dock()
    self._setup_message_dock()
    self._set_initial_dock_sizes()
    self._setup_panel_state_manager()  # NEW

def _setup_panel_state_manager(self) -> None:
    self.panel_state_manager = PanelStateManager(self)

    self.panel_state_manager.register_panel("Hierarchy", self.hierarchy_dock)
    self.panel_state_manager.register_panel("Properties", self.property_dock)
    self.panel_state_manager.register_panel("Messages", self.message_dock)
```

## 5. TDD Workflow

### 5.1 TDD Cycles

**Cycle 1: Data Structures**
```
RED:   27 tests → ModuleNotFoundError (panel_state.py doesn't exist)
GREEN: Implemented DockArea, PanelGeometry, PanelInfo, PanelState
       27 tests → All passing
```

**Cycle 2: PanelStateManager Core**
```
RED:   28 tests → ModuleNotFoundError (panel_state_manager.py doesn't exist)
GREEN: Implemented PanelStateManager with signals and handlers
       28 tests → All passing
```

**Cycle 3: Integration**
```
RED:   19 tests → Some failures due to headless mode behavior
GREEN: Adapted tests for headless Qt behavior
       19 tests → All passing
```

### 5.2 Test Distribution

| Category | Test File | Count |
|----------|-----------|-------|
| Data Structures | `test_panel_state.py` | 27 |
| Manager (mocked) | `test_panel_state_manager.py` | 28 |
| Integration | `test_panel_state_integration.py` | 19 |
| **Total** | | **74** |

## 6. Headless Testing Challenges

### Problem
Qt's `visibilityChanged` signal behaves differently when the window isn't shown:
- `hide()` → Emits `visibilityChanged(False)` reliably
- `show()` → May NOT emit signal (widget not truly visible)
- `isVisible()` → Returns `False` for all widgets in unshown window

### Solution
Tests adapted to verify behavior via:
1. `isHidden()` - Checks explicit hidden flag (not visibility)
2. State tracking - Verify `PanelState.panels[name].visible` updates

**Example Adaptation:**
```python
# Before (fails in headless):
assert dock.isVisible() is True

# After (works in headless):
assert not dock.isHidden()
```

## 7. Code Flow Examples

### 7.1 Panel Hide Flow

```
User closes Hierarchy dock (clicks X button)
         │
         ▼
QDockWidget.hide() called internally by Qt
         │
         ▼
Qt emits visibilityChanged(False)
         │
         ▼
Lambda connected during register_panel() receives signal
lambda visible: self._on_visibility_changed("Hierarchy", visible)
         │
         ▼
_on_visibility_changed("Hierarchy", False) executes:
  1. self.state.panels["Hierarchy"].visible = False
  2. self.panel_visibility_changed.emit("Hierarchy", False)
  3. self.state_changed.emit()
         │
         ▼
View menu checkbox updates (when E06-F02 implemented)
```

### 7.2 State Capture Flow

```
Application needs to save state (e.g., on close)
         │
         ▼
capture_state() called
         │
         ▼
For each registered panel:
  - Update geometry from dock widget
         │
         ▼
self.state.qt_state = self.main_window.saveState()
self.state.qt_geometry = self.main_window.saveGeometry()
         │
         ▼
Return complete PanelState
         │
         ▼
AppSettings persists to QSettings (E06-F05-T02)
```

## 8. API Reference Summary

### PanelStateManager

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `register_panel` | `name: str, dock: QDockWidget` | `None` | Register dock for tracking |
| `capture_state` | - | `PanelState` | Capture complete state snapshot |
| `restore_state` | `state: PanelState` | `None` | Restore from saved state |
| `show_panel` | `name: str` | `None` | Show and raise panel |
| `hide_panel` | `name: str` | `None` | Hide panel |
| `toggle_panel` | `name: str` | `None` | Toggle visibility |
| `get_state` | - | `PanelState` | Alias for capture_state |

### Signals

| Signal | Parameters | Emitted When |
|--------|------------|--------------|
| `state_changed` | - | Any panel state changes |
| `panel_visibility_changed` | `name: str, visible: bool` | Panel shown/hidden |
| `panel_area_changed` | `name: str, area: DockArea` | Panel moved to new area |

## 9. Performance Considerations

1. **Signal Connections**: O(1) per signal emission, no performance concerns
2. **State Capture**: O(n) where n = number of panels (typically 3)
3. **Qt saveState()**: Single Qt call, O(1) conceptually

## 10. Future Enhancements

### E06-F05-T02: State Persistence
- Serialize `PanelState` to `AppSettings`
- Call `capture_state()` on window close
- Call `restore_state()` on window open

### E06-F05-T03: Settings Migration
- Handle format changes between versions
- Provide graceful fallback for corrupted state

### E06-F02: View Menu Integration
- Connect View menu checkboxes to `toggle_panel()`
- Update checkboxes from `panel_visibility_changed` signal

## 11. Commits Summary

| Commit | Description |
|--------|-------------|
| `c53ba7e` | feat(state): add panel state data structures |
| `e611558` | feat(state): add PanelStateManager for reactive tracking |
| `2322fb3` | test(integration): add panel state integration tests |
| `c50710e` | feat(window): integrate PanelStateManager into InkMainWindow |
| `8bf1b57` | style: format code with ruff |

## 12. Conclusion

The Panel State Management implementation successfully provides:

1. **Clean Architecture**: Separation between data structures and manager
2. **Reactive Design**: Qt signal-based state synchronization
3. **Testability**: 74 tests covering unit and integration scenarios
4. **Extensibility**: Ready for persistence and UI integration
5. **Robustness**: Handles headless environments and edge cases

The implementation follows DDD principles with the state management living in the presentation layer, ready to serve both the view layer (menus) and infrastructure layer (persistence).
