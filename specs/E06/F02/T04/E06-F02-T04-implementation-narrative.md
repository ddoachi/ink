# E06-F02-T04: View and Help Menus - Implementation Narrative

## 1. Introduction

This document provides a comprehensive narrative of implementing View menu zoom actions and Help menu dialogs for the Ink schematic viewer application. Following Test-Driven Development (TDD), we first wrote failing tests, then implemented the features to make them pass.

## 2. Business Context

### 2.1 The Problem
Users need intuitive access to:
- **View controls**: Zooming in/out and fitting the schematic to the viewport
- **Help resources**: Keyboard shortcuts reference and application information

Without these, users would need to rely solely on toolbar buttons or mouse gestures, making the application less discoverable and accessible.

### 2.2 The Solution
Add menu actions with standard keyboard shortcuts that mirror common application patterns:
- `Ctrl+=` / `Ctrl+-` for zoom (browser standard)
- `Ctrl+0` for fit view (browser standard)
- `F1` for help (universal standard)

## 3. Technical Architecture

### 3.1 Component Structure

```
ink/presentation/
├── main_window.py          # Modified: Added View/Help menu actions
└── dialogs/
    ├── __init__.py         # NEW: Package initialization
    └── shortcuts_dialog.py # NEW: KeyboardShortcutsDialog class
```

### 3.2 Class Responsibilities

| Class | Responsibility |
|-------|---------------|
| `InkMainWindow` | Creates menu actions, connects to handlers, delegates to canvas |
| `KeyboardShortcutsDialog` | Displays formatted HTML table of keyboard shortcuts |

## 4. Implementation Walkthrough

### 4.1 Phase 1: Test-Driven Development Setup

We started by writing 37 comprehensive tests in `tests/unit/presentation/test_view_help_menus.py`:

```python
# tests/unit/presentation/test_view_help_menus.py:120-135

class TestViewMenuZoomActions:
    def test_zoom_in_action_exists_in_view_menu(
        self, qtbot: QtBot, app_settings: AppSettings
    ) -> None:
        """Test Zoom In action exists in View menu."""
        window = InkMainWindow(app_settings)
        qtbot.addWidget(window)

        actions = window.view_menu.actions()
        action_texts = [a.text() for a in actions if not a.isSeparator()]

        assert any("Zoom" in text and "In" in text for text in action_texts)
```

**Why this approach?**
- Tests define expected behavior before implementation
- Failing tests guide implementation scope
- All 37 tests initially failed as expected

### 4.2 Phase 2: View Menu Zoom Actions

#### 4.2.1 Adding Zoom Actions to _create_view_menu()

Modified `src/ink/presentation/main_window.py:987-1006`:

```python
def _create_view_menu(self) -> None:
    """Create View menu items with zoom controls and panel toggle actions."""

    # =====================================================================
    # Zoom Actions (E06-F02-T04)
    # =====================================================================

    # Zoom In action (Ctrl+=)
    zoom_in_action = QAction("Zoom &In", self)
    zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
    zoom_in_action.setStatusTip("Zoom in on schematic")
    zoom_in_action.triggered.connect(self._on_zoom_in)
    self.view_menu.addAction(zoom_in_action)

    # Zoom Out action (Ctrl+-)
    zoom_out_action = QAction("Zoom &Out", self)
    zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
    zoom_out_action.setStatusTip("Zoom out on schematic")
    zoom_out_action.triggered.connect(self._on_zoom_out)
    self.view_menu.addAction(zoom_out_action)

    # Fit View action (Ctrl+0)
    fit_view_action = QAction("&Fit View", self)
    fit_view_action.setShortcut(QKeySequence("Ctrl+0"))
    fit_view_action.setStatusTip("Fit schematic to view")
    fit_view_action.triggered.connect(self._on_fit_view)
    self.view_menu.addAction(fit_view_action)

    # Separator between zoom controls and panel toggles
    self.view_menu.addSeparator()

    # ... existing Panels submenu code ...
```

**Key design decisions:**
1. **Use Qt StandardKey**: `QKeySequence.StandardKey.ZoomIn/ZoomOut` ensures platform-native shortcuts
2. **Status tips**: Provide status bar feedback when hovering
3. **Mnemonics**: `&In`, `&Out`, `&Fit` allow Alt+key access
4. **Separator**: Visual distinction between zoom and panel controls

#### 4.2.2 Zoom Handler Methods

The zoom handlers already existed from E06-F03-T02 toolbar implementation. They safely call canvas methods with `hasattr()` checks:

```python
def _on_zoom_in(self) -> None:
    """Handle View > Zoom In or toolbar action."""
    if self.schematic_canvas and hasattr(self.schematic_canvas, "zoom_in"):
        self.schematic_canvas.zoom_in()

def _on_zoom_out(self) -> None:
    """Handle View > Zoom Out or toolbar action."""
    if self.schematic_canvas and hasattr(self.schematic_canvas, "zoom_out"):
        self.schematic_canvas.zoom_out()

def _on_fit_view(self) -> None:
    """Handle View > Fit View or toolbar action."""
    if self.schematic_canvas and hasattr(self.schematic_canvas, "fit_view"):
        self.schematic_canvas.fit_view()
```

### 4.3 Phase 3: Help Menu Implementation

#### 4.3.1 Adding Help Menu Actions

Modified `src/ink/presentation/main_window.py:1188-1207`:

```python
def _create_help_menu(self) -> None:
    """Create Help menu items."""

    # =====================================================================
    # Keyboard Shortcuts Action (F1) - E06-F02-T04
    # =====================================================================
    shortcuts_action = QAction("&Keyboard Shortcuts", self)
    shortcuts_action.setShortcut(QKeySequence("F1"))
    shortcuts_action.setStatusTip("Show keyboard shortcuts")
    shortcuts_action.triggered.connect(self._on_show_shortcuts)
    self.help_menu.addAction(shortcuts_action)

    # =====================================================================
    # About Ink Action - E06-F02-T04
    # =====================================================================
    about_action = QAction("&About Ink", self)
    about_action.setStatusTip("About this application")
    about_action.triggered.connect(self._on_about)
    self.help_menu.addAction(about_action)

    # Add separator before settings submenu
    self.help_menu.addSeparator()

    # ... existing Settings submenu code ...
```

**Key decisions:**
1. **F1 for shortcuts**: Universal help key binding
2. **Menu order**: Shortcuts first, then About, then Settings (least used)
3. **Separator before Settings**: Groups primary help vs. app settings

#### 4.3.2 Keyboard Shortcuts Dialog

Created `src/ink/presentation/dialogs/shortcuts_dialog.py`:

```python
class KeyboardShortcutsDialog(QDialog):
    """Dialog showing all keyboard shortcuts."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        browser = QTextBrowser()
        browser.setHtml(self._get_shortcuts_html())
        browser.setOpenExternalLinks(False)
        layout.addWidget(browser)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _get_shortcuts_html(self) -> str:
        """Generate HTML content for the shortcuts display."""
        return """
        <style>
            h2 { color: #333; margin-bottom: 16px; }
            h3 {
                color: #555;
                margin-top: 20px;
                margin-bottom: 8px;
                border-bottom: 1px solid #ddd;
                padding-bottom: 4px;
            }
            table { border-collapse: collapse; width: 100%; }
            td { padding: 6px 12px; }
            td:first-child { font-weight: bold; width: 140px; color: #0066cc; }
        </style>

        <h2>Keyboard Shortcuts</h2>

        <h3>File Menu</h3>
        <table>
            <tr><td>Ctrl+O</td><td>Open netlist file</td></tr>
            <tr><td>Ctrl+Q</td><td>Exit application</td></tr>
        </table>

        <!-- ... more categories ... -->
        """
```

**Design rationale:**
1. **QTextBrowser**: Supports HTML rendering, read-only by default
2. **CSS styling**: Clean, professional appearance with blue shortcut keys
3. **Categories**: Organized by menu/context (File, Edit, View, Canvas, Help)
4. **Close button**: Standard dialog dismiss pattern

#### 4.3.3 About Dialog Handler

```python
def _on_about(self) -> None:
    """Handle Help > About Ink action."""
    QMessageBox.about(
        self,
        "About Ink",
        "<h2>Ink - Incremental Schematic Viewer</h2>"
        "<p>Version 0.1.0 (MVP)</p>"
        "<p>A GUI tool for schematic exploration targeting gate-level netlists.</p>"
        "<p><b>Features:</b></p>"
        "<ul>"
        "<li>Incremental exploration from user-selected points</li>"
        "<li>Hop-based fanin/fanout expansion</li>"
        "<li>Orthogonal net routing with Sugiyama layout</li>"
        "<li>Search and navigation</li>"
        "</ul>"
        "<p>Built with PySide6 and Python</p>"
        "<p>&copy; 2025 Ink Project</p>",
    )
```

**Why QMessageBox.about()?**
- Platform-native appearance
- Automatic theming support
- Standard close behavior
- HTML formatting support

### 4.4 Phase 4: Test Mocking Strategy

To test dialogs without blocking test execution:

```python
def test_keyboard_shortcuts_action_opens_dialog(
    self, qtbot: QtBot, app_settings: AppSettings
) -> None:
    window = InkMainWindow(app_settings)
    qtbot.addWidget(window)

    shortcuts_action = None
    for action in window.help_menu.actions():
        if "Keyboard" in action.text() and "Shortcut" in action.text():
            shortcuts_action = action
            break

    with patch(
        "ink.presentation.dialogs.shortcuts_dialog.KeyboardShortcutsDialog"
    ) as MockDialog:
        mock_dialog = Mock()
        MockDialog.return_value = mock_dialog

        shortcuts_action.trigger()

        MockDialog.assert_called_once_with(window)
        mock_dialog.exec.assert_called_once()
```

**Key patterns:**
- Mock at import location in target module
- Verify constructor arguments
- Verify exec() called for modal behavior

## 5. Testing Results

### 5.1 Test Execution
```
============================= test session starts ==============================
collected 37 items

tests/unit/presentation/test_view_help_menus.py .......................... [100%]

============================== 37 passed in 4.97s ==============================
```

### 5.2 Test Coverage by Category

| Category | Count | Description |
|----------|-------|-------------|
| View Menu Zoom | 14 | Action existence, shortcuts, status tips, canvas integration |
| Keyboard Shortcuts Action | 4 | Action existence, F1 shortcut, dialog launch |
| Shortcuts Dialog | 11 | Import, creation, content, structure |
| About Dialog | 6 | Action existence, QMessageBox content |
| Menu Structure | 2 | Item ordering, separators |

## 6. Code Quality

### 6.1 Linting (ruff)
```
All checks passed!
```

### 6.2 Type Checking (mypy)
```
Success: no issues found in 20 source files
```

### 6.3 Full Test Suite
```
============================= 691 passed in 32.51s =============================
```

## 7. Lessons Learned

### 7.1 Import Location for Dialogs
Initially placed the import at the top of main_window.py but ruff flagged late imports inside methods. Moved to top-level import for consistency:

```python
# At top of main_window.py
from ink.presentation.dialogs.shortcuts_dialog import KeyboardShortcutsDialog
```

### 7.2 HTML Line Length in CSS
Ruff enforces 100-character line limit, including HTML strings. Reformatted CSS:

```python
# Before (too long)
h3 { color: #555; margin-top: 20px; margin-bottom: 8px; border-bottom: 1px solid #ddd; padding-bottom: 4px; }

# After (multi-line)
h3 {
    color: #555;
    margin-top: 20px;
    margin-bottom: 8px;
    border-bottom: 1px solid #ddd;
    padding-bottom: 4px;
}
```

### 7.3 Type Annotations for Qt Parent
Qt widgets accept `parent=None` by default. Added proper typing:

```python
def __init__(self, parent: QWidget | None = None) -> None:
```

## 8. Integration with Existing Code

### 8.1 Reuse of Zoom Handlers
The View menu zoom actions connect to the same `_on_zoom_in()`, `_on_zoom_out()`, `_on_fit_view()` methods used by the toolbar (E06-F03-T02). This ensures consistent behavior between menu and toolbar.

### 8.2 Menu Structure Preservation
The implementation preserves the existing Help menu structure (Settings submenu) while adding new items at the top.

## 9. Future Considerations

1. **Dynamic Version**: Read from `pyproject.toml` instead of hardcoded "0.1.0"
2. **Shortcut Customization**: Allow users to modify shortcuts
3. **What's New Dialog**: Add changelog view for new versions
4. **Help Documentation**: Link to online documentation from Help menu
