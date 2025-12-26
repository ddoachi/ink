# Ink - Incremental Schematic Viewer

## Project Overview

Ink is a GUI tool for schematic exploration targeting gate-level netlists. It uses an incremental exploration model starting from user-selected points instead of full schematic rendering, designed to minimize rendering overhead and maximize analysis efficiency in large-scale netlists.

## Tech Stack

- **Language:** Python 3.10+
- **UI Framework:** PySide6 (Qt6)
- **Platform:** Linux
- **Architecture:** Domain-Driven Design (DDD) with Clean Architecture
- **Graph Library:** NetworkX (MVP), rustworkx (performance optimization)
- **Layout:** Sugiyama algorithm (hierarchical) via grandalf or custom
- **CDL Parser:** Custom (SPICE-like CDL netlist format)
- **TCL:** Embedded interpreter (tkinter.Tcl or tclpy)

## Architecture

Ink follows **Domain-Driven Design (DDD)** with a **Clean/Hexagonal Architecture**. See [Architecture Documentation](docs/architecture/README.md) for details.

### Layer Structure

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                                   │
│                    (PySide6 UI Components)                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                         APPLICATION LAYER                                    │
│                    (Use Cases & Services)                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                          DOMAIN LAYER                                        │
│              (Entities, Value Objects, Domain Services)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                       INFRASTRUCTURE LAYER                                   │
│              (Parsers, Persistence, External Adapters)                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Bounded Contexts

- **Netlist Context**: CDL parsing, graph building, latch detection
- **Schematic Context**: Symbol rendering, layout, net routing
- **Exploration Context**: Expand/collapse, state management, undo/redo
- **Query Context**: Search engine, indexing, navigation

## Project Structure (DDD)

```
ink/
├── src/
│   └── ink/
│       ├── __init__.py
│       ├── main.py                    # Application entry point
│       │
│       ├── domain/                    # DOMAIN LAYER (no external dependencies)
│       │   ├── __init__.py
│       │   ├── model/                 # Entities and Aggregates
│       │   │   ├── design.py          # Design aggregate root
│       │   │   ├── cell.py            # Cell entity
│       │   │   ├── pin.py             # Pin entity
│       │   │   ├── net.py             # Net entity
│       │   │   ├── port.py            # Port entity
│       │   │   └── subcircuit.py      # Subcircuit entity
│       │   ├── value_objects/         # Immutable value objects
│       │   │   ├── pin_direction.py   # PinDirection enum
│       │   │   ├── position.py        # Position, BoundingBox
│       │   │   └── identifiers.py     # CellId, NetId, PinId, etc.
│       │   ├── services/              # Domain service INTERFACES
│       │   │   ├── graph_traverser.py # GraphTraverser protocol
│       │   │   ├── layout_engine.py   # LayoutEngine protocol
│       │   │   └── net_router.py      # NetRouter protocol
│       │   ├── events/                # Domain events
│       │   │   └── domain_events.py
│       │   └── repositories/          # Repository INTERFACES
│       │       ├── design_repository.py
│       │       └── session_repository.py
│       │
│       ├── application/               # APPLICATION LAYER
│       │   ├── __init__.py
│       │   ├── services/              # Application services (use cases)
│       │   │   ├── expansion_service.py
│       │   │   ├── selection_service.py
│       │   │   ├── search_service.py
│       │   │   └── file_service.py
│       │   ├── commands/              # Command handlers
│       │   │   ├── expand_command.py
│       │   │   └── collapse_command.py
│       │   └── queries/               # Query handlers
│       │       ├── search_query.py
│       │       └── property_query.py
│       │
│       ├── infrastructure/            # INFRASTRUCTURE LAYER
│       │   ├── __init__.py
│       │   ├── parsing/               # File parsers
│       │   │   ├── cdl_parser.py
│       │   │   └── pindir_parser.py
│       │   ├── graph/                 # Graph library adapters
│       │   │   └── networkx_adapter.py
│       │   ├── layout/                # Layout implementations
│       │   │   └── sugiyama_engine.py
│       │   ├── routing/               # Net routing
│       │   │   └── orthogonal_router.py
│       │   ├── persistence/           # Storage implementations
│       │   │   ├── json_session_store.py
│       │   │   └── qsettings_store.py
│       │   └── search/                # Search index
│       │       └── trie_index.py
│       │
│       └── presentation/              # PRESENTATION LAYER (PySide6)
│           ├── __init__.py
│           ├── app.py                 # Composition root
│           ├── main_window.py
│           ├── canvas/
│           │   ├── schematic_canvas.py
│           │   ├── cell_item.py
│           │   ├── pin_item.py
│           │   └── net_item.py
│           ├── panels/
│           │   ├── property_panel.py
│           │   ├── hierarchy_panel.py
│           │   └── search_panel.py
│           └── dialogs/
│               └── expansion_settings.py
│
├── tests/                             # Test files mirroring src/ structure
│   ├── unit/
│   │   ├── domain/                    # Pure unit tests
│   │   └── application/               # Mock domain services
│   ├── integration/
│   │   └── infrastructure/            # Real external libs
│   └── ui/                            # Qt widget tests
│
├── docs/
│   ├── prd.md                         # Product Requirements Document
│   └── architecture/                  # Architecture Documentation
│       ├── README.md                  # Architecture overview
│       ├── system-overview.md         # High-level system architecture
│       ├── ddd-architecture.md        # DDD structure and bounded contexts
│       ├── layer-architecture.md      # Layered architecture details
│       ├── data-flow.md               # Data flow diagrams
│       └── components.md              # Component specifications
│
├── specs/                             # Feature specifications
├── examples/                          # Sample .ckt files for testing
├── pyproject.toml                     # Project configuration
└── CLAUDE.md                          # This file
```

## Development Guidelines

### Architecture Rules

**Dependency Direction**: Dependencies flow inward only.

```
Presentation → Application → Domain ← Infrastructure
```

| Layer | Can Import | Cannot Import |
|-------|-----------|---------------|
| Domain | Nothing (pure Python) | Application, Infrastructure, Presentation |
| Application | Domain | Infrastructure, Presentation |
| Infrastructure | Domain (interfaces) | Application, Presentation |
| Presentation | Application | Domain (use Application), Infrastructure |

### Code Style

- Follow PEP 8 with 100 character line limit
- Use type hints for all function signatures
- Use dataclasses for domain models (immutable where possible)
- Use `Protocol` for domain service interfaces
- Prefer composition over inheritance

### Naming Conventions

- Classes: `PascalCase` (e.g., `SchematicCanvas`, `CDLParser`)
- Functions/methods: `snake_case` (e.g., `expand_fanout`, `get_connected_pins`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_HOP_COUNT`)
- Private methods: prefix with `_` (e.g., `_build_graph`)
- Domain Events: Past tense nouns (e.g., `CellsExpanded`, `DesignLoaded`)
- Value Objects: Immutable, use `@dataclass(frozen=True)`

### Testing Strategy

| Layer | Test Type | Dependencies |
|-------|-----------|--------------|
| Domain | Unit | None (pure functions) |
| Application | Unit + Integration | Mock domain services |
| Infrastructure | Integration | Real external libs |
| Presentation | UI/Widget | Mock application services |

### Git Workflow

- Branch naming: `feat/`, `fix/`, `refactor/`, `docs/`
- Use inline backticks in commit messages for code references (e.g., "Add `CDLParser` class")
- Keep commits focused and atomic

## Key Domain Concepts

### Ubiquitous Language

| Term | Definition |
|------|------------|
| **Cell** | Gate-level instance (e.g., `AND2_X1`, `DFFR_X1`) |
| **Pin** | Connection point on a cell (INPUT, OUTPUT, INOUT) |
| **Port** | Top-level I/O of the design |
| **Net** | Wire connecting multiple pins |
| **Fanout** | Cells driven by a signal (downstream) |
| **Fanin** | Cells driving a signal (upstream) |
| **Latch/FF** | Sequential element (expansion boundary) |
| **Expansion** | Revealing connected cells |
| **Collapse** | Hiding previously expanded cells |
| **Hop** | One level of connection |

### Aggregates

- **Design**: Root aggregate containing cells, nets, ports
- **ExpansionState**: Manages visible cells and undo/redo history

### Domain Services

- **GraphTraverser**: Fanin/fanout queries
- **LayoutEngine**: Sugiyama layout computation
- **NetRouter**: Orthogonal net routing

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

## Architecture Documentation

See [docs/architecture/](docs/architecture/README.md) for detailed architecture documentation:

- [System Overview](docs/architecture/system-overview.md) - High-level architecture
- [DDD Architecture](docs/architecture/ddd-architecture.md) - Bounded contexts and aggregates
- [Layer Architecture](docs/architecture/layer-architecture.md) - Dependency rules
- [Data Flow](docs/architecture/data-flow.md) - Operation flow diagrams
- [Components](docs/architecture/components.md) - Component specifications
