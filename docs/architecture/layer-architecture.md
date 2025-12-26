# Layer Architecture

## 1. Overview

Ink follows a **Clean Architecture** / **Hexagonal Architecture** approach with four distinct layers. The key principle is that dependencies point inward, with the Domain layer at the center having no external dependencies.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                                                                  │
│    ┌─────────────────────────────────────────────────────────────────────────┐  │
│    │                        PRESENTATION LAYER                                │  │
│    │                                                                          │  │
│    │   PySide6 UI Components • Qt Signals/Slots • View Models                │  │
│    │                                                                          │  │
│    └──────────────────────────────────┬───────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│    ┌─────────────────────────────────────────────────────────────────────────┐  │
│    │                        APPLICATION LAYER                                 │  │
│    │                                                                          │  │
│    │   Use Cases • Application Services • Command/Query Handlers             │  │
│    │                                                                          │  │
│    └──────────────────────────────────┬───────────────────────────────────────┘  │
│                                       │                                          │
│                                       ▼                                          │
│    ┌─────────────────────────────────────────────────────────────────────────┐  │
│    │                          DOMAIN LAYER                                    │  │
│    │                                                                          │  │
│    │   Entities • Value Objects • Aggregates • Domain Services • Events      │  │
│    │                                                                          │  │
│    │   ★ NO EXTERNAL DEPENDENCIES ★                                          │  │
│    │                                                                          │  │
│    └──────────────────────────────────▲───────────────────────────────────────┘  │
│                                       │                                          │
│                                       │ implements                               │
│    ┌─────────────────────────────────────────────────────────────────────────┐  │
│    │                       INFRASTRUCTURE LAYER                               │  │
│    │                                                                          │  │
│    │   Parsers • Graph Adapters • Persistence • External Libraries           │  │
│    │                                                                          │  │
│    └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer Details

### 2.1 Domain Layer (Core)

**Location**: `src/ink/domain/`

**Responsibility**: Contains the business logic and domain model. This layer is the heart of the application and has **zero external dependencies**.

**Contents**:
```
domain/
├── model/              # Entities and Aggregates
│   ├── design.py       # Design aggregate root
│   ├── cell.py         # Cell entity
│   ├── pin.py          # Pin entity
│   ├── net.py          # Net entity
│   └── port.py         # Port entity
│
├── value_objects/      # Immutable value types
│   ├── pin_direction.py
│   ├── position.py
│   └── identifiers.py
│
├── services/           # Domain service INTERFACES
│   ├── graph_traverser.py    # Protocol/ABC only
│   ├── layout_engine.py      # Protocol/ABC only
│   └── net_router.py         # Protocol/ABC only
│
├── events/             # Domain events
│   └── domain_events.py
│
└── repositories/       # Repository INTERFACES
    ├── design_repository.py  # Protocol/ABC only
    └── session_repository.py # Protocol/ABC only
```

**Rules**:
- ✅ Pure Python (no external libraries except typing)
- ✅ Uses `Protocol` or `ABC` for interfaces
- ✅ Dataclasses or Pydantic for models
- ❌ No I/O operations
- ❌ No framework dependencies
- ❌ No infrastructure imports

**Example**:
```python
# domain/model/cell.py
from dataclasses import dataclass, field
from typing import List
from ink.domain.value_objects import CellId, CellType, Position
from ink.domain.model.pin import Pin


@dataclass
class Cell:
    """
    A gate-level cell instance in the netlist.

    Represents a single logic element (AND, OR, INV, DFF, etc.)
    with its pins and connectivity information.
    """
    id: CellId
    instance_name: str
    cell_type: CellType
    pins: List[Pin] = field(default_factory=list)
    is_sequential: bool = False
    position: Position = field(default_factory=Position)

    def get_input_pins(self) -> List[Pin]:
        """Return all input pins of this cell."""
        return [p for p in self.pins if p.direction.is_input]

    def get_output_pins(self) -> List[Pin]:
        """Return all output pins of this cell."""
        return [p for p in self.pins if p.direction.is_output]
```

---

### 2.2 Application Layer

**Location**: `src/ink/application/`

**Responsibility**: Orchestrates domain objects to fulfill use cases. Contains application services that coordinate between presentation and domain.

**Contents**:
```
application/
├── services/           # Application services
│   ├── expansion_service.py    # Handles expansion use cases
│   ├── selection_service.py    # Handles selection use cases
│   ├── search_service.py       # Handles search use cases
│   └── file_service.py         # Handles file operations
│
├── commands/           # Command handlers (write operations)
│   ├── expand_command.py
│   ├── collapse_command.py
│   └── load_design_command.py
│
├── queries/            # Query handlers (read operations)
│   ├── search_query.py
│   ├── fanout_query.py
│   └── property_query.py
│
└── dto/                # Data Transfer Objects
    ├── expansion_dto.py
    └── search_result_dto.py
```

**Rules**:
- ✅ Depends on Domain layer
- ✅ Orchestrates domain objects
- ✅ Defines DTOs for layer boundaries
- ❌ No direct UI dependencies
- ❌ No infrastructure implementation details

**Example**:
```python
# application/services/expansion_service.py
from typing import Set
from ink.domain.model import Cell, Pin
from ink.domain.services import GraphTraverser, LayoutEngine
from ink.domain.value_objects import CellId, Direction
from ink.domain.events import CellsExpanded


class ExpansionService:
    """
    Application service that handles expansion use cases.

    Coordinates between graph traversal, layout computation,
    and state management to implement the expand operation.
    """

    def __init__(
        self,
        graph_traverser: GraphTraverser,
        layout_engine: LayoutEngine,
        expansion_state: ExpansionState,
        event_bus: EventBus
    ):
        self._traverser = graph_traverser
        self._layout = layout_engine
        self._state = expansion_state
        self._events = event_bus

    def expand_fanout(self, pin: Pin, hops: int = 1) -> Set[Cell]:
        """
        Expand fanout from a pin.

        1. Query graph for downstream cells
        2. Filter already visible cells
        3. Compute layout for new cells
        4. Update expansion state
        5. Emit domain event
        """
        # Query graph (uses domain service)
        all_cells = self._traverser.get_fanout(pin, hops)

        # Filter already visible
        new_cells = {c for c in all_cells if not self._state.is_visible(c.id)}

        if not new_cells:
            return set()

        # Compute layout
        layout_result = self._layout.update_layout(
            self._state.current_layout,
            added_cells=new_cells
        )

        # Update state
        self._state.expand(new_cells)

        # Emit event
        self._events.publish(CellsExpanded(
            cells=frozenset(c.id for c in new_cells),
            origin=pin.cell.id,
            direction=Direction.FANOUT
        ))

        return new_cells
```

---

### 2.3 Infrastructure Layer

**Location**: `src/ink/infrastructure/`

**Responsibility**: Implements domain interfaces using external libraries and handles all I/O operations.

**Contents**:
```
infrastructure/
├── parsing/            # File parsers
│   ├── cdl_parser.py           # CDL netlist parser
│   └── pindir_parser.py        # Pin direction file parser
│
├── graph/              # Graph library adapters
│   ├── networkx_adapter.py     # NetworkX implementation
│   └── rustworkx_adapter.py    # rustworkx implementation (future)
│
├── layout/             # Layout algorithm implementations
│   ├── sugiyama_engine.py      # Sugiyama layout
│   └── grandalf_adapter.py     # grandalf library adapter
│
├── routing/            # Net routing implementations
│   └── orthogonal_router.py    # Orthogonal net router
│
├── persistence/        # Storage implementations
│   ├── json_session_store.py   # JSON session persistence
│   └── qsettings_store.py      # Qt settings persistence
│
└── search/             # Search index implementations
    └── trie_index.py           # Trie-based search index
```

**Rules**:
- ✅ Implements domain interfaces
- ✅ Uses external libraries (NetworkX, grandalf, etc.)
- ✅ Handles file I/O
- ✅ Depends on Domain layer interfaces
- ❌ Domain layer never imports from here

**Example**:
```python
# infrastructure/graph/networkx_adapter.py
import networkx as nx
from typing import Set, Dict, Callable
from ink.domain.services import GraphTraverser
from ink.domain.model import Cell, Pin, Net
from ink.domain.value_objects import CellId, Direction


class NetworkXGraphTraverser(GraphTraverser):
    """
    GraphTraverser implementation using NetworkX.

    Adapts NetworkX graph operations to the domain service interface,
    isolating the domain from NetworkX-specific concepts.
    """

    def __init__(self):
        self._graph = nx.DiGraph()
        self._cell_index: Dict[CellId, Cell] = {}

    def build_graph(self, cells: List[Cell], nets: List[Net]) -> None:
        """Build NetworkX graph from domain objects."""
        # Add cell nodes
        for cell in cells:
            self._graph.add_node(cell.id, cell=cell)
            self._cell_index[cell.id] = cell

        # Add edges based on net connectivity
        for net in nets:
            drivers = [p for p in net.connected_pins if p.direction.is_output]
            loads = [p for p in net.connected_pins if p.direction.is_input]

            for driver in drivers:
                for load in loads:
                    self._graph.add_edge(
                        driver.cell.id,
                        load.cell.id,
                        net=net
                    )

    def get_fanout(self, pin: Pin, hops: int = 1) -> Set[Cell]:
        """Get cells within N hops downstream using BFS."""
        result = set()
        current = {pin.cell.id}

        for _ in range(hops):
            next_level = set()
            for cell_id in current:
                for successor in self._graph.successors(cell_id):
                    if successor not in result:
                        next_level.add(successor)
                        result.add(successor)
            current = next_level

        return {self._cell_index[cid] for cid in result}
```

---

### 2.4 Presentation Layer

**Location**: `src/ink/presentation/`

**Responsibility**: User interface using PySide6 (Qt6). Receives user input, displays output, and communicates with Application layer.

**Contents**:
```
presentation/
├── main_window.py          # Main application window
├── app.py                  # Application bootstrap
│
├── canvas/                 # Schematic canvas components
│   ├── schematic_canvas.py     # Main canvas widget
│   ├── schematic_scene.py      # Qt Graphics Scene
│   ├── cell_item.py            # Cell visual item
│   ├── pin_item.py             # Pin visual item
│   └── net_item.py             # Net visual item
│
├── panels/                 # Dock panels
│   ├── property_panel.py       # Property inspector
│   ├── hierarchy_panel.py      # Design hierarchy tree
│   └── search_panel.py         # Search interface
│
├── dialogs/                # Modal dialogs
│   ├── open_file_dialog.py
│   └── expansion_settings.py
│
├── viewmodels/             # View models (MVVM pattern)
│   ├── canvas_viewmodel.py
│   ├── property_viewmodel.py
│   └── search_viewmodel.py
│
└── widgets/                # Reusable widgets
    ├── zoom_slider.py
    └── search_input.py
```

**Rules**:
- ✅ Depends on Application layer
- ✅ Uses PySide6 (Qt6)
- ✅ Translates user actions to application commands
- ✅ Subscribes to domain events for updates
- ❌ No business logic
- ❌ No direct domain manipulation

**Example**:
```python
# presentation/canvas/schematic_canvas.py
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Signal, Slot
from ink.application.services import ExpansionService, SelectionService
from ink.domain.events import CellsExpanded, SelectionChanged


class SchematicCanvas(QGraphicsView):
    """
    Main schematic visualization canvas.

    Handles user interactions (pan, zoom, selection, expansion)
    and renders schematic elements.
    """

    # Qt signals for UI events
    cell_double_clicked = Signal(str)  # cell_id
    selection_changed = Signal(list)   # selected_ids

    def __init__(
        self,
        expansion_service: ExpansionService,
        selection_service: SelectionService,
        parent=None
    ):
        super().__init__(parent)
        self._expansion = expansion_service
        self._selection = selection_service
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Subscribe to domain events
        self._expansion.events.subscribe(CellsExpanded, self._on_cells_expanded)
        self._selection.events.subscribe(SelectionChanged, self._on_selection_changed)

    def mouseDoubleClickEvent(self, event):
        """Handle double-click for expansion."""
        item = self.itemAt(event.pos())
        if isinstance(item, CellItem):
            # Delegate to application service
            self._expansion.expand_fanout(item.cell.get_output_pins()[0])

    @Slot()
    def _on_cells_expanded(self, event: CellsExpanded):
        """React to cells being expanded - update the view."""
        for cell_id in event.cells:
            cell = self._expansion.get_cell(cell_id)
            self._add_cell_to_scene(cell)

        self._update_net_routing()
```

---

## 3. Dependency Rules

### 3.1 Allowed Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DEPENDENCY MATRIX                                      │
│                                                                                  │
│                        Can depend on:                                            │
│                   ┌──────────┬──────────┬──────────┬──────────┐                 │
│                   │ Present. │ Applic.  │ Domain   │ Infra.   │                 │
│    ┌──────────────┼──────────┼──────────┼──────────┼──────────┤                 │
│    │ Presentation │    -     │    ✅    │    ❌    │    ❌    │                 │
│    ├──────────────┼──────────┼──────────┼──────────┼──────────┤                 │
│    │ Application  │    ❌    │    -     │    ✅    │    ❌    │                 │
│    ├──────────────┼──────────┼──────────┼──────────┼──────────┤                 │
│    │ Domain       │    ❌    │    ❌    │    -     │    ❌    │                 │
│    ├──────────────┼──────────┼──────────┼──────────┼──────────┤                 │
│    │ Infra.       │    ❌    │    ❌    │    ✅*   │    -     │                 │
│    └──────────────┴──────────┴──────────┴──────────┴──────────┘                 │
│                                                                                  │
│    * Infrastructure implements Domain interfaces                                 │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Import Rules by Layer

```python
# ✅ ALLOWED IMPORTS

# domain/ - Only standard library + typing
from dataclasses import dataclass
from typing import Protocol, List, Set
from enum import Enum

# application/ - Domain layer
from ink.domain.model import Cell, Pin, Net
from ink.domain.services import GraphTraverser
from ink.domain.events import CellsExpanded

# infrastructure/ - Domain interfaces + external libs
from ink.domain.services import GraphTraverser  # interface to implement
import networkx as nx                            # external library

# presentation/ - Application layer + Qt
from ink.application.services import ExpansionService
from PySide6.QtWidgets import QWidget
```

```python
# ❌ FORBIDDEN IMPORTS

# domain/ must NOT import:
from ink.infrastructure import ...  # NO!
from ink.application import ...     # NO!
from ink.presentation import ...    # NO!
import networkx                     # NO external libs!

# application/ must NOT import:
from ink.infrastructure import ...  # NO!
from ink.presentation import ...    # NO!

# presentation/ must NOT import:
from ink.domain import ...          # Use application layer instead
from ink.infrastructure import ...  # NO direct infrastructure access
```

---

## 4. Dependency Injection

Dependencies are wired together at application startup in a composition root:

```python
# presentation/app.py (Composition Root)
from ink.domain.services import GraphTraverser, LayoutEngine
from ink.infrastructure.graph import NetworkXGraphTraverser
from ink.infrastructure.layout import SugiyamaLayoutEngine
from ink.application.services import ExpansionService, SelectionService
from ink.presentation import MainWindow


def create_application():
    """
    Composition Root: Wire all dependencies together.

    This is the ONLY place where infrastructure implementations
    are connected to domain interfaces.
    """

    # Create infrastructure implementations
    graph_traverser: GraphTraverser = NetworkXGraphTraverser()
    layout_engine: LayoutEngine = SugiyamaLayoutEngine()

    # Create application services (inject domain service implementations)
    expansion_service = ExpansionService(
        graph_traverser=graph_traverser,
        layout_engine=layout_engine
    )

    selection_service = SelectionService()
    search_service = SearchService(graph_traverser)

    # Create presentation layer (inject application services)
    main_window = MainWindow(
        expansion_service=expansion_service,
        selection_service=selection_service,
        search_service=search_service
    )

    return main_window
```

---

## 5. Testing Strategy by Layer

| Layer | Test Type | Dependencies | Mocking Strategy |
|-------|-----------|--------------|------------------|
| **Domain** | Unit | None | Pure functions, no mocks needed |
| **Application** | Unit + Integration | Domain | Mock domain services |
| **Infrastructure** | Integration | External libs | Real libs, test databases |
| **Presentation** | UI/Widget | Application | Mock application services |

### Example Test Structure

```
tests/
├── unit/
│   ├── domain/           # Pure unit tests
│   │   ├── test_cell.py
│   │   └── test_design.py
│   │
│   └── application/      # Mock domain services
│       └── test_expansion_service.py
│
├── integration/
│   ├── infrastructure/   # Real external libs
│   │   ├── test_cdl_parser.py
│   │   └── test_networkx_adapter.py
│   │
│   └── end_to_end/       # Full stack
│       └── test_load_and_expand.py
│
└── ui/                   # Qt widget tests
    └── test_schematic_canvas.py
```

---

*See [Data Flow](./data-flow.md) for detailed operation flows.*
