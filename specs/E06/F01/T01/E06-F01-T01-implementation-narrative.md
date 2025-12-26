# E06-F01-T01: QMainWindow Setup - Implementation Narrative

## Spec Reference
[E06-F01-T01.spec.md](./E06-F01-T01.spec.md)

---

## 1. Executive Summary

This document tells the story of implementing the foundational `InkMainWindow` class for the Ink schematic viewer application. The implementation followed a strict TDD (Test-Driven Development) workflow with TypeScript-level strict type checking, establishing patterns that will be used throughout the codebase.

**Key Outcomes:**
- Created presentation layer foundation with `InkMainWindow`
- Established Python project structure with strict typing
- Wrote 13 comprehensive tests covering all acceptance criteria
- Set up quality tooling (pytest, mypy, pyright, ruff)

---

## 2. Problem Context

### 2.1 What Problem Are We Solving?

Ink is a schematic viewer for gate-level netlists. Before we can display schematics, search components, or navigate hierarchies, we need a window to host the UI. The `InkMainWindow` serves as this foundational container.

### 2.2 Why Is This the First Task?

The presentation layer follows a bottom-up approach:
1. **E06-F01-T01** (this task): Create the window shell
2. **E06-F01-T02**: Add the schematic canvas as central widget
3. **E06-F01-T03**: Add dock widgets (hierarchy, properties panels)
4. **E06-F01-T04**: Wire everything into `main.py`

This order ensures each task has a stable foundation to build on.

---

## 3. Technical Requirements Analysis

### 3.1 From Spec to Implementation

The spec defined clear requirements:

| Requirement | Spec Section | Implementation |
|-------------|--------------|----------------|
| Window title | 2.1, 2.2 | `self.setWindowTitle("Ink - Incremental Schematic Viewer")` |
| Default size 1600x900 | 2.2, 2.3 | `self.resize(1600, 900)` |
| Minimum size 1024x768 | 2.2, 2.3 | `self.setMinimumSize(QSize(1024, 768))` |
| Standard decorations | 2.1 | Explicit `setWindowFlags()` call |

### 3.2 Why These Values?

**1600x900 Default Size:**
```
┌─────────────────────────────────────────────────────────┐
│                    1920px (1080p display)               │
│  ┌───────────────────────────────────────────────────┐  │
│  │                                                   │  │
│  │              1600px Window Width                  │  │
│  │                                                   │  │
│  │              (leaves 320px for other windows)     │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│  [           Taskbar (typically 40-60px)            ]   │
└─────────────────────────────────────────────────────────┘
                       900px
                       Height
```

**1024x768 Minimum Size:**
- Below this, UI elements become too cramped
- Property panel text becomes unreadable
- Hierarchy tree becomes too narrow
- Standard minimum for professional tools

---

## 4. Implementation Walkthrough

### 4.1 Project Structure Created

```
ink/
├── pyproject.toml              # Project config with strict typing
├── README.md                   # Project overview
├── src/
│   └── ink/
│       ├── __init__.py         # Package: __version__ = "0.1.0"
│       └── presentation/
│           ├── __init__.py     # Presentation layer package
│           └── main_window.py  # ⭐ InkMainWindow class
└── tests/
    ├── __init__.py
    ├── conftest.py             # Qt fixtures, offscreen mode
    └── unit/
        └── presentation/
            └── test_main_window.py  # 13 test cases
```

### 4.2 The InkMainWindow Class

```python
# src/ink/presentation/main_window.py

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QMainWindow


class InkMainWindow(QMainWindow):
    """Main application window shell for Ink schematic viewer."""

    # Class-level constants make requirements explicit
    _WINDOW_TITLE: str = "Ink - Incremental Schematic Viewer"
    _DEFAULT_WIDTH: int = 1600
    _DEFAULT_HEIGHT: int = 900
    _MIN_WIDTH: int = 1024
    _MIN_HEIGHT: int = 768

    def __init__(self) -> None:
        super().__init__()
        self._setup_window()

    def _setup_window(self) -> None:
        """Configure main window properties."""
        # 1. Window title for identification
        self.setWindowTitle(self._WINDOW_TITLE)

        # 2. Default size for 1080p displays
        self.resize(self._DEFAULT_WIDTH, self._DEFAULT_HEIGHT)

        # 3. Minimum size to prevent unusable layouts
        self.setMinimumSize(QSize(self._MIN_WIDTH, self._MIN_HEIGHT))

        # 4. Explicit window flags for consistent decorations
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
```

### 4.3 Code Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Startup                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  window = InkMainWindow()                                        │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ __init__(self)                                               ││
│  │   └─► super().__init__()  # Initialize QMainWindow           ││
│  │   └─► _setup_window()     # Configure properties             ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  _setup_window(self)                                             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 1. setWindowTitle("Ink - Incremental Schematic Viewer")      ││
│  │ 2. resize(1600, 900)                                         ││
│  │ 3. setMinimumSize(QSize(1024, 768))                          ││
│  │ 4. setWindowFlags(Window | TitleHint | SystemMenu | ...)     ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  window.show()  # Future: called from main.py                    │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Qt creates native window with:                               ││
│  │   - Title bar: "Ink - Incremental Schematic Viewer"          ││
│  │   - Size: 1600x900 pixels                                    ││
│  │   - Min size enforced: 1024x768                              ││
│  │   - Decorations: [_][□][X] buttons                           ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. TDD Workflow in Practice

### 5.1 Phase 1: RED (Tests Fail)

First, we wrote tests before any implementation existed:

```python
# tests/unit/presentation/test_main_window.py

def test_window_title_is_set_correctly(self, qtbot: QtBot) -> None:
    """Test window title matches spec requirement."""
    window = InkMainWindow()
    qtbot.addWidget(window)
    assert window.windowTitle() == "Ink - Incremental Schematic Viewer"
```

Running tests at this point:
```
$ uv run pytest tests/
ImportError: cannot import name 'InkMainWindow' from 'ink.presentation.main_window'
```

**Result**: Tests fail because module doesn't exist. ✅ This is correct TDD behavior.

### 5.2 Phase 2: GREEN (Tests Pass)

We implemented just enough code to make tests pass:

```python
# src/ink/presentation/main_window.py
class InkMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ink - Incremental Schematic Viewer")
        self.resize(1600, 900)
        self.setMinimumSize(QSize(1024, 768))
        # ... window flags
```

Running tests:
```
$ uv run pytest tests/ -v
13 passed in 0.03s
```

**Result**: All 13 tests pass. ✅

### 5.3 Phase 3: REFACTOR (Clean Up)

We added comprehensive documentation and ran quality checks:

```
$ uv run mypy src/ tests/
Success: no issues found in 8 source files

$ uv run pyright src/ tests/
0 errors, 0 warnings, 0 informations

$ uv run ruff check src/ tests/
All checks passed!
```

**Result**: Code is clean, well-typed, and documented. ✅

---

## 6. Strict Type Checking Configuration

### 6.1 TypeScript Equivalency

We configured Python type checking to be as strict as TypeScript's `--strict` flag:

| TypeScript Flag | Python Equivalent | Configuration |
|-----------------|-------------------|---------------|
| `noImplicitAny` | `disallow_any_*` | mypy: `disallow_any_generics = true` |
| `strictNullChecks` | `reportOptional*` | pyright: `reportOptionalMemberAccess = "error"` |
| `noImplicitReturns` | `reportReturnType` | pyright: `reportReturnType = "error"` |
| `strictFunctionTypes` | strict mode | Both: enabled by default in strict |

### 6.2 Why Both mypy and pyright?

```
┌─────────────────────────────────────────────────────────────────┐
│                    Type Checking Strategy                        │
├─────────────────────────────────────────────────────────────────┤
│  mypy                        │  pyright                         │
│  ─────────────────────────   │  ─────────────────────────────   │
│  • Industry standard         │  • Faster execution              │
│  • More mature               │  • Powers VS Code Pylance        │
│  • Better plugin ecosystem   │  • Stricter by default           │
│  • CI/CD integration         │  • Better incremental checks     │
└─────────────────────────────────────────────────────────────────┘
                    │
                    ▼
         Using both catches more issues
```

---

## 7. Qt Testing Strategy

### 7.1 The Display Problem

Qt widgets require a display server (X11, Wayland, or Windows desktop). In CI environments, there's no display. We solved this with:

```python
# tests/conftest.py
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

This tells Qt to use an offscreen rendering backend, allowing tests to run without a display.

### 7.2 pytest-qt Integration

The `pytest-qt` plugin provides:

1. **qtbot fixture**: Manages widget lifecycle
   ```python
   def test_window(self, qtbot: QtBot) -> None:
       window = InkMainWindow()
       qtbot.addWidget(window)  # Ensures cleanup after test
   ```

2. **Signal handling**: Wait for Qt signals (future use)
3. **Exception capture**: Catches Qt exceptions properly

---

## 8. Patterns Established for Future Tasks

### 8.1 Class Structure Pattern

```python
class InkSomeWidget(QWidget):
    # 1. Class constants for configuration
    _SOME_CONFIG: str = "value"

    def __init__(self) -> None:
        super().__init__()
        self._setup_widget()  # 2. Delegate to setup method

    def _setup_widget(self) -> None:
        """Configure widget properties."""
        pass  # 3. All setup logic here
```

### 8.2 Test Structure Pattern

```python
class TestSomeWidgetBehavior:
    """Tests for specific behavior category."""

    def test_specific_behavior(self, qtbot: QtBot) -> None:
        """Test one specific thing.

        Verifies:
        - What is being tested
        """
        widget = SomeWidget()
        qtbot.addWidget(widget)
        assert widget.some_property == expected_value
```

### 8.3 Documentation Pattern

```python
"""Module docstring explaining purpose.

Design Decisions:
    - Why we made certain choices
    - What alternatives we considered

See Also:
    - Related specs and documentation
"""
```

---

## 9. Lessons Learned

### 9.1 What Went Well

1. **TDD caught design issues early**: Writing tests first forced us to think about the API
2. **Strict typing found bugs**: Pyright caught an unused import immediately
3. **Comprehensive tests give confidence**: 13 tests covering all acceptance criteria

### 9.2 Challenges Overcome

1. **Qt offscreen mode**: Initial tests failed without display; solved with `QT_QPA_PLATFORM=offscreen`
2. **Package discovery**: Hatch needed `src/ink/__init__.py` before `uv sync` would work
3. **Deprecated ruff rules**: Removed `ANN101`/`ANN102` which no longer exist

### 9.3 Recommendations for Future Tasks

1. **Always run quality checks**: mypy + pyright + ruff before committing
2. **Set up conftest.py early**: Qt offscreen mode must be set before any Qt imports
3. **Use class constants**: Makes requirements explicit and testable

---

## 10. Files Reference

### Implementation Files

| File | Lines | Purpose |
|------|-------|---------|
| `src/ink/presentation/main_window.py` | 111 | InkMainWindow class |
| `src/ink/__init__.py` | 3 | Package with version |
| `src/ink/presentation/__init__.py` | 1 | Presentation layer package |

### Test Files

| File | Lines | Purpose |
|------|-------|---------|
| `tests/unit/presentation/test_main_window.py` | 128 | 13 test cases |
| `tests/conftest.py` | 38 | Qt fixtures, offscreen config |

### Configuration Files

| File | Lines | Purpose |
|------|-------|---------|
| `pyproject.toml` | 225 | Project config, strict typing |
| `README.md` | 27 | Project overview |

---

## 11. Next Steps

This implementation enables the following tasks:

1. **E06-F01-T02**: Add `SchematicCanvas` as central widget
   ```python
   self.setCentralWidget(SchematicCanvas())
   ```

2. **E06-F01-T03**: Add dock widgets
   ```python
   self.addDockWidget(Qt.LeftDockWidgetArea, HierarchyPanel())
   ```

3. **E06-F01-T04**: Create `main.py` entry point
   ```python
   app = QApplication(sys.argv)
   window = InkMainWindow()
   window.show()
   sys.exit(app.exec())
   ```

---

## 12. Appendix: Full Test Output

```
$ uv run pytest tests/ -v
============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.2, pluggy-1.6.0
PySide6 6.10.1 -- Qt runtime 6.10.1 -- Qt compiled 6.10.1
rootdir: /home/joohan/dev/project-ink/worktrees/E06-F01-T01-QMainWindow-Setup
configfile: pyproject.toml
plugins: cov-7.0.0, qt-4.5.0
collected 13 items

tests/unit/presentation/test_main_window.py::TestInkMainWindowCreation::test_main_window_can_be_created PASSED [  7%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowCreation::test_main_window_is_qmainwindow_subclass PASSED [ 15%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowTitle::test_window_title_is_set_correctly PASSED [ 23%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowSize::test_window_default_width_is_1600 PASSED [ 30%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowSize::test_window_default_height_is_900 PASSED [ 38%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowSize::test_window_minimum_width_is_1024 PASSED [ 46%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowSize::test_window_minimum_height_is_768 PASSED [ 53%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowSize::test_window_cannot_be_resized_below_minimum PASSED [ 61%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowFlags::test_window_has_title_hint PASSED [ 69%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowFlags::test_window_has_system_menu_hint PASSED [ 76%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowFlags::test_window_has_minimize_button_hint PASSED [ 84%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowFlags::test_window_has_maximize_button_hint PASSED [ 92%]
tests/unit/presentation/test_main_window.py::TestInkMainWindowFlags::test_window_has_close_button_hint PASSED [100%]

============================== 13 passed in 0.03s ==============================
```
