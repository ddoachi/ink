# E06-F02-T02: File Menu Actions - Implementation Narrative

## Executive Summary

This document provides a comprehensive walkthrough of the File Menu Actions implementation for the Ink schematic viewer. The feature enables users to open netlist files, manage recently opened files, and exit the application - fundamental operations that form the backbone of any file-based application.

The implementation was verified through a TDD approach, with 29 tests confirming all acceptance criteria are met. The existing codebase already contained a complete implementation; this task validated and documented that implementation.

---

## 1. Business Context

### 1.1 The Problem

Users of schematic viewers need efficient ways to:
1. **Open files quickly** - Either through dialog or recent files
2. **Resume work** - Access previously opened files without remembering paths
3. **Exit cleanly** - Save state and close the application properly

Without these features, users would need to:
- Navigate file paths from scratch each time
- Remember full paths to frequently-used netlists
- Use system-level close buttons instead of application-level

### 1.2 The Solution

A standard File menu with three key components:

```
File
├── Open...           Ctrl+O    → Opens file dialog
├── Open Recent       ►         → Submenu with last 10 files
│   ├── &1. design.ckt
│   ├── &2. power.cdl
│   ├── ...
│   ├── ───────────
│   └── Clear Recent Files
├── ───────────────
└── Exit              Ctrl+Q    → Closes application
```

---

## 2. Technical Deep Dive

### 2.1 Component Architecture

The File Menu Actions span three layers of the application:

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                            │
│                                                                  │
│  InkMainWindow                                                  │
│  ├── file_menu: QMenu                                           │
│  ├── recent_files_menu: QMenu                                   │
│  ├── _on_open_file_dialog()    → Shows file selection dialog   │
│  ├── _open_file()               → Central file opening method   │
│  ├── _on_open_recent_file()     → Handles recent file clicks   │
│  ├── _update_recent_files_menu() → Rebuilds menu from settings │
│  └── _on_clear_recent_files_from_menu()                        │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                    APPLICATION LAYER                            │
│  (FileService - future integration point for netlist loading)   │
├─────────────────────────────────────────────────────────────────┤
│                   INFRASTRUCTURE LAYER                          │
│                                                                  │
│  AppSettings                                                    │
│  ├── KEY_RECENT_FILES = "files/recent"                         │
│  ├── KEY_MAX_RECENT = "files/max_recent"                       │
│  ├── add_recent_file(path)      → Adds/moves file to front     │
│  ├── get_recent_files()          → Returns filtered list        │
│  ├── clear_recent_files()        → Empties the list            │
│  └── get_max_recent_files()      → Returns limit (default: 10) │
│                                                                  │
│  QSettings (Qt Platform-Native Storage)                         │
│  └── ~/.config/InkProject/Ink.conf                              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow: Opening a File

This sequence shows what happens when a user opens a file:

```
User clicks File > Open...
         │
         ▼
┌─────────────────────────────────────────┐
│ _on_open_file_dialog()                   │
│ main_window.py:629-644                   │
└─────────────────────────────────────────┘
         │
         │ QFileDialog.getOpenFileName()
         │ Filter: "Netlist Files (*.ckt *.cdl *.sp);;All Files (*)"
         │
         ▼
   User selects file
         │
         │ Returns: ("/path/to/design.ckt", "Netlist Files...")
         │
         ▼
┌─────────────────────────────────────────┐
│ _open_file(file_path)                    │
│ main_window.py:669-697                   │
│                                          │
│ 1. app_settings.add_recent_file(path)   │
│ 2. _update_recent_files_menu()          │
│ 3. setWindowTitle(f"Ink - {filename}")  │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ add_recent_file(path)                    │
│ app_settings.py:448-494                  │
│                                          │
│ 1. Normalize to absolute path           │
│ 2. Remove duplicate if exists           │
│ 3. Insert at front of list              │
│ 4. Trim to max (10) entries             │
│ 5. Save to QSettings                    │
└─────────────────────────────────────────┘
         │
         ▼
   Menu updated, title updated
   File ready for loading (future: CDLParser integration)
```

### 2.3 Data Flow: Opening a Recent File

```
User clicks recent file in menu
         │
         │ Action stores full path in action.data()
         │
         ▼
┌─────────────────────────────────────────┐
│ _on_open_recent_file(file_path)          │
│ main_window.py:646-668                   │
└─────────────────────────────────────────┘
         │
         │ Path(file_path).exists()?
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    ▼         ▼
 _open_file() │
    │         │ QMessageBox.warning()
    │         │ "File no longer exists"
    │         │
    │         ▼
    │   _update_recent_files_menu()
    │   (auto-removes non-existent files)
    │
    └────┬────┘
         │
         ▼
   Operation complete
```

### 2.4 The Recent Files Menu Update Algorithm

The `_update_recent_files_menu()` method rebuilds the entire menu each time:

```python
def _update_recent_files_menu(self) -> None:
    """Update the recent files menu with current list from settings.

    Algorithm:
    1. Clear existing menu items (prevent duplicates)
    2. Get filtered recent files (non-existent auto-removed)
    3. If files exist:
       a. Add numbered action for each file (&1. through 10.)
       b. Store full path in action.data() for retrieval
       c. Set tooltip to full path for user reference
       d. Connect action to _on_open_recent_file handler
       e. Add separator
       f. Add "Clear Recent Files" action
    4. If no files:
       a. Add disabled "No Recent Files" placeholder
    """
    self.recent_files_menu.clear()

    recent_files = self.app_settings.get_recent_files()

    if recent_files:
        for i, file_path in enumerate(recent_files):
            display_name = self._format_recent_file_name(file_path, i)
            action = self.recent_files_menu.addAction(display_name)
            action.setData(file_path)
            action.setToolTip(file_path)
            action.triggered.connect(
                lambda _checked=False, path=file_path: self._on_open_recent_file(path)
            )

        self.recent_files_menu.addSeparator()

        clear_action = self.recent_files_menu.addAction("Clear Recent Files")
        clear_action.triggered.connect(self._on_clear_recent_files_from_menu)
    else:
        no_files_action = self.recent_files_menu.addAction("No Recent Files")
        no_files_action.setEnabled(False)
```

### 2.5 Recent Files Persistence

The `AppSettings` class handles persistence using Qt's `QSettings`:

```
Application Lifecycle
         │
         ▼
┌─────────────────────────────────────────┐
│ AppSettings.__init__()                   │
│                                          │
│ self.settings = QSettings("InkProject", "Ink")
│                                          │
│ Storage location (Linux):               │
│   ~/.config/InkProject/Ink.conf         │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ add_recent_file("/path/to/file.ckt")     │
│                                          │
│ settings.setValue("files/recent", [      │
│   "/path/to/file.ckt",                   │
│   "/older/file.cdl",                     │
│   ...                                    │
│ ])                                       │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Application closes                       │
│                                          │
│ QSettings auto-syncs to disk            │
│ (or manual sync() for critical saves)   │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│ Application restarts                     │
│                                          │
│ get_recent_files() loads from disk      │
│ Non-existent files automatically        │
│ filtered and list updated               │
└─────────────────────────────────────────┘
```

---

## 3. Key Code Walkthrough

### 3.1 File Menu Creation (`main_window.py:446-476`)

```python
def _create_file_menu(self) -> None:
    """Create File menu items.

    Structure:
        &Open...         Ctrl+O   → Opens file dialog
        Open &Recent     ►        → Submenu
        ─────────────              → Separator
        E&xit            Ctrl+Q   → Closes application
    """
    # Open action - the primary way to open files
    # "&Open..." means Alt+O will activate it
    open_action = self.file_menu.addAction("&Open...")
    open_action.setShortcut("Ctrl+O")
    open_action.triggered.connect(self._on_open_file_dialog)

    # Recent files submenu - stored for later updates
    # Using "Open &Recent" so Alt+R activates (R is unique in menu)
    self.recent_files_menu = self.file_menu.addMenu("Open &Recent")

    # Separator provides visual distinction before Exit
    self.file_menu.addSeparator()

    # Exit action - uses "E&xit" so Alt+X activates
    # (Alt+E is taken by Edit menu)
    exit_action = self.file_menu.addAction("E&xit")
    exit_action.setShortcut("Ctrl+Q")
    exit_action.triggered.connect(self.close)
```

### 3.2 Numbered Menu Formatting (`main_window.py:597-627`)

```python
def _format_recent_file_name(self, file_path: str, index: int) -> str:
    """Format a recent file path for menu display.

    Examples:
        _format_recent_file_name("/path/to/design.ckt", 0) → "&1. design.ckt"
        _format_recent_file_name("/path/to/other.ckt", 9)  → "10. other.ckt"

    Why & prefix on 1-9?
        The & creates a mnemonic, so users can press Alt+1 through Alt+9
        to quickly open the corresponding file without using the mouse.

    Why no & on 10+?
        Two-key shortcuts like "Alt+1, 0" would be confusing and non-standard.
    """
    path = Path(file_path)
    number = index + 1  # 1-based for display

    if number <= self._MAX_SHORTCUT_ITEMS:  # 9
        return f"&{number}. {path.name}"
    return f"{number}. {path.name}"
```

### 3.3 File Opening Handler (`main_window.py:669-697`)

```python
def _open_file(self, file_path: str) -> None:
    """Open a netlist file.

    This is the central file opening method. All file opens (dialog,
    recent menu, command line) should go through this method.

    Current behavior (MVP):
        1. Add to recent files
        2. Update recent files menu
        3. Update window title

    Future behavior (with CDLParser):
        1. Parse netlist file
        2. Build graph structure
        3. Display on canvas
        4-6. (Current steps continue)
    """
    # Recent files management
    self.app_settings.add_recent_file(file_path)
    self._update_recent_files_menu()

    # Update window title to show current file
    filename = Path(file_path).name
    self.setWindowTitle(f"Ink - {filename}")
```

---

## 4. Testing Coverage

### 4.1 Test File Structure

```
tests/unit/presentation/test_file_menu_actions.py
├── TestFileMenuStructure (4 tests)
│   ├── test_file_menu_has_open_action
│   ├── test_file_menu_has_open_recent_submenu
│   ├── test_file_menu_has_exit_action
│   └── test_file_menu_has_separator_before_exit
│
├── TestOpenActionKeyboardShortcut (1 test)
│   └── test_open_action_has_ctrl_o_shortcut
│
├── TestExitActionKeyboardShortcut (1 test)
│   └── test_exit_action_has_ctrl_q_shortcut
│
├── TestExitActionClosesWindow (1 test)
│   └── test_exit_action_closes_window
│
├── TestOpenFileDialog (3 tests)
│   ├── test_on_open_file_dialog_method_exists
│   ├── test_open_action_triggers_file_dialog
│   └── test_open_dialog_filter_includes_ckt_and_cdl
│
├── TestOpenFileIntegration (3 tests)
│   ├── test_open_file_adds_to_recent
│   ├── test_open_file_updates_menu
│   └── test_open_file_updates_window_title
│
├── TestRecentFilesLimit (2 tests)
│   ├── test_recent_files_limited_to_ten
│   └── test_recent_menu_shows_max_ten_items
│
├── TestRecentFilesOrder (1 test)
│   └── test_most_recent_file_at_top
│
├── TestRecentFileClick (1 test)
│   └── test_clicking_recent_file_opens_it
│
├── TestMissingRecentFile (2 tests)
│   ├── test_nonexistent_file_shows_warning
│   └── test_nonexistent_file_removed_from_list
│
├── TestClearRecentFiles (3 tests)
│   ├── test_clear_action_exists
│   ├── test_clear_action_clears_all_files
│   └── test_clear_action_updates_menu
│
├── TestRecentFilesPersistence (1 test)
│   └── test_recent_files_persist_after_reload
│
├── TestRecentFilesPathDisplay (3 tests)
│   ├── test_menu_action_shows_filename
│   ├── test_menu_action_stores_full_path
│   └── test_menu_action_tooltip_shows_full_path
│
├── TestRecentFilesNumbering (2 tests)
│   ├── test_first_nine_files_have_shortcuts
│   └── test_tenth_file_has_no_shortcut
│
└── TestEmptyRecentFilesMenu (1 test)
    └── test_empty_menu_shows_placeholder
```

### 4.2 Test Isolation Strategy

Each test uses isolated `QSettings` via the `isolated_settings` fixture:

```python
@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Redirect QSettings to temp directory for test isolation."""
    settings_path = tmp_path / "settings"
    settings_path.mkdir()

    # Configure QSettings to use temp path
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    # Clear any existing settings
    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.clear()
    temp_settings.sync()

    yield settings_path
```

This ensures:
- Tests don't pollute user settings
- Tests don't affect each other
- Tests are reproducible across machines

---

## 5. Edge Cases and Error Handling

### 5.1 Missing Recent File

**Scenario**: User clicks a recent file that was deleted from disk.

**Handling**:
```python
def _on_open_recent_file(self, file_path: str) -> None:
    if Path(file_path).exists():
        self._open_file(file_path)
    else:
        # Show warning dialog
        QMessageBox.warning(
            self,
            "File Not Found",
            f"The file no longer exists:\n{file_path}",
        )
        # Menu will auto-refresh via get_recent_files() filter
        self._update_recent_files_menu()
```

### 5.2 Duplicate File Opens

**Scenario**: User opens the same file twice.

**Handling**:
```python
def add_recent_file(self, file_path: str) -> None:
    normalized_path = str(Path(file_path).resolve())
    recent = self._get_raw_recent_files()

    # Remove duplicate if exists (moves to front)
    if normalized_path in recent:
        recent.remove(normalized_path)

    recent.insert(0, normalized_path)
```

### 5.3 Path Normalization

**Scenario**: User opens file via relative path.

**Handling**:
```python
def add_recent_file(self, file_path: str) -> None:
    # Normalize to absolute path for consistent storage
    normalized_path = str(Path(file_path).resolve())
```

This ensures:
- Relative paths become absolute
- Symlinks are resolved
- Consistent matching across sessions

---

## 6. Future Integration Points

### 6.1 Netlist Loading (E01-F01)

Current `_open_file()` just updates recent files. Future integration:

```python
def _open_file(self, file_path: str) -> None:
    try:
        # Future: Parse netlist
        design = self.file_service.load_netlist(file_path)

        # Future: Display on canvas
        self.schematic_canvas.set_design(design)

        # Current: Recent files
        self.app_settings.add_recent_file(file_path)
        self._update_recent_files_menu()

        # Current: Window title
        filename = Path(file_path).name
        self.setWindowTitle(f"Ink - {filename}")

        # Future: Status bar message
        self.statusBar().showMessage(f"Loaded: {file_path}", 3000)

    except ParseError as e:
        QMessageBox.critical(self, "Error", str(e))
```

### 6.2 Status Bar Updates (E06-F05)

The status bar (`file_label`) should show the current file:

```python
def _open_file(self, file_path: str) -> None:
    # ... existing code ...

    # Update status bar
    filename = Path(file_path).name
    self.file_label.setText(f"File: {filename}")
```

---

## 7. Debugging Checkpoints

When troubleshooting File Menu issues, check these locations:

| Issue | Checkpoint | Location |
|-------|------------|----------|
| Open action not working | Is action connected? | `main_window.py:462-464` |
| Dialog not showing | Mock interfering? | Check test mocks |
| Recent files not saving | Settings sync issue? | `app_settings.py:437` |
| Menu not updating | Forgot to call update? | `_update_recent_files_menu()` |
| Wrong file opened | Lambda capture bug? | Check `path=file_path` pattern |
| Missing file not removed | Filter not applied? | `get_recent_files()` |

---

## 8. References

- [Qt QFileDialog Documentation](https://doc.qt.io/qt-6/qfiledialog.html)
- [Qt QSettings Documentation](https://doc.qt.io/qt-6/qsettings.html)
- [Python Lambda Closure Gotchas](https://docs.python.org/3/faq/programming.html#why-do-lambdas-defined-in-a-loop-with-different-values-all-return-the-same-result)
- [Spec: E06-F02-T02](./E06-F02-T02.spec.md)
- [Post-Docs: E06-F02-T02](./E06-F02-T02.post-docs.md)
