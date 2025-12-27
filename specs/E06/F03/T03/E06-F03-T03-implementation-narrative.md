# E06-F03-T03: File, Edit and Search Tools - Implementation Narrative

## Document Overview
- **Task**: E06-F03-T03 - File, Edit and Search Tools
- **Implementation Date**: 2025-12-27
- **Author**: Claude Opus 4.5
- **Methodology**: Test-Driven Development (TDD)

This narrative provides a comprehensive walkthrough of how the File, Edit, and Search toolbar actions were implemented in the Ink schematic viewer application.

---

## 1. Understanding the Problem

### 1.1 The User Need

Schematic exploration is a workflow-intensive task. Users need immediate access to:

1. **File Loading**: The starting point for every session - opening a netlist file
2. **Undo/Redo**: A safety net that enables experimentation without fear of losing work
3. **Search**: Quick navigation to specific cells, nets, or pins without manual traversal

Without toolbar buttons, users would need to:
- Navigate menus for every file operation
- Remember keyboard shortcuts without visual cues
- Have no indication of whether undo/redo is available

### 1.2 The Technical Challenge

The implementation presented several interesting challenges:

1. **Dynamic State Management**: Unlike static buttons, Undo/Redo must reflect the current state of the expansion history. They start disabled and only become enabled when actions are available.

2. **Service Dependencies**: The buttons need to interact with services (file loading, expansion, search) that may not exist yet during incremental development. The implementation must be robust against missing dependencies.

3. **Consistent UX**: The buttons must follow Qt conventions for shortcuts, tooltips, and icon themes while maintaining the application's visual identity.

---

## 2. The TDD Journey

### 2.1 Phase 1: RED - Writing Failing Tests

I started by defining the expected behavior through comprehensive tests. This approach ensures:
- Clear requirements before coding
- A safety net for refactoring
- Documentation through test cases

#### Test Categories Defined

I organized tests into logical groups matching the spec:

```python
class TestFileActions:        # 7 tests for Open button
class TestUndoAction:         # 5 tests for Undo button
class TestRedoAction:         # 5 tests for Redo button
class TestUndoRedoStateManagement:  # 8 tests for state logic
class TestSearchAction:       # 5 tests for Search button
class TestSearchPanelIntegration:   # 3 tests for panel behavior
class TestToolbarOrganization:      # 2 tests for layout
class TestGracefulDegradation:      # 3 tests for missing services
class TestNoRuntimeErrors:    # 2 tests for stability
```

**Total: 40 tests**

#### Key Test Design Decisions

**1. Testing Action Existence and Properties**
```python
def test_open_action_exists(self, main_window: InkMainWindow) -> None:
    assert hasattr(main_window, "_open_action")
    assert main_window._open_action is not None
    assert isinstance(main_window._open_action, QAction)
```
This pattern verifies the action is created, stored, and is the correct type.

**2. Testing Shortcuts with Qt Standard Keys**
```python
def test_open_action_shortcut(self, main_window: InkMainWindow) -> None:
    assert main_window._open_action.shortcut() == QKeySequence.StandardKey.Open
```
Using `QKeySequence.StandardKey` ensures platform-appropriate shortcuts.

**3. Testing State Management with Mocks**
```python
def test_undo_enabled_when_can_undo(
    self, main_window: InkMainWindow, mock_expansion_service: Mock
) -> None:
    main_window._expansion_service = mock_expansion_service
    mock_expansion_service.can_undo.return_value = True
    mock_expansion_service.can_redo.return_value = False

    main_window._update_undo_redo_state()

    assert main_window._undo_action.isEnabled()
    assert not main_window._redo_action.isEnabled()
```
This tests the state update logic in isolation from actual services.

**4. Testing Graceful Degradation**
```python
def test_no_crash_without_expansion_service(self, main_window: InkMainWindow) -> None:
    if hasattr(main_window, "_expansion_service"):
        delattr(main_window, "_expansion_service")

    # These should not raise exceptions
    main_window._on_undo()
    main_window._on_redo()
    main_window._update_undo_redo_state()
```
This ensures the application doesn't crash when services are unavailable.

### 2.2 Phase 2: GREEN - Making Tests Pass

With 40 failing tests as my guide, I implemented the solution systematically.

#### Step 1: Add Imports

First, I added the necessary Qt imports:

```python
from PySide6.QtGui import QAction, QCloseEvent, QGuiApplication, QIcon, QKeySequence
```

#### Step 2: Define Type Hints

Added class-level type hints for the new action attributes:

```python
# Toolbar action type hints (E06-F03-T03)
_open_action: QAction
_undo_action: QAction
_redo_action: QAction
_search_action: QAction
```

#### Step 3: Update `_setup_toolbar()`

Modified the existing toolbar setup to add action groups:

```python
def _setup_toolbar(self) -> None:
    # ... existing toolbar creation code ...

    self._toolbar = toolbar

    # Add action groups with separators (E06-F03-T03)
    # Group 1: File operations
    self._add_file_actions(toolbar)
    toolbar.addSeparator()

    # Group 2: Edit operations (Undo/Redo)
    self._add_edit_actions(toolbar)
    toolbar.addSeparator()

    # Group 3: Search operations
    self._add_search_actions(toolbar)
```

#### Step 4: Implement Action Group Methods

**File Actions (`_add_file_actions`)**:
```python
def _add_file_actions(self, toolbar: QToolBar) -> None:
    self._open_action = QAction(
        QIcon.fromTheme("document-open"),
        "Open",
        self,
    )
    self._open_action.setToolTip("Open netlist file (Ctrl+O)")
    self._open_action.setShortcut(QKeySequence.StandardKey.Open)
    self._open_action.triggered.connect(self._on_open_file_dialog)
    toolbar.addAction(self._open_action)
```

**Edit Actions (`_add_edit_actions`)**:
```python
def _add_edit_actions(self, toolbar: QToolBar) -> None:
    # Undo action
    self._undo_action = QAction(
        QIcon.fromTheme("edit-undo"),
        "Undo",
        self,
    )
    self._undo_action.setToolTip("Undo expansion/collapse (Ctrl+Z)")
    self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
    self._undo_action.setEnabled(False)  # Initially disabled
    self._undo_action.triggered.connect(self._on_undo)
    toolbar.addAction(self._undo_action)

    # Redo action
    self._redo_action = QAction(
        QIcon.fromTheme("edit-redo"),
        "Redo",
        self,
    )
    self._redo_action.setToolTip("Redo expansion/collapse (Ctrl+Shift+Z)")
    self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
    self._redo_action.setEnabled(False)  # Initially disabled
    self._redo_action.triggered.connect(self._on_redo)
    toolbar.addAction(self._redo_action)
```

**Search Actions (`_add_search_actions`)**:
```python
def _add_search_actions(self, toolbar: QToolBar) -> None:
    self._search_action = QAction(
        QIcon.fromTheme("edit-find"),
        "Search",
        self,
    )
    self._search_action.setToolTip("Search cells/nets/pins (Ctrl+F)")
    self._search_action.setShortcut(QKeySequence.StandardKey.Find)
    self._search_action.triggered.connect(self._on_find)
    toolbar.addAction(self._search_action)
```

#### Step 5: Implement Action Handlers

**Undo Handler with Defensive Check**:
```python
def _on_undo(self) -> None:
    if hasattr(self, "_expansion_service") and self._expansion_service is not None:
        self._expansion_service.undo()
        self._update_undo_redo_state()
```

The pattern `hasattr(self, "attr") and self.attr is not None` ensures:
1. The attribute exists (avoids `AttributeError`)
2. The attribute is not `None` (avoids `NoneType` errors)

**Search Handler with Toggle/Focus Logic**:
```python
def _on_find(self) -> None:
    if hasattr(self, "_search_panel") and self._search_panel is not None:
        if self._search_panel.isVisible():
            self._search_panel.focus_search_input()
        else:
            self._search_panel.show()
            self._search_panel.focus_search_input()
```

This implements the "always focus" behavior - pressing Ctrl+F repeatedly always brings focus to the search input.

#### Step 6: Implement State Management

```python
def _update_undo_redo_state(self) -> None:
    if hasattr(self, "_expansion_service") and self._expansion_service is not None:
        can_undo = self._expansion_service.can_undo()
        can_redo = self._expansion_service.can_redo()
        self._undo_action.setEnabled(can_undo)
        self._redo_action.setEnabled(can_redo)
```

This method queries the expansion service for current state and updates button enabled states accordingly.

### 2.3 Phase 3: REFACTOR - Code Quality

After all 40 tests passed, I refined the implementation:

1. **Type Annotations**: Fixed mock function signatures for strict linting
   ```python
   # Before (failed linting)
   def mock_get_open_filename(*args, **kwargs):

   # After (passes linting)
   def mock_get_open_filename(
       *args: object, **kwargs: object
   ) -> tuple[str, str]:
   ```

2. **Comprehensive Docstrings**: Added detailed documentation to all new methods explaining:
   - Purpose and behavior
   - Configuration details
   - Related specs and methods

3. **Removed Unused Imports**: Cleaned up the `Any` import after type annotation fix

---

## 3. Code Flow Deep Dive

### 3.1 Toolbar Initialization Flow

```
InkMainWindow.__init__()
    │
    ├── _setup_toolbar()                    # Line 328
    │       │
    │       ├── Create QToolBar             # Lines 361-390
    │       │   └── Set name, movable, size, style
    │       │
    │       ├── _add_file_actions()         # Line 394
    │       │   └── Create _open_action
    │       │
    │       ├── toolbar.addSeparator()      # Line 395
    │       │
    │       ├── _add_edit_actions()         # Line 398
    │       │   ├── Create _undo_action (disabled)
    │       │   └── Create _redo_action (disabled)
    │       │
    │       ├── toolbar.addSeparator()      # Line 399
    │       │
    │       └── _add_search_actions()       # Line 402
    │           └── Create _search_action
```

### 3.2 Undo Operation Flow

```
User clicks Undo button OR presses Ctrl+Z
    │
    ├── _undo_action.triggered emits signal
    │
    └── _on_undo() called                   # Line 533
        │
        ├── Check: hasattr(self, "_expansion_service")?
        │   │
        │   ├── No: Silent return (graceful degradation)
        │   │
        │   └── Yes: Check self._expansion_service is not None?
        │       │
        │       ├── No: Silent return
        │       │
        │       └── Yes: Continue...
        │
        ├── self._expansion_service.undo()
        │   └── Service performs undo operation
        │
        └── _update_undo_redo_state()       # Line 599
            │
            ├── can_undo = service.can_undo()
            ├── can_redo = service.can_redo()
            │
            ├── _undo_action.setEnabled(can_undo)
            └── _redo_action.setEnabled(can_redo)
```

### 3.3 Search Panel Toggle Flow

```
User clicks Search button OR presses Ctrl+F
    │
    ├── _search_action.triggered emits signal
    │
    └── _on_find() called                   # Line 572
        │
        ├── Check: _search_panel exists and not None?
        │   │
        │   └── No: Silent return
        │
        ├── Check: _search_panel.isVisible()?
        │   │
        │   ├── Yes (panel visible):
        │   │   └── _search_panel.focus_search_input()
        │   │       └── Focus moves to search text input
        │   │
        │   └── No (panel hidden):
        │       ├── _search_panel.show()
        │       │   └── Panel becomes visible
        │       │
        │       └── _search_panel.focus_search_input()
        │           └── Focus moves to search text input
```

---

## 4. Architecture Insights

### 4.1 Why Defensive Programming?

The extensive use of defensive checks like:
```python
if hasattr(self, "_expansion_service") and self._expansion_service is not None:
```

Serves multiple purposes:

1. **Incremental Development**: Features can be developed in parallel. The UI doesn't need to wait for services to be complete.

2. **Testing Isolation**: Tests can mock or omit services without causing crashes.

3. **Runtime Flexibility**: Services can be attached or detached at runtime without breaking the UI.

4. **Error Prevention**: Prevents cryptic `AttributeError` or `NoneType` errors that would confuse developers.

### 4.2 Why Reuse `_on_open_file_dialog()`?

The Open button connects to the existing `_on_open_file_dialog()` method rather than implementing a new handler:

```python
self._open_action.triggered.connect(self._on_open_file_dialog)
```

Benefits:
- **DRY (Don't Repeat Yourself)**: Same file dialog logic used by menu and toolbar
- **Consistency**: Identical behavior regardless of how user opens file
- **Maintainability**: Changes to file opening logic only need to be made in one place

### 4.3 Signal Connection Strategy

The current implementation uses manual state updates after operations:
```python
self._expansion_service.undo()
self._update_undo_redo_state()  # Explicit call
```

A future enhancement could use Qt signals:
```python
# In service initialization
self._expansion_service.history_changed.connect(self._update_undo_redo_state)
```

This would automatically update button states whenever the expansion history changes, regardless of what triggered the change.

---

## 5. Testing Philosophy

### 5.1 What Makes Good Toolbar Tests?

The 40 tests in `test_toolbar_file_edit_search.py` demonstrate several testing principles:

**1. Test One Thing Per Test**
```python
def test_undo_action_initially_disabled(self, main_window):
    assert not main_window._undo_action.isEnabled()
```
This test verifies exactly one behavior - the initial disabled state.

**2. Use Descriptive Names**
```python
def test_state_updates_after_undo(...)  # Clear intent
def test_no_crash_without_expansion_service(...)  # Describes edge case
```

**3. Mock External Dependencies**
```python
@pytest.fixture
def mock_expansion_service() -> Mock:
    service = Mock()
    service.can_undo.return_value = False
    service.can_redo.return_value = False
    return service
```
Mocks provide controlled test environments without real service implementations.

**4. Test Edge Cases**
```python
class TestGracefulDegradation:
    def test_no_crash_without_expansion_service(...)
    def test_no_crash_without_search_panel(...)
    def test_update_state_without_service_is_safe(...)
```
These tests verify the application handles missing dependencies gracefully.

### 5.2 Test Coverage Map

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Coverage Map                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  _add_file_actions() ──────────► TestFileActions (7 tests)  │
│                                                             │
│  _add_edit_actions() ──────────► TestUndoAction (5 tests)   │
│                          └─────► TestRedoAction (5 tests)   │
│                                                             │
│  _add_search_actions() ────────► TestSearchAction (5 tests) │
│                                                             │
│  _on_undo() ───────────────────► TestUndoRedoState (8)      │
│  _on_redo() ───────────────────► TestUndoRedoState (8)      │
│  _update_undo_redo_state() ────► TestUndoRedoState (8)      │
│                                                             │
│  _on_find() ───────────────────► TestSearchPanelInt (3)     │
│                                                             │
│  Toolbar layout ───────────────► TestToolbarOrg (2 tests)   │
│                                                             │
│  Error handling ───────────────► TestGracefulDeg (3 tests)  │
│                                                             │
│  Initialization ───────────────► TestNoRuntimeErrors (2)    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Future Integration Points

### 6.1 When Expansion Service is Ready (E04)

1. Create the service instance in `InkMainWindow.__init__()`:
   ```python
   self._expansion_service = ExpansionService()
   ```

2. Connect to history changes:
   ```python
   if hasattr(self._expansion_service, 'history_changed'):
       self._expansion_service.history_changed.connect(
           self._update_undo_redo_state
       )
   ```

3. The existing `_on_undo()` and `_on_redo()` handlers will work automatically.

### 6.2 When Search Panel is Ready (E05)

1. Create the search panel as a dock widget:
   ```python
   self._search_panel = SearchPanel(self)
   self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._search_panel)
   ```

2. The existing `_on_find()` handler will work automatically.

### 6.3 Icon Enhancement (E06-F03-T04)

When custom icons are implemented:
```python
# Replace theme icons with custom resources
from ink.presentation.icons import IconProvider

self._open_action = QAction(
    IconProvider.get_icon("document-open"),  # Custom icon with fallback
    "Open",
    self,
)
```

---

## 7. Troubleshooting Guide

### 7.1 Common Issues

**Issue: Buttons don't appear in toolbar**
- Check: Is `_setup_toolbar()` called in `__init__()`?
- Check: Are action group methods being called?
- Check: Is the toolbar added with `self.addToolBar(toolbar)`?

**Issue: Shortcuts don't work**
- Check: Is the window focused?
- Check: Are shortcuts set with `QKeySequence.StandardKey`?
- Check: Is there a conflicting shortcut elsewhere?

**Issue: Undo/Redo stay disabled**
- Check: Is `_expansion_service` set on the window?
- Check: Does the service have `can_undo()` and `can_redo()` methods?
- Check: Is `_update_undo_redo_state()` being called after operations?

**Issue: Search button does nothing**
- Check: Is `_search_panel` set on the window?
- Check: Does the panel have `show()`, `isVisible()`, and `focus_search_input()` methods?

### 7.2 Debugging Tips

```python
# Add debug logging to track action triggers
import logging
logger = logging.getLogger(__name__)

def _on_undo(self) -> None:
    logger.debug("Undo action triggered")
    if hasattr(self, "_expansion_service") and self._expansion_service is not None:
        logger.debug("Expansion service available, calling undo()")
        self._expansion_service.undo()
        self._update_undo_redo_state()
    else:
        logger.debug("Expansion service not available")
```

---

## 8. Conclusion

This implementation demonstrates how TDD leads to well-structured, testable code. By writing 40 tests first, I:

1. **Clarified Requirements**: Each test defined a specific behavior
2. **Designed the API**: Test fixtures revealed the needed interfaces
3. **Built Confidence**: All 465 project tests pass, no regressions
4. **Created Documentation**: Tests serve as executable specifications

The defensive programming approach ensures the UI remains functional during the incremental development of dependent services (E01, E04, E05), while the comprehensive test suite provides a safety net for future modifications.

---

## Document Revision History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-27 | 1.0 | Claude Opus 4.5 | Initial implementation narrative |
