# Implementation Narrative: E06-F06-T01 QSettings Infrastructure

## Executive Summary

This document tells the complete story of implementing the `AppSettings` class - Ink's centralized settings management system. It provides a thorough understanding of the design decisions, implementation details, and lessons learned for future maintainers.

**Implementation Date**: 2025-12-26
**ClickUp Task**: CU-86evzm36h
**GitHub Issue**: [#7](https://github.com/ddoachi/ink/issues/7)

---

## 1. Problem Statement & Context

### The Need

The Ink schematic viewer needs to persist user preferences across sessions:
- Window position and size
- Recently opened files
- UI state and configuration

Without persistence, users would need to reconfigure the application every time they open it - a poor user experience for a professional tool.

### Why QSettings?

Qt provides `QSettings`, a battle-tested cross-platform settings storage mechanism. Alternatives considered:

| Option | Pros | Cons |
|--------|------|------|
| QSettings | Platform-native, no dependencies, handles serialization | Qt-specific API |
| JSON file | Human-readable, simple | Manual file handling, no OS integration |
| SQLite | Powerful queries | Overkill for simple key-value |
| ConfigParser | Python stdlib | Linux-only conventions |

**Decision**: QSettings chosen for platform-native integration and Qt ecosystem alignment.

---

## 2. Architecture & Design

### Layer Placement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                                   │
│                    InkMainWindow uses AppSettings                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                         APPLICATION LAYER                                    │
│                    (Use Cases could use AppSettings)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                          DOMAIN LAYER                                        │
│                    (No settings access - pure domain)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                       INFRASTRUCTURE LAYER                                   │
│              ┌─────────────────────────────────────────┐                    │
│              │    persistence/app_settings.py        │ ← HERE              │
│              └─────────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

The `AppSettings` class lives in the **Infrastructure Layer** because:
1. It wraps an external library (PySide6/Qt)
2. It handles persistence concerns
3. It's an adapter for platform-native storage

### Class Design

```python
class AppSettings:
    """Clean API over QSettings."""

    # Constants - Semantic keys organized by category
    KEY_WINDOW_GEOMETRY = "geometry/window"
    KEY_WINDOW_STATE = "geometry/state"
    KEY_RECENT_FILES = "files/recent"
    KEY_MAX_RECENT = "files/max_recent"
    KEY_SETTINGS_VERSION = "meta/version"

    CURRENT_VERSION = 1
    DEFAULT_MAX_RECENT = 10

    # Instance state
    settings: QSettings  # Wrapped Qt object

    # Public API
    def get_value(key, default=None, value_type=None) -> Any
    def set_value(key, value) -> None
    def has_key(key) -> bool
    def remove_key(key) -> None
    def get_all_keys() -> list[str]
    def get_settings_file_path() -> str
    def sync() -> None
```

### Key Design Decisions

#### 1. Hierarchical Key Naming

```python
# Category/subcategory pattern
KEY_WINDOW_GEOMETRY = "geometry/window"
KEY_RECENT_FILES = "files/recent"
KEY_SETTINGS_VERSION = "meta/version"
```

**Rationale**:
- Matches QSettings' native grouping capability
- Prevents key collisions
- Makes settings file human-readable when debugging

#### 2. Type Conversion Parameter

```python
def get_value(self, key, default=None, value_type=None) -> Any:
    if value_type is not None:
        return self.settings.value(key, default, type=value_type)
    return self.settings.value(key, default)
```

**Rationale**:
- QSettings stores INI values as strings
- Without explicit type, `42` might return as `"42"`
- `value_type=int` ensures correct Python type
- Critical for `QByteArray` (window geometry)

#### 3. First-Run Initialization

```python
def __init__(self):
    self.settings = QSettings("InkProject", "Ink")
    self._initialize_defaults()

def _initialize_defaults(self):
    if not self.has_key(self.KEY_SETTINGS_VERSION):
        # First run - set defaults
        self.set_value(self.KEY_SETTINGS_VERSION, self.CURRENT_VERSION)
        self.set_value(self.KEY_MAX_RECENT, self.DEFAULT_MAX_RECENT)
        self.set_value(self.KEY_RECENT_FILES, [])
        self.sync()
```

**Rationale**:
- Ensures consistent initial state
- Version key enables future migrations (E06-F06-T04)
- `sync()` call ensures defaults survive crashes

---

## 3. Implementation Journey

### Phase 1: TDD Red - Writing Failing Tests (36 tests)

Started by defining the expected behavior through tests:

```python
# test_app_settings.py

class TestAppSettingsClassConstants:
    """7 tests for class-level constants"""
    def test_has_window_geometry_key(self) -> None:
        assert hasattr(AppSettings, "KEY_WINDOW_GEOMETRY")
        assert AppSettings.KEY_WINDOW_GEOMETRY == "geometry/window"
    # ... 6 more constant tests

class TestAppSettingsInitialization:
    """5 tests for initialization"""
    def test_creates_qsettings_instance(self, app_settings):
        assert isinstance(app_settings.settings, QSettings)

    def test_initializes_defaults_on_first_run(self, isolated_settings):
        settings = AppSettings()
        assert settings.has_key(AppSettings.KEY_SETTINGS_VERSION)

class TestAppSettingsGetValue:
    """8 tests for get_value()"""
    def test_converts_to_int_type(self, app_settings):
        app_settings.set_value("test/int", 42)
        result = app_settings.get_value("test/int", value_type=int)
        assert result == 42
        assert isinstance(result, int)

# ... more test classes
```

**Initial run result**: 36 tests failed (as expected in TDD Red phase)

### Phase 2: TDD Green - Making Tests Pass

Implemented the class to pass all tests:

```python
# app_settings.py

class AppSettings:
    KEY_WINDOW_GEOMETRY: str = "geometry/window"
    # ... other constants

    def __init__(self) -> None:
        self.settings = QSettings("InkProject", "Ink")
        self._initialize_defaults()

    def get_value(self, key, default=None, value_type=None) -> Any:
        if value_type is not None:
            return self.settings.value(key, default, type=value_type)
        return self.settings.value(key, default)

    # ... other methods
```

**Result**: All 36 tests passed

### Phase 3: TDD Refactor - Code Quality

Fixed linting and type checking issues:

1. **Raw docstrings for backslashes**:
   ```python
   r"""Windows path: HKEY_CURRENT_USER\Software\InkProject\Ink"""
   ```

2. **Any type exception**:
   ```toml
   # pyproject.toml
   "**/app_settings.py" = ["ANN401"]  # Settings need Any type
   ```

3. **Type imports in TYPE_CHECKING block**:
   ```python
   if TYPE_CHECKING:
       from pathlib import Path
   ```

---

## 4. Test Strategy Deep Dive

### The Test Isolation Problem

**Problem**: `QSettings.setPath()` is global - affects all instances.

**Symptom**: Tests passed individually but failed when run together:
```
FAILED test_initializes_defaults_on_first_run
AssertionError: assert 5 == 10
```

Test A set `KEY_MAX_RECENT` to 5, then Test B ran and found 5 instead of default 10.

**Solution**: Clear settings in fixture:

```python
@pytest.fixture
def isolated_settings(tmp_path):
    settings_path = tmp_path / "settings"
    settings_path.mkdir()

    QSettings.setPath(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        str(settings_path),
    )

    # CRITICAL: Clear existing settings
    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.clear()
    temp_settings.sync()

    yield settings_path
```

### Test Coverage by Method

| Method | Tests | Coverage |
|--------|-------|----------|
| Constants | 7 | All KEY_* and constants |
| `__init__` | 5 | QSettings creation, defaults |
| `get_value` | 8 | Default, type conversion, QByteArray |
| `set_value` | 4 | String, int, float, overwrite |
| `has_key` | 2 | Exists, not exists |
| `remove_key` | 2 | Remove, missing key |
| `get_all_keys` | 2 | Returns list, includes keys |
| `get_settings_file_path` | 2 | Returns string, non-empty |
| `sync` | 2 | No error, persists values |
| Persistence | 2 | Cross-instance, QByteArray |

---

## 5. File-by-File Walkthrough

### `src/ink/infrastructure/persistence/app_settings.py` (317 lines)

```
Lines 1-25:    Module docstring with design decisions
Lines 27-31:   Imports (only typing.Any and QSettings)
Lines 34-70:   Class docstring with usage examples
Lines 72-101:  Class constants (KEY_* and defaults)
Lines 103-123: __init__ with QSettings creation
Lines 125-150: _initialize_defaults (first-run logic)
Lines 152-189: get_value with type conversion
Lines 191-217: set_value (simple wrapper)
Lines 219-239: has_key (existence check)
Lines 241-260: remove_key (deletion)
Lines 262-279: get_all_keys (enumeration)
Lines 281-299: get_settings_file_path (debugging)
Lines 301-317: sync (force disk write)
```

### `tests/unit/infrastructure/persistence/test_app_settings.py` (380 lines)

```
Lines 1-29:    Imports and TYPE_CHECKING
Lines 31-70:  Module-level fixtures (isolated_settings, app_settings)
Lines 72-127:  TestAppSettingsClassConstants (7 tests)
Lines 129-175: TestAppSettingsInitialization (5 tests)
Lines 177-232: TestAppSettingsGetValue (8 tests)
Lines 234-259: TestAppSettingsSetValue (4 tests)
Lines 261-275: TestAppSettingsHasKey (2 tests)
Lines 277-290: TestAppSettingsRemoveKey (2 tests)
Lines 292-307: TestAppSettingsGetAllKeys (2 tests)
Lines 309-321: TestAppSettingsGetSettingsFilePath (2 tests)
Lines 323-344: TestAppSettingsSync (2 tests)
Lines 346-379: TestAppSettingsPersistence (2 tests)
```

---

## 6. Integration Points

### Downstream Dependencies

This `AppSettings` class will be used by:

```
E06-F06-T02: Window Geometry Persistence
├── Uses: KEY_WINDOW_GEOMETRY, KEY_WINDOW_STATE
└── Pattern: saveGeometry() → QByteArray → set_value()

E06-F06-T03: Recent Files Management
├── Uses: KEY_RECENT_FILES, KEY_MAX_RECENT
└── Pattern: get_value(KEY_RECENT_FILES) → list[str]

E06-F06-T04: Settings Migration & Reset
├── Uses: KEY_SETTINGS_VERSION, CURRENT_VERSION
└── Pattern: Check version, migrate, update version
```

### Usage in InkMainWindow (Future)

```python
class InkMainWindow(QMainWindow):
    def __init__(self, app_settings: AppSettings):
        super().__init__()
        self._settings = app_settings
        self._restore_geometry()

    def _restore_geometry(self):
        geometry = self._settings.get_value(
            AppSettings.KEY_WINDOW_GEOMETRY,
            value_type=QByteArray
        )
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event):
        self._settings.set_value(
            AppSettings.KEY_WINDOW_GEOMETRY,
            self.saveGeometry()
        )
        super().closeEvent(event)
```

---

## 7. Performance Considerations

### QSettings Caching
- QSettings caches values in memory
- Disk reads only on first access
- Disk writes batched (unless `sync()` called)

### Memory Footprint
- Single `QSettings` instance per `AppSettings`
- String keys stored once as class constants
- Values stored in Qt's native format

### Threading
- **Warning**: `QSettings` is NOT thread-safe
- For multi-threaded access, wrap in `QMutex` or use one instance per thread
- Current design assumes single-threaded GUI access (typical Qt pattern)

---

## 8. Error Handling

### Current Approach
- No explicit error handling (Qt handles gracefully)
- Invalid types passed to `set_value()` → Qt logs warning
- Missing keys → Returns `default` (None if not specified)

### Potential Improvements
```python
# Future: Add validation
def set_value(self, key: str, value: Any) -> None:
    if not isinstance(key, str) or not key:
        raise ValueError("Key must be non-empty string")
    self.settings.setValue(key, value)
```

---

## 9. Platform-Specific Behavior

### Linux
- Storage: `~/.config/InkProject/Ink.conf`
- Format: INI file
- Editable with text editor for debugging

### Windows
- Storage: `HKEY_CURRENT_USER\Software\InkProject\Ink`
- Format: Windows Registry
- Use `regedit` for debugging

### macOS
- Storage: `~/Library/Preferences/com.InkProject.Ink.plist`
- Format: Property List (XML or binary)
- Use `defaults read` for debugging

---

## 10. Debugging Tips

### Find Settings File Location
```python
settings = AppSettings()
print(settings.get_settings_file_path())
# Linux: /home/user/.config/InkProject/Ink.conf
```

### View All Stored Keys
```python
settings = AppSettings()
for key in settings.get_all_keys():
    print(f"{key} = {settings.get_value(key)}")
```

### Force Clear All Settings
```python
settings = AppSettings()
settings.settings.clear()
settings.sync()
```

### Linux: View Settings File
```bash
cat ~/.config/InkProject/Ink.conf
```

---

## 11. Security Considerations

- Settings stored in user-readable location
- **Never store**: Passwords, API keys, sensitive data
- For sensitive data: Use platform keychain (SecretService on Linux, Keychain on macOS)
- QSettings supports encryption via custom format (not implemented here)

---

## 12. Lessons Learned

### 1. QSettings Global State is Tricky
The `setPath()` method affects all QSettings instances. Test isolation requires explicit `clear()` calls.

### 2. Type Conversion is Essential
Without `value_type`, integers become strings after serialization. Always specify type for non-string values.

### 3. TDD Caught Real Issues
The test isolation problem would have been a production bug. TDD's parallel test runs exposed it early.

### 4. Ruff is Strict but Helpful
The strict linting caught:
- Deprecated imports (`typing.Generator` → `collections.abc.Generator`)
- Unused parameters
- Type annotations in runtime vs TYPE_CHECKING

### 5. Raw Docstrings for Paths
Windows paths with backslashes in docstrings need `r"""raw strings"""`.

---

## 13. Code Quality Metrics

### Final Statistics
- **Implementation**: 317 lines
- **Tests**: 380 lines (36 test cases)
- **Test:Code Ratio**: 1.2:1
- **Lint Issues**: 0
- **Type Errors**: 0
- **Test Coverage**: All public methods

### Tools Used
- **Linting**: Ruff (strict mode)
- **Type Checking**: mypy (strict mode)
- **Testing**: pytest + pytest-qt
- **Qt**: PySide6 6.10.1

---

## 14. Related Resources

- [Qt QSettings Documentation](https://doc.qt.io/qt-6/qsettings.html)
- [PySide6 QSettings API](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QSettings.html)
- [Spec E06-F06-T01](./E06-F06-T01.spec.md)
- [Post-Docs Quick Reference](./E06-F06-T01.post-docs.md)
- [GitHub Issue #7](https://github.com/ddoachi/ink/issues/7)

---

## 15. Acknowledgments

This implementation follows the TDD workflow specified in the `/spec_work` command system. The clean architecture placement in the Infrastructure layer follows Ink's DDD design principles documented in `CLAUDE.md`.
