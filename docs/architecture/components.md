# Component Specifications

## 1. Domain Layer Components

### 1.1 Design Aggregate

**File**: `src/ink/domain/model/design.py`

```python
@dataclass
class Design:
    """
    Aggregate root for the entire netlist design.

    The Design is the top-level container that holds all cells, nets, ports,
    and subcircuit definitions. It enforces invariants across the design
    and provides the entry point for all design queries.

    Invariants:
    - Each cell has a unique instance name
    - Each net has at least one driver or is a port connection
    - All cell pins reference valid nets
    - Top module ports match the design interface
    """

    id: DesignId
    name: str
    top_module: str
    cells: Dict[CellId, Cell]
    nets: Dict[NetId, Net]
    ports: Dict[PortId, Port]
    subcircuits: Dict[str, Subcircuit]

    # Factory method
    @classmethod
    def create(cls, name: str, top_module: str) -> "Design":
        """Create a new empty design."""

    # Cell operations
    def add_cell(self, cell: Cell) -> None:
        """Add a cell to the design. Raises if name conflict."""

    def get_cell(self, cell_id: CellId) -> Cell:
        """Get cell by ID. Raises CellNotFoundError if missing."""

    def get_cell_by_name(self, name: str) -> Cell:
        """Get cell by instance name."""

    # Net operations
    def add_net(self, net: Net) -> None:
        """Add a net to the design."""

    def get_cells_on_net(self, net_id: NetId) -> List[Cell]:
        """Get all cells connected to a net."""

    # Queries
    def get_sequential_cells(self) -> List[Cell]:
        """Get all latches and flip-flops."""

    def get_primary_inputs(self) -> List[Port]:
        """Get input ports."""

    def get_primary_outputs(self) -> List[Port]:
        """Get output ports."""
```

### 1.2 Cell Entity

**File**: `src/ink/domain/model/cell.py`

```python
@dataclass
class Cell:
    """
    A gate-level cell instance.

    Represents a single logic element instantiated in the design.
    Examples: AND2_X1, INV_X1, DFFR_X1

    Properties:
    - Unique instance name within design
    - Cell type determines functionality
    - Pins connect to nets for signal flow
    - Sequential flag marks timing boundaries
    """

    id: CellId
    instance_name: str      # e.g., "XI123", "U_ALU_add_0"
    cell_type: CellType     # e.g., CellType("AND2_X1")
    pins: List[Pin]         # Ordered by subcircuit definition
    is_sequential: bool     # True for latches, flip-flops
    position: Position      # Layout position (set by LayoutEngine)

    # Pin queries
    def get_input_pins(self) -> List[Pin]:
        """Get all input pins."""

    def get_output_pins(self) -> List[Pin]:
        """Get all output pins."""

    def get_pin_by_name(self, name: str) -> Pin:
        """Get pin by name. Raises PinNotFoundError if missing."""

    # Connectivity queries
    def get_fanin_nets(self) -> List[Net]:
        """Get all nets driving this cell's inputs."""

    def get_fanout_nets(self) -> List[Net]:
        """Get all nets driven by this cell's outputs."""
```

### 1.3 Pin Entity

**File**: `src/ink/domain/model/pin.py`

```python
@dataclass
class Pin:
    """
    A connection point on a cell.

    Each pin belongs to exactly one cell and connects to exactly one net.
    Pin direction determines signal flow for traversal algorithms.
    """

    id: PinId
    name: str               # e.g., "A", "B", "Y", "Q"
    direction: PinDirection # INPUT, OUTPUT, INOUT
    net: NetId              # Connected net
    cell: CellId            # Parent cell (back-reference)
    index: int              # Position in subcircuit definition

    def is_driver(self) -> bool:
        """True if this pin drives its net (OUTPUT or INOUT)."""

    def is_load(self) -> bool:
        """True if this pin is driven by its net (INPUT or INOUT)."""
```

### 1.4 Net Entity

**File**: `src/ink/domain/model/net.py`

```python
@dataclass
class Net:
    """
    A wire connecting multiple pins.

    A net represents electrical connectivity - all pins on a net
    share the same signal value. Special nets include power (VDD)
    and ground (VSS).
    """

    id: NetId
    name: str                       # e.g., "n123", "clk", "VDD"
    connected_pins: List[PinId]     # All pins on this net
    is_power: bool = False          # VDD net
    is_ground: bool = False         # VSS net

    def get_drivers(self, design: Design) -> List[Pin]:
        """Get pins driving this net (outputs/inouts)."""

    def get_loads(self, design: Design) -> List[Pin]:
        """Get pins driven by this net (inputs/inouts)."""

    @property
    def fanout(self) -> int:
        """Number of load pins on this net."""
```

### 1.5 Value Objects

**File**: `src/ink/domain/value_objects/`

```python
# pin_direction.py
class PinDirection(Enum):
    """Pin direction enum."""
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    INOUT = "INOUT"

    @property
    def is_input(self) -> bool:
        return self in (PinDirection.INPUT, PinDirection.INOUT)

    @property
    def is_output(self) -> bool:
        return self in (PinDirection.OUTPUT, PinDirection.INOUT)


# position.py
@dataclass(frozen=True)
class Position:
    """Immutable 2D position."""
    x: float = 0.0
    y: float = 0.0

    def translate(self, dx: float, dy: float) -> "Position":
        return Position(self.x + dx, self.y + dy)


@dataclass(frozen=True)
class BoundingBox:
    """Immutable bounding rectangle."""
    x: float
    y: float
    width: float
    height: float

    def contains(self, pos: Position) -> bool:
        """Check if position is inside box."""

    def intersects(self, other: "BoundingBox") -> bool:
        """Check if boxes overlap."""


# identifiers.py
@dataclass(frozen=True)
class CellId:
    """Unique cell identifier."""
    value: str

@dataclass(frozen=True)
class NetId:
    """Unique net identifier."""
    value: str

@dataclass(frozen=True)
class PinId:
    """Unique pin identifier (cell_id + pin_name)."""
    cell_id: CellId
    pin_name: str
```

---

## 2. Application Layer Components

### 2.1 ExpansionService

**File**: `src/ink/application/services/expansion_service.py`

```python
class ExpansionService:
    """
    Application service for incremental expansion operations.

    Orchestrates graph traversal, layout computation, and state
    management to implement expand/collapse functionality.
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

    # Expansion operations
    def expand_fanout(
        self,
        pin: Pin,
        hops: int = 1
    ) -> ExpansionResult:
        """
        Expand N hops downstream from a pin.

        Returns the newly visible cells and their layout positions.
        """

    def expand_fanin(
        self,
        pin: Pin,
        hops: int = 1
    ) -> ExpansionResult:
        """Expand N hops upstream from a pin."""

    def expand_to_boundary(
        self,
        pin: Pin,
        direction: Direction
    ) -> ExpansionResult:
        """Expand until reaching a latch or port."""

    # Collapse operations
    def collapse_cells(
        self,
        cells: Set[CellId]
    ) -> CollapseResult:
        """
        Collapse specified cells.

        Cells connected to other visible cells remain visible.
        """

    def collapse_subtree(
        self,
        root: CellId,
        direction: Direction
    ) -> CollapseResult:
        """Collapse all cells in subtree from root."""

    # Undo/Redo
    def undo(self) -> bool:
        """Undo last expansion/collapse. Returns False if nothing to undo."""

    def redo(self) -> bool:
        """Redo last undone operation. Returns False if nothing to redo."""

    # Queries
    def is_visible(self, cell_id: CellId) -> bool:
        """Check if cell is currently visible."""

    def get_visible_cells(self) -> Set[CellId]:
        """Get all currently visible cells."""
```

### 2.2 SelectionService

**File**: `src/ink/application/services/selection_service.py`

```python
class SelectionService:
    """
    Application service for selection management.

    Handles single and multi-selection, property queries,
    and selection-related operations.
    """

    def __init__(self, event_bus: EventBus):
        self._selected: Set[ObjectId] = set()
        self._events = event_bus

    # Selection operations
    def select(
        self,
        object_id: ObjectId,
        mode: SelectMode = SelectMode.REPLACE
    ) -> None:
        """
        Select an object.

        Modes:
        - REPLACE: Clear previous, select new
        - ADD: Add to selection
        - TOGGLE: Toggle selection state
        """

    def select_multiple(
        self,
        object_ids: Set[ObjectId],
        mode: SelectMode = SelectMode.REPLACE
    ) -> None:
        """Select multiple objects."""

    def select_in_rect(
        self,
        rect: BoundingBox,
        mode: SelectMode = SelectMode.REPLACE
    ) -> None:
        """Select all objects within rectangle."""

    def clear(self) -> None:
        """Clear all selections."""

    # Queries
    def get_selected(self) -> Set[ObjectId]:
        """Get currently selected objects."""

    def is_selected(self, object_id: ObjectId) -> bool:
        """Check if object is selected."""

    @property
    def selection_count(self) -> int:
        """Number of selected objects."""
```

### 2.3 SearchService

**File**: `src/ink/application/services/search_service.py`

```python
class SearchService:
    """
    Application service for search and navigation.

    Provides pattern-based search across cells, pins, nets, and ports
    with navigation to results.
    """

    def __init__(
        self,
        search_index: SearchIndex,
        expansion_service: ExpansionService,
        event_bus: EventBus
    ):
        self._index = search_index
        self._expansion = expansion_service
        self._events = event_bus
        self._history: List[str] = []

    # Search operations
    def search(
        self,
        query: str,
        filters: SearchFilters = SearchFilters()
    ) -> List[SearchResult]:
        """
        Search for objects matching query.

        Supports wildcards: * (any chars), ? (single char)
        """

    # Navigation
    def navigate_to(self, object_id: ObjectId) -> None:
        """
        Navigate to an object.

        If object is not visible, expands to show it.
        Selects object and pans view to center on it.
        """

    # History
    def get_history(self) -> List[str]:
        """Get recent search queries."""

    def clear_history(self) -> None:
        """Clear search history."""


@dataclass
class SearchFilters:
    """Search filter options."""
    include_cells: bool = True
    include_pins: bool = True
    include_nets: bool = True
    include_ports: bool = True
    max_results: int = 100


@dataclass
class SearchResult:
    """Single search result."""
    object_type: str        # "cell", "pin", "net", "port"
    object_id: ObjectId
    name: str
    context: str            # e.g., "Pin of XI123"
    score: float            # Relevance score
```

---

## 3. Infrastructure Layer Components

### 3.1 CDL Parser

**File**: `src/ink/infrastructure/parsing/cdl_parser.py`

```python
class CDLParser:
    """
    Parser for gate-level CDL netlist files.

    Handles SPICE-like CDL syntax including:
    - .SUBCKT / .ENDS blocks
    - X-prefix cell instances
    - M-prefix transistors (skipped for gate-level)
    - Comment lines (*)
    - Bus notation (<N>)
    """

    def parse_file(self, file_path: Path) -> ParseResult:
        """
        Parse a .ckt file.

        Returns parsed cells, nets, ports, and any errors/warnings.
        """

    def parse_subcircuit(self, lines: List[str]) -> Subcircuit:
        """Parse a .SUBCKT block."""

    def parse_instance(self, line: str) -> CellInstance:
        """Parse an X-prefix instance line."""


@dataclass
class ParseResult:
    """Result of parsing a CDL file."""
    cells: List[Cell]
    nets: List[Net]
    ports: List[Port]
    subcircuits: Dict[str, Subcircuit]
    errors: List[ParseError]
    warnings: List[ParseWarning]
```

### 3.2 NetworkX Adapter

**File**: `src/ink/infrastructure/graph/networkx_adapter.py`

```python
class NetworkXGraphTraverser(GraphTraverser):
    """
    GraphTraverser implementation using NetworkX.

    Builds a directed graph where:
    - Nodes represent cells
    - Edges represent net connections (driver → load)
    """

    def __init__(self):
        self._graph = nx.DiGraph()
        self._cell_index: Dict[CellId, Cell] = {}
        self._net_index: Dict[NetId, Net] = {}

    def build_graph(
        self,
        cells: List[Cell],
        nets: List[Net]
    ) -> None:
        """Build NetworkX graph from domain objects."""

    # GraphTraverser interface implementation
    def get_fanout(self, pin: Pin, hops: int = 1) -> Set[Cell]:
        """BFS downstream from pin."""

    def get_fanin(self, pin: Pin, hops: int = 1) -> Set[Cell]:
        """BFS upstream from pin."""

    def get_cone_to_boundary(
        self,
        pin: Pin,
        direction: Direction,
        boundary_predicate: Callable[[Cell], bool]
    ) -> Set[Cell]:
        """BFS until predicate returns True."""

    def get_path(
        self,
        source: Pin,
        target: Pin
    ) -> Optional[List[Cell]]:
        """Find shortest path between pins."""
```

### 3.3 Sugiyama Layout Engine

**File**: `src/ink/infrastructure/layout/sugiyama_engine.py`

```python
class SugiyamaLayoutEngine(LayoutEngine):
    """
    Sugiyama hierarchical layout algorithm implementation.

    Produces left-to-right signal flow layouts:
    - Inputs on left, outputs on right
    - Cells organized in vertical layers
    - Edge crossings minimized
    """

    def __init__(self, config: LayoutConfig = LayoutConfig()):
        self._config = config

    def compute_layout(
        self,
        cells: Set[Cell],
        nets: Set[Net]
    ) -> LayoutResult:
        """
        Compute full layout for given cells.

        Steps:
        1. Cycle removal (reverse edges if needed)
        2. Layer assignment (logic depth)
        3. Crossing reduction (barycenter method)
        4. Coordinate assignment (Brandes-Köpf)
        """

    def update_layout(
        self,
        current: LayoutResult,
        added_cells: Set[Cell],
        removed_cells: Set[Cell]
    ) -> LayoutResult:
        """
        Incrementally update layout.

        Minimizes visual disruption when expanding/collapsing.
        """


@dataclass
class LayoutConfig:
    """Layout configuration parameters."""
    layer_spacing: float = 100.0    # Horizontal spacing between layers
    cell_spacing: float = 50.0      # Vertical spacing within layer
    min_edge_length: int = 1        # Minimum layers between connected cells
    direction: str = "LR"           # Layout direction (LR, RL, TB, BT)


@dataclass
class LayoutResult:
    """Layout computation result."""
    positions: Dict[CellId, Position]
    layer_assignment: Dict[CellId, int]
    bounding_box: BoundingBox
```

### 3.4 Orthogonal Router

**File**: `src/ink/infrastructure/routing/orthogonal_router.py`

```python
class OrthogonalRouter(NetRouter):
    """
    Orthogonal net routing implementation.

    Routes nets using only horizontal and vertical segments.
    Minimizes crossings and total wire length.
    """

    def __init__(self, config: RoutingConfig = RoutingConfig()):
        self._config = config

    def route_net(
        self,
        net: Net,
        pin_positions: Dict[PinId, Position]
    ) -> List[RouteSegment]:
        """
        Route a single net orthogonally.

        Uses channel routing between layers and
        Steiner tree approximation for multi-pin nets.
        """

    def route_all_nets(
        self,
        nets: Set[Net],
        pin_positions: Dict[PinId, Position]
    ) -> Dict[NetId, List[RouteSegment]]:
        """Route all nets with global optimization."""


@dataclass
class RouteSegment:
    """A single segment of a net route."""
    start: Position
    end: Position
    net_id: NetId
    is_junction: bool = False   # True if this is a branch point


@dataclass
class RoutingConfig:
    """Routing configuration."""
    channel_width: float = 20.0
    min_wire_spacing: float = 5.0
    prefer_horizontal: bool = True
```

---

## 4. Presentation Layer Components

### 4.1 Main Window

**File**: `src/ink/presentation/main_window.py`

```python
class InkMainWindow(QMainWindow):
    """
    Main application window.

    Standard EDA tool layout:
    - Central: Schematic canvas
    - Left: Hierarchy panel (dockable)
    - Right: Property panel (dockable)
    - Bottom: Search/messages panel (dockable)
    - Top: Menu bar + toolbar
    - Bottom: Status bar
    """

    def __init__(
        self,
        expansion_service: ExpansionService,
        selection_service: SelectionService,
        search_service: SearchService,
        file_service: FileService
    ):
        super().__init__()
        self._setup_ui()
        self._setup_menus()
        self._setup_shortcuts()
        self._connect_services()

    # UI Setup
    def _setup_ui(self) -> None:
        """Create and layout UI components."""

    def _setup_menus(self) -> None:
        """Create menu bar with actions."""

    def _setup_shortcuts(self) -> None:
        """Register keyboard shortcuts."""

    # Actions
    def open_file(self) -> None:
        """Open file dialog and load netlist."""

    def save_session(self) -> None:
        """Save current exploration state."""

    def load_session(self) -> None:
        """Load saved session."""
```

### 4.2 Schematic Canvas

**File**: `src/ink/presentation/canvas/schematic_canvas.py`

```python
class SchematicCanvas(QGraphicsView):
    """
    Main schematic visualization canvas.

    Features:
    - Pan (drag) and zoom (wheel)
    - Selection (click, Ctrl+click, drag rectangle)
    - Expansion (double-click)
    - Level of detail (zoom-dependent rendering)
    """

    # Signals
    cell_double_clicked = Signal(str)       # cell_id
    cell_selected = Signal(str)             # cell_id
    selection_changed = Signal(list)        # [object_ids]
    view_changed = Signal(QRectF)           # visible_rect

    def __init__(
        self,
        expansion_service: ExpansionService,
        selection_service: SelectionService
    ):
        super().__init__()
        self._scene = SchematicScene(self)
        self.setScene(self._scene)
        self._setup_view()

    # View control
    def zoom_in(self) -> None:
        """Zoom in by 25%."""

    def zoom_out(self) -> None:
        """Zoom out by 25%."""

    def fit_view(self) -> None:
        """Fit all visible content in view."""

    def fit_selection(self) -> None:
        """Fit selected items in view."""

    def center_on(self, position: Position) -> None:
        """Center view on position."""

    # Rendering
    def add_cell(self, cell: Cell, position: Position) -> CellItem:
        """Add cell to canvas at position."""

    def add_net(self, net: Net, routes: List[RouteSegment]) -> NetItem:
        """Add net routing to canvas."""

    def remove_cell(self, cell_id: CellId) -> None:
        """Remove cell from canvas."""

    # LOD
    def _update_lod(self) -> None:
        """Update level of detail based on zoom."""
```

### 4.3 Property Panel

**File**: `src/ink/presentation/panels/property_panel.py`

```python
class PropertyPanel(QDockWidget):
    """
    Property inspector panel.

    Displays details of selected objects:
    - Cell: name, type, pins, sequential flag
    - Pin: name, direction, connected net
    - Net: name, driver, fanout count
    - Port: name, direction
    """

    def __init__(self, selection_service: SelectionService):
        super().__init__("Properties")
        self._selection = selection_service
        self._setup_ui()
        self._connect_signals()

    def update_properties(self, objects: List[ObjectId]) -> None:
        """Update display for selected objects."""

    def _show_cell_properties(self, cell: Cell) -> None:
        """Display cell properties."""

    def _show_net_properties(self, net: Net) -> None:
        """Display net properties."""

    def _show_multi_selection(self, count: int) -> None:
        """Display summary for multiple selection."""
```

### 4.4 Search Panel

**File**: `src/ink/presentation/panels/search_panel.py`

```python
class SearchPanel(QDockWidget):
    """
    Search interface panel.

    Features:
    - Incremental search as you type
    - Wildcard patterns (* and ?)
    - Filter by object type
    - Search history dropdown
    - Click result to navigate
    """

    # Signals
    result_selected = Signal(str)   # object_id

    def __init__(self, search_service: SearchService):
        super().__init__("Search")
        self._search = search_service
        self._setup_ui()

    def _on_text_changed(self, text: str) -> None:
        """Handle search input changes."""

    def _on_result_clicked(self, item: QListWidgetItem) -> None:
        """Handle result selection."""

    def _on_filter_changed(self) -> None:
        """Handle filter checkbox changes."""

    def show_and_focus(self) -> None:
        """Show panel and focus search input."""
```

---

## 5. Shared Interfaces (Protocols)

### 5.1 Domain Service Protocols

**File**: `src/ink/domain/services/`

```python
# graph_traverser.py
class GraphTraverser(Protocol):
    """Interface for graph traversal operations."""

    def get_fanout(self, pin: Pin, hops: int = 1) -> Set[Cell]: ...
    def get_fanin(self, pin: Pin, hops: int = 1) -> Set[Cell]: ...
    def get_cone_to_boundary(
        self,
        pin: Pin,
        direction: Direction,
        boundary_predicate: Callable[[Cell], bool]
    ) -> Set[Cell]: ...


# layout_engine.py
class LayoutEngine(Protocol):
    """Interface for layout computation."""

    def compute_layout(
        self,
        cells: Set[Cell],
        nets: Set[Net]
    ) -> LayoutResult: ...

    def update_layout(
        self,
        current: LayoutResult,
        added_cells: Set[Cell],
        removed_cells: Set[Cell]
    ) -> LayoutResult: ...


# net_router.py
class NetRouter(Protocol):
    """Interface for net routing."""

    def route_net(
        self,
        net: Net,
        pin_positions: Dict[PinId, Position]
    ) -> List[RouteSegment]: ...
```

---

*Last Updated: 2025-12-26*
