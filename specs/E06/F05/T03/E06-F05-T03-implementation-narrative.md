# E06-F05-T03: Panel Toggle Actions - Implementation Narrative

## 1. Executive Summary

This document provides a comprehensive technical narrative of the Panel Toggle Actions implementation for the Ink schematic viewer. The implementation adds View menu actions to show, hide, and toggle panel visibility using Qt's built-in `toggleViewAction()` API, with keyboard shortcuts for power users.

**Key Achievements:**
- 31 tests passing (TDD RED-GREEN-REFACTOR approach)
- Leverages Qt's `toggleViewAction()` for automatic state synchronization
- Keyboard shortcuts for all panel toggles (Ctrl+Shift+H/P/M/R)
- Seamless integration with existing PanelStateManager

## 2. Problem Statement

### Business Context
Users of the Ink schematic viewer need quick access to show/hide panels without manually dragging or clicking X buttons. Professional applications provide:

1. Menu items to toggle panel visibility
2. Keyboard shortcuts for power users
3. Visual indication (checkmarks) of current panel state
4. Quick reset to default layout

### Technical Challenge
The challenge was to create panel toggle actions that:
- Stay synchronized with panel visibility (bidirectionally)
- Work with existing PanelStateManager infrastructure
- Follow Qt patterns for dock widget control
- Avoid manual signal handling that could lead to sync bugs

## 3. Architecture Design

### 3.1 Qt's toggleViewAction() Pattern

Qt provides a built-in API for dock widget toggle actions:

```
QDockWidget::toggleViewAction()
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                     QAction (returned)                       │
├─────────────────────────────────────────────────────────────┤
│  Built-in Features:                                          │
│  • isCheckable() == true                                     │
│  • isChecked() syncs with dock.isVisible()                   │
│  • text() == dock.windowTitle()                              │
│  • Clicking toggles dock visibility                          │
│  • State syncs when dock closed via X button                 │
├─────────────────────────────────────────────────────────────┤
│  What We Customize:                                          │
│  • setShortcut("Ctrl+Shift+H")                              │
│  • setToolTip("Show or hide...")                            │
│  • setStatusTip("Toggle... (shortcut)")                     │
│  • triggered.connect(raise_handler)                          │
└─────────────────────────────────────────────────────────────┘
```

**Why toggleViewAction() Instead of Custom QAction?**

| toggleViewAction() | Custom QAction |
|-------------------|----------------|
| Automatic state sync | Manual signal handling |
| Zero-config checkmarks | Must track isChecked() |
| Qt-maintained | Prone to sync bugs |
| Text from dock title | Must set manually |

### 3.2 Menu Structure

```
View Menu
    │
    └── Panels Submenu (&Panels)
            │
            ├── Hierarchy          [Ctrl+Shift+H]  ☑
            ├── Properties         [Ctrl+Shift+P]  ☑
            ├── Messages           [Ctrl+Shift+M]  ☑
            ├── ──────────────────
            └── Reset Panel Layout [Ctrl+Shift+R]
```

### 3.3 Signal Flow

```
User Action
    │
    ├── Menu Click ──────────────────────┐
    ├── Keyboard Shortcut ───────────────┤
    │                                    ▼
    │                        toggleViewAction.triggered
    │                                    │
    │                        ┌───────────┴───────────┐
    │                        ▼                       ▼
    │            Qt: Toggle dock visibility   Our: Raise panel if shown
    │                        │
    │                        ▼
    │            QDockWidget.visibilityChanged
    │                        │
    │                        ▼
    │            PanelStateManager._on_visibility_changed
    │                        │
    │                        ▼
    │            Update panels dict + emit signals
    │                        │
    │                        ▼
    │            Action checkmark automatically syncs
    │
    └── Panel X Button ──────────────────┐
                                         ▼
                        QDockWidget.close()
                                         │
                                         ▼
                        visibilityChanged(False)
                                         │
                                         ▼
                        Action unchecks automatically
```

## 4. Implementation Details

### 4.1 View Menu Creation (`_create_view_menu`)

```python
def _create_view_menu(self) -> None:
    """Create View menu items with panel toggle actions."""
    # Create Panels submenu with mnemonic for Alt+P access
    self.panels_menu = self.view_menu.addMenu("&Panels")

    # Add toggle actions from dock widgets
    self._setup_panel_toggle_actions()

    # Visual separator before Reset Layout
    self.panels_menu.addSeparator()

    # Add Reset Panel Layout action
    self._setup_reset_panel_layout_action()
```

**Design Decision:** The `&Panels` mnemonic enables Alt+P keyboard navigation to the submenu, following Windows/Linux conventions.

### 4.2 Toggle Action Setup (`_setup_panel_toggle_actions`)

```python
def _setup_panel_toggle_actions(self) -> None:
    """Set up toggle actions for each panel dock widget."""
    # Hierarchy panel toggle
    self.hierarchy_toggle_action = self.hierarchy_dock.toggleViewAction()
    self.hierarchy_toggle_action.setShortcut("Ctrl+Shift+H")
    self.hierarchy_toggle_action.setToolTip(
        "Show or hide the hierarchy navigation panel"
    )
    self.hierarchy_toggle_action.setStatusTip(
        "Toggle hierarchy panel visibility (Ctrl+Shift+H)"
    )
    self.panels_menu.addAction(self.hierarchy_toggle_action)

    # Similar for property and message panels...

    # Connect raise behavior
    self._connect_panel_raise_behavior()
```

**Key Points:**
1. `toggleViewAction()` returns a pre-configured QAction
2. We add shortcuts, tooltips, and status tips
3. Action is added to menu after configuration
4. Raise behavior connected for UX polish

### 4.3 Panel Raise Behavior (`_connect_panel_raise_behavior`)

```python
def _connect_panel_raise_behavior(self) -> None:
    """Connect signals to raise panels when toggled to visible."""
    # Factory function to capture dock by value (closure)
    def make_raise_handler(dock_widget: QDockWidget) -> Callable[[bool], None]:
        def handler(checked: bool) -> None:
            # If action was checked (panel shown), raise to front
            if checked:
                dock_widget.raise_()
        return handler

    # Connect handlers
    self.hierarchy_toggle_action.triggered.connect(
        make_raise_handler(self.hierarchy_dock)
    )
    # Similar for other panels...
```

**Design Decision:** Factory pattern for closures

The factory function `make_raise_handler` is necessary because Python closures capture variables by reference. Without the factory:

```python
# WRONG: All handlers would use the last dock value
for dock in [hierarchy_dock, property_dock, message_dock]:
    action.triggered.connect(lambda checked: dock.raise_())
    # When called, 'dock' is always message_dock!

# CORRECT: Factory captures each dock by value
action.triggered.connect(make_raise_handler(dock))
# Each handler has its own dock reference
```

### 4.4 Reset Panel Layout (`_reset_panel_layout`)

```python
def _reset_panel_layout(self) -> None:
    """Reset panels to default layout."""
    # Restore hierarchy dock to left area
    self.hierarchy_dock.setFloating(False)  # Undock if floating
    self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.hierarchy_dock)
    self.hierarchy_dock.show()  # Ensure visible

    # Similar for property (right) and message (bottom) docks...
```

**Reset Sequence:**
1. `setFloating(False)` - Ensures dock is not floating
2. `addDockWidget(area, dock)` - Moves to default area
3. `show()` - Makes visible if hidden

## 5. TDD Implementation Process

### 5.1 RED Phase: Write Failing Tests

Created 31 tests covering all acceptance criteria:

```python
class TestPanelsSubmenu:
    """3 tests for submenu existence and structure"""

class TestPanelToggleActions:
    """8 tests for action existence and checkability"""

class TestPanelsMenuStructure:
    """2 tests for menu structure (separator before Reset)"""

class TestKeyboardShortcuts:
    """4 tests for correct shortcuts"""

class TestTooltipsAndStatusTips:
    """6 tests for tooltips and status tips"""

class TestActionBehavior:
    """5 tests for toggle behavior and sync"""

class TestPanelRaiseBehavior:
    """1 test for raise when shown"""

class TestPanelStateManagerIntegration:
    """2 tests for integration with manager"""
```

All tests failed initially (as expected).

### 5.2 GREEN Phase: Make Tests Pass

Implemented in this order:
1. `_create_view_menu()` - Entry point
2. `_setup_panel_toggle_actions()` - Core functionality
3. `_connect_panel_raise_behavior()` - UX polish
4. `_setup_reset_panel_layout_action()` - Reset feature
5. `_reset_panel_layout()` - Reset implementation

### 5.3 REFACTOR Phase: Clean Up

1. Fixed lint issue: Moved `Callable` import to `TYPE_CHECKING` block
2. Added return type annotation to `make_raise_handler`
3. Merged duplicate imports

## 6. Testing Insights

### 6.1 Qt Visibility in Tests

**Problem:** `dock.isVisible()` returns False when parent window isn't shown.

**Solution:** Show window before testing visibility:

```python
def test_action_checked_when_panel_visible(self, main_window, qtbot):
    # MUST show window first
    main_window.show()
    qtbot.waitExposed(main_window)

    # Now visibility checks work
    assert main_window.hierarchy_dock.isVisible()
    assert main_window.hierarchy_toggle_action.isChecked()
```

### 6.2 Testing toggleViewAction() Behavior

Qt's `toggleViewAction()` provides automatic sync, but tests verify it:

```python
def test_action_syncs_when_panel_closed_via_x_button(self, main_window, qtbot):
    main_window.show()
    qtbot.waitExposed(main_window)

    # Panel visible, action checked
    assert main_window.hierarchy_toggle_action.isChecked()

    # Close panel (simulates X button)
    main_window.hierarchy_dock.close()

    # Action automatically unchecks (Qt handles this)
    assert not main_window.hierarchy_toggle_action.isChecked()
```

## 7. File Changes

### Modified Files

| File | Lines Changed | Description |
|------|---------------|-------------|
| `src/ink/presentation/main_window.py` | +140 | Panel toggle implementation |

### New Files

| File | Lines | Description |
|------|-------|-------------|
| `tests/unit/presentation/test_panel_toggle_actions.py` | 620 | TDD tests |
| `specs/E06/F05/T03/E06-F05-T03.post-docs.md` | - | Quick reference doc |
| `specs/E06/F05/T03/E06-F05-T03-implementation-narrative.md` | - | This document |

## 8. Code Quality Metrics

- **Tests:** 31 passing (100%)
- **Lint:** All checks passed (ruff)
- **Type Check:** No issues (mypy strict mode)
- **Coverage:** Actions tested for existence, behavior, and integration

## 9. Usage Guide

### Menu-Based Panel Control

```
View → Panels → Hierarchy    Toggle hierarchy panel
View → Panels → Properties   Toggle properties panel
View → Panels → Messages     Toggle messages panel
View → Panels → Reset...     Restore default layout
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+H | Toggle Hierarchy |
| Ctrl+Shift+P | Toggle Properties |
| Ctrl+Shift+M | Toggle Messages |
| Ctrl+Shift+R | Reset Layout |

### Programmatic API

```python
# Toggle via action
window.hierarchy_toggle_action.trigger()

# Check if panel visible via action
if window.hierarchy_toggle_action.isChecked():
    print("Hierarchy panel is visible")

# Or via panel state manager
window.panel_state_manager.toggle_panel("Hierarchy")
```

## 10. Future Considerations

### Potential Enhancements

1. **Toolbar Panel Buttons**: Reuse toggle actions in toolbar (E06-F03)
2. **Custom Layouts**: Save/restore named layouts
3. **Per-Monitor Settings**: Remember layout per display configuration

### Integration Points

- **E06-F05-T04**: `_reset_panel_layout()` reusable for settings reset
- **E06-F02**: View menu structure established for future items
- **PanelStateManager**: Full integration for reactive state tracking

## 11. Lessons Learned

1. **Use Qt's Built-in APIs**: `toggleViewAction()` eliminates manual sync bugs
2. **Factory Pattern for Closures**: Python lambda variable capture requires care
3. **Show Window for Visibility Tests**: Qt visibility depends on parent visibility
4. **Type Hints in Nested Functions**: Annotate return types for inner functions
5. **TDD Works**: Writing tests first exposed visibility testing requirement early
