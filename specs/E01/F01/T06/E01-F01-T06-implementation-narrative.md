# Implementation Narrative: E01-F01-T06 - Net Classification Configuration

> **Spec**: [E01-F01-T06.spec.md](./E01-F01-T06.spec.md)
> **Author**: Claude Opus 4.5
> **Date**: 2025-12-27

---

## Executive Summary

This document provides a comprehensive walkthrough of implementing per-project net classification configuration for the Ink schematic viewer. The implementation enables users to customize which nets are classified as power or ground on a per-project basis, supporting different PDK naming conventions without code modifications.

---

## 1. The Problem We're Solving

### Background

Gate-level netlists from CDL files contain nets with names that indicate power (VDD, VCC) or ground (VSS, GND) supplies. Ink's `NetNormalizer` class (from E01-F01-T04) already classifies these nets, but it uses hardcoded patterns.

### The Challenge

Different foundries and PDKs use different naming conventions:
- **TSMC**: AVDD, AVSS, DVDD, DVSS
- **Samsung**: VDD_CORE, VSS_CORE, VDD_IO
- **GlobalFoundries**: VPWR, VGND
- **Custom blocks**: PWR_*, GND_*, VDDQ0-VDDQ15

Without configuration, users would need to modify source code to support their conventions.

### The Solution

A three-part system:
1. **YAML Configuration File**: Stores power/ground net definitions per project
2. **Configuration Loading**: Reads YAML and creates typed Python objects
3. **UI Dialog**: Allows visual editing without touching files directly

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         User Interaction Flow                            │
│                                                                          │
│   User opens "Edit > Net Classification..."                              │
│              │                                                           │
│              ▼                                                           │
│   ┌────────────────────────────────────┐                                │
│   │     NetClassificationDialog        │ ◄─── Qt UI (Presentation)      │
│   │  - Power/Ground tabs               │                                │
│   │  - Name/Pattern lists              │                                │
│   │  - Override checkbox               │                                │
│   └────────────────┬───────────────────┘                                │
│                    │ get_config()                                        │
│                    ▼                                                     │
│   ┌────────────────────────────────────┐                                │
│   │    NetClassificationConfig         │ ◄─── Data (Infrastructure)     │
│   │  - load(project_path)              │                                │
│   │  - save(project_path)              │                                │
│   └────────────────┬───────────────────┘                                │
│                    │                                                     │
│                    ▼                                                     │
│   ┌────────────────────────────────────┐                                │
│   │  {project}/.ink/                   │ ◄─── File System               │
│   │  └── net_classification.yaml       │                                │
│   └────────────────────────────────────┘                                │
│                                                                          │
│   On file load or config save:                                           │
│              │                                                           │
│              ▼                                                           │
│   ┌────────────────────────────────────┐                                │
│   │   NetNormalizer.from_config()      │ ◄─── Factory (Infrastructure)  │
│   │  - Creates normalizer from config  │                                │
│   │  - Sets up custom patterns         │                                │
│   └────────────────────────────────────┘                                │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Implementation Deep Dive

### Phase 1: Configuration Data Structure

**File**: `src/ink/infrastructure/config/net_classification_config.py`

The configuration is represented as a Python dataclass:

```python
@dataclass
class NetClassificationConfig:
    """Configuration for power/ground net classification."""

    power_names: list[str] = field(default_factory=list)
    power_patterns: list[str] = field(default_factory=list)
    ground_names: list[str] = field(default_factory=list)
    ground_patterns: list[str] = field(default_factory=list)
    override_defaults: bool = False
```

**Design Rationale**:
- `list[str]` for names/patterns allows ordered storage and easy iteration
- `override_defaults` flag gives users full control when needed
- Immutable defaults via `field(default_factory=list)` prevent shared state bugs

#### Load Method

The `load()` class method reads YAML with defensive programming:

```python
@classmethod
def load(cls, project_path: Path) -> NetClassificationConfig:
    config_file = project_path / CONFIG_DIR / CONFIG_FILENAME

    # Graceful handling of missing file
    if not config_file.exists():
        return cls()  # Empty defaults

    with config_file.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Handle empty file (safe_load returns None)
    if data is None:
        return cls()

    # Extract with fallbacks for missing sections
    power_nets = data.get("power_nets", {})
    if not isinstance(power_nets, dict):
        power_nets = {}

    return cls(
        power_names=power_nets.get("names", []) or [],
        power_patterns=power_nets.get("patterns", []) or [],
        # ... similar for ground
    )
```

**Key Defensive Patterns**:
1. Missing file → return empty defaults
2. Empty file → return empty defaults
3. Missing sections → use empty lists
4. Non-dict sections → treat as empty

#### Save Method

The `save()` method ensures the `.ink/` directory exists:

```python
def save(self, project_path: Path) -> None:
    config_dir = project_path / CONFIG_DIR
    config_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "version": CONFIG_VERSION,  # Future migration support
        "power_nets": {
            "names": self.power_names,
            "patterns": self.power_patterns,
        },
        # ... ground_nets, override_defaults
    }

    with config_file.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
```

---

### Phase 2: NetNormalizer Enhancement

**File**: `src/ink/infrastructure/parsing/net_normalizer.py`

#### New Instance Variables

```python
def __init__(self, power_nets=None, ground_nets=None):
    # Existing: exact name sets
    self._power_nets: set[str] = {name.upper() for name in power_nets} if power_nets else set()
    self._ground_nets: set[str] = {name.upper() for name in ground_nets} if ground_nets else set()

    # NEW: custom pattern sets
    self._custom_power_patterns: set[str] = set()
    self._custom_ground_patterns: set[str] = set()

    # NEW: default pattern control
    self._use_default_patterns: bool = True

    # Existing: cache
    self._net_cache: dict[str, NetInfo] = {}
```

#### Pattern Management Methods

```python
def add_power_patterns(self, patterns: Iterable[str]) -> None:
    """Add custom regex patterns for power net classification."""
    self._custom_power_patterns.update(patterns)
    self._net_cache.clear()  # CRITICAL: invalidate cache

def clear_default_patterns(self) -> None:
    """Disable default VDD/VSS patterns."""
    self._use_default_patterns = False
    self._net_cache.clear()
```

**Cache Invalidation**: Whenever classification rules change, the cache must be cleared. Otherwise, previously cached results would be incorrect for subsequent lookups.

#### Updated Classification Logic

The `_classify_type()` method now checks patterns in priority order:

```python
def _classify_type(self, net_name: str) -> NetType:
    net_name_upper = net_name.upper()

    # Priority 1: Custom exact names (O(1) lookup)
    if net_name_upper in self._power_nets:
        return NetType.POWER
    if net_name_upper in self._ground_nets:
        return NetType.GROUND

    # Collect all applicable patterns
    power_patterns = list(self._custom_power_patterns)
    if self._use_default_patterns:
        power_patterns.extend(self.POWER_PATTERNS)

    ground_patterns = list(self._custom_ground_patterns)
    if self._use_default_patterns:
        ground_patterns.extend(self.GROUND_PATTERNS)

    # Priority 2: Pattern matching
    if any(re.match(p, net_name, re.IGNORECASE) for p in power_patterns):
        return NetType.POWER
    if any(re.match(p, net_name, re.IGNORECASE) for p in ground_patterns):
        return NetType.GROUND

    return NetType.SIGNAL
```

**Pattern Merge Strategy**: Custom patterns come first, then defaults (if enabled). This ensures user patterns take precedence.

#### Factory Method

```python
@classmethod
def from_config(cls, config: NetClassificationConfig) -> NetNormalizer:
    """Create NetNormalizer from configuration."""
    normalizer = cls(
        power_nets=config.power_names,
        ground_nets=config.ground_names,
    )

    if config.power_patterns:
        normalizer.add_power_patterns(config.power_patterns)
    if config.ground_patterns:
        normalizer.add_ground_patterns(config.ground_patterns)

    if config.override_defaults:
        normalizer.clear_default_patterns()

    return normalizer
```

---

### Phase 3: Qt Configuration Dialog

**File**: `src/ink/presentation/dialogs/net_classification_dialog.py`

#### Dialog Structure

```
┌─────────────────────────────────────────────────────────────┐
│ Net Classification Settings                            [X] │
├─────────────────────────────────────────────────────────────┤
│ ┌───────────────┬─────────────────┐                        │
│ │ Power Nets    │ Ground Nets     │ ◄── QTabWidget         │
│ └───────────────┴─────────────────┘                        │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Net Names (exact match, case-insensitive)               ││◄── QGroupBox
│ │ ┌─────────────────────────────────────────────────────┐ ││
│ │ │ AVDD                                                │ ││◄── QListWidget
│ │ │ DVDD                                                │ ││
│ │ └─────────────────────────────────────────────────────┘ ││
│ │ [Add]  [Remove]                                         ││◄── QPushButtons
│ └─────────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Regex Patterns (additional)                             ││◄── QGroupBox
│ │ ┌─────────────────────────────────────────────────────┐ ││
│ │ │ ^VDDQ[0-9]*$                                        │ ││◄── QListWidget
│ │ └─────────────────────────────────────────────────────┘ ││
│ │ [Add]  [Remove]                                         ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ [ ] Override default patterns (VDD*, VSS*, GND*, etc.)     │◄── QCheckBox
│                                                             │
│                              [Cancel]  [OK]                 │◄── QDialogButtonBox
└─────────────────────────────────────────────────────────────┘
```

#### Tab Creation Pattern

Both Power and Ground tabs use the same structure, created by a reusable method:

```python
def _create_net_tab(self) -> tuple[QWidget, QListWidget, QListWidget]:
    """Create a tab with names list + patterns list + buttons."""
    tab = QWidget()
    layout = QVBoxLayout(tab)

    # Names section
    names_group = QGroupBox("Net Names (exact match, case-insensitive)")
    names_list = QListWidget()
    # ... add/remove buttons

    # Patterns section
    patterns_group = QGroupBox("Regex Patterns (additional)")
    patterns_list = QListWidget()
    # ... add/remove buttons

    return tab, names_list, patterns_list
```

#### Button Handler with Closures

```python
add_name_btn.clicked.connect(lambda: self._on_add_item(names_list))
remove_name_btn.clicked.connect(lambda: self._on_remove_item(names_list))
```

**Why Lambda**: The handler method needs to know which list widget to modify. Lambda captures the specific `names_list` variable at creation time.

#### Config Extraction

```python
def get_config(self) -> NetClassificationConfig:
    """Extract configuration from current UI state."""
    from ink.infrastructure.config.net_classification_config import (
        NetClassificationConfig,
    )

    return NetClassificationConfig(
        power_names=self.get_power_names(),      # List from UI
        power_patterns=self.get_power_patterns(),
        ground_names=self.get_ground_names(),
        ground_patterns=self.get_ground_patterns(),
        override_defaults=self._override_checkbox.isChecked(),
    )
```

---

## 4. Test Strategy

### Test-Driven Development (TDD) Flow

Each component followed the RED-GREEN-REFACTOR cycle:

1. **RED**: Write failing tests first
   ```bash
   $ pytest tests/.../test_net_classification_config.py -v
   FAILED - ModuleNotFoundError: No module named '...'
   ```

2. **GREEN**: Implement minimal code to pass
   ```bash
   $ pytest tests/.../test_net_classification_config.py -v
   12 passed
   ```

3. **REFACTOR**: Improve code quality
   ```bash
   $ ruff check src/...  # Fix lint issues
   $ mypy src/...        # Fix type issues
   ```

### Test Categories

| Component | Test Count | Key Scenarios |
|-----------|------------|---------------|
| `NetClassificationConfig` | 12 | Load/save YAML, empty file, missing sections |
| `NetNormalizer.from_config` | 8 | Custom names, patterns, override_defaults |
| `NetNormalizer` pattern methods | 9 | add_*_patterns, clear_defaults, cache invalidation |
| `NetClassificationDialog` | 20 | UI structure, config display, get_config |

### Test Fixtures

**Temporary Directory Pattern**:
```python
def test_load_parses_power_names(self, tmp_path: Path) -> None:
    config_dir = tmp_path / ".ink"
    config_dir.mkdir()
    config_file = config_dir / "net_classification.yaml"
    config_file.write_text("""
version: 1
power_nets:
  names:
    - AVDD
""")

    config = NetClassificationConfig.load(tmp_path)
    assert config.power_names == ["AVDD"]
```

**Qt Widget Testing with qtbot**:
```python
def test_dialog_displays_power_names(self, qtbot) -> None:
    config = NetClassificationConfig(power_names=["AVDD", "DVDD"])
    dialog = NetClassificationDialog(config)
    qtbot.addWidget(dialog)  # Required for cleanup

    power_names = dialog.get_power_names()
    assert "AVDD" in power_names
```

---

## 5. Integration Points

### With MainWindow (Future Work)

The dialog will be integrated into the Edit menu:

```python
# In MainWindow._create_edit_menu()
net_classification_action = QAction("Net Classification...", self)
net_classification_action.triggered.connect(self._open_net_classification_dialog)
edit_menu.addAction(net_classification_action)

def _open_net_classification_dialog(self) -> None:
    project_path = self._get_current_project_path()
    config = NetClassificationConfig.load(project_path)

    dialog = NetClassificationDialog(config, self)
    if dialog.exec() == QDialog.Accepted:
        new_config = dialog.get_config()
        new_config.save(project_path)
        self._reload_net_normalizer(new_config)
```

### With CDL Parser (E01-F01-T05)

When loading a CDL file, the parser will use the configuration:

```python
# In file loading code
config = NetClassificationConfig.load(project_path)
normalizer = NetNormalizer.from_config(config)

# Pass normalizer to parser
parser = CDLParser(normalizer=normalizer)
design = parser.parse(cdl_file)
```

---

## 6. Error Handling

### YAML Parsing Errors

Currently, invalid YAML will raise a `yaml.YAMLError`. Future enhancement could catch this and show a user-friendly message.

### Invalid Regex Patterns

Currently, invalid regex patterns will fail at runtime when `re.match()` is called. Future enhancement could validate patterns on save.

### File Permission Errors

The `save()` method could fail if the user doesn't have write permission. This would raise an `OSError` that should be caught and reported to the user.

---

## 7. Performance Considerations

### Cache Invalidation

The `_net_cache` dictionary is cleared whenever:
- `add_power_patterns()` is called
- `add_ground_patterns()` is called
- `clear_default_patterns()` is called

This is necessary because cached classification results may become invalid.

### Pattern Compilation

Currently, regex patterns are compiled on each `_classify_type()` call via `re.match()`. For large netlists with many unique nets, pre-compiling patterns could improve performance:

```python
# Future optimization
self._compiled_power_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
```

---

## 8. Conclusion

The net classification configuration system successfully enables per-project customization of power/ground net detection. The implementation follows DDD principles with clear layer separation:

- **Infrastructure Layer**: Configuration loading/saving, NetNormalizer enhancements
- **Presentation Layer**: Qt dialog for visual editing

Key success factors:
1. **TDD approach** caught edge cases early
2. **Defensive coding** handles missing files/sections gracefully
3. **Type hints + linting** prevented runtime errors
4. **Cache invalidation** ensures correctness after state changes

The system is now ready for integration with the main application's Edit menu and CDL parser.
