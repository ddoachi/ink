# Implementation Narrative: Pattern Configuration for Sequential Cell Detection

**Spec ID**: E01-F04-T01
**Author**: Claude
**Date**: 2025-12-27

---

## The Story: Making Latch Detection Configurable

### The Problem We Solved

In the Ink schematic viewer, we need to identify sequential cells (flip-flops and latches) to use them as expansion boundaries. The challenge? Different cell libraries use different naming conventions:

- **Library A**: `DFFR_X1`, `SDFFR_X2`
- **Library B**: `DFF_1`, `DFF_2`
- **Library C**: `LATCH_X1`, `DLATCH_X2`

Hard-coding these patterns would require code changes for every new library. Engineers would need developer support just to add a new pattern. That's not acceptable for a tool designed for hardware engineers.

### Our Solution: Configuration-Driven Pattern Matching

We built a YAML-based configuration system that lets anyone customize the patterns without touching code. Here's what we created:

```
┌─────────────────────────────────────────────────────────────┐
│                    User's Perspective                        │
│                                                              │
│  config/latch_patterns.yaml                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ latch_identification:                                │    │
│  │   patterns:                                          │    │
│  │     - "*DFF*"      # Edit this line!                │    │
│  │     - "*LATCH*"                                      │    │
│  │     - "*REGF*"     # Add your library's patterns    │    │
│  │   case_sensitive: false                              │    │
│  └─────────────────────────────────────────────────────┘    │
│                            ↓                                  │
│                    Restart Application                        │
│                            ↓                                  │
│              Patterns are now active                         │
└─────────────────────────────────────────────────────────────┘
```

---

## The Implementation Journey

### Phase 1: Test-Driven Design (RED Phase)

We started by writing 26 tests that describe exactly what we wanted to build. Before any implementation:

```python
# These tests FAILED initially (which is correct for TDD)

def test_default_patterns_contains_dff(self) -> None:
    """Test that default patterns include *DFF* pattern."""
    from ink.infrastructure.config.latch_config import DEFAULT_SEQUENTIAL_PATTERNS
    assert "*DFF*" in DEFAULT_SEQUENTIAL_PATTERNS

def test_config_is_frozen_dataclass(self) -> None:
    """Config should be immutable to prevent accidental changes."""
    config = LatchIdentificationConfig(patterns=["*DFF*"])
    with pytest.raises(AttributeError):
        config.patterns = ["*LATCH*"]  # This should fail!
```

Running `pytest` showed 26 failures because `latch_config.py` didn't exist yet. Perfect - that's exactly what TDD requires.

### Phase 2: Making Tests Pass (GREEN Phase)

We implemented the `LatchIdentificationConfig` class step by step:

**Step 1: Define the Default Patterns**

```python
# src/ink/infrastructure/config/latch_config.py:65-69

DEFAULT_SEQUENTIAL_PATTERNS: list[str] = [
    "*DFF*",    # D flip-flops - most common sequential element
    "*LATCH*",  # Latch elements - level-sensitive storage
    "*FF*",     # Generic flip-flops - broader fallback (includes JK, SR, etc.)
]
```

Why this order? More specific patterns (`*DFF*`) come before broader patterns (`*FF*`). When matching, we can exit early on specific matches.

**Step 2: Create the Immutable Dataclass**

```python
# src/ink/infrastructure/config/latch_config.py:72-141

@dataclass(frozen=True)
class LatchIdentificationConfig:
    """Configuration for sequential cell (latch/flip-flop) identification."""

    patterns: tuple[str, ...]  # Tuple, not list!
    case_sensitive: bool = False

    def __init__(
        self, patterns: list[str] | tuple[str, ...], case_sensitive: bool = False
    ) -> None:
        # Convert list to tuple for immutability
        if isinstance(patterns, list):
            object.__setattr__(self, "patterns", tuple(patterns))
        else:
            object.__setattr__(self, "patterns", patterns)
        object.__setattr__(self, "case_sensitive", case_sensitive)
```

**Why `tuple` instead of `list`?**

A frozen dataclass prevents reassigning `config.patterns = [...]`, but it doesn't prevent `config.patterns.append("...")`. By using a tuple, we get true immutability:

```python
config = LatchIdentificationConfig(patterns=["*DFF*"])
config.patterns.append("*NEW*")  # AttributeError: tuple has no 'append'
```

**Step 3: Implement YAML Loading with Graceful Fallback**

The real complexity is in error handling. We need to handle:

- Missing config file
- Invalid YAML syntax
- Empty file
- Missing sections
- Empty patterns list

```python
# src/ink/infrastructure/config/latch_config.py:167-200

@staticmethod
def load_from_yaml(config_path: Path) -> LatchIdentificationConfig:
    """Load configuration from a YAML file."""
    # Delegate to helper methods for clean structure
    data = LatchIdentificationConfig._load_yaml_data(config_path)
    if data is None:
        return LatchIdentificationConfig.default()
    return LatchIdentificationConfig._parse_config_data(data, config_path)
```

The helper methods handle the complexity:

```python
# _load_yaml_data handles file operations
# Returns None for any error, letting load_from_yaml use defaults

# _parse_config_data handles parsing
# Logs warnings for missing sections but continues with defaults
```

### Phase 3: Refactoring (REFACTOR Phase)

After all tests passed, we cleaned up:

1. **Extracted Helper Methods**: Original `load_from_yaml` had 8 return statements (violated `PLR0911`). Split into `_load_yaml_data` and `_parse_config_data`.

2. **Added Type Hints**: Using `dict[str, Any]` instead of just `dict` for mypy compliance.

3. **Formatted Code**: `ruff format` ensured consistent style.

---

## Code Flow: Loading Configuration

Here's the complete execution path when loading configuration:

```python
config = LatchIdentificationConfig.load_from_yaml(Path("config/latch_patterns.yaml"))
```

### Happy Path

```
load_from_yaml(config_path)
    │
    ├─► _load_yaml_data(config_path)
    │       │
    │       ├─► Check file exists: YES ✓
    │       │
    │       ├─► yaml.safe_load(file)
    │       │       → {"latch_identification": {"patterns": [...], ...}}
    │       │
    │       └─► Return data dict
    │
    ├─► data is not None, continue
    │
    └─► _parse_config_data(data, config_path)
            │
            ├─► Extract latch_identification section
            │
            ├─► Validate section exists and is dict ✓
            │
            ├─► Extract patterns list: ["*DFF*", "*LATCH*", "*FF*"]
            │
            ├─► Validate patterns not empty ✓
            │
            ├─► Extract case_sensitive: False
            │
            └─► Return LatchIdentificationConfig(
                    patterns=("*DFF*", "*LATCH*", "*FF*"),
                    case_sensitive=False
                )
```

### Error Path: Missing File

```
load_from_yaml(config_path)
    │
    └─► _load_yaml_data(config_path)
            │
            ├─► Check file exists: NO ✗
            │
            ├─► logger.warning("Latch configuration file not found...")
            │
            └─► Return None

    ↓ (data is None)

    └─► Return LatchIdentificationConfig.default()
            │
            └─► LatchIdentificationConfig(
                    patterns=("*DFF*", "*LATCH*", "*FF*"),
                    case_sensitive=False
                )
```

---

## The Configuration File

We created `config/latch_patterns.yaml` with extensive documentation:

```yaml
# Latch/Sequential Cell Identification Configuration
# =================================================
#
# This file configures pattern matching for detecting sequential cells
# (latches, flip-flops) in gate-level netlists.
#
# Pattern Syntax (Glob-Style):
# ----------------------------
#   *     - Matches any sequence of characters (including none)
#   ?     - Matches any single character
#
# Examples:
#   "*DFF*"    - Matches: DFFR_X1, SDFFR_X2, DFF_POS, SCAN_DFF
#   "*LATCH*"  - Matches: LATCH_X1, DLATCH_X2, HLATCH

latch_identification:
  patterns:
    - "*DFF*"      # D flip-flops (DFFR_X1, SDFFR_X2, DFF_POS, etc.)
    - "*LATCH*"    # Latch elements (LATCH_X1, DLATCH_X2, etc.)
    - "*FF*"       # Generic flip-flops (JKFF, SRFF, FF_X1, etc.)

  case_sensitive: false
```

The comments serve as user documentation. Engineers can understand and modify the file without reading source code.

---

## Testing: What We Verified

### Test Organization

```
tests/unit/infrastructure/config/test_latch_config.py

├── TestDefaultSequentialPatterns (5 tests)
│   ├── test_default_patterns_constant_exists
│   ├── test_default_patterns_contains_dff
│   ├── test_default_patterns_contains_latch
│   ├── test_default_patterns_contains_ff
│   └── test_default_patterns_order_is_specific_to_general

├── TestLatchIdentificationConfigDataclass (3 tests)
│   ├── test_config_is_frozen_dataclass
│   ├── test_config_has_patterns_field
│   └── test_config_has_case_sensitive_field

├── TestLatchIdentificationConfigDefault (3 tests)
│   ├── test_default_factory_returns_config
│   ├── test_default_factory_uses_default_patterns
│   └── test_default_factory_is_case_insensitive

├── TestLatchIdentificationConfigLoadFromYaml (4 tests)
│   ├── test_load_valid_yaml_file
│   ├── test_load_yaml_with_case_sensitive_true
│   ├── test_load_yaml_with_comments
│   └── test_load_yaml_with_missing_case_sensitive

├── TestLatchIdentificationConfigErrorHandling (6 tests)
│   ├── test_missing_file_returns_default_config
│   ├── test_invalid_yaml_returns_default_config
│   ├── test_empty_yaml_file_returns_default_config
│   ├── test_empty_patterns_list_returns_default_patterns
│   ├── test_missing_patterns_key_returns_default_patterns
│   └── test_missing_latch_identification_section_returns_defaults

├── TestLatchIdentificationConfigPatternFormat (3 tests)
│   ├── test_patterns_with_wildcards_are_accepted
│   ├── test_patterns_preserve_order
│   └── test_unicode_patterns_are_supported

└── TestLatchIdentificationConfigIntegration (2 tests)
    ├── test_load_from_project_config_directory
    └── test_config_file_with_whitespace_patterns
```

### Key Test: Verifying Immutability

```python
def test_config_is_frozen_dataclass(self) -> None:
    """Test that config is an immutable (frozen) dataclass."""
    from dataclasses import is_dataclass
    from ink.infrastructure.config.latch_config import LatchIdentificationConfig

    assert is_dataclass(LatchIdentificationConfig)

    # Test that it's frozen by attempting modification
    config = LatchIdentificationConfig(patterns=["*DFF*"], case_sensitive=False)
    with pytest.raises(AttributeError):
        config.patterns = ["*LATCH*"]  # type: ignore[misc]
```

### Key Test: Graceful Error Handling

```python
def test_missing_file_returns_default_config(
    self, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that missing config file returns default configuration."""
    missing_file = tmp_path / "nonexistent.yaml"

    with caplog.at_level(logging.WARNING):
        config = LatchIdentificationConfig.load_from_yaml(missing_file)

    assert list(config.patterns) == DEFAULT_SEQUENTIAL_PATTERNS
    assert config.case_sensitive is False
    assert "missing" in caplog.text.lower() or "not found" in caplog.text.lower()
```

---

## Integration with Future Components

This configuration will be consumed by the Latch Detector Service (E01-F04-T02):

```python
# Future implementation in E01-F04-T02
import fnmatch

class LatchDetectorService:
    def __init__(self, config: LatchIdentificationConfig):
        self.config = config

    def is_sequential(self, cell_type: str) -> bool:
        """Check if a cell type matches any sequential pattern."""
        check_type = cell_type if self.config.case_sensitive else cell_type.upper()

        for pattern in self.config.patterns:
            check_pattern = pattern if self.config.case_sensitive else pattern.upper()
            if fnmatch.fnmatch(check_type, check_pattern):
                return True

        return False
```

Usage in application:

```python
from ink.infrastructure.config import LatchIdentificationConfig

# At application startup
config = LatchIdentificationConfig.load_from_yaml(Path("config/latch_patterns.yaml"))
detector = LatchDetectorService(config)

# During graph construction
if detector.is_sequential("DFFR_X1"):
    cell.is_sequential = True  # Mark as expansion boundary
```

---

## Conclusion

This implementation provides:

1. **User-Friendly Configuration**: YAML file with extensive comments
2. **Robustness**: Graceful fallback for all error cases
3. **Immutability**: Frozen dataclass + tuple storage
4. **Testability**: 26 comprehensive tests covering all scenarios
5. **Extensibility**: Easy to add new patterns or features

The configuration system is the foundation for the latch detection feature, enabling Ink to work with any cell library without code modifications.
