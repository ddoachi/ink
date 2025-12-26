# Ink - Incremental Schematic Viewer

## Project Overview

Ink is a GUI tool for schematic exploration targeting gate-level netlists. It uses an incremental exploration model starting from user-selected points instead of full schematic rendering, designed to minimize rendering overhead and maximize analysis efficiency in large-scale netlists.

## Tech Stack

- **Language:** Python 3.10+
- **UI Framework:** PySide6 (Qt6)
- **Platform:** Linux
- **Graph Library:** NetworkX (MVP), rustworkx (performance optimization)
- **Layout:** Sugiyama algorithm (hierarchical) via grandalf or custom
- **CDL Parser:** Custom (SPICE-like CDL netlist format)
- **TCL:** Embedded interpreter (tkinter.Tcl or tclpy)

## Project Structure

```
ink/
├── src/
│   └── ink/
│       ├── __init__.py
│       ├── main.py              # Application entry point
│       ├── core/                # Core data models and graph logic
│       │   ├── __init__.py
│       │   ├── parser/          # Gate-level CDL (.ckt) parsing
│       │   ├── graph/           # Graph data structure and queries
│       │   ├── layout/          # Sugiyama layout algorithm
│       │   └── models/          # Cell, Pin, Port, Net models
│       ├── ui/                  # PySide6 UI components
│       │   ├── __init__.py
│       │   ├── main_window.py   # Main application window
│       │   ├── canvas/          # Schematic canvas and rendering
│       │   ├── widgets/         # Reusable UI widgets
│       │   ├── dialogs/         # Settings and expansion dialogs
│       │   └── panels/          # Property panel, search panel
│       └── services/            # Business logic services
│           ├── __init__.py
│           ├── expansion/       # Incremental expansion logic
│           ├── routing/         # Orthogonal net routing
│           ├── search/          # Search and navigation
│           └── tcl/             # Embedded TCL interpreter (P1)
├── tests/                       # Test files mirroring src/ structure
├── docs/
│   └── prd.md                   # Product Requirements Document
├── examples/                    # Sample .ckt files for testing
├── pyproject.toml               # Project configuration (uv/poetry)
└── CLAUDE.md                    # This file
```

## Development Guidelines

### Code Style

- Follow PEP 8 with 100 character line limit
- Use type hints for all function signatures
- Use dataclasses or Pydantic models for data structures
- Prefer composition over inheritance

### Naming Conventions

- Classes: `PascalCase` (e.g., `SchematicCanvas`, `NetlistParser`)
- Functions/methods: `snake_case` (e.g., `expand_fanout`, `get_connected_pins`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_HOP_COUNT`)
- Private methods: prefix with `_` (e.g., `_build_graph`)

### Testing

- Use `pytest` for testing
- Test files should mirror source structure: `src/ink/core/parser/` → `tests/core/parser/`
- Aim for high coverage on core graph logic and parsing

### Git Workflow

- Branch naming: `feat/`, `fix/`, `refactor/`, `docs/`
- Use inline backticks in commit messages for code references (e.g., "Add `NetlistParser` class")
- Keep commits focused and atomic

## Key Concepts

### Internal Data Model

- **Cell**: Gate-level instance with input/output pins (e.g., `AND2_X1`, `INV_X1`)
- **Pin**: Connection point on a cell (input/output direction)
- **Port**: Top-level I/O of the design
- **Net**: Connection between pins/ports (represented as graph edges)
- **Latch**: Level-sensitive sequential element (used as semantic boundary)

### Incremental Expansion

- **Hop-based**: Expand N levels of fanin/fanout from selected object
- **Semantic boundary**: Expand until reaching latch or I/O port (P1)

### Layout & Rendering

- **Sugiyama algorithm**: Hierarchical layout with left-to-right signal flow
- **Orthogonal routing**: All nets use right-angle connections only
- **Level of Detail**: Bounding boxes when zoomed out, full details when zoomed in

## Commands

```bash
# Install dependencies
uv sync  # or: pip install -e .

# Run application
uv run python -m ink  # or: python -m ink

# Run tests
uv run pytest  # or: pytest

# Run tests with coverage
uv run pytest --cov=src/ink

# Type checking
uv run mypy src/

# Linting
uv run ruff check src/
```

## P0 MVP Features

1. Netlist parsing (gate-level CDL `.ckt`) and graph construction
2. Basic schematic rendering with Sugiyama layout
3. Orthogonal net routing
4. Hop-based incremental expansion (double-click)
5. Collapse functionality
6. Object selection and property display
7. Search and navigation
8. Undo/redo for expansion/collapse
9. Keyboard shortcuts
10. Zoom-based level of detail

## Future Features

- **P1:** Semantic boundary expansion, TCL integration (embedded), session save/load, image export, theming
- **P2:** Path highlighting, clock tree view, expansion history, annotations, cross-probing
