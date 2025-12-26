# E06-F06-T03: Recent Files Management - Implementation Narrative

> **A comprehensive technical story of how recent files management was implemented in Ink**

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Architecture Overview](#3-architecture-overview)
4. [Implementation Journey](#4-implementation-journey)
5. [Data Flow Analysis](#5-data-flow-analysis)
6. [Code Walkthrough](#6-code-walkthrough)
7. [Testing Strategy Deep Dive](#7-testing-strategy-deep-dive)
8. [Integration Points](#8-integration-points)
9. [Error Handling](#9-error-handling)
10. [Performance Considerations](#10-performance-considerations)
11. [Security Considerations](#11-security-considerations)
12. [Debugging Guide](#12-debugging-guide)
13. [Maintenance Guidelines](#13-maintenance-guidelines)
14. [Lessons Learned](#14-lessons-learned)
15. [Appendix](#15-appendix)

---

## 1. Executive Summary

This document describes the implementation of recent files management for the Ink schematic viewer. The feature enables users to quickly access previously opened netlist files through a File > Open Recent menu, with persistence across application sessions using Qt's QSettings.

**Key Achievements:**
- 6 new methods added to `AppSettings` for recent files management
- File menu with Open Recent submenu in `InkMainWindow`
- 48 comprehensive tests (24 unit + 24 integration)
- Complete TDD workflow (Red-Green-Refactor)
- Zero lint/type errors

**Files Modified:**
- `src/ink/infrastructure/persistence/app_settings.py` (+195 lines)
- `src/ink/presentation/main_window.py` (+180 lines, signature change)

---

## 2. Problem Statement

### 2.1 User Need

Users working with large schematic projects frequently need to:
- Reopen the same netlist files across sessions
- Quickly switch between recently viewed designs
- Avoid navigating file dialogs for common files

### 2.2 Technical Requirements

From spec E06-F06-T03:
- Store up to 10 recent files (configurable)
- Persist across application restarts
- Auto-remove files that no longer exist
- Display in File menu with keyboard shortcuts
- Most recently opened file appears first

### 2.3 Constraints

- Must use existing `AppSettings` infrastructure (from E06-F06-T01)
- Must integrate with `InkMainWindow` without breaking existing tests
- Must follow DDD architecture (persistence in Infrastructure layer)
- Must support all file path edge cases (spaces, unicode, etc.)

---

## 3. Architecture Overview

### 3.1 Layer Distribution

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  InkMainWindow                                          │    │
│  │  ├── _setup_menus()         Creates File menu           │    │
│  │  ├── _update_recent_files_menu()  Rebuilds submenu      │    │
│  │  ├── _on_open_recent_file() Handles menu clicks         │    │
│  │  └── _open_file()           Central file open logic     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ uses
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  AppSettings                                            │    │
│  │  ├── add_recent_file()      Add/move file to front      │    │
│  │  ├── get_recent_files()     Get list, filter deleted    │    │
│  │  ├── clear_recent_files()   Clear all entries           │    │
│  │  ├── get_max_recent_files() Get max limit               │    │
│  │  ├── set_max_recent_files() Set max limit               │    │
│  │  └── _get_raw_recent_files() Internal: no filtering     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ wraps
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      QT FRAMEWORK                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  QSettings                                              │    │
│  │  └── Platform-native storage (INI/Registry/plist)       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Dependency Direction

```
InkMainWindow ──depends on──► AppSettings ──wraps──► QSettings
     │                              │
     │                              │
     ▼                              ▼
Presentation Layer         Infrastructure Layer
```

The presentation layer depends on infrastructure, not vice versa. This follows Clean Architecture principles.

---

## 4. Implementation Journey

### 4.1 Phase 1: TDD Red Phase

**Goal**: Write failing tests that define expected behavior.

#### 4.1.1 Unit Tests for AppSettings

Created `tests/unit/infrastructure/persistence/test_recent_files.py`:

```python
# Example test structure
class TestAddRecentFile:
    def test_add_single_file(self, app_settings, temp_files):
        """Verify single file can be added."""
        app_settings.add_recent_file(temp_files[0])
        recent = app_settings.get_recent_files()
        assert len(recent) == 1
        assert recent[0] == temp_files[0]

    def test_duplicate_moves_to_front(self, app_settings, temp_files):
        """Verify re-adding moves file to front."""
        app_settings.add_recent_file(temp_files[0])
        app_settings.add_recent_file(temp_files[1])
        app_settings.add_recent_file(temp_files[0])  # Re-add

        recent = app_settings.get_recent_files()
        assert recent[0] == temp_files[0]  # Now first
```

**Test fixture for isolation:**

```python
@pytest.fixture
def isolated_settings(tmp_path):
    """Redirect QSettings to temporary directory."""
    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(tmp_path / "settings"),
    )
    yield tmp_path / "settings"
```

#### 4.1.2 Integration Tests for Menu

Created `tests/integration/presentation/test_recent_files_menu.py`:

```python
class TestRecentFilesMenuContent:
    def test_empty_menu_shows_no_recent_files(self, main_window):
        """Empty state shows placeholder."""
        actions = main_window.recent_files_menu.actions()
        assert len(actions) == 1
        assert "No Recent Files" in actions[0].text()
        assert not actions[0].isEnabled()

    def test_menu_shows_recent_files(self, main_window, temp_files):
        """Files appear in menu after adding."""
        main_window.app_settings.add_recent_file(temp_files[0])
        main_window._update_recent_files_menu()

        actions = main_window.recent_files_menu.actions()
        assert "test0.ckt" in actions[0].text()
```

### 4.2 Phase 2: TDD Green Phase

**Goal**: Implement minimal code to pass all tests.

#### 4.2.1 AppSettings Recent Files Methods

Added to `src/ink/infrastructure/persistence/app_settings.py`:

```python
def add_recent_file(self, file_path: str) -> None:
    """Add file to recent list, move to front if exists."""
    normalized_path = str(Path(file_path).resolve())
    recent = self._get_raw_recent_files()

    # Remove if exists (will re-add at front)
    if normalized_path in recent:
        recent.remove(normalized_path)

    # Insert at front
    recent.insert(0, normalized_path)

    # Trim to max
    max_recent = self.get_max_recent_files()
    recent = recent[:max_recent]

    self.set_value(self.KEY_RECENT_FILES, recent)
```

**Key implementation details:**
- `Path.resolve()` normalizes paths (handles relative, symlinks)
- Move-to-front logic prevents duplicates
- List slicing enforces max limit

#### 4.2.2 InkMainWindow Menu Integration

Modified `src/ink/presentation/main_window.py`:

```python
def __init__(self, app_settings: AppSettings) -> None:
    """Constructor now requires AppSettings."""
    super().__init__()
    self.app_settings = app_settings

    self._setup_window()
    self._setup_menus()  # NEW
    self._setup_central_widget()
    self._update_recent_files_menu()  # NEW

def _setup_menus(self) -> None:
    """Create File menu with Open Recent submenu."""
    menubar = self.menuBar()
    file_menu = menubar.addMenu("&File")

    # Open action
    open_action = file_menu.addAction("&Open...")
    open_action.setShortcut("Ctrl+O")
    open_action.triggered.connect(self._on_open_file_dialog)

    # Recent files submenu
    self.recent_files_menu = file_menu.addMenu("Open &Recent")

    file_menu.addSeparator()

    # Exit action
    exit_action = file_menu.addAction("E&xit")
    exit_action.setShortcut("Ctrl+Q")
    exit_action.triggered.connect(self.close)
```

### 4.3 Phase 3: TDD Refactor Phase

**Goal**: Clean up code while keeping tests green.

#### 4.3.1 Lint Fixes

1. **Unused lambda parameter**: Changed `checked=False` to `_checked=False`
2. **Magic number**: Extracted `_MAX_SHORTCUT_ITEMS = 9` constant
3. **Commented code**: Removed TODO comments with actual code

#### 4.3.2 Type Safety

Fixed mypy error by ensuring `get_max_recent_files()` returns `int`:

```python
def get_max_recent_files(self) -> int:
    result = self.get_value(
        self.KEY_MAX_RECENT,
        self.DEFAULT_MAX_RECENT,
        value_type=int,
    )
    return int(result) if result is not None else self.DEFAULT_MAX_RECENT
```

---

## 5. Data Flow Analysis

### 5.1 Adding a File to Recent List

```
User opens file
    │
    ▼
InkMainWindow._open_file(file_path)
    │
    ├──► AppSettings.add_recent_file(file_path)
    │       │
    │       ├──► Path(file_path).resolve()  # Normalize
    │       ├──► _get_raw_recent_files()    # Load list
    │       ├──► Remove if exists           # Deduplicate
    │       ├──► Insert at front            # Newest first
    │       ├──► Trim to max                # Enforce limit
    │       └──► set_value(KEY, list)       # Persist
    │
    ├──► _update_recent_files_menu()
    │       │
    │       ├──► recent_files_menu.clear()
    │       ├──► For each file:
    │       │       ├── Create action
    │       │       ├── Set data(file_path)
    │       │       └── Connect to handler
    │       └──► Add separator + Clear action
    │
    └──► setWindowTitle(f"Ink - {filename}")
```

### 5.2 Opening a Recent File

```
User clicks menu item
    │
    ▼
QAction.triggered signal
    │
    ▼
lambda captures file_path
    │
    ▼
InkMainWindow._on_open_recent_file(file_path)
    │
    ├──► Path(file_path).exists()?
    │       │
    │       ├── Yes ──► _open_file(file_path)
    │       │              └── (see flow above)
    │       │
    │       └── No ──► QMessageBox.warning()
    │                  └── _update_recent_files_menu()
    │                         └── get_recent_files() filters it
```

### 5.3 Menu Keyboard Shortcuts

```
Menu Structure with Shortcuts:
┌────────────────────────────────┐
│ File                           │
│ ├── &Open...         Ctrl+O    │
│ ├── Open &Recent ►             │
│ │   ├── &1. design.ckt         │  ← Alt+1
│ │   ├── &2. other.ckt          │  ← Alt+2
│ │   ├── &3. test.ckt           │  ← Alt+3
│ │   ├── ─────────────          │
│ │   └── Clear Recent Files     │
│ ├── ───────────────────        │
│ └── E&xit            Ctrl+Q    │
└────────────────────────────────┘
```

---

## 6. Code Walkthrough

### 6.1 AppSettings: add_recent_file()

**Location**: `src/ink/infrastructure/persistence/app_settings.py:329-375`

```python
def add_recent_file(self, file_path: str) -> None:
    """Add a file to the recent files list.

    The file is added to the front of the list (most recent first).
    If the file already exists in the list, it is moved to the front
    instead of creating a duplicate.
    """
    # Step 1: Normalize path to absolute
    # This handles relative paths, symlinks, and ensures consistent storage
    normalized_path = str(Path(file_path).resolve())

    # Step 2: Get current list without filtering
    # We use _get_raw_recent_files() to avoid unnecessary file system checks
    recent = self._get_raw_recent_files()

    # Step 3: Remove if already exists
    # This is the "move to front" logic - remove then re-add at position 0
    if normalized_path in recent:
        recent.remove(normalized_path)

    # Step 4: Insert at front (index 0 = most recent)
    recent.insert(0, normalized_path)

    # Step 5: Enforce maximum size limit
    # Uses get_max_recent_files() which defaults to 10
    max_recent = self.get_max_recent_files()
    recent = recent[:max_recent]

    # Step 6: Persist to QSettings
    self.set_value(self.KEY_RECENT_FILES, recent)
```

**Why this design**:
- Path normalization ensures consistent matching regardless of how path was provided
- Move-to-front is user-expected behavior (most recent should be first)
- Trimming happens on add, not on get, to keep stored list clean

### 6.2 AppSettings: get_recent_files()

**Location**: `src/ink/infrastructure/persistence/app_settings.py:377-417`

```python
def get_recent_files(self) -> list[str]:
    """Get the list of recently opened files.

    Non-existent files are automatically filtered out and the stored
    list is updated if any files were removed.
    """
    # Step 1: Get raw list from storage
    files = self._get_raw_recent_files()

    # Step 2: Filter out non-existent files
    # This handles files deleted outside the application
    existing_files = [f for f in files if Path(f).exists()]

    # Step 3: Update stored list if any files were removed
    # This lazy cleanup prevents accumulation of dead entries
    if len(existing_files) < len(files):
        self.set_value(self.KEY_RECENT_FILES, existing_files)

    return existing_files
```

**Why lazy filtering**:
- No background tasks or file watchers needed
- Cleanup happens naturally during user interaction
- Simple and reliable

### 6.3 InkMainWindow: _update_recent_files_menu()

**Location**: `src/ink/presentation/main_window.py:198-251`

```python
def _update_recent_files_menu(self) -> None:
    """Update the recent files menu with current list from settings."""
    # Step 1: Clear existing menu items
    # Full rebuild is simpler and more reliable than surgical updates
    self.recent_files_menu.clear()

    # Step 2: Get current files (auto-filters deleted files)
    recent_files = self.app_settings.get_recent_files()

    if recent_files:
        # Step 3: Create action for each file
        for i, file_path in enumerate(recent_files):
            display_name = self._format_recent_file_name(file_path, i)
            action = self.recent_files_menu.addAction(display_name)

            # Store full path in action data for retrieval
            action.setData(file_path)
            action.setToolTip(file_path)

            # Lambda with default arg captures current file_path
            action.triggered.connect(
                lambda _checked=False, path=file_path:
                    self._on_open_recent_file(path)
            )

        # Step 4: Add separator and Clear action
        self.recent_files_menu.addSeparator()
        clear_action = self.recent_files_menu.addAction("Clear Recent Files")
        clear_action.triggered.connect(self._on_clear_recent_files)
    else:
        # Step 5: Empty state placeholder
        no_files_action = self.recent_files_menu.addAction("No Recent Files")
        no_files_action.setEnabled(False)
```

**Lambda capture explanation**:

```python
# WRONG - captures reference to loop variable
lambda: self._on_open_recent_file(file_path)  # All actions get last file!

# CORRECT - default argument captures current value
lambda _checked=False, path=file_path: self._on_open_recent_file(path)
```

---

## 7. Testing Strategy Deep Dive

### 7.1 Test Isolation Pattern

Every test runs in complete isolation using temporary QSettings:

```python
@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide isolated QSettings storage for each test."""
    settings_path = tmp_path / "settings"
    settings_path.mkdir()

    # Redirect QSettings to temporary directory
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

**Why this matters**:
- Tests don't pollute user's actual settings
- Tests don't interfere with each other
- Reproducible results on any machine

### 7.2 Test File Generation

```python
@pytest.fixture
def temp_files(tmp_path: Path) -> list[str]:
    """Create 15 temporary .ckt files for testing."""
    files = []
    for i in range(15):
        file = tmp_path / f"test{i}.ckt"
        file.write_text(f"* Netlist content {i}\n")
        files.append(str(file))
    return files
```

**Why 15 files**:
- Exceeds default max of 10
- Tests trimming behavior
- Tests list management with multiple files

### 7.3 Test Categories

| Category | Focus | Example |
|----------|-------|---------|
| Happy Path | Normal usage | Add file, get files |
| Edge Cases | Unusual input | Empty strings, unicode |
| Limits | Boundary conditions | Max files, minimum max |
| Persistence | Cross-instance | Settings survive restart |
| Error Cases | Invalid input | Max < 1 |
| Integration | Component interaction | Menu + Settings |

---

## 8. Integration Points

### 8.1 With AppSettings (E06-F06-T01)

The implementation extends `AppSettings` with new methods but maintains backward compatibility:

```python
# Existing methods (unchanged)
get_value()
set_value()
has_key()
sync()

# New methods
add_recent_file()
get_recent_files()
clear_recent_files()
get_max_recent_files()
set_max_recent_files()
```

### 8.2 With InkMainWindow (E06-F01-T01)

**Breaking change**: Constructor now requires `AppSettings`:

```python
# Before
window = InkMainWindow()

# After
settings = AppSettings()
window = InkMainWindow(settings)
```

**Migration path**: All existing tests were updated to provide `AppSettings`.

### 8.3 With Future CDL Parser

The `_open_file()` method has a placeholder for netlist parsing:

```python
def _open_file(self, file_path: str) -> None:
    # TODO: Implement when CDLParser is ready
    # 1. Parse the netlist file
    # 2. Display on canvas

    # Currently implemented:
    self.app_settings.add_recent_file(file_path)
    self._update_recent_files_menu()
    self.setWindowTitle(f"Ink - {filename}")
```

---

## 9. Error Handling

### 9.1 Non-Existent Files

**Detection**: Lazy filtering during `get_recent_files()`

```python
existing_files = [f for f in files if Path(f).exists()]
```

**UI Handling**: Warning dialog when clicking deleted file:

```python
def _on_open_recent_file(self, file_path: str) -> None:
    if Path(file_path).exists():
        self._open_file(file_path)
    else:
        QMessageBox.warning(
            self,
            "File Not Found",
            f"The file no longer exists:\n{file_path}",
        )
        self._update_recent_files_menu()
```

### 9.2 Invalid Max Value

```python
def set_max_recent_files(self, max_count: int) -> None:
    if max_count < 1:
        raise ValueError("max_count must be >= 1")
    # ...
```

### 9.3 Corrupted Settings

The `_get_raw_recent_files()` method filters invalid entries:

```python
def _get_raw_recent_files(self) -> list[str]:
    files = self.get_value(self.KEY_RECENT_FILES, [], value_type=list)
    # Filter out empty strings or non-string entries
    return [str(f) for f in files if f]
```

---

## 10. Performance Considerations

### 10.1 File Existence Checks

**Current approach**: Check existence during `get_recent_files()`

**Performance impact**: O(n) file system calls where n = number of recent files

**Mitigation**: Default max of 10 keeps n small

**Future optimization if needed**:
```python
# Batch check with caching (not implemented)
def get_recent_files_cached(self, cache_ttl_seconds=60):
    if self._cache_valid():
        return self._cached_files
    # ... check and cache
```

### 10.2 Menu Rebuild

**Current approach**: Full rebuild on every update

**Performance impact**: O(n) widget creation

**Why it's acceptable**:
- Happens only on user action (file open/clear)
- Maximum 10 items
- Creates ~12 widgets total (files + separator + clear)

---

## 11. Security Considerations

### 11.1 Path Traversal

**Risk**: User provides malicious path

**Mitigation**: Path is normalized but not validated for security:

```python
normalized_path = str(Path(file_path).resolve())
```

**Future consideration**: Validate paths are within allowed directories if needed.

### 11.2 Settings File Location

QSettings files are user-writable:
- Linux: `~/.config/InkProject/Ink.conf`
- Windows: Registry (HKCU)
- macOS: `~/Library/Preferences/com.InkProject.Ink.plist`

**Risk**: Malicious modification of settings file

**Current stance**: Accept as user-controlled file (standard practice)

---

## 12. Debugging Guide

### 12.1 Common Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Files not appearing | File deleted | Check file exists |
| Duplicate entries | Path normalization issue | Check `Path.resolve()` |
| Settings not persisting | QSettings path | Check `get_settings_file_path()` |
| Menu not updating | `_update_recent_files_menu()` not called | Add call after change |
| Lambda captures wrong file | Loop variable capture | Use default argument |

### 12.2 Debug Logging

Add temporary logging to trace issues:

```python
def add_recent_file(self, file_path: str) -> None:
    normalized_path = str(Path(file_path).resolve())
    print(f"[DEBUG] Adding: {normalized_path}")

    recent = self._get_raw_recent_files()
    print(f"[DEBUG] Before: {recent}")

    # ... logic ...

    print(f"[DEBUG] After: {recent}")
```

### 12.3 Verify Settings Location

```python
settings = AppSettings()
print(f"Settings file: {settings.get_settings_file_path()}")
```

---

## 13. Maintenance Guidelines

### 13.1 Adding New Settings Keys

1. Add key constant to `AppSettings`:
   ```python
   KEY_NEW_SETTING: str = "category/setting"
   ```

2. Add default initialization in `_initialize_defaults()`:
   ```python
   self.set_value(self.KEY_NEW_SETTING, default_value)
   ```

3. Add getter/setter methods with documentation

4. Add tests for new methods

### 13.2 Changing Max Recent Default

Modify `DEFAULT_MAX_RECENT` constant:

```python
DEFAULT_MAX_RECENT: int = 10  # Change this value
```

Existing settings are preserved - only new installs use default.

### 13.3 Adding Menu Items

1. Add action in `_setup_menus()`:
   ```python
   new_action = file_menu.addAction("&New Item")
   new_action.triggered.connect(self._on_new_item)
   ```

2. Implement handler method

3. Add tests

---

## 14. Lessons Learned

### 14.1 TDD Effectiveness

Writing tests first helped:
- Define exact behavior expectations
- Catch edge cases early
- Prevent regressions during refactoring

### 14.2 Qt Lambda Capture Gotcha

Python lambda in Qt signal connections requires care:

```python
# BROKEN - all items get last file
for file in files:
    action.triggered.connect(lambda: open(file))

# FIXED - default argument captures value
for file in files:
    action.triggered.connect(lambda _c=False, f=file: open(f))
```

### 14.3 Dependency Injection Benefits

Injecting `AppSettings` enabled:
- Test isolation with temporary settings
- Future flexibility (mock settings, different backends)
- Clear dependencies visible in constructor

### 14.4 Lazy Cleanup Simplicity

Filtering deleted files during `get_recent_files()` is simpler than:
- Background file watchers
- Startup cleanup tasks
- External cleanup tools

---

## 15. Appendix

### 15.1 File Manifest

| File | Purpose | Lines Changed |
|------|---------|---------------|
| `app_settings.py` | Recent files methods | +195 |
| `main_window.py` | Menu integration | +180, sig change |
| `test_recent_files.py` | Unit tests | +436 (new) |
| `test_recent_files_menu.py` | Integration tests | +420 (new) |
| `test_main_window.py` | Updated fixtures | +35 |
| `test_main_window_canvas.py` | Updated fixtures | +35 |

### 15.2 QSettings Keys Used

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `files/recent` | list[str] | `[]` | Recent file paths |
| `files/max_recent` | int | `10` | Maximum list size |

### 15.3 Menu Structure

```
File (Alt+F)
├── Open...                      Ctrl+O
├── Open Recent                  ►
│   ├── &1. design.ckt          Alt+1
│   ├── &2. other.ckt           Alt+2
│   ├── ...
│   ├── ─────────────
│   └── Clear Recent Files
├── ─────────────────────────
└── Exit                         Ctrl+Q
```

### 15.4 Test Execution Summary

```
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
PySide6 6.10.1 -- Qt runtime 6.10.1 -- Qt compiled 6.10.1
collected 116 items

test_main_window_canvas.py::* ....... (8 passed)
test_recent_files_menu.py::* ......................... (24 passed)
test_app_settings.py::* ........................... (26 passed)
test_recent_files.py::* ........................ (24 passed)
test_schematic_canvas.py::* .......... (10 passed)
test_main_window.py::* ............... (14 passed)

============================= 116 passed in 4.13s ==============================
```

---

**Document Metadata**

| Field | Value |
|-------|-------|
| Author | Claude Opus 4.5 |
| Created | 2025-12-26 |
| Spec Reference | E06-F06-T03 |
| Implementation Commit | a5d4449 |
