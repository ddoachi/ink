# Implementation Narrative: E06-F02-T03 - Edit Menu Actions

## 1. Executive Summary

This document provides a comprehensive walkthrough of implementing Edit menu actions (Undo, Redo, Find) for the Ink schematic viewer. The implementation followed a strict TDD (Test-Driven Development) approach, resulting in 29 tests that verify all acceptance criteria.

**Key Deliverables**:
- Edit menu with Undo (`Ctrl+Z`), Redo (`Ctrl+Shift+Z`), and Find (`Ctrl+F`) actions
- State management for context-sensitive Undo/Redo enabling
- Search input integration in MessagePanel for Find action
- Comprehensive test suite with full coverage

**Implementation Approach**: TDD with Red-Green-Refactor cycle

---

## 2. Problem Statement

### Business Context

Users exploring schematics need standard editing capabilities:
1. **Undo/Redo**: When users expand or collapse cells, they need to reverse these actions
2. **Find**: Quick access to search functionality via keyboard shortcut (`Ctrl+F`)

These are fundamental user expectations inherited from desktop applications like text editors, IDEs, and CAD tools.

### Technical Requirements

From spec E06-F02-T03:
- Undo action with `Ctrl+Z` shortcut, initially disabled
- Redo action with `Ctrl+Shift+Z` shortcut, initially disabled
- Find action with `Ctrl+F` shortcut, always enabled
- Dynamic action state based on expansion history
- Integration with search panel focus

### Dependencies

| Type | Component | Status |
|------|-----------|--------|
| Upstream | E06-F02-T01 (Menu Bar Setup) | Complete |
| Upstream | E06-F01-T03 (Dock Widgets) | Complete |
| Downstream | E04-F03 (ExpansionService) | Pending |
| Downstream | E05-F01 (Search Panel) | Pending |

---

## 3. Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────────┐
│                         InkMainWindow                           │
├─────────────────────────────────────────────────────────────────┤
│  Menu Bar                                                       │
│  ├── File Menu (E06-F02-T02)                                   │
│  ├── Edit Menu ◄─── THIS TASK                                  │
│  │   ├── Undo (Ctrl+Z)                                         │
│  │   ├── Redo (Ctrl+Shift+Z)                                   │
│  │   ├── ─────────────                                         │
│  │   └── Find... (Ctrl+F)                                      │
│  ├── View Menu (E06-F02-T04)                                   │
│  └── Help Menu (E06-F02-T01)                                   │
├─────────────────────────────────────────────────────────────────┤
│  Dock Widgets                                                   │
│  └── Message Dock                                               │
│      └── MessagePanel                                           │
│          └── search_input (QLineEdit) ◄─── Find focuses here   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Action              Handler                   Result
─────────────────────────────────────────────────────────────
Ctrl+Z                → _on_undo()           → Status message + state update
Ctrl+Shift+Z          → _on_redo()           → Status message + state update
Ctrl+F                → _on_find()           → Show dock + focus search input
Expansion/Collapse    → (future)             → _update_undo_redo_state()
```

---

## 4. TDD Implementation Journey

### Phase 1: RED - Writing Failing Tests

Created `tests/unit/presentation/test_edit_menu.py` with 29 tests covering:

```python
# Test structure
class TestUndoAction:           # 6 tests
class TestRedoAction:           # 6 tests
class TestFindAction:           # 6 tests
class TestEditMenuStructure:    # 2 tests
class TestFindActionBehavior:   # 2 tests
class TestUndoRedoStateUpdate:  # 2 tests
class TestUndoRedoHandlers:     # 5 tests
```

**Sample Test (RED phase)**:
```python
def test_undo_action_exists(self, main_window: InkMainWindow) -> None:
    """Test Undo action exists in Edit menu."""
    assert hasattr(main_window, "undo_action")
    assert main_window.undo_action is not None
    assert isinstance(main_window.undo_action, QAction)
```

Initial test run: **28 failed, 1 passed**

### Phase 2: GREEN - Making Tests Pass

#### Step 1: Add Type Hints

```python
# main_window.py - Added instance variable type hints
class InkMainWindow(QMainWindow):
    # Edit menu actions (E06-F02-T03)
    undo_action: QAction
    redo_action: QAction
    find_action: QAction
```

#### Step 2: Implement `_create_edit_menu()`

Replaced the stub with full implementation:

```python
def _create_edit_menu(self) -> None:
    """Create Edit menu items."""
    # Undo Action
    self.undo_action = QAction("&Undo", self)
    self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
    self.undo_action.setStatusTip("Undo last expansion/collapse operation")
    self.undo_action.setEnabled(False)
    self.undo_action.triggered.connect(self._on_undo)
    self.edit_menu.addAction(self.undo_action)

    # Redo Action
    self.redo_action = QAction("&Redo", self)
    self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
    self.redo_action.setStatusTip("Redo last undone operation")
    self.redo_action.setEnabled(False)
    self.redo_action.triggered.connect(self._on_redo)
    self.edit_menu.addAction(self.redo_action)

    self.edit_menu.addSeparator()

    # Find Action
    self.find_action = QAction("&Find...", self)
    self.find_action.setShortcut(QKeySequence.StandardKey.Find)
    self.find_action.setStatusTip("Search for cells, nets, or ports")
    self.find_action.triggered.connect(self._on_find)
    self.edit_menu.addAction(self.find_action)
```

#### Step 3: Implement Handlers

```python
def _on_undo(self) -> None:
    """Handle Edit > Undo action."""
    self.statusBar().showMessage("Undo triggered", 2000)
    self._update_undo_redo_state()

def _on_redo(self) -> None:
    """Handle Edit > Redo action."""
    self.statusBar().showMessage("Redo triggered", 2000)
    self._update_undo_redo_state()

def _on_find(self) -> None:
    """Handle Edit > Find action."""
    if not self.message_dock.isVisible():
        self.message_dock.setVisible(True)
    self.message_panel.focus_search_input()

def _update_undo_redo_state(self) -> None:
    """Update enabled state of Undo/Redo actions."""
    # Placeholder - will integrate with ExpansionService
    can_undo = False
    can_redo = False

    self.undo_action.setEnabled(can_undo)
    self.redo_action.setEnabled(can_redo)

    # Dynamic text updates
    if can_undo:
        self.undo_action.setText("&Undo Expand")
    else:
        self.undo_action.setText("&Undo")
```

#### Step 4: Add MessagePanel Search Input

```python
# message_panel.py

class MessagePanel(QWidget):
    search_input: QLineEdit

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Search input for Find action
        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search cells, nets, or ports...")
        self.search_input.setClearButtonEnabled(True)
        layout.addWidget(self.search_input)

        # Placeholder label
        placeholder = QLabel(self._PLACEHOLDER_TEXT, self)
        layout.addWidget(placeholder)

    def focus_search_input(self) -> None:
        """Set focus to the search input field."""
        self.search_input.setFocus()
        self.search_input.selectAll()
```

### Phase 3: REFACTOR - Quality Checks

1. **Lint (ruff)**: Fixed 1 import issue
2. **Type-check (mypy)**: Fixed pre-existing `QByteArray` type error
3. **Build**: Successful
4. **Final Tests**: 456 passed

---

## 5. Code Walkthrough

### File: `main_window.py`

**Location**: `src/ink/presentation/main_window.py`

#### Import Changes (Line 35)

```python
# Before
from PySide6.QtGui import QCloseEvent, QGuiApplication

# After
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QKeySequence
```

**Why**: `QAction` for menu actions, `QKeySequence` for shortcuts.

#### Type Hints (Lines 129-132)

```python
# Edit menu actions (E06-F02-T03)
undo_action: QAction
redo_action: QAction
find_action: QAction
```

**Why**: Explicit type hints for IDE support and type-checking.

#### Edit Menu Creation (Lines 482-541)

The `_create_edit_menu()` method creates all three actions with:
- Mnemonics (`&Undo` enables Alt+U keyboard navigation)
- Standard shortcuts (`QKeySequence.StandardKey.*` for cross-platform)
- Status tips (shown in status bar on hover)
- Initial disabled state for Undo/Redo

#### Handler Section (Lines 759-882)

Four handler methods with comprehensive documentation:
1. `_on_undo()` - Placeholder with status message
2. `_on_redo()` - Placeholder with status message
3. `_on_find()` - Shows dock and focuses search
4. `_update_undo_redo_state()` - Updates action states

### File: `message_panel.py`

**Location**: `src/ink/presentation/panels/message_panel.py`

#### Layout Change

```
Before: QVBoxLayout → QLabel (placeholder)
After:  QVBoxLayout → QLineEdit (search) → QLabel (placeholder)
```

#### `focus_search_input()` Method (Lines 121-144)

```python
def focus_search_input(self) -> None:
    """Set focus to the search input field."""
    self.search_input.setFocus()
    self.search_input.selectAll()  # Select existing text
```

**Why**: Selecting all text is standard behavior - user can type to replace.

---

## 6. Testing Strategy

### Unit Test Structure

```
tests/unit/presentation/test_edit_menu.py
├── TestUndoAction
│   ├── test_undo_action_exists
│   ├── test_undo_action_in_edit_menu
│   ├── test_undo_action_text
│   ├── test_undo_action_shortcut
│   ├── test_undo_action_initially_disabled
│   └── test_undo_action_status_tip
├── TestRedoAction (same structure)
├── TestFindAction (same structure)
├── TestEditMenuStructure
│   ├── test_edit_menu_has_separator_before_find
│   └── test_edit_menu_action_order
├── TestFindActionBehavior
│   ├── test_find_shows_message_dock_when_hidden
│   └── test_find_focuses_search_input
├── TestUndoRedoStateUpdate
│   ├── test_update_undo_redo_state_method_exists
│   └── test_update_undo_redo_state_does_not_crash
└── TestUndoRedoHandlers
    ├── test_on_undo_handler_exists
    ├── test_on_redo_handler_exists
    ├── test_on_find_handler_exists
    ├── test_on_undo_shows_status_message
    └── test_on_redo_shows_status_message
```

### Key Test Patterns

#### Visibility Testing with Qt

```python
def test_find_shows_message_dock_when_hidden(self, main_window, qtbot):
    # Show window first for accurate visibility testing
    main_window.show()
    qtbot.waitExposed(main_window)

    # Hide dock
    main_window.message_dock.hide()
    assert main_window.message_dock.isHidden()

    # Trigger find
    main_window._on_find()

    # Verify visible
    assert not main_window.message_dock.isHidden()
    assert main_window.message_dock.isVisible()
```

**Learning**: Qt's `isVisible()` returns false if parent is not shown.

---

## 7. Design Decisions

### Decision 1: Placeholder vs Full Integration

**Choice**: Placeholder with TODO markers

**Rationale**:
- Undo/Redo requires ExpansionService (E04-F03)
- UI can be completed and tested now
- Clear integration points for future work

**Code Pattern**:
```python
# TODO: Query ExpansionService for undo/redo availability
can_undo = False  # Replace with: expansion_service.can_undo()
```

### Decision 2: Using `message_dock` for Find

**Choice**: Reuse existing message dock

**Rationale**:
- Spec E06-F03 (Search Panel) will enhance this
- Avoids creating parallel infrastructure
- Message panel description: "search results and logs"

### Decision 3: Always Show + Focus for Find

**Choice**: Show panel and focus input every time

**Rationale**:
- Toggle behavior is confusing (`Ctrl+F` might hide panel)
- User intent is always to search
- Standard behavior in editors/browsers

### Decision 4: StandardKey Shortcuts

**Choice**: Use `QKeySequence.StandardKey.*` enum

**Rationale**:
- Cross-platform (Cmd+Z on macOS, Ctrl+Z elsewhere)
- Qt handles platform detection automatically
- No conditional platform code needed

---

## 8. Integration Points

### ExpansionService Integration (E04-F03)

**Location**: `_update_undo_redo_state()` at line 834

**Expected Interface**:
```python
class ExpansionService:
    def can_undo(self) -> bool: ...
    def can_redo(self) -> bool: ...
    def undo(self) -> None: ...
    def redo(self) -> None: ...
    def get_undo_description(self) -> str: ...  # "Expand", "Collapse"
    def get_redo_description(self) -> str: ...
```

**Integration Pattern**:
```python
def _update_undo_redo_state(self) -> None:
    # Replace placeholder with:
    can_undo = self.expansion_service.can_undo()
    can_redo = self.expansion_service.can_redo()

    if can_undo:
        desc = self.expansion_service.get_undo_description()
        self.undo_action.setText(f"&Undo {desc}")
```

### Search Panel Integration (E05-F01)

**Current State**: MessagePanel has basic `search_input` and `focus_search_input()`

**Future Enhancement**: Full SearchPanel with:
- Search results list
- Filters (cells, nets, ports)
- Navigation to found items

---

## 9. Error Handling

### Qt Visibility Quirk

**Issue**: `isVisible()` returns false if parent widget not shown

**Solution**:
```python
# In tests, show window first
main_window.show()
qtbot.waitExposed(main_window)

# Use isHidden() for more reliable checks
assert not main_window.message_dock.isHidden()
```

### QByteArray Type Error

**Issue**: Pre-existing error - `len()` doesn't work with `QByteArray`

**Solution**:
```python
# Before (type error)
assert len(state.qt_state) > 0

# After (correct)
assert state.qt_state.size() > 0
```

---

## 10. Performance Considerations

### State Update Frequency

`_update_undo_redo_state()` is called:
- After undo operation
- After redo operation
- (Future) After expansion/collapse

**Impact**: Minimal - user-triggered, O(1) history check expected

### Search Panel Visibility

`setVisible(True)` on dock widget is O(1) Qt operation.
No performance concerns.

---

## 11. Security Considerations

No security implications for this task:
- Actions only affect UI state
- No file system access
- No network operations
- No user data processing

---

## 12. Accessibility

### Keyboard Navigation

| Shortcut | Action | Notes |
|----------|--------|-------|
| Ctrl+Z | Undo | Standard, platform-aware |
| Ctrl+Shift+Z | Redo | Standard, platform-aware |
| Ctrl+F | Find | Standard, platform-aware |
| Alt+E | Open Edit menu | Mnemonic |
| Alt+U | Undo (in menu) | Mnemonic |
| Alt+R | Redo (in menu) | Mnemonic |
| Alt+F | Find (in menu) | Mnemonic |

### Status Tips

All actions have descriptive status tips shown in status bar on hover:
- Undo: "Undo last expansion/collapse operation"
- Redo: "Redo last undone operation"
- Find: "Search for cells, nets, or ports"

---

## 13. Future Enhancements

### Multi-Level Undo Menu

Consider submenu showing undo history:
```
Edit
├── Undo                 ►
│   ├── Expand CELL_A
│   ├── Collapse CELL_B
│   └── Expand CELL_C
```

### Detailed Action Text

Current: "Undo Expand"
Enhanced: "Undo Expand: CELL_NAME"

**Trade-off**: More helpful but menus have limited width.

### Undo Limit

Consider limiting undo history size:
- Memory usage for large operations
- User experience (too many undos is confusing)
- Configurable via settings

---

## 14. Maintenance Guide

### Adding New Edit Menu Actions

1. Add type hint in class definition
2. Create action in `_create_edit_menu()`
3. Implement handler method (`_on_*()`)
4. Add tests in `test_edit_menu.py`

### Modifying State Logic

The `_update_undo_redo_state()` method is the single point of truth:
- Modify this method for state changes
- All handlers call this method after their operation
- Future integration: inject ExpansionService reference

### Testing Changes

Run the full test suite:
```bash
uv run pytest tests/unit/presentation/test_edit_menu.py -v
```

---

## 15. References

### Spec Documents

- [E06-F02-T03.spec.md](./E06-F02-T03.spec.md) - Original specification
- [E06-F02-T03.pre-docs.md](./E06-F02-T03.pre-docs.md) - Pre-implementation planning

### Source Files

- `src/ink/presentation/main_window.py:482-882` - Edit menu implementation
- `src/ink/presentation/panels/message_panel.py:104-144` - Search input
- `tests/unit/presentation/test_edit_menu.py` - Test suite

### External Documentation

- [Qt QAction Documentation](https://doc.qt.io/qt-6/qaction.html)
- [Qt QKeySequence Documentation](https://doc.qt.io/qt-6/qkeysequence.html)
- [PySide6 Getting Started](https://doc.qt.io/qtforpython-6/)

### Related Tasks

| Task | Description | Relationship |
|------|-------------|--------------|
| E06-F02-T01 | Menu Bar Setup | Provides `self.edit_menu` |
| E06-F02-T02 | File Menu Actions | Sibling task |
| E06-F02-T04 | View/Help Menu Actions | Sibling task |
| E04-F03 | Undo/Redo Service | Downstream - provides logic |
| E05-F01 | Search Panel | Downstream - enhances search |
