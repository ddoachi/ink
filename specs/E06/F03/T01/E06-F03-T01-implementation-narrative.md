# E06-F03-T01: Toolbar Setup and Infrastructure - Implementation Narrative

## The Story of Building Ink's Main Toolbar

This document tells the complete story of implementing the toolbar infrastructure for the Ink schematic viewer. It explains not just **what** was built, but **why** each decision was made and **how** the implementation fits into the larger application architecture.

---

## 1. The Business Need

### The Problem We're Solving

The Ink schematic viewer needed a way for users to access common operations quickly without navigating through menus. While the menu bar (implemented in E06-F02) provides organized access to all features, power users expect toolbar buttons for frequently-used actions like:

- **File operations**: Opening netlists
- **Edit operations**: Undo/Redo changes
- **View operations**: Zoom in/out, fit to view
- **Search**: Quick navigation to components

### Why a Toolbar?

Toolbars are a standard UI pattern in professional applications because they:

1. **Reduce clicks**: One click vs. two (menu + item)
2. **Visual recognition**: Icons are faster to scan than text
3. **Always visible**: No need to open a menu to see available actions
4. **Muscle memory**: Fixed positions allow muscle memory to develop

---

## 2. The Technical Approach

### 2.1 Test-Driven Development (TDD)

We followed TDD methodology for this implementation:

```
┌─────────────────────────────────────────────────────────────┐
│                     TDD Cycle                                │
│                                                              │
│   ┌─────────┐    ┌─────────┐    ┌──────────┐               │
│   │  RED    │───>│  GREEN  │───>│ REFACTOR │───> Done      │
│   │ (Tests) │    │ (Code)  │    │ (Polish) │               │
│   └─────────┘    └─────────┘    └──────────┘               │
│                                                              │
│   11 tests       Minimal        Documentation               │
│   written        impl to        and cleanup                 │
│   first          pass                                       │
└─────────────────────────────────────────────────────────────┘
```

**Why TDD for this task?**

- Clear acceptance criteria mapped directly to tests
- Tests serve as executable documentation
- Confidence that all requirements are met
- Safety net for future modifications

### 2.2 Architecture Integration

The toolbar needed to integrate seamlessly with the existing `InkMainWindow` architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                     InkMainWindow                            │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │                     Menu Bar                             ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   MAIN TOOLBAR  ← We built this          ││
│  │  ┌──────┐ ┌──────┐ │ ┌──────┐ ┌──────┐ │ ┌──────┐      ││
│  │  │      │ │      │ │ │      │ │      │ │ │      │      ││
│  │  └──────┘ └──────┘ │ └──────┘ └──────┘ │ └──────┘      ││
│  │   File    Edit     │  View    Zoom     │  Search       ││
│  │   Group   Group    │  Group   Group    │  Group        ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  ┌──────────┐  ┌────────────────────┐  ┌────────────┐  ││
│  │  │          │  │                    │  │            │  ││
│  │  │ Hierarchy│  │  Schematic Canvas  │  │ Properties │  ││
│  │  │  Panel   │  │  (Central Widget)  │  │   Panel    │  ││
│  │  │          │  │                    │  │            │  ││
│  │  └──────────┘  └────────────────────┘  └────────────┘  ││
│  │                                                          ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │              Message Panel                          │││
│  │  └─────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## 3. The Implementation Journey

### Step 1: Understanding the Requirements

From the spec (E06-F03-T01.spec.md), we extracted these requirements:

| Requirement | Technical Translation |
|------------|----------------------|
| Toolbar visible below menu bar | `addToolBar()` adds to top area by default |
| Non-movable | `setMovable(False)` |
| 24x24 icons | `setIconSize(QSize(24, 24))` |
| Icon-only buttons | `setToolButtonStyle(ToolButtonIconOnly)` |
| Settings persistence | `setObjectName("MainToolBar")` |

### Step 2: Writing the Tests First (RED Phase)

We wrote 11 tests covering all acceptance criteria:

```python
# Test Categories:
# 1. TestToolbarCreated - Does toolbar exist?
# 2. TestToolbarConfiguration - Is it configured correctly?
# 3. TestToolbarPosition - Is it in the right place?
# 4. TestToolbarReference - Can downstream tasks access it?
# 5. TestToolbarNoErrors - Does it work without crashing?
```

**Key Test Example - Configuration Check:**

```python
def test_toolbar_icon_size_is_24x24(self, main_window: InkMainWindow) -> None:
    """Test toolbar icon size is 24x24 pixels.

    24x24 is a standard toolbar icon size that:
    - Is readable on high-DPI displays
    - Maintains consistent button sizing
    - Works well with common icon libraries
    """
    toolbar = main_window.findChild(QToolBar, "MainToolBar")
    assert toolbar is not None
    expected_size = QSize(24, 24)
    assert toolbar.iconSize() == expected_size
```

All 11 tests failed initially - exactly what we wanted for RED phase.

### Step 3: Making Tests Pass (GREEN Phase)

We added the minimal implementation in `main_window.py`:

```python
def _setup_toolbar(self) -> None:
    """Create and configure the main toolbar."""
    # Create toolbar with descriptive title
    toolbar = QToolBar("Main Toolbar", self)

    # Set object name for QSettings persistence
    toolbar.setObjectName("MainToolBar")

    # Make toolbar fixed (non-movable) for MVP
    toolbar.setMovable(False)

    # Set standard 24x24 icon size
    toolbar.setIconSize(QSize(24, 24))

    # Set button style to icon-only
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)

    # Add toolbar to main window
    self.addToolBar(toolbar)

    # Store reference for downstream tasks
    self._toolbar = toolbar
```

All 11 tests passed after this implementation.

### Step 4: Integration

We integrated the toolbar into the initialization flow:

```python
def __init__(self, app_settings: AppSettings) -> None:
    super().__init__()
    self.app_settings = app_settings

    self._setup_window()
    self._setup_central_widget()
    self._setup_dock_widgets()
    self._setup_menus()
    self._setup_toolbar()  # ← Added here

    self._restore_geometry()
    self._update_recent_files_menu()
```

**Why this order?**

- After `_setup_menus()`: Toolbar appears below menu bar
- Before `_restore_geometry()`: Toolbar state can be restored from settings

---

## 4. Design Decisions Deep Dive

### 4.1 Why `setMovable(False)`?

**The Debate:**

| Option | Pros | Cons |
|--------|------|------|
| Movable | User customization | Accidental rearrangement |
| Fixed | Consistent layout | Less flexibility |

**Our Decision: Fixed for MVP**

Reasoning:
1. New users won't accidentally break their layout
2. Consistent experience across installations
3. Simplifies support and documentation
4. Can be enabled as P1 feature with preferences

### 4.2 Why 24x24 Icon Size?

Common icon sizes in Qt:

- 16x16: Too small for comfortable clicking
- 24x24: Standard for toolbars ← We chose this
- 32x32: Takes too much space
- 48x48: Oversized for typical use

24x24 hits the sweet spot: recognizable icons without wasting screen space.

### 4.3 Why Icon-Only Style?

Button style options:

| Style | Appearance | Use Case |
|-------|------------|----------|
| IconOnly | [icon] | Dense toolbars (chosen) |
| TextOnly | [text] | Rare, accessibility |
| TextBesideIcon | [icon] [text] | Important actions |
| TextUnderIcon | [icon]/[text] | Spacious toolbars |

We chose `IconOnly` because:
- Schematic viewers need maximum canvas space
- Tooltips provide text on hover
- Icons are universally recognized

---

## 5. Code Walkthrough

### 5.1 The Implementation File

**Location**: `src/ink/presentation/main_window.py`

```python
# Line 42: Added import
from PySide6.QtWidgets import QToolBar

# Line 117: Added type hint
_toolbar: QToolBar

# Line 171: Added call to setup
self._setup_toolbar()

# Lines 305-367: The implementation
def _setup_toolbar(self) -> None:
    """Create and configure the main toolbar.

    [Comprehensive docstring explaining configuration,
    design decisions, and integration points]
    """
    toolbar = QToolBar("Main Toolbar", self)
    toolbar.setObjectName("MainToolBar")
    toolbar.setMovable(False)
    toolbar.setIconSize(QSize(24, 24))
    toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    self.addToolBar(toolbar)
    self._toolbar = toolbar
```

### 5.2 The Test File

**Location**: `tests/unit/presentation/test_toolbar.py`

```
test_toolbar.py
├── Fixtures
│   ├── isolated_settings (temp QSettings)
│   ├── app_settings (clean AppSettings)
│   └── main_window (InkMainWindow with toolbar)
├── TestToolbarCreated
│   ├── test_toolbar_exists_in_main_window
│   ├── test_toolbar_has_correct_window_title
│   └── test_toolbar_has_object_name_for_persistence
├── TestToolbarConfiguration
│   ├── test_toolbar_is_not_movable
│   ├── test_toolbar_icon_size_is_24x24
│   └── test_toolbar_button_style_is_icon_only
├── TestToolbarPosition
│   └── test_toolbar_is_in_top_area
├── TestToolbarReference
│   ├── test_toolbar_stored_as_instance_variable
│   └── test_toolbar_reference_matches_findchild
└── TestToolbarNoErrors
    ├── test_main_window_launches_without_toolbar_errors
    └── test_toolbar_visible_after_window_show
```

---

## 6. For Future Developers

### 6.1 Adding Actions to the Toolbar

In tasks E06-F03-T02 and E06-F03-T03, you'll add actions:

```python
# Example: Adding a zoom action (in T02)
zoom_in_action = QAction("Zoom In", self)
zoom_in_action.setIcon(QIcon(":/icons/zoom-in.svg"))
zoom_in_action.setShortcut("Ctrl++")
zoom_in_action.triggered.connect(self._on_zoom_in)

self._toolbar.addAction(zoom_in_action)

# Add separator between groups
self._toolbar.addSeparator()
```

### 6.2 Adding Toolbar State Persistence

When implementing E06-F05 (state persistence):

```python
# The object name "MainToolBar" enables this:
state = self.saveState()  # Saves toolbar position, visibility
self.restoreState(state)  # Restores from QSettings
```

### 6.3 Common Modifications

| Change | How To |
|--------|--------|
| Make movable | `toolbar.setMovable(True)` |
| Add text labels | `toolbar.setToolButtonStyle(Qt.TextBesideIcon)` |
| Change icon size | `toolbar.setIconSize(QSize(32, 32))` |
| Add to different area | `self.addToolBar(Qt.RightToolBarArea, toolbar)` |

---

## 7. Testing This Implementation

### Run Toolbar Tests

```bash
# Just toolbar tests
uv run pytest tests/unit/presentation/test_toolbar.py -v

# Expected output:
# tests/unit/presentation/test_toolbar.py::TestToolbarCreated::test_toolbar_exists_in_main_window PASSED
# tests/unit/presentation/test_toolbar.py::TestToolbarCreated::test_toolbar_has_correct_window_title PASSED
# ... (9 more)
# 11 passed
```

### Manual Verification

```bash
# Launch the application
uv run python -m ink

# Verify:
# 1. Toolbar appears below menu bar
# 2. Toolbar is empty (no buttons yet - that's expected)
# 3. Toolbar cannot be moved/dragged
# 4. Window functions normally
```

---

## 8. Related Documentation

| Document | Purpose |
|----------|---------|
| `E06-F03-T01.spec.md` | Original requirements |
| `E06-F03-T01.post-docs.md` | Quick reference summary |
| `E06-F03-T02.spec.md` | View control tools (next task) |
| `E06-F03-T03.spec.md` | Edit/search tools (next task) |
| `E06-F03-T04.spec.md` | Icon resources (next task) |

---

## 9. Quality Assurance

### Checks Performed

| Check | Command | Result |
|-------|---------|--------|
| Unit Tests | `uv run pytest tests/unit/presentation/test_toolbar.py` | 11 passed |
| All Tests | `uv run pytest tests/` | 324 passed |
| Linting | `uv run ruff check src/ tests/` | No issues |
| Type Check | `uv run mypy src/` | No issues |
| Import Test | `python -c "from ink.presentation.main_window import InkMainWindow"` | Success |

---

## 10. Conclusion

This implementation establishes the toolbar infrastructure that will host all action buttons in the Ink schematic viewer. By following TDD methodology, we ensured:

1. **Complete Coverage**: All acceptance criteria have corresponding tests
2. **Clean Architecture**: Seamless integration with existing code
3. **Future Ready**: Clear API for downstream tasks to add actions
4. **Well Documented**: This narrative explains all decisions

The toolbar is now ready for E06-F03-T02 to add view control tools (zoom, fit) and E06-F03-T03 to add edit/search tools (undo, redo, search).

---

## Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-27 | 1.0 | Claude Opus 4.5 | Initial implementation narrative |
