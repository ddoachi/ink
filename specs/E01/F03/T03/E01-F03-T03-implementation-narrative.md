# E01-F03-T03: NetworkX Graph Builder - Implementation Narrative

## Overview

This document provides a comprehensive walkthrough of the NetworkX Graph Builder implementation, explaining the business logic, design decisions, and technical details that enable developers to fully understand and maintain the system.

---

## 1. The Problem

The Ink schematic viewer needs to perform efficient connectivity queries on gate-level netlists. The domain model (Design aggregate with Cell, Pin, Net, Port entities) provides entity storage, but **schematic operations require graph-based traversal**:

- **Fanout expansion**: Given a cell output, find all cells driven by that signal
- **Fanin exploration**: Given a cell input, trace back to the driving cell
- **Sequential boundary detection**: Identify paths between flip-flops

A graph representation enables O(1) neighbor lookups compared to O(n) linear scans through entity collections.

---

## 2. The Solution Architecture

### 2.1 Design Pattern: Adapter

The `NetworkXGraphBuilder` is an **adapter** that translates the domain model into a NetworkX graph:

```
┌─────────────────────┐        ┌─────────────────────┐
│     Domain Layer    │        │  Infrastructure     │
│                     │        │       Layer         │
│  ┌───────────────┐  │        │  ┌───────────────┐  │
│  │    Design     │──┼───────>│  │  NetworkX     │  │
│  │   Aggregate   │  │        │  │ MultiDiGraph  │  │
│  │               │  │        │  │               │  │
│  │ ┌───┐ ┌───┐   │  │        │  │  ┌───┐ ┌───┐  │  │
│  │ │Cell│ │Net│  │  │        │  │  │ ● │─│ ● │  │  │
│  │ └───┘ └───┘   │  │ build_ │  │  └───┘ └───┘  │  │
│  │ ┌───┐ ┌───┐   │  │ from_  │  │  ┌───┐ ┌───┐  │  │
│  │ │Pin│ │Port│  │──┼─design─│  │  │ ● │─│ ● │  │  │
│  │ └───┘ └───┘   │  │        │  │  └───┘ └───┘  │  │
│  └───────────────┘  │        │  └───────────────┘  │
└─────────────────────┘        └─────────────────────┘
```

### 2.2 Why MultiDiGraph?

NetworkX offers several graph types:

| Graph Type | Directed | Multiple Edges | Use Case |
|------------|----------|----------------|----------|
| Graph | No | No | Simple undirected |
| DiGraph | Yes | No | Simple directed |
| MultiGraph | No | Yes | Parallel edges |
| **MultiDiGraph** | Yes | Yes | Our choice |

We need:
1. **Directed edges**: Signal flow has direction (output→input)
2. **Multiple edges**: Same nodes may connect via different nets

Example requiring multiple edges:
```
Cell A output pin Y connects to Cell B input pin A via net_1
Cell A output pin Z connects to Cell B input pin B via net_2
Result: Two edges from A to B
```

---

## 3. Graph Structure Deep Dive

### 3.1 Node Types

Every graph node has a `node_type` attribute identifying its kind:

```python
# Cell node example
graph.nodes[CellId("XI1")] = {
    "node_type": "cell",
    "name": "XI1",
    "cell_type": "INV_X1",     # Reference to cell library
    "is_sequential": False,    # True for flip-flops/latches
    "entity": <Cell object>    # Original domain entity
}

# Pin node example
graph.nodes[PinId("XI1.A")] = {
    "node_type": "pin",
    "name": "A",               # Local pin name
    "direction": PinDirection.INPUT,
    "net_id": NetId("net_1"),  # Connected net or None if floating
    "entity": <Pin object>
}

# Net node example
graph.nodes[NetId("net_1")] = {
    "node_type": "net",
    "name": "net_1",
    "pin_count": 3,            # Number of connected pins
    "entity": <Net object>
}

# Port node example
graph.nodes[PortId("CLK")] = {
    "node_type": "port",
    "name": "CLK",
    "direction": PinDirection.INPUT,
    "net_id": NetId("clk_internal"),
    "entity": <Port object>
}
```

### 3.2 Edge Types and Direction

Two edge types represent different relationships:

#### Containment Edges (`contains_pin`)

Cells **contain** their pins. This is a structural relationship:

```
Cell ────contains_pin────> Pin
```

Code:
```python
def _add_cell_pin_edges(self) -> None:
    for cell in self._design.get_all_cells():
        for pin_id in cell.pin_ids:
            self.graph.add_edge(
                cell.id, pin_id,
                edge_type="contains_pin"
            )
```

#### Signal Flow Edges (`drives`)

Signal flow follows electrical semantics:

```
OUTPUT Pin ──drives──> Net ──drives──> INPUT Pin
```

This matches how signals propagate in digital circuits:
1. A cell's output pin **drives** a net
2. The net **drives** input pins of downstream cells

Code for pins:
```python
def _add_pin_net_edges(self) -> None:
    for pin in self._design.get_all_pins():
        if pin.net_id is None:
            continue  # Skip floating pins

        if pin.direction.is_output():
            # OUTPUT: Pin drives Net
            self.graph.add_edge(pin.id, pin.net_id, edge_type="drives")

        if pin.direction.is_input():
            # INPUT: Net drives Pin
            self.graph.add_edge(pin.net_id, pin.id, edge_type="drives")
```

**INOUT pins**: Both `is_input()` and `is_output()` return True, so both edges are created. This represents bidirectional capability.

#### Port Edge Direction

Ports are the design's external interface. Their direction is opposite to internal pins:

- **INPUT Port**: External signal enters the design → Port drives internal net
- **OUTPUT Port**: Internal signal exits the design → Net drives port

```python
if port.direction.is_input():
    # External signal drives internal net
    self.graph.add_edge(port.id, port.net_id, edge_type="drives")

if port.direction.is_output():
    # Internal net drives external interface
    self.graph.add_edge(port.net_id, port.id, edge_type="drives")
```

---

## 4. Building the Graph

### 4.1 Build Phases

The `build_from_design` method executes in two phases:

**Phase 1: Add all nodes**
```python
self._add_cell_nodes()   # All cells become nodes
self._add_pin_nodes()    # All pins become nodes
self._add_net_nodes()    # All nets become nodes
self._add_port_nodes()   # All ports become nodes
```

**Phase 2: Add all edges**
```python
self._add_cell_pin_edges()  # Cell → Pin containment
self._add_pin_net_edges()   # Pin ↔ Net connectivity
self._add_port_net_edges()  # Port ↔ Net I/O connectivity
```

Order matters: Nodes must exist before creating edges to them.

### 4.2 Builder Reuse

The builder clears previous state before building:

```python
def build_from_design(self, design: Design) -> nx.MultiDiGraph:
    self._design = design
    self.graph.clear()  # Critical: remove previous graph data

    # ... build new graph ...
    return self.graph
```

This enables reusing the same builder instance for multiple designs.

---

## 5. Entity Reference Pattern

Each node stores a reference to its original domain entity:

```python
self.graph.add_node(
    cell.id,
    node_type="cell",
    # ... other attributes ...
    entity=cell  # Store the actual Cell object
)
```

**Benefits:**

1. **No redundant lookups**: During graph traversal, we can access entity data directly without querying the Design aggregate

2. **Rich queries**: Combine graph structure with entity attributes
   ```python
   # Find all sequential cells reachable from a pin
   for node in nx.descendants(graph, start_pin):
       entity = graph.nodes[node].get("entity")
       if isinstance(entity, Cell) and entity.is_sequential:
           yield entity
   ```

3. **Memory efficiency**: Domain entities are immutable (frozen dataclasses), so references don't cause data inconsistency

---

## 6. Access Methods

### 6.1 Entity Retrieval

```python
def get_node_entity(self, node_id: str) -> Cell | Pin | Net | Port | None:
    """Get the domain entity associated with a graph node."""
    return self.graph.nodes[node_id].get("entity")
```

Usage:
```python
cell = builder.get_node_entity(CellId("XI1"))
if isinstance(cell, Cell):
    print(f"Cell type: {cell.cell_type}")
```

### 6.2 Node Type Query

```python
def get_node_type(self, node_id: str) -> str | None:
    """Get the type of a graph node."""
    return self.graph.nodes[node_id].get("node_type")
```

Usage:
```python
node_type = builder.get_node_type(some_id)
if node_type == "cell":
    # Handle cell-specific logic
```

### 6.3 Statistics

```python
def node_count(self) -> int:
    return int(self.graph.number_of_nodes())

def edge_count(self) -> int:
    return int(self.graph.number_of_edges())

def cell_node_count(self) -> int:
    return sum(1 for _, data in self.graph.nodes(data=True)
               if data.get("node_type") == "cell")

def net_node_count(self) -> int:
    return sum(1 for _, data in self.graph.nodes(data=True)
               if data.get("node_type") == "net")
```

---

## 7. Performance Analysis

### 7.1 Time Complexity

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `build_from_design` | O(n) | Linear in total entities |
| Node addition | O(1) | Hash table insertion |
| Edge addition | O(1) | Hash table insertion |
| `node_count()` | O(1) | NetworkX caches count |
| `edge_count()` | O(1) | NetworkX caches count |
| `cell_node_count()` | O(n) | Iterates all nodes |

### 7.2 Measured Performance

```
Design Size | Build Time | Scaling
------------|------------|--------
100 cells   | 0.6ms     | baseline
500 cells   | 2.9ms     | 4.8x
1000 cells  | 6.2ms     | 10.3x
```

Near-linear scaling confirms O(n) complexity.

### 7.3 Memory Footprint

Each node stores:
- Dictionary with 4-6 key-value pairs
- Reference to domain entity (not a copy)

Approximate memory per node: ~200-300 bytes

For 1000 cells with average 3 pins each:
- ~1000 cell nodes
- ~3000 pin nodes
- ~2000 net nodes (estimated)
- Total: ~6000 nodes × 250 bytes ≈ 1.5 MB

---

## 8. Test Strategy

### 8.1 TDD Workflow

The implementation followed Test-Driven Development:

1. **RED**: Write failing tests first (55 unit tests)
2. **GREEN**: Implement minimal code to pass tests
3. **REFACTOR**: Improve code quality, add documentation

### 8.2 Test Fixtures

```python
@pytest.fixture
def simple_design() -> Design:
    """Single inverter with ports."""
    # IN → [net_in] → XI1.A → XI1 → XI1.Y → [net_out] → OUT

@pytest.fixture
def fanout_design() -> Design:
    """One output driving multiple inputs."""
    # XI1.Y → [net_fanout] → [XI2.A, XI3.A]

@pytest.fixture
def sequential_design() -> Design:
    """Flip-flop with D, CLK, Q pins."""

@pytest.fixture
def inout_design() -> Design:
    """INOUT pin and port for bidirectional testing."""
```

### 8.3 Integration Test Scenarios

| Scenario | Cells | Purpose |
|----------|-------|---------|
| Inverter chain | 10 | Basic signal path |
| Pipeline | 7 | Sequential + combinational |
| High fanout | 50 | Clock distribution |
| Grid | 100 | Medium scale |

---

## 9. Error Handling

### 9.1 Empty Design

Building from an empty design produces an empty graph:
```python
empty_design = Design(name="empty")
builder.build_from_design(empty_design)
assert builder.node_count() == 0
```

### 9.2 Floating Pins

Pins with `net_id=None` are handled gracefully:
- Pin node is created
- No connectivity edges are added
- Cell→Pin containment edge still exists

```python
if pin.net_id is None:
    continue  # Skip connectivity edge creation
```

### 9.3 Missing Nodes

`get_node_entity` and `get_node_type` may raise `KeyError` if the node doesn't exist. Callers should check node existence first:

```python
if node_id in graph:
    entity = builder.get_node_entity(node_id)
```

---

## 10. Type Safety

### 10.1 Type Hints

Full type hints throughout:
```python
def build_from_design(self, design: Design) -> nx.MultiDiGraph:
def get_node_entity(self, node_id: str) -> Cell | Pin | Net | Port | None:
def get_node_type(self, node_id: str) -> str | None:
```

### 10.2 NetworkX Type Ignores

NetworkX lacks type stubs, requiring pragmatic ignores:
```python
# type: ignore[no-any-unimported]
self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
```

This is standard practice for untyped external libraries.

---

## 11. Future Migration Path

### 11.1 rustworkx Compatibility

The implementation is designed for easy migration to rustworkx:

**Current (networkx)**:
```python
import networkx as nx
self.graph = nx.MultiDiGraph()
```

**Future (rustworkx)**:
```python
import rustworkx as rx
self.graph = rx.PyDiGraph(multigraph=True)
```

Key differences to address during migration:
1. Edge indices (rustworkx uses integer indices)
2. Node data access syntax
3. Traversal method names

### 11.2 Performance Improvement

rustworkx typically provides 10-100x performance improvement due to Rust-based implementation. For 10,000+ cell designs, this may become necessary.

---

## 12. Code Organization

```
src/ink/infrastructure/graph/
├── __init__.py              # Module exports
│   └── NetworkXGraphBuilder
│
└── networkx_adapter.py      # Implementation
    ├── NetworkXGraphBuilder
    │   ├── __init__
    │   ├── build_from_design
    │   ├── _add_cell_nodes
    │   ├── _add_pin_nodes
    │   ├── _add_net_nodes
    │   ├── _add_port_nodes
    │   ├── _add_cell_pin_edges
    │   ├── _add_pin_net_edges
    │   ├── _add_port_net_edges
    │   ├── get_graph
    │   ├── get_node_entity
    │   ├── get_node_type
    │   ├── node_count
    │   ├── edge_count
    │   ├── cell_node_count
    │   └── net_node_count
```

---

## 13. Downstream Usage

The Graph Query Interface (E01-F03-T04) will use this builder:

```python
from ink.infrastructure.graph import NetworkXGraphBuilder

class GraphQueryService:
    def __init__(self, design: Design):
        builder = NetworkXGraphBuilder()
        self.graph = builder.build_from_design(design)

    def fanout(self, cell_id: CellId) -> list[Cell]:
        """Find all cells driven by this cell's outputs."""
        # Use graph.successors() for traversal
        ...

    def fanin(self, cell_id: CellId) -> list[Cell]:
        """Find all cells that drive this cell's inputs."""
        # Use graph.predecessors() for traversal
        ...
```

---

## 14. Summary

The `NetworkXGraphBuilder` provides:

1. **Domain-to-Graph Translation**: Converts Design aggregate entities to a queryable graph structure

2. **Signal Flow Semantics**: Edge direction matches electrical signal propagation

3. **Entity References**: Direct access to domain objects from graph nodes

4. **Performance**: ~6ms for 1000-cell designs, linear scaling

5. **Maintainability**: Comprehensive documentation, type hints, 72 tests

This implementation forms the foundation for all graph-based connectivity queries in the Ink schematic viewer.
