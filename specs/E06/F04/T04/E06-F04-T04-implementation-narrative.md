# E06-F04-T04: File and Object Count Display - Implementation Narrative

## Overview

This document tells the complete story of implementing file name and object count display in the Ink schematic viewer's status bar. Following test-driven development (TDD), we built a system that shows users which file is loaded and how many cells/nets are currently visible.

---

## Chapter 1: Understanding the Requirements

### The User's Need

When working with schematic files, users need to answer two questions at a glance:

1. **"What file am I looking at?"** - Especially important when working with multiple designs
2. **"How much of the circuit is visible?"** - Important for understanding exploration scope

The status bar provides the perfect location for this information - always visible, unobtrusive, and contextual.

### Requirements Analysis

From spec E06-F04-T04, we identified these key requirements:

| Requirement | Design Decision |
|-------------|-----------------|
| Show current file name | Display base name only ("design.ckt" not full path) |
| Access full path | Store in tooltip for hover access |
| No file state | Show "No file loaded" placeholder |
| Show cell count | Format as "Cells: N" |
| Show net count | Format as "/ Nets: M" |
| Real-time updates | Connect to expansion service signals |

---

## Chapter 2: The TDD Journey

### Phase 1: RED - Writing Failing Tests

Following TDD, we started by writing tests that described the behavior we wanted:

```python
# Test for file status with path
def test_update_file_status_shows_basename(self, main_window):
    """Given a full path, only show the base name."""
    file_path = "/home/user/project/design.ckt"
    main_window.update_file_status(file_path)
    assert main_window.file_label.text() == "File: design.ckt"
```

We created 33 tests covering:
- Method existence and signatures
- Text formatting for various inputs
- Tooltip behavior
- Edge cases (unicode, spaces, long names)
- Object count formatting
- Expansion state handling
- Missing service graceful handling

**Initial test run**: 29 failures, 4 passes (initial state tests)

### Phase 2: GREEN - Making Tests Pass

We implemented three new methods in `InkMainWindow`:

#### 1. update_file_status() - File Name Display

```python
def update_file_status(self, file_path: str | None) -> None:
    """Update file name in status bar."""
    if file_path:
        # Extract base name using pathlib for cross-platform compatibility
        file_name = Path(file_path).name
        self.file_label.setText(f"File: {file_name}")
        self.file_label.setToolTip(file_path)  # Full path on hover
    else:
        self.file_label.setText("No file loaded")
        self.file_label.setToolTip("")
```

**Why pathlib.Path?**
- Cross-platform: Works correctly on Windows, Linux, and macOS
- Unicode-safe: Handles international characters in filenames
- Clean API: `.name` property extracts just the filename

#### 2. update_object_count_status() - Cell/Net Counts

```python
def update_object_count_status(self, cell_count: int, net_count: int) -> None:
    """Update visible object counts in status bar."""
    self.object_count_label.setText(f"Cells: {cell_count} / Nets: {net_count}")
```

Simple and direct - the format matches user expectations from the spec.

#### 3. _update_view_counts() - Query Expansion State

```python
def _update_view_counts(self) -> None:
    """Query and update visible object counts from expansion state."""
    if hasattr(self, "expansion_state") and self.expansion_state:
        cell_count = len(self.expansion_state.visible_cells)
        net_count = len(self.expansion_state.visible_nets)
        self.update_object_count_status(cell_count, net_count)
    else:
        self.update_object_count_status(0, 0)
```

**Why defensive hasattr() checks?**
- The expansion_state may not exist during early development
- After file close, expansion_state might be None
- Allows the UI to work even when services aren't fully integrated

### Phase 3: REFACTOR - Clean Code

The code was already clean from following existing patterns:
- Consistent docstring style matching `update_zoom_status()`
- Same defensive programming patterns
- Comprehensive inline comments explaining "why"

---

## Chapter 3: Signal Architecture

### The Signal Flow

The status bar updates are event-driven using Qt's signal-slot mechanism:

```
┌─────────────────┐                        ┌────────────────────┐
│   File opened   │                        │  Status bar shows  │
│   by user       │                        │  "File: name.ckt"  │
└────────┬────────┘                        └────────────────────┘
         │                                          ▲
         ▼                                          │
┌─────────────────┐    file_loaded signal   ┌──────┴───────────┐
│   FileService   │─────────────────────────│ update_file_status│
└─────────────────┘                         └──────────────────┘


┌─────────────────┐                        ┌────────────────────┐
│   User expands  │                        │  Status bar shows  │
│   a cell        │                        │ "Cells: 5/Nets: 8" │
└────────┬────────┘                        └────────────────────┘
         │                                          ▲
         ▼                                          │
┌─────────────────┐    view_changed signal  ┌──────┴───────────┐
│ExpansionService │─────────────────────────│_update_view_counts│
└─────────────────┘                         └──────────────────┘
```

### Signal Connection Code

We extended `_connect_status_signals()` to handle the new signals:

```python
def _connect_status_signals(self) -> None:
    # ... existing zoom and selection connections ...

    # Connect file service signals (E06-F04-T04)
    if hasattr(self, "file_service"):
        service = self.file_service
        if hasattr(service, "file_loaded"):
            service.file_loaded.connect(self.update_file_status)
        if hasattr(service, "file_closed"):
            service.file_closed.connect(lambda: self.update_file_status(None))

    # Connect expansion service signal (E06-F04-T04)
    if hasattr(self, "expansion_service"):
        service = self.expansion_service
        if hasattr(service, "view_changed"):
            service.view_changed.connect(self._update_view_counts)
```

**Key Design Choices:**
- `hasattr()` checks allow graceful handling of missing services
- Lambda for `file_closed` provides None parameter
- Same defensive pattern as existing selection_service connection

---

## Chapter 4: Edge Cases and Robustness

### Unicode Filename Handling

```python
def test_update_file_status_unicode_filename(self, main_window):
    """File status should handle unicode characters in filename."""
    file_path = "/home/用户/项目/设计.ckt"
    main_window.update_file_status(file_path)
    assert main_window.file_label.text() == "File: 设计.ckt"
```

Python's pathlib handles unicode correctly, so no special code needed.

### Missing Expansion State

When no design is loaded or after file close, `expansion_state` might not exist:

```python
def test_update_view_counts_no_expansion_state(self, main_window):
    """Counts should be 0 when expansion_state is not available."""
    if hasattr(main_window, "expansion_state"):
        delattr(main_window, "expansion_state")
    main_window._update_view_counts()
    assert main_window.object_count_label.text() == "Cells: 0 / Nets: 0"
```

The implementation handles this with a simple `hasattr()` check.

### Large Object Counts

```python
def test_update_view_counts_large_sets(self, main_window):
    """Counts should handle large visible sets."""
    mock_state = Mock()
    mock_state.visible_cells = {f"cell{i}" for i in range(5000)}
    mock_state.visible_nets = {f"net{i}" for i in range(7500)}
    main_window.expansion_state = mock_state

    main_window._update_view_counts()
    assert main_window.object_count_label.text() == "Cells: 5000 / Nets: 7500"
```

Since `visible_cells` and `visible_nets` are Python sets, `len()` is O(1) - no performance concerns.

---

## Chapter 5: Integration Points

### Where This Fits in the Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   InkMainWindow                      │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌───────────────┐  │    │
│  │  │  file_label │ │ zoom_label  │ │object_count_  │  │    │
│  │  │             │ │             │ │    label      │  │    │
│  │  └─────────────┘ └─────────────┘ └───────────────┘  │    │
│  │           ▲              ▲              ▲           │    │
│  │           │              │              │           │    │
│  │   update_file_   update_zoom_  _update_view_       │    │
│  │   status()       status()      counts()            │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                    │              │              │
                    ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│  ┌─────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│  │ FileService │ │SchematicCanvas  │ │ExpansionService │    │
│  │file_loaded  │ │zoom_changed     │ │view_changed     │    │
│  │file_closed  │ │                 │ │                 │    │
│  └─────────────┘ └─────────────────┘ └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   ExpansionState                     │    │
│  │  visible_cells: set[str]   visible_nets: set[str]   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Dependencies

- **Upstream**: E06-F04-T01 (Status Bar Setup) provides the `file_label` and `object_count_label` widgets
- **Future Integration**:
  - E01-F02 (FileService) will emit `file_loaded`/`file_closed` signals
  - E03-F01 (ExpansionService) will emit `view_changed` signal
  - E01-F01 (Design Model) will provide `expansion_state`

---

## Chapter 6: Testing Strategy

### Test Organization

```
tests/unit/presentation/test_main_window_file_status.py
├── TestUpdateFileStatusMethodExists (3 tests)
│   └── Method existence and signature validation
├── TestUpdateFileStatusFormatting (4 tests)
│   └── Base name extraction, tooltips, extensions
├── TestUpdateFileStatusNoFile (3 tests)
│   └── None handling, placeholder text
├── TestUpdateFileStatusEdgeCases (3 tests)
│   └── Unicode, long names, spaces
├── TestUpdateObjectCountStatusMethodExists (2 tests)
│   └── Method existence and signature validation
├── TestUpdateObjectCountStatusFormatting (6 tests)
│   └── Count formatting, zeros, large numbers
├── TestUpdateObjectCountStatusUpdates (2 tests)
│   └── Sequential and immediate updates
├── TestUpdateViewCountsMethodExists (1 test)
│   └── Helper method existence
├── TestUpdateViewCountsBehavior (5 tests)
│   └── Expansion state handling
├── TestConnectStatusSignalsGracefulHandling (2 tests)
│   └── Missing service tolerance
└── TestCombinedStatusUpdates (2 tests)
    └── Independent update verification
```

### Mock Usage

For testing `_update_view_counts()`, we use Python's `unittest.mock.Mock`:

```python
from unittest.mock import Mock

def test_update_view_counts_with_expansion_state(self, main_window):
    mock_state = Mock()
    mock_state.visible_cells = {"cell1", "cell2", "cell3", "cell4", "cell5"}
    mock_state.visible_nets = {"net1", "net2", "net3"}
    main_window.expansion_state = mock_state

    main_window._update_view_counts()
    assert main_window.object_count_label.text() == "Cells: 5 / Nets: 3"
```

---

## Chapter 7: Lessons and Insights

### What Worked Well

1. **Following existing patterns** - The code style matches `update_zoom_status()` and `update_selection_status()`, making it easy to understand and maintain

2. **Defensive programming** - Using `hasattr()` checks allows the UI to work during incremental development

3. **TDD clarity** - Writing tests first forced us to think about all edge cases before implementation

4. **Separation of concerns** - File status and object counts are independent - updating one doesn't affect the other

### Architecture Principles Applied

1. **Single Responsibility**: Each method does one thing
   - `update_file_status()` - displays file name
   - `update_object_count_status()` - displays counts
   - `_update_view_counts()` - queries state and calls update

2. **Open for Extension**: New status displays can follow the same pattern
   - Add a new label in `_setup_status_bar()`
   - Add an update method
   - Connect to signals in `_connect_status_signals()`

3. **Dependency Inversion**: The UI doesn't depend on concrete services
   - Uses `hasattr()` to check for services
   - Will work with any service that has the expected signals

---

## Chapter 8: Future Considerations

### When Services Are Implemented

When FileService and ExpansionService are built:

1. The signals will automatically connect during `_connect_status_signals()`
2. No changes needed to the status bar code
3. The UI will start showing real file names and counts

### Potential Enhancements

| Enhancement | Consideration |
|-------------|---------------|
| Truncate long file names | Currently shows full name; widget width handles overflow |
| Click to reveal full path | Alternative to tooltip for accessibility |
| Count animation | Smooth transitions when counts change rapidly |
| Memory indicator | Show memory usage alongside counts |

---

## Conclusion

This implementation demonstrates clean TDD practices and robust Qt signal handling. The file and object count display enhances user awareness of their current context in the Ink schematic viewer, following the established patterns of the existing status bar infrastructure.

The defensive programming approach ensures the UI remains functional even as upstream services are still being developed, enabling parallel development across the team.
