# Domain-Driven Design Architecture

## 1. Strategic Design

### 1.1 Domain Overview

**Core Domain**: Gate-level netlist exploration and incremental schematic visualization

**Problem Space**:
- Engineers analyze complex gate-level netlists with hundreds of thousands of cells
- Traditional tools render everything, causing performance issues
- Need to trace signal paths (fanin/fanout) efficiently
- Require visual understanding of circuit connectivity

**Solution Space**:
- Incremental exploration starting from points of interest
- Graph-based representation enabling fast traversal queries
- On-demand rendering with level-of-detail optimization

### 1.2 Ubiquitous Language

| Term | Definition |
|------|------------|
| **Cell** | A gate-level instance (e.g., AND2, INV, DFF) representing a logic element |
| **Pin** | A connection point on a cell with direction (INPUT, OUTPUT, INOUT) |
| **Port** | A top-level I/O of the design (external interface) |
| **Net** | A wire connecting multiple pins together |
| **Fanout** | Cells driven by a signal (downstream connections) |
| **Fanin** | Cells driving a signal (upstream connections) |
| **Latch/FF** | Sequential storage element (flip-flop or latch) |
| **Expansion** | Action of revealing connected cells from a starting point |
| **Collapse** | Action of hiding previously expanded cells |
| **Hop** | One level of connection (1-hop = immediate neighbors) |
| **Semantic Boundary** | A latch, flip-flop, or port that terminates expansion |
| **Subcircuit** | A reusable cell definition (template for instances) |

---

## 2. Bounded Contexts

### 2.1 Context Map

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                CONTEXT MAP                                       │
│                                                                                  │
│  ┌─────────────────────┐          ┌─────────────────────┐                       │
│  │   NETLIST CONTEXT   │          │  SCHEMATIC CONTEXT  │                       │
│  │                     │          │                     │                       │
│  │  Upstream (U)       │  U/D     │  Downstream (D)     │                       │
│  │                     │─────────►│                     │                       │
│  │  • CDL Parsing      │ Conformist│  • Symbol Rendering │                       │
│  │  • Graph Building   │          │  • Layout Engine    │                       │
│  │  • Pin Directions   │          │  • Net Routing      │                       │
│  │  • Latch Detection  │          │  • LOD Management   │                       │
│  └─────────────────────┘          └──────────┬──────────┘                       │
│           │                                   │                                  │
│           │ Shared Kernel                     │ Shared Kernel                    │
│           ▼                                   ▼                                  │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │                           SHARED KERNEL                                     │ │
│  │                                                                             │ │
│  │   Cell, Pin, Port, Net, PinDirection, Position, BoundingBox                │ │
│  │   GraphTraverser interface, LayoutResult, RenderObject                      │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│           ▲                                   ▲                                  │
│           │                                   │                                  │
│  ┌─────────────────────┐          ┌─────────────────────┐                       │
│  │ EXPLORATION CONTEXT │          │   QUERY CONTEXT     │                       │
│  │                     │          │                     │                       │
│  │  • Expansion Logic  │   ACL    │  • Search Engine    │                       │
│  │  • Collapse Logic   │◄────────►│  • Pattern Matching │                       │
│  │  • State Management │          │  • Navigation       │                       │
│  │  • Undo/Redo Stack  │          │  • Index Building   │                       │
│  └─────────────────────┘          └─────────────────────┘                       │
│                                                                                  │
│  Legend:                                                                         │
│    U/D = Upstream/Downstream relationship                                        │
│    ACL = Anti-Corruption Layer                                                   │
│    Shared Kernel = Shared domain model                                           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Bounded Context Details

#### Netlist Context (Upstream)

**Responsibility**: Parse and model the netlist structure

**Aggregates**:
- `Design` (Aggregate Root)
- `Subcircuit` (Aggregate Root)

**Key Operations**:
- Parse CDL file
- Parse pin direction file
- Build connectivity graph
- Identify sequential elements

**Team/Module**: `ink.core.parser`, `ink.core.graph`

---

#### Schematic Context (Downstream)

**Responsibility**: Visual representation and layout

**Aggregates**:
- `SchematicView` (Aggregate Root)

**Key Operations**:
- Compute Sugiyama layout
- Route nets orthogonally
- Render at appropriate LOD
- Handle pan/zoom

**Team/Module**: `ink.ui.canvas`, `ink.core.layout`

---

#### Exploration Context

**Responsibility**: Manage incremental exploration state

**Aggregates**:
- `ExpansionState` (Aggregate Root)

**Key Operations**:
- Expand fanin/fanout
- Collapse subtrees
- Manage expansion history
- Undo/redo

**Team/Module**: `ink.services.expansion`

---

#### Query Context

**Responsibility**: Search and navigation

**Aggregates**:
- `SearchSession` (Aggregate Root)

**Key Operations**:
- Index objects for search
- Execute wildcard queries
- Navigate to results
- Maintain search history

**Team/Module**: `ink.services.search`

---

## 3. Tactical Design

### 3.1 Aggregates

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DESIGN AGGREGATE                                    │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ Design (Aggregate Root)                                                  │    │
│  │                                                                          │    │
│  │  - id: DesignId                                                         │    │
│  │  - name: str                                                            │    │
│  │  - top_module: str                                                      │    │
│  │  - cells: Dict[CellId, Cell]                                           │    │
│  │  - nets: Dict[NetId, Net]                                              │    │
│  │  - ports: Dict[PortId, Port]                                           │    │
│  │  - subcircuits: Dict[str, Subcircuit]                                  │    │
│  │                                                                          │    │
│  │  + add_cell(cell: Cell)                                                 │    │
│  │  + add_net(net: Net)                                                    │    │
│  │  + get_cell(cell_id: CellId) -> Cell                                   │    │
│  │  + get_cells_on_net(net_id: NetId) -> List[Cell]                       │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                        │                                         │
│                 ┌──────────────────────┼──────────────────────┐                 │
│                 ▼                      ▼                      ▼                 │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐     │
│  │ Cell (Entity)       │  │ Net (Entity)        │  │ Port (Entity)       │     │
│  │                     │  │                     │  │                     │     │
│  │ - id: CellId        │  │ - id: NetId         │  │ - id: PortId        │     │
│  │ - instance_name: str│  │ - name: str         │  │ - name: str         │     │
│  │ - cell_type: CellType│ │ - connected_pins: []│  │ - direction: PinDir │     │
│  │ - pins: List[Pin]   │  │ - is_power: bool    │  │ - net: NetId        │     │
│  │ - is_sequential: bool│ │ - is_ground: bool   │  │                     │     │
│  │ - position: Position│  │                     │  │                     │     │
│  └──────────┬──────────┘  └─────────────────────┘  └─────────────────────┘     │
│             │                                                                    │
│             ▼                                                                    │
│  ┌─────────────────────┐                                                        │
│  │ Pin (Entity)        │         VALUE OBJECTS                                  │
│  │                     │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐      │
│  │ - name: str         │  │ PinDirection│ │ Position    │ │ CellType    │      │
│  │ - direction: PinDir │  │             │ │             │ │             │      │
│  │ - net: NetId        │  │ INPUT       │ │ x: float    │ │ name: str   │      │
│  │ - index: int        │  │ OUTPUT      │ │ y: float    │ │ is_seq: bool│      │
│  └─────────────────────┘  │ INOUT       │ └─────────────┘ └─────────────┘      │
│                           └─────────────┘                                       │
│  INVARIANTS:                                                                    │
│  • Each Cell has unique instance name within Design                             │
│  • Each Pin belongs to exactly one Cell                                         │
│  • Each Net connects at least 2 Pins (or 1 Port + 1 Pin)                       │
│  • Sequential cells have specific naming patterns                               │
└─────────────────────────────────────────────────────────────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          EXPANSION STATE AGGREGATE                               │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ ExpansionState (Aggregate Root)                                          │    │
│  │                                                                          │    │
│  │  - visible_cells: Set[CellId]                                           │    │
│  │  - visible_nets: Set[NetId]                                             │    │
│  │  - expansion_history: List[ExpansionCommand]                            │    │
│  │  - undo_stack: List[ExpansionCommand]                                   │    │
│  │  - redo_stack: List[ExpansionCommand]                                   │    │
│  │                                                                          │    │
│  │  + expand(cells: Set[CellId], command: ExpansionCommand)                │    │
│  │  + collapse(cells: Set[CellId], command: CollapseCommand)               │    │
│  │  + undo() -> bool                                                       │    │
│  │  + redo() -> bool                                                       │    │
│  │  + is_visible(cell_id: CellId) -> bool                                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                        │                                         │
│                                        ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │ ExpansionCommand (Value Object)                                          │    │
│  │                                                                          │    │
│  │  - type: CommandType (EXPAND | COLLAPSE)                                │    │
│  │  - cells_affected: FrozenSet[CellId]                                    │    │
│  │  - nets_affected: FrozenSet[NetId]                                      │    │
│  │  - origin: CellId | PinId                                               │    │
│  │  - direction: Direction (FANIN | FANOUT | BOTH)                         │    │
│  │  - hops: int                                                            │    │
│  │  - timestamp: datetime                                                  │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  INVARIANTS:                                                                    │
│  • visible_cells and visible_nets are always consistent                         │
│  • undo_stack + redo_stack preserve complete history                            │
│  • Collapse cannot make connected visible cells orphaned                        │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Domain Services

```python
# Graph Traversal Service
class GraphTraverser(Protocol):
    """Domain service for graph queries"""

    def get_fanout(self, pin: Pin, hops: int = 1) -> Set[Cell]:
        """Get cells within N hops downstream of pin"""
        ...

    def get_fanin(self, pin: Pin, hops: int = 1) -> Set[Cell]:
        """Get cells within N hops upstream of pin"""
        ...

    def get_cone_to_boundary(
        self,
        pin: Pin,
        direction: Direction,
        boundary_predicate: Callable[[Cell], bool]
    ) -> Set[Cell]:
        """Get all cells to nearest boundary (latch/port)"""
        ...

    def get_path(self, source: Pin, target: Pin) -> List[Cell]:
        """Find path between two pins"""
        ...


# Layout Service
class LayoutEngine(Protocol):
    """Domain service for schematic layout"""

    def compute_layout(
        self,
        cells: Set[Cell],
        nets: Set[Net]
    ) -> LayoutResult:
        """Compute Sugiyama layout for given cells"""
        ...

    def update_layout(
        self,
        current: LayoutResult,
        added_cells: Set[Cell],
        removed_cells: Set[Cell]
    ) -> LayoutResult:
        """Incrementally update layout"""
        ...


# Net Routing Service
class NetRouter(Protocol):
    """Domain service for orthogonal net routing"""

    def route_net(
        self,
        net: Net,
        pin_positions: Dict[PinId, Position]
    ) -> List[RouteSegment]:
        """Compute orthogonal route for a net"""
        ...
```

### 3.3 Repository Interfaces

```python
# Design Repository (in Domain Layer - interface only)
class DesignRepository(Protocol):
    """Repository for Design aggregate persistence"""

    def save(self, design: Design) -> None:
        """Persist design to storage"""
        ...

    def load(self, design_id: DesignId) -> Design:
        """Load design from storage"""
        ...

    def exists(self, design_id: DesignId) -> bool:
        """Check if design exists"""
        ...


# Session Repository
class SessionRepository(Protocol):
    """Repository for exploration session persistence"""

    def save_session(
        self,
        design_id: DesignId,
        expansion_state: ExpansionState,
        view_state: ViewState
    ) -> SessionId:
        """Save current exploration session"""
        ...

    def load_session(self, session_id: SessionId) -> Tuple[ExpansionState, ViewState]:
        """Load previous session"""
        ...
```

---

## 4. Domain Events

```python
# Events emitted by the domain
@dataclass(frozen=True)
class CellsExpanded:
    """Raised when cells are expanded into view"""
    cells: FrozenSet[CellId]
    nets: FrozenSet[NetId]
    origin: CellId
    direction: Direction
    timestamp: datetime


@dataclass(frozen=True)
class CellsCollapsed:
    """Raised when cells are collapsed from view"""
    cells: FrozenSet[CellId]
    nets: FrozenSet[NetId]
    timestamp: datetime


@dataclass(frozen=True)
class SelectionChanged:
    """Raised when selection changes"""
    selected: FrozenSet[ObjectId]
    previously_selected: FrozenSet[ObjectId]


@dataclass(frozen=True)
class DesignLoaded:
    """Raised when a design is loaded"""
    design_id: DesignId
    cell_count: int
    net_count: int
    port_count: int
```

---

## 5. Module Structure

```
src/ink/
├── domain/                      # DOMAIN LAYER (no external dependencies)
│   ├── __init__.py
│   ├── model/                   # Entities and Aggregates
│   │   ├── __init__.py
│   │   ├── design.py           # Design aggregate root
│   │   ├── cell.py             # Cell entity
│   │   ├── pin.py              # Pin entity
│   │   ├── net.py              # Net entity
│   │   ├── port.py             # Port entity
│   │   └── subcircuit.py       # Subcircuit entity
│   │
│   ├── value_objects/          # Immutable value objects
│   │   ├── __init__.py
│   │   ├── pin_direction.py    # PinDirection enum
│   │   ├── position.py         # Position, BoundingBox
│   │   ├── cell_type.py        # CellType value object
│   │   └── identifiers.py      # CellId, NetId, etc.
│   │
│   ├── services/               # Domain services (interfaces)
│   │   ├── __init__.py
│   │   ├── graph_traverser.py  # GraphTraverser protocol
│   │   ├── layout_engine.py    # LayoutEngine protocol
│   │   └── net_router.py       # NetRouter protocol
│   │
│   ├── events/                 # Domain events
│   │   ├── __init__.py
│   │   └── domain_events.py
│   │
│   └── repositories/           # Repository interfaces
│       ├── __init__.py
│       ├── design_repository.py
│       └── session_repository.py
│
├── application/                 # APPLICATION LAYER
│   ├── __init__.py
│   ├── services/               # Application services (use cases)
│   │   ├── __init__.py
│   │   ├── expansion_service.py
│   │   ├── selection_service.py
│   │   ├── search_service.py
│   │   └── file_service.py
│   │
│   ├── commands/               # Command handlers
│   │   ├── __init__.py
│   │   ├── expand_command.py
│   │   └── collapse_command.py
│   │
│   └── queries/                # Query handlers
│       ├── __init__.py
│       ├── search_query.py
│       └── property_query.py
│
├── infrastructure/              # INFRASTRUCTURE LAYER
│   ├── __init__.py
│   ├── parsing/                # File parsers
│   │   ├── __init__.py
│   │   ├── cdl_parser.py
│   │   └── pindir_parser.py
│   │
│   ├── graph/                  # Graph implementations
│   │   ├── __init__.py
│   │   └── networkx_adapter.py
│   │
│   ├── layout/                 # Layout implementations
│   │   ├── __init__.py
│   │   └── sugiyama_engine.py
│   │
│   ├── routing/                # Routing implementations
│   │   ├── __init__.py
│   │   └── orthogonal_router.py
│   │
│   ├── persistence/            # Storage implementations
│   │   ├── __init__.py
│   │   ├── json_session_store.py
│   │   └── qsettings_store.py
│   │
│   └── search/                 # Search implementations
│       ├── __init__.py
│       └── trie_index.py
│
└── presentation/               # PRESENTATION LAYER (PySide6)
    ├── __init__.py
    ├── main_window.py
    ├── canvas/
    │   ├── __init__.py
    │   ├── schematic_canvas.py
    │   ├── cell_item.py
    │   ├── pin_item.py
    │   └── net_item.py
    │
    ├── panels/
    │   ├── __init__.py
    │   ├── property_panel.py
    │   ├── hierarchy_panel.py
    │   └── search_panel.py
    │
    └── dialogs/
        ├── __init__.py
        └── expansion_settings.py
```

---

## 6. Anti-Corruption Layer Example

```python
# infrastructure/graph/networkx_adapter.py
"""
Anti-Corruption Layer: Adapts NetworkX to domain's GraphTraverser interface
"""
import networkx as nx
from ink.domain.services.graph_traverser import GraphTraverser
from ink.domain.model import Cell, Pin, Net
from ink.domain.value_objects import CellId, Direction


class NetworkXGraphTraverser(GraphTraverser):
    """
    Implements domain's GraphTraverser using NetworkX.

    This adapter isolates the domain from NetworkX-specific concepts,
    translating between domain objects and NetworkX graph operations.
    """

    def __init__(self, graph: nx.DiGraph):
        self._graph = graph
        self._cell_index: Dict[CellId, Cell] = {}
        self._pin_to_node: Dict[PinId, str] = {}

    def get_fanout(self, pin: Pin, hops: int = 1) -> Set[Cell]:
        """
        Get cells within N hops downstream.

        Translates domain Pin to NetworkX node, performs BFS,
        then translates back to domain Cells.
        """
        start_node = self._pin_to_node[pin.id]

        # NetworkX BFS with depth limit
        visited = set()
        current_level = {start_node}

        for _ in range(hops):
            next_level = set()
            for node in current_level:
                for successor in self._graph.successors(node):
                    if successor not in visited:
                        next_level.add(successor)
                        visited.add(successor)
            current_level = next_level

        # Translate back to domain objects
        return {
            self._cell_index[self._node_to_cell[node]]
            for node in visited
            if node in self._node_to_cell
        }
```

---

*See [Layer Architecture](./layer-architecture.md) for dependency rules and testing strategies.*
