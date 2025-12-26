# E06-F01-T03 - Dock Widget Setup: Implementation Narrative

**Task**: E06-F01-T03 - Dock Widget Setup
**Date**: 2025-12-26
**Author**: Claude

---

## 1. The Problem We Solved

EDA tools like Ink need supporting panels around the central schematic canvas:
- **Hierarchy panel**: Navigate the design object tree (cells, nets, ports)
- **Property panel**: Inspect selected object properties
- **Message panel**: View search results, logs, and status messages

These panels must support standard docking behaviors:
- Close (hide) panels to maximize canvas space
- Float panels as independent windows for multi-monitor setups
- Move panels to different window edges
- Resize panels with splitter handles
- Tab multiple panels in the same area

Qt's `QDockWidget` system provides all this functionality automatically, but requires careful configuration to achieve the desired layout and behavior.

---

## 2. Architecture Overview

### 2.1 Component Structure

```
InkMainWindow (QMainWindow)
├── Central Widget: SchematicCanvas
├── Left Dock Area
│   └── hierarchy_dock (QDockWidget)
│       └── hierarchy_panel (HierarchyPanel)
├── Right Dock Area
│   └── property_dock (QDockWidget)
│       └── property_panel (PropertyPanel)
└── Bottom Dock Area
    └── message_dock (QDockWidget)
        └── message_panel (MessagePanel)
```

### 2.2 Why Separate Panel and Dock Widgets?

The dock widget is a **container** providing docking behavior. The panel widget is the **content** providing actual UI.

This separation provides:
1. **Independent testing**: Panel content can be tested without dock behavior
2. **Reusability**: Panels could be used in non-dock contexts
3. **Clean replacement**: Future implementations replace panel, not dock
4. **Qt convention**: Standard pattern in Qt applications

---

## 3. Implementation Walkthrough

### 3.1 Creating the Panels Package

First, we created the panels package structure:

```
src/ink/presentation/panels/
├── __init__.py           # Package exports
├── hierarchy_panel.py    # Left panel
├── property_panel.py     # Right panel
└── message_panel.py      # Bottom panel
```

**`panels/__init__.py`** (`src/ink/presentation/panels/__init__.py:1-29`):
```python
"""Panel widgets for supporting UI areas."""

from ink.presentation.panels.hierarchy_panel import HierarchyPanel
from ink.presentation.panels.message_panel import MessagePanel
from ink.presentation.panels.property_panel import PropertyPanel

__all__ = ["HierarchyPanel", "MessagePanel", "PropertyPanel"]
```

The `__all__` list makes these the public API of the package.

### 3.2 Panel Widget Implementation

Each panel follows the same pattern. Here's `HierarchyPanel` (`src/ink/presentation/panels/hierarchy_panel.py:40-96`):

```python
class HierarchyPanel(QWidget):
    """Design hierarchy and object tree panel.

    Placeholder for MVP main window setup. Full implementation in E04-F01.
    """

    _PLACEHOLDER_TEXT: str = "Hierarchy Panel\n(Implementation: E04-F01)"
    _PLACEHOLDER_STYLE: str = "QLabel { color: #666; padding: 10px; }"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize hierarchy panel placeholder."""
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup placeholder UI with centered label."""
        layout = QVBoxLayout(self)
        placeholder = QLabel(self._PLACEHOLDER_TEXT, self)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(self._PLACEHOLDER_STYLE)
        layout.addWidget(placeholder)
```

**Why this design?**
- Class constants for placeholder text make testing easier
- Gray color (`#666`) indicates placeholder status
- Implementation reference (E04-F01) helps developers understand the plan
- `QVBoxLayout` allows content to expand when real implementation is added

### 3.3 Main Window Dock Setup

The dock setup was added to `InkMainWindow` (`src/ink/presentation/main_window.py`):

**Constructor change** (line 107):
```python
def __init__(self) -> None:
    super().__init__()
    self._setup_window()
    self._setup_central_widget()
    self._setup_dock_widgets()  # NEW
```

**Dock nesting** (line 156-159):
```python
# Enable dock nesting for complex layouts
self.setDockNestingEnabled(True)
```

**Main dock setup method** (line 186-215):
```python
def _setup_dock_widgets(self) -> None:
    """Create and configure dockable panels."""
    self._setup_hierarchy_dock()
    self._setup_property_dock()
    self._setup_message_dock()
    self._set_initial_dock_sizes()
```

### 3.4 Individual Dock Configuration

Each dock has its own setup method. Here's hierarchy dock (`src/ink/presentation/main_window.py:217-249`):

```python
def _setup_hierarchy_dock(self) -> None:
    """Create and configure the hierarchy dock widget (left area)."""
    # Create panel content
    self.hierarchy_panel = HierarchyPanel(self)

    # Create dock widget container
    self.hierarchy_dock = QDockWidget("Hierarchy", self)

    # Set object name - required for saveState()/restoreState()
    self.hierarchy_dock.setObjectName("HierarchyDock")

    # Set panel as dock content
    self.hierarchy_dock.setWidget(self.hierarchy_panel)

    # Restrict to left/right areas
    self.hierarchy_dock.setAllowedAreas(
        Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
    )

    # Add to left dock area by default
    self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.hierarchy_dock)
```

**Key configuration points:**
1. **Object name**: Critical for state persistence - Qt uses this to identify docks
2. **Allowed areas**: Vertical panels on sides only (not top/bottom)
3. **Default position**: Left area for hierarchy

### 3.5 Size Configuration

Initial sizes use minimums (`src/ink/presentation/main_window.py:313-349`):

```python
def _set_initial_dock_sizes(self) -> None:
    """Set initial size hints for dock widgets."""
    # Hierarchy (left): minimum usable width for tree view
    self.hierarchy_dock.setMinimumWidth(150)
    self.hierarchy_panel.setMinimumSize(150, 200)

    # Property (right): wider for property names and values
    self.property_dock.setMinimumWidth(200)
    self.property_panel.setMinimumSize(200, 200)

    # Message (bottom): minimum height for log viewing
    self.message_dock.setMinimumHeight(100)
    self.message_panel.setMinimumSize(300, 100)
```

**Why minimum sizes instead of exact ratios?**
- Qt's dock layout is complex and sizes are approximate
- Users resize to their preference anyway
- Minimums prevent unusable panels
- E06-F05 will add exact sizing with `QSettings` persistence

---

## 4. Test-Driven Development Approach

### 4.1 RED Phase: Writing Failing Tests First

Before any implementation, we wrote 51 tests:

**Panel unit tests** (`tests/unit/presentation/panels/test_panels.py`):
```python
class TestHierarchyPanel:
    def test_hierarchy_panel_creation(self, qapp):
        panel = HierarchyPanel()
        assert panel is not None

    def test_hierarchy_panel_has_placeholder_label(self, qapp):
        panel = HierarchyPanel()
        layout = panel.layout()
        assert layout is not None
        label_widget = layout.itemAt(0).widget()
        assert isinstance(label_widget, QLabel)
        assert "Hierarchy" in label_widget.text()
```

**Integration tests** (`tests/integration/presentation/test_main_window_docks.py`):
```python
class TestDockWidgetPositions:
    def test_hierarchy_dock_on_left(self, window):
        area = window.dockWidgetArea(window.hierarchy_dock)
        assert area == Qt.DockWidgetArea.LeftDockWidgetArea

class TestDockWidgetAllowedAreas:
    def test_message_dock_allowed_areas(self, window):
        allowed = window.message_dock.allowedAreas()
        assert allowed & Qt.DockWidgetArea.BottomDockWidgetArea
        assert not (allowed & Qt.DockWidgetArea.LeftDockWidgetArea)
```

### 4.2 GREEN Phase: Making Tests Pass

We implemented the minimal code to pass each test:
1. Created panel widgets with proper structure
2. Added dock setup to main window
3. Configured allowed areas and positions
4. Set minimum sizes

### 4.3 Test Fixture Lessons

**Problem 1**: Generator type hints for pytest fixtures

```python
# Wrong - mypy error
def qapp() -> QApplication:
    yield app

# Correct
def qapp() -> Generator[QApplication, None, None]:
    yield app
```

**Problem 2**: QApplication.instance() returns `QCoreApplication | None`

```python
# Wrong - type error
existing = QApplication.instance()
if existing is not None:
    yield existing  # Error: QCoreApplication, not QApplication

# Correct
existing = QApplication.instance()
if existing is not None and isinstance(existing, QApplication):
    yield existing
```

**Problem 3**: Qt visibility before window shown

```python
# Wrong - fails before show()
assert window.hierarchy_dock.isVisible()

# Correct - checks hidden flag, not visibility
assert not window.hierarchy_dock.isHidden()
```

---

## 5. How It All Connects

### 5.1 Initialization Flow

```
InkMainWindow.__init__()
    ├── _setup_window()
    │   └── setDockNestingEnabled(True)
    ├── _setup_central_widget()
    │   └── setCentralWidget(SchematicCanvas)
    └── _setup_dock_widgets()
        ├── _setup_hierarchy_dock()
        │   ├── HierarchyPanel(self)
        │   ├── QDockWidget("Hierarchy", self)
        │   ├── setObjectName("HierarchyDock")
        │   ├── setAllowedAreas(Left | Right)
        │   └── addDockWidget(Left, hierarchy_dock)
        ├── _setup_property_dock()
        │   └── (similar to hierarchy)
        ├── _setup_message_dock()
        │   └── (similar, but Bottom only)
        └── _set_initial_dock_sizes()
            └── setMinimumWidth/Height on each dock
```

### 5.2 User Interaction Flow

```
User clicks close button on hierarchy dock
    └── hierarchy_dock.close() called by Qt
        └── Dock becomes hidden (isHidden() = True)
            └── Canvas expands to fill space

User drags hierarchy dock title bar
    └── Qt initiates dock floating
        └── Dock becomes separate window
            └── User can move it to other monitors

User drags floating dock to left edge
    └── Qt shows dock highlight
        └── User releases mouse
            └── Dock re-docks in left area
```

### 5.3 Future Integration

**E06-F02 (Menu System)**:
```python
# Will add to InkMainWindow
view_menu = menubar.addMenu("&View")
panels_menu = view_menu.addMenu("&Panels")
panels_menu.addAction(self.hierarchy_dock.toggleViewAction())
panels_menu.addAction(self.property_dock.toggleViewAction())
panels_menu.addAction(self.message_dock.toggleViewAction())
```

**E06-F05 (Settings Persistence)**:
```python
# Save dock layout
settings.setValue("window/state", self.saveState())

# Restore on startup
state = settings.value("window/state")
if state:
    self.restoreState(state)
```

**E04-F01 (Full Hierarchy Implementation)**:
```python
# Replace placeholder - same file, same class name
class HierarchyPanel(QTreeView):  # Was QWidget
    """Full hierarchy tree implementation."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_tree_model()
        self._connect_signals()
```

---

## 6. Key Takeaways

### 6.1 Qt Dock Widget Best Practices

1. **Always set object names** - Required for state persistence
2. **Separate panel from dock** - Content vs. container
3. **Restrict allowed areas** - Guide users to sensible layouts
4. **Use minimum sizes** - Prevent unusable panels
5. **Enable dock nesting** - Allows more layout flexibility

### 6.2 TDD Benefits Realized

1. **Caught visibility issue early** - `isVisible()` vs `isHidden()`
2. **Defined API before implementation** - Tests document expected behavior
3. **Confidence in refactoring** - 51 tests verified changes didn't break anything
4. **Documentation through tests** - Test names describe functionality

### 6.3 Code Organization Patterns

1. **Package structure** - `panels/` package with `__init__.py` exports
2. **Private methods** - `_setup_*` methods for each logical step
3. **Class constants** - Configuration values as class-level constants
4. **Comprehensive docstrings** - Every public method documented

---

## 7. Visual Overview

### 7.1 Default Window Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Ink - Incremental Schematic Viewer              [_][□][X]│
├────────────┬────────────────────────────────────────────────┬───────────────┤
│            │                                                │               │
│ Hierarchy  │                                                │  Properties   │
│   Panel    │             SchematicCanvas                    │    Panel      │
│            │             (Central Widget)                   │               │
│ (left dock)│                                                │ (right dock)  │
│            │                                                │               │
│            │                                                │               │
├────────────┴────────────────────────────────────────────────┴───────────────┤
│                           Message Panel (bottom dock)                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Allowed Dock Movements

```
Hierarchy Panel: ◀───────────────────▶
                 Left            Right

Property Panel:  ◀───────────────────▶
                 Left            Right

Message Panel:            ▼
                       Bottom (only)
```

---

**Document Status**: Complete
**Implementation Status**: Complete
**Next Steps**: E06-F01-T04 (Application Entry Point), E06-F02 (Menu System)
