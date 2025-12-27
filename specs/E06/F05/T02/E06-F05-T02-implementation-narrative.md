# E06-F05-T02: Panel Layout Persistence - Implementation Narrative

## 1. Executive Summary

This document provides a comprehensive technical narrative of the Panel Layout Persistence implementation for the Ink schematic viewer. The implementation adds persistent storage for panel layout state using Qt's QSettings, enabling panel visibility, dock positions, and arrangement to persist across application sessions.

**Key Achievements:**
- 48 tests passing (36 unit for store + 12 unit for integration)
- Full TDD workflow with RED-GREEN-REFACTOR cycles
- Robust error handling for corrupted settings
- Integration with existing `PanelStateManager` and `InkMainWindow`

## 2. Problem Statement

### Business Context
Users expect professional applications to remember their workspace configuration. When a user:
- Hides the Messages panel because they're not debugging
- Moves the Hierarchy panel to the right side
- Makes the Properties panel a floating window

These preferences should persist across application sessions without manual reconfiguration.

### Technical Challenge
The challenge was to:
1. Serialize the `PanelState` to persistent storage
2. Handle Qt's opaque state blobs alongside structured metadata
3. Restore complex dock arrangements accurately
4. Gracefully handle corrupted or missing settings
5. Integrate seamlessly with existing MainWindow lifecycle

## 3. Architecture Design

### 3.1 Storage Strategy

The implementation stores both structured metadata and Qt's native state blobs:

```
QSettings Storage Structure
├── geometry/
│   ├── window         # QByteArray - main window geometry
│   └── state          # QByteArray - dock layout (tabs, splits, sizes)
└── panels/
    ├── Hierarchy/
    │   ├── visible     # bool
    │   ├── area        # string ("LEFT", "RIGHT", "BOTTOM", "FLOATING")
    │   ├── is_floating # bool
    │   ├── geometry    # dict {width, height, x, y}
    │   └── tab_group   # string (optional)
    ├── Properties/
    │   └── ...
    └── Messages/
        └── ...
```

**Why Both Storage Methods?**

| Qt State Blobs | Structured Metadata |
|----------------|---------------------|
| Perfect restoration of complex layouts | Queryable for application logic |
| Handles tabs, splits, nested docks | Human-readable in INI file |
| Opaque binary format | Supports schema migration |
| Qt version dependent | Stable across versions |

### 3.2 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Application Lifecycle                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐                              ┌─────────────────┐   │
│  │ App Start   │──►_restore_panel_layout()──►│ PanelSettingsStore │   │
│  └─────────────┘                              │  load_panel_state()│   │
│                                                └────────┬────────┘   │
│                                                         │            │
│                                                         ▼            │
│                                          ┌─────────────────────────┐ │
│                                          │   PanelStateManager     │ │
│                                          │   restore_state(state)  │ │
│                                          └─────────────────────────┘ │
│                                                                       │
│                           ... User works with app ...                 │
│                                                                       │
│  ┌─────────────┐                              ┌─────────────────┐   │
│  │ App Close   │──►closeEvent()────────────►│ PanelStateManager │   │
│  └─────────────┘                              │  capture_state()  │   │
│                                                └────────┬────────┘   │
│                                                         │            │
│                                                         ▼            │
│                                          ┌─────────────────────────┐ │
│                                          │ PanelSettingsStore      │ │
│                                          │ save_panel_state(state) │ │
│                                          └────────┬────────────────┘ │
│                                                   │                  │
│                                                   ▼                  │
│                                          ┌─────────────────────────┐ │
│                                          │     QSettings           │ │
│                                          │   (Disk Persistence)    │ │
│                                          └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Class Responsibilities

```
PanelSettingsStore (Infrastructure Layer)
├── Responsibility: Persist PanelState to/from QSettings
├── Dependencies: PySide6.QtCore.QSettings
└── Methods:
    ├── save_panel_state(state) → None
    ├── load_panel_state() → PanelState | None
    ├── has_saved_settings() → bool
    └── clear_panel_state() → None

InkMainWindow (Presentation Layer)
├── Responsibility: Coordinate persistence at lifecycle events
├── New Attributes:
│   └── panel_settings_store: PanelSettingsStore
└── New Methods:
    ├── _restore_panel_layout() → None
    ├── _save_panel_layout() → None
    └── reset_panel_layout() → None
```

## 4. Implementation Details

### 4.1 PanelSettingsStore Class

Located at: `src/ink/infrastructure/persistence/panel_settings_store.py`

#### Core Methods

```python
def save_panel_state(self, state: PanelState) -> None:
    """Save complete panel state to QSettings."""
    # 1. Save Qt's native state blobs for accurate restoration
    self.settings.beginGroup(self.GEOMETRY_GROUP)
    if state.qt_geometry is not None:
        self.settings.setValue("window", state.qt_geometry)
    if state.qt_state is not None:
        self.settings.setValue("state", state.qt_state)
    self.settings.endGroup()

    # 2. Save structured panel metadata for queryability
    self.settings.beginGroup(self.SETTINGS_GROUP)
    for panel_name, panel_info in state.panels.items():
        self._save_panel_info(panel_name, panel_info)
    self.settings.endGroup()

    # 3. Force write to disk (prevents data loss on crash)
    self.settings.sync()
```

#### Error Handling Strategy

```python
def _load_panel_info(self, panel_name: str) -> PanelInfo | None:
    """Load with validation and fallback defaults."""

    # Required field check - skip incomplete panels
    if not self.settings.contains("visible"):
        return None

    # Enum parsing with fallback
    try:
        area = DockArea[area_name]  # e.g., "LEFT" → DockArea.LEFT
    except KeyError:
        area = DockArea.LEFT  # Safe fallback

    # Dict handling without type parameter (QSettings limitation)
    geometry_value = self.settings.value("geometry", {})
    geometry_dict = geometry_value if isinstance(geometry_value, dict) else {}
```

### 4.2 MainWindow Integration

Located at: `src/ink/presentation/main_window.py`

#### Initialization Order
```python
def __init__(self, app_settings: AppSettings) -> None:
    # 1. Create panel settings store BEFORE dock widgets
    self.panel_settings_store = PanelSettingsStore()

    # 2. Setup UI components
    self._setup_dock_widgets()  # Creates docks and registers with manager

    # 3. Restore geometry (window size/position)
    self._restore_geometry()

    # 4. Restore panel layout (dock arrangement)
    self._restore_panel_layout()  # <-- NEW
```

**Why This Order?**
- Settings store must exist before docks (for potential early queries)
- Dock widgets must exist before restoration (Qt requires widgets to exist)
- Window geometry first, then dock layout (docks sized relative to window)

#### Close Event Integration
```python
def closeEvent(self, event: QCloseEvent) -> None:
    # Save window geometry
    self._save_geometry()

    # Save panel layout (NEW)
    self._save_panel_layout()

    event.accept()
```

### 4.3 Type Validation Fix

The integration revealed a critical edge case: corrupted settings could cause type mismatches.

**Problem:** Test sets invalid string in geometry key → PanelSettingsStore loads it → `restoreGeometry()` receives string instead of QByteArray → crash.

**Solution:** Type validation before Qt method calls:

```python
# In PanelStateManager.restore_state()
if state.qt_geometry is not None and isinstance(state.qt_geometry, QByteArray):
    self.main_window.restoreGeometry(state.qt_geometry)
if state.qt_state is not None and isinstance(state.qt_state, QByteArray):
    self.main_window.restoreState(state.qt_state)
```

## 5. TDD Implementation Flow

### 5.1 RED Phase - PanelSettingsStore Tests

Wrote 36 failing tests covering:
- Initialization (`test_creates_instance`, `test_has_settings_attribute`)
- Save operations (`test_save_panel_state_stores_*`)
- Load operations (`test_load_restores_*`)
- Round-trip (`test_roundtrip_preserves_complete_state`)
- Error handling (`test_load_handles_invalid_area_name`)
- Clear functionality (`test_clear_removes_*`)

### 5.2 GREEN Phase - Implementation

1. Created `PanelSettingsStore` class
2. Implemented `save_panel_state()` with group hierarchy
3. Implemented `load_panel_state()` with validation
4. Fixed QSettings dict handling (no `type=dict` parameter)
5. Added explicit casts for mypy compatibility

### 5.3 RED Phase - MainWindow Integration Tests

Wrote 12 failing tests covering:
- Attribute existence (`test_has_panel_settings_store_attribute`)
- Save on close (`test_close_event_saves_panel_state`)
- Restore on startup (`test_restores_panel_visibility`)
- Reset functionality (`test_reset_panel_layout_clears_saved_state`)
- Round-trip (`test_panel_layout_persists_across_sessions`)

### 5.4 GREEN Phase - MainWindow Changes

1. Added `panel_settings_store` attribute
2. Added `_restore_panel_layout()` called after dock setup
3. Added `_save_panel_layout()` called from `closeEvent()`
4. Added public `reset_panel_layout()` method

### 5.5 REFACTOR Phase

1. Fixed window visibility issue in tests (added `show()` and `waitExposed()`)
2. Fixed type validation in `restore_state()` for corrupted settings
3. Added `QByteArray` import to `panel_state_manager.py`

## 6. Testing Insights

### 6.1 Qt Visibility in Headless Mode

**Problem:** `isVisible()` returns `False` for widgets in a hidden window.

**Solution:** Show window and wait for exposure before checking visibility:
```python
window.show()
qtbot.waitExposed(window)
assert window.hierarchy_dock.isVisible() is True
```

### 6.2 Isolated QSettings in Tests

Each test gets isolated QSettings via fixture:
```python
@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    settings_path = tmp_path / "settings"
    settings_path.mkdir()
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(settings_path))
    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.clear()
    temp_settings.sync()
    yield settings_path
```

## 7. Deployment Considerations

### Storage Locations
| Platform | Path |
|----------|------|
| Linux | `~/.config/InkProject/Ink.conf` |
| Windows | `HKEY_CURRENT_USER\Software\InkProject\Ink` |
| macOS | `~/Library/Preferences/com.InkProject.Ink.plist` |

### Migration Strategy
The structured panel metadata enables future schema migrations:
1. Add version field to settings
2. Detect old version on load
3. Migrate or clear and use defaults

## 8. Code Statistics

| Metric | Value |
|--------|-------|
| New Lines of Code | ~650 (production) |
| Test Lines | ~700 |
| Test Count | 48 (36 + 12) |
| Files Added | 3 |
| Files Modified | 4 |
| Commits | 3 |

## 9. References

- **Spec:** `specs/E06/F05/T02/E06-F05-T02.spec.md`
- **Pre-docs:** `specs/E06/F05/T02/E06-F05-T02.pre-docs.md`
- **Dependency:** E06-F05-T01 (Panel State Management)
- **Qt Documentation:** [QSettings](https://doc.qt.io/qt-6/qsettings.html), [QMainWindow State](https://doc.qt.io/qt-6/qmainwindow.html#saveState)
