# E06-F05-T04 Implementation Narrative: Default Layout Reset

## 1. Executive Summary

This document provides a comprehensive technical walkthrough of the Default Layout Reset feature implementation for the Ink Schematic Viewer. The feature enables users to restore their panel layout (Hierarchy, Properties, Messages docks) to a default configuration with a single menu action.

**Key Achievement**: Implemented a complete TDD workflow with 21 tests covering all acceptance criteria, including confirmation dialog, layout reset, persistence clearing, status feedback, and error handling.

## 2. Business Context

### Problem Statement

Users of the Ink schematic viewer can customize their panel layout by:
- Hiding/showing panels via View menu or keyboard shortcuts
- Floating panels as separate windows
- Docking panels in different areas (left, right, bottom)
- Tabbing panels together
- Resizing panels

While this flexibility is valuable, users may:
- Accidentally misconfigure their layout
- Want to return to a familiar starting point
- Need to quickly undo complex arrangements

### Solution

A "Reset Panel Layout" action that:
1. Shows a confirmation dialog (prevents accidental resets)
2. Clears all saved panel state
3. Restores panels to default positions immediately
4. Provides visual feedback on success

## 3. Technical Architecture

### Component Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                       InkMainWindow                             │
│                                                                 │
│  ┌────────────────────┐   ┌────────────────────────────────┐   │
│  │  reset_panel_layout│   │  View Menu                      │   │
│  │  Action (Ctrl+Shift│──▶│  └─ Panels                     │   │
│  │  +R)               │   │     └─ Reset Panel Layout      │   │
│  └────────────────────┘   └────────────────────────────────┘   │
│           │                                                     │
│           ▼                                                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │                 reset_panel_layout()                    │    │
│  │  1. Show QMessageBox.question()                         │    │
│  │  2. If Yes:                                             │    │
│  │     - panel_settings_store.clear_panel_state()          │──┐ │
│  │     - _apply_default_panel_layout()                     │  │ │
│  │     - statusBar().showMessage()                         │  │ │
│  │  3. Catch exceptions: logging + warning dialog          │  │ │
│  └────────────────────────────────────────────────────────┘  │ │
│                                                               │ │
│  ┌────────────────────────────────────────────────────────┐  │ │
│  │              _apply_default_panel_layout()              │  │ │
│  │  1. removeDockWidget() × 3                              │  │ │
│  │  2. addDockWidget() × 3 (Left, Right, Bottom)           │  │ │
│  │  3. setFloating(False), show() × 3                      │  │ │
│  │  4. _set_default_dock_sizes()                           │  │ │
│  │  5. panel_state_manager.capture_state()                 │  │ │
│  └────────────────────────────────────────────────────────┘  │ │
│                                                               │ │
│  ┌────────────────────────────────────────────────────────┐  │ │
│  │               _set_default_dock_sizes()                 │  │ │
│  │  1. QApplication.processEvents()                        │  │ │
│  │  2. Calculate proportional sizes                        │  │ │
│  │  3. resizeDocks() for each panel                        │  │ │
│  └────────────────────────────────────────────────────────┘  │ │
│                                                               │ │
└───────────────────────────────────────────────────────────────┘ │
                                                                  │
┌─────────────────────────────────────────────────────────────────▼─┐
│                    PanelSettingsStore                              │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │  clear_panel_state()                                          │ │
│  │  1. settings.beginGroup("geometry"); remove(""); endGroup()  │ │
│  │  2. settings.beginGroup("panels"); remove(""); endGroup()    │ │
│  │  3. settings.sync()  # Force disk write                       │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User clicks "Reset Panel Layout"
    │
    ▼
┌──────────────────────────────────────────┐
│ QMessageBox.question()                   │
│ "This will reset all panels..."          │
│ [Yes] [No (default)]                     │
└──────────────────────────────────────────┘
    │ User clicks Yes
    ▼
┌──────────────────────────────────────────┐
│ PanelSettingsStore.clear_panel_state()   │
│ - Clears geometry/window, geometry/state │
│ - Clears panels/{name}/* for all panels  │
│ - Forces sync() to disk                  │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ removeDockWidget() × 3                   │
│ - Removes from main window               │
│ - Clears Qt internal dock state          │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ addDockWidget() × 3                      │
│ - hierarchy_dock → Left                  │
│ - property_dock → Right                  │
│ - message_dock → Bottom                  │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ setFloating(False), show() × 3           │
│ - Ensure all panels are docked           │
│ - Ensure all panels are visible          │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ processEvents()                          │
│ - Let Qt process layout changes          │
│ - Ensures accurate width()/height()      │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ resizeDocks()                            │
│ - Hierarchy: 15% width                   │
│ - Properties: 25% width                  │
│ - Messages: 20% height                   │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ panel_state_manager.capture_state()      │
│ - Updates internal tracking state        │
│ - Syncs with dock widget positions       │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│ statusBar().showMessage()                │
│ "Panel layout reset to default" (3 sec)  │
└──────────────────────────────────────────┘
```

## 4. Implementation Details

### 4.1 The Confirmation Dialog

The confirmation dialog serves as a safety barrier between the user and a destructive operation. Here's the complete implementation:

```python
# src/ink/presentation/main_window.py:1932-1944

result = QMessageBox.question(
    self,
    "Reset Panel Layout",                    # Title
    "This will reset all panels to their default positions and sizes.\n"
    "Any custom layout will be lost.\n\n"
    "Continue?",                             # Message
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,  # Buttons
    QMessageBox.StandardButton.No,           # Default button (safe choice)
)

if result != QMessageBox.StandardButton.Yes:
    return  # User cancelled - no changes made
```

**Design Considerations**:

1. **Default Button**: Setting `No` as the default prevents accidental resets when users press Enter
2. **Message Clarity**: The message explicitly states what will be lost ("custom layout")
3. **Question Format**: Using "Continue?" prompts a clear Yes/No response
4. **Modal Behavior**: The dialog blocks interaction until dismissed

### 4.2 Clearing Saved State

The `PanelSettingsStore.clear_panel_state()` method removes all saved panel configuration:

```python
# src/ink/infrastructure/persistence/panel_settings_store.py:351-376

def clear_panel_state(self) -> None:
    # Clear geometry group (Qt state blobs)
    self.settings.beginGroup(self.GEOMETRY_GROUP)  # "geometry"
    self.settings.remove("")  # Remove all keys in group
    self.settings.endGroup()

    # Clear panels group (individual panel metadata)
    self.settings.beginGroup(self.SETTINGS_GROUP)  # "panels"
    self.settings.remove("")  # Remove all keys in group
    self.settings.endGroup()

    # Force write to disk to ensure clear persists
    self.settings.sync()
```

**What Gets Cleared**:

```
QSettings:
├── geometry/
│   ├── window  (deleted)  # Window position/size blob
│   └── state   (deleted)  # Dock arrangement blob
└── panels/
    ├── Hierarchy/  (deleted)
    │   ├── visible
    │   ├── area
    │   ├── is_floating
    │   └── geometry
    ├── Properties/  (deleted)
    │   └── ...
    └── Messages/  (deleted)
        └── ...
```

### 4.3 Applying Default Layout

The `_apply_default_panel_layout()` method performs the actual layout reset:

```python
# src/ink/presentation/main_window.py:1971-2028

def _apply_default_panel_layout(self) -> None:
    # Step 1: Remove all dock widgets to clear Qt's internal state
    self.removeDockWidget(self.hierarchy_dock)
    self.removeDockWidget(self.property_dock)
    self.removeDockWidget(self.message_dock)

    # Step 2: Re-add dock widgets in default positions
    self.addDockWidget(
        Qt.DockWidgetArea.LeftDockWidgetArea,
        self.hierarchy_dock,
    )
    self.addDockWidget(
        Qt.DockWidgetArea.RightDockWidgetArea,
        self.property_dock,
    )
    self.addDockWidget(
        Qt.DockWidgetArea.BottomDockWidgetArea,
        self.message_dock,
    )

    # Step 3: Ensure all panels are visible and docked
    for dock in [self.hierarchy_dock, self.property_dock, self.message_dock]:
        dock.setFloating(False)
        dock.show()

    # Step 4: Apply default sizes
    self._set_default_dock_sizes()

    # Step 5: Update panel state manager with new state
    self.panel_state_manager.capture_state()
```

**Why Remove/Re-add?**

Simply calling `addDockWidget()` with a new area doesn't clear:
- Tab groups (multiple docks stacked as tabs)
- Splitter configurations (nested dock arrangements)
- Z-order (which dock is on top)
- Floating window positions

The remove/re-add pattern starts fresh, ensuring a clean default state.

### 4.4 Setting Default Sizes

The `_set_default_dock_sizes()` method applies proportional sizing:

```python
# src/ink/presentation/main_window.py:2030-2079

def _set_default_dock_sizes(self) -> None:
    # Wait for layout to settle
    QApplication.processEvents()

    width = self.width()
    height = self.height()

    # Hierarchy panel: 15% of window width
    self.resizeDocks(
        [self.hierarchy_dock],
        [int(width * 0.15)],
        Qt.Orientation.Horizontal,
    )

    # Property panel: 25% of window width
    self.resizeDocks(
        [self.property_dock],
        [int(width * 0.25)],
        Qt.Orientation.Horizontal,
    )

    # Message panel: 20% of window height
    self.resizeDocks(
        [self.message_dock],
        [int(height * 0.20)],
        Qt.Orientation.Vertical,
    )
```

**The processEvents() Puzzle**:

Qt layout operations are asynchronous. After calling `addDockWidget()`:

```
Timeline:
  1. addDockWidget() called → Returns immediately
  2. Qt posts layout event to event queue
  3. Your code continues...
  4. Event loop processes layout event
  5. Dock widget geometry is updated
```

Without `processEvents()`, `self.width()` returns the pre-layout value. The `processEvents()` forces Qt to process pending layout events, ensuring accurate geometry calculations.

### 4.5 Error Handling

The implementation includes comprehensive error handling:

```python
# src/ink/presentation/main_window.py:1946-1969

try:
    # Clear saved panel settings
    self.panel_settings_store.clear_panel_state()

    # Apply the default panel layout
    self._apply_default_panel_layout()

    # Show success feedback
    self.statusBar().showMessage("Panel layout reset to default", 3000)

except Exception as e:
    # Log the error for debugging
    logging.exception("Failed to reset panel layout")

    # Show user-friendly error message
    QMessageBox.warning(
        self,
        "Reset Failed",
        f"Failed to reset panel layout: {e!s}\n\n"
        "Please restart the application.",
        QMessageBox.StandardButton.Ok,
    )
```

**Error Recovery**:
- The `logging.exception()` captures the full stack trace for debugging
- The warning dialog informs the user without technical jargon
- The application continues to run (no crash)

## 5. Test Implementation

### 5.1 Test Structure

The tests are organized into logical groups:

```
tests/unit/presentation/test_panel_reset.py
├── TestConfirmationDialog (6 tests)
│   ├── test_confirmation_dialog_shown_on_reset
│   ├── test_clicking_no_cancels_reset
│   ├── test_clicking_yes_proceeds_with_reset
│   ├── test_confirmation_dialog_default_is_no
│   ├── test_confirmation_dialog_has_question_title
│   └── test_confirmation_dialog_explains_consequences
├── TestResetBehavior (5 tests)
│   ├── test_all_panels_visible_after_reset
│   ├── test_all_panels_docked_after_reset
│   ├── test_hierarchy_in_left_area_after_reset
│   ├── test_property_in_right_area_after_reset
│   └── test_message_in_bottom_area_after_reset
├── TestSettingsPersistence (2 tests)
│   ├── test_reset_clears_saved_panel_state
│   └── test_cancelled_reset_preserves_settings
├── TestStatusBarFeedback (2 tests)
│   ├── test_success_message_shown_after_reset
│   └── test_success_message_duration_is_3_seconds
├── TestErrorHandling (3 tests)
│   ├── test_error_during_reset_shows_warning
│   ├── test_error_during_reset_does_not_crash
│   └── test_error_during_reset_is_logged
├── TestResetKeyboardShortcut (2 tests)
│   ├── test_reset_action_has_correct_shortcut
│   └── test_reset_action_connected_to_reset_method
└── TestStateAfterReset (1 test)
    └── test_state_manager_captures_state_after_reset
```

### 5.2 Key Test Patterns

**Mocking the Confirmation Dialog**:

```python
def test_clicking_yes_proceeds_with_reset(self, main_window, qtbot):
    main_window.show()
    qtbot.waitExposed(main_window)

    # Hide a panel first
    main_window.hierarchy_dock.hide()

    # Mock dialog to return Yes
    with patch.object(
        QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
    ):
        main_window.reset_panel_layout()

    QApplication.processEvents()

    # Panel should now be visible (reset applied)
    assert main_window.hierarchy_dock.isVisible()
```

**Testing Error Handling**:

```python
def test_error_during_reset_shows_warning(self, main_window, qtbot):
    with (
        patch.object(
            main_window.panel_settings_store,
            "clear_panel_state",
            side_effect=Exception("Simulated disk error"),
        ),
        patch.object(
            QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes
        ),
        patch.object(QMessageBox, "warning") as mock_warning,
    ):
        main_window.reset_panel_layout()

        mock_warning.assert_called_once()
```

### 5.3 Test Isolation

Each test uses an isolated QSettings instance:

```python
@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    settings_path = tmp_path / "settings"
    settings_path.mkdir()

    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.clear()
    temp_settings.sync()

    yield settings_path
```

## 6. Debugging and Troubleshooting

### 6.1 Common Issues

**Issue**: Panels don't resize correctly after reset

**Solution**: Ensure `processEvents()` is called before `resizeDocks()`:

```python
QApplication.processEvents()  # Must come first
self.resizeDocks([self.hierarchy_dock], [int(width * 0.15)], Qt.Horizontal)
```

**Issue**: Tests affect each other's settings

**Solution**: Use the `isolated_settings` fixture to create temp QSettings per test.

**Issue**: Panel state not updated after reset

**Solution**: Call `panel_state_manager.capture_state()` after layout changes.

### 6.2 Debugging Tips

1. **Check QSettings location**: `~/.config/InkProject/Ink.conf` on Linux
2. **View settings manually**: `cat ~/.config/InkProject/Ink.conf`
3. **Add logging**: `logging.debug(f"Dock area: {self.dockWidgetArea(dock)}")`

## 7. Maintenance Guidelines

### Adding New Panels

When adding a new panel, update:

1. `_apply_default_panel_layout()`: Add remove/add for new panel
2. `_set_default_dock_sizes()`: Add sizing if proportional sizing needed
3. Tests: Add assertions for new panel's default position

### Changing Default Layout

To change default positions:

1. Modify `addDockWidget()` calls in `_apply_default_panel_layout()`
2. Update size percentages in `_set_default_dock_sizes()` if needed
3. Update tests to match new expected positions

### Changing Dialog Text

Update the `QMessageBox.question()` call in `reset_panel_layout()`. Remember to update the test `test_confirmation_dialog_explains_consequences` if message content changes.

## 8. Conclusion

The Default Layout Reset feature demonstrates effective TDD practices in a Qt/Python application:

1. **RED Phase**: 21 failing tests written first
2. **GREEN Phase**: Minimal implementation to pass all tests
3. **REFACTOR Phase**: Clean, well-documented code

The implementation integrates cleanly with existing infrastructure (`PanelSettingsStore`, `PanelStateManager`) while providing a reliable user experience with proper error handling and feedback.

## Appendix: File References

| File | Purpose |
|------|---------|
| `src/ink/presentation/main_window.py:1900-2079` | Implementation |
| `tests/unit/presentation/test_panel_reset.py` | Test suite (21 tests) |
| `src/ink/infrastructure/persistence/panel_settings_store.py:351-376` | Settings clearing |
| `specs/E06/F05/T04/E06-F05-T04.spec.md` | Original specification |
| `specs/E06/F05/T04/E06-F05-T04.pre-docs.md` | Pre-implementation planning |
