# E06-F06-T04: Settings Migration & Reset - Implementation Narrative

## Executive Summary

This document provides a comprehensive walkthrough of implementing the Settings Migration & Reset feature for the Ink schematic viewer. The implementation adds forward-compatible version tracking, sequential migration support, and user-friendly settings management through the application's menu system.

---

## 1. Problem Context

### 1.1 The Challenge

As applications evolve, their settings schemas inevitably change:
- Keys get renamed for better organization
- Data formats change (string to dict, list to object)
- New required settings are added
- Deprecated settings need cleanup

Without a migration system:
- Users upgrading may crash due to schema mismatches
- Old settings may silently cause bugs
- Users can't recover from corrupted settings
- Support debugging is difficult without visibility into settings

### 1.2 Solution Approach

The solution implements three pillars:
1. **Version Tracking**: Store a schema version with settings
2. **Migration Framework**: Apply changes sequentially when upgrading
3. **Reset Capability**: Allow users to recover to a known-good state

---

## 2. Implementation Walkthrough

### 2.1 Migration Framework (`app_settings.py:168-272`)

The migration system follows a pattern used by major frameworks like Django and Rails:

```python
def _migrate_if_needed(self) -> None:
    """Check and migrate settings from older versions if needed."""
    stored_version = self.get_value(self.KEY_SETTINGS_VERSION, 0, value_type=int)

    if stored_version < self.CURRENT_VERSION:
        # Apply migrations sequentially from stored version to current
        self._migrate_settings(stored_version, self.CURRENT_VERSION)

        # Update stored version after successful migration
        self.set_value(self.KEY_SETTINGS_VERSION, self.CURRENT_VERSION)
        self.sync()
```

**Key Design Decisions:**

1. **Sequential Application**: If a user upgrades from v0 to v3, the system applies v0→v1, then v1→v2, then v2→v3. This means each migration only needs to handle the delta from its immediate predecessor.

2. **Named Methods**: Each migration is a separate method (`_migrate_v0_to_v1`, `_migrate_v1_to_v2`, etc.). This provides:
   - Individual testability
   - Clear documentation of changes
   - Easy addition of new migrations

3. **Version Check at Init**: Migration runs during `__init__` before `_initialize_defaults`, ensuring the schema is correct before defaults are applied.

### 2.2 Reset Methods (`app_settings.py:431-509`)

Three levels of reset granularity were implemented:

#### Full Reset
```python
def reset_all_settings(self) -> None:
    """Reset all settings to defaults."""
    # Clear all settings from storage
    self.settings.clear()

    # Re-initialize defaults
    self.set_value(self.KEY_SETTINGS_VERSION, self.CURRENT_VERSION)
    self.set_value(self.KEY_MAX_RECENT, self.DEFAULT_MAX_RECENT)
    self.set_value(self.KEY_RECENT_FILES, [])

    self.sync()
```

#### Geometry Reset
```python
def reset_window_geometry(self) -> None:
    """Reset only window geometry and state."""
    self.remove_key(self.KEY_WINDOW_GEOMETRY)
    self.remove_key(self.KEY_WINDOW_STATE)
    self.sync()
```

#### Recent Files Reset
```python
def reset_recent_files(self) -> None:
    """Reset recent files list."""
    self.set_value(self.KEY_RECENT_FILES, [])
    self.sync()
```

**Design Rationale:**
- Granular resets let users fix specific issues without losing everything
- `sync()` called immediately to ensure persistence
- Geometry reset removes keys entirely (defaults will be used on restart)
- Recent files reset sets empty list (key still exists with empty value)

### 2.3 Diagnostic Methods (`app_settings.py:517-624`)

Three diagnostic tools were added:

#### Settings Dictionary Export
```python
def get_all_settings(self) -> dict[str, Any]:
    """Get all settings as dictionary."""
    result: dict[str, Any] = {}
    for key in self.settings.allKeys():
        result[key] = self.settings.value(key)
    return result
```

#### JSON Export with QByteArray Handling
```python
def export_settings(self, file_path: str) -> None:
    """Export settings to JSON file."""
    settings_dict = self.get_all_settings()

    # Convert QByteArray values to base64 for JSON serialization
    for key, value in settings_dict.items():
        if isinstance(value, QByteArray):
            settings_dict[key] = {
                "_type": "QByteArray",
                "_data": base64.b64encode(value.data()).decode("utf-8"),
            }

    with Path(file_path).open("w") as f:
        json.dump(settings_dict, f, indent=2)
```

**Note on QByteArray**: The `value.data()` method is used instead of `bytes(value)` because:
- `bytes()` constructor doesn't directly accept QByteArray
- `.data()` returns a memoryview that base64 can encode

#### Corruption Detection
```python
def is_corrupted(self) -> bool:
    """Check if settings appear corrupted."""
    try:
        version = self.get_value(self.KEY_SETTINGS_VERSION, value_type=int)
        if version is None or not isinstance(version, int):
            return True
        self.get_value(self.KEY_RECENT_FILES)
        return False
    except Exception:
        return True
```

### 2.4 MainWindow Integration (`main_window.py:169-316`)

The UI integration required:

1. **Optional Dependency Injection**:
```python
def __init__(self, app_settings: AppSettings | None = None) -> None:
    super().__init__()
    self.app_settings = app_settings
    self._setup_window()
    self._setup_central_widget()
    self._setup_menus()
```

2. **Menu Structure**:
```
Help
├── (separator)
└── Settings
    ├── Reset Window Layout
    ├── Clear Recent Files
    ├── (separator)
    ├── Reset All Settings...
    ├── (separator)
    └── Show Settings File Location
```

3. **Confirmation Dialogs**: Each destructive action shows a confirmation dialog before proceeding, with the "Reset All Settings" dialog providing extra detail about what will be reset.

4. **Graceful Degradation**: When `app_settings` is None, menu items are disabled:
```python
reset_geometry_action.setEnabled(self.app_settings is not None)
```

---

## 3. Data Flow Diagrams

### 3.1 Migration on Application Start

```
┌──────────────────┐
│  AppSettings()   │
│    __init__      │
└────────┬─────────┘
         │
         ▼
┌────────────────────┐
│ _migrate_if_needed │
│  stored_version=0  │
│  CURRENT_VERSION=1 │
└────────┬───────────┘
         │ stored < current?
         ▼
┌────────────────────┐
│  _migrate_settings │
│    0 → 1           │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  _migrate_v0_to_v1 │
│  (baseline, no-op) │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  Update version    │
│  sync() to disk    │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ _initialize_defaults│
│ (fills missing keys)│
└────────────────────┘
```

### 3.2 Reset All Settings Flow

```
┌──────────────────┐
│  User clicks     │
│  "Reset All..."  │
└────────┬─────────┘
         │
         ▼
┌────────────────────┐
│  QMessageBox       │
│  .question()       │
│  "Are you sure?"   │
└────────┬───────────┘
         │ Yes
         ▼
┌────────────────────┐
│  settings.clear()  │
│  (removes all keys)│
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  Set defaults:     │
│  - version         │
│  - max_recent      │
│  - recent_files=[] │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  sync() to disk    │
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│  QMessageBox       │
│  .information()    │
│  "Restart needed"  │
└────────────────────┘
```

---

## 4. Testing Approach

### 4.1 Test Fixture: Isolated Settings

```python
@pytest.fixture
def isolated_settings(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide isolated QSettings storage for each test."""
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

This fixture ensures:
- Each test gets a fresh settings file
- No pollution of real user settings
- Complete isolation between tests
- Automatic cleanup via pytest's tmp_path

### 4.2 Test Categories

| Category | Tests | What They Verify |
|----------|-------|------------------|
| Migration | 4 | Version tracking, sequential migration, no-op for current |
| Reset | 7 | Full reset, partial resets, preservation of unrelated settings |
| Diagnostics | 6 | Dictionary export, JSON export, QByteArray handling, corruption detection |

### 4.3 Example Test: Migration Sequence

```python
def test_migrate_if_needed_called_on_init(self, isolated_settings: Path) -> None:
    """Verify _migrate_if_needed is called during initialization."""
    # Pre-set an old version to simulate upgrade scenario
    temp_settings = QSettings("InkProject", "Ink")
    temp_settings.setValue(AppSettings.KEY_SETTINGS_VERSION, 0)
    temp_settings.sync()

    # Create new instance - should trigger migration
    settings = AppSettings()

    # Version should now be current
    assert settings.get_settings_version() == AppSettings.CURRENT_VERSION
```

---

## 5. Error Handling

### 5.1 Corrupted Settings

The `is_corrupted()` method provides a heuristic check:

```python
def is_corrupted(self) -> bool:
    try:
        version = self.get_value(self.KEY_SETTINGS_VERSION, value_type=int)
        if version is None or not isinstance(version, int):
            return True
        self.get_value(self.KEY_RECENT_FILES)
        return False
    except Exception:
        return True
```

**Limitations:**
- Only checks version and recent_files keys
- Won't detect all types of corruption
- Should be used as a hint, not definitive check

**Future Enhancement:**
A startup check in `main.py` could use this:
```python
if app_settings.is_corrupted():
    reply = QMessageBox.question(None, "Corrupted Settings", "Reset?")
    if reply == Yes:
        app_settings.reset_all_settings()
```

### 5.2 Type Safety

Return types from QSettings are `Any`, so explicit conversion is needed:

```python
def get_settings_version(self) -> int:
    version = self.get_value(self.KEY_SETTINGS_VERSION, 0, value_type=int)
    return int(version) if version is not None else 0
```

---

## 6. Performance Considerations

### 6.1 Migration Cost

- Migrations run once per version upgrade
- Each migration is O(n) where n is number of keys to transform
- `sync()` called once at end, not per key
- Negligible startup impact for typical usage

### 6.2 Export Cost

- `get_all_settings()` iterates all keys: O(n)
- JSON serialization: O(n)
- File I/O: depends on file size
- Not called frequently, acceptable for diagnostic use

---

## 7. Security Considerations

### 7.1 Settings Location

Settings are stored in platform-standard locations:
- **Linux**: `~/.config/InkProject/Ink.conf` (user-only readable by default)
- **Windows**: Registry (user hive, per-user access)
- **macOS**: `~/Library/Preferences/` (user-only)

### 7.2 Exported Settings

The `export_settings()` method exports all settings including:
- Window geometry (not sensitive)
- Recent file paths (may reveal project structure)

Users should be cautioned when sharing exported settings.

---

## 8. Maintenance Guide

### 8.1 Adding a New Migration

1. Increment `CURRENT_VERSION`:
   ```python
   CURRENT_VERSION: int = 2  # Was 1
   ```

2. Add migration method:
   ```python
   def _migrate_v1_to_v2(self) -> None:
       """Migrate from version 1 to version 2.

       Changes:
       - Rename 'old/key' to 'new/key'
       """
       if self.has_key("old/key"):
           value = self.get_value("old/key")
           self.set_value("new/key", value)
           self.remove_key("old/key")
   ```

3. Add tests for the migration

### 8.2 When to Migrate vs. Add Optional Key

**Migrate when:**
- Renaming existing keys
- Changing data format of existing keys
- Removing deprecated keys

**Just add default when:**
- Adding new optional settings
- Changing default values (old value is still valid)

---

## 9. References

- [Qt QSettings Documentation](https://doc.qt.io/qt-6/qsettings.html)
- [Django Migrations](https://docs.djangoproject.com/en/4.2/topics/migrations/) - similar pattern inspiration
- Spec E06-F06-T04: Original requirements
- Spec E06-F06-T01: QSettings Infrastructure foundation
