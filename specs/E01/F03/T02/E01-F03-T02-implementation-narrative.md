# E01-F03-T02: Design Aggregate Root - Implementation Narrative

## The Story

This document tells the complete story of implementing the Design aggregate root - the central data structure that manages all domain entities in a netlist. It's written for developers who need to understand not just *what* was built, but *why* each decision was made.

## Context: Why We Need a Design Aggregate

### The Problem

The Ink schematic viewer needs to manage four types of entities:
- **Cells**: Gate-level instances (INV_X1, DFF_X1, etc.)
- **Pins**: Connection points on cells (A, Y, CLK, etc.)
- **Nets**: Wires connecting pins
- **Ports**: Top-level I/O of the design

Without a central coordinator, code would need to:
- Query multiple collections for related data
- Manually maintain consistency between collections
- Handle cross-references without validation
- Duplicate lookup logic across services

### The Solution: Aggregate Root Pattern

Following Domain-Driven Design, we created a `Design` aggregate that:
1. Acts as the single entry point for all netlist operations
2. Maintains dual indexes for O(1) lookup by ID and name
3. Enforces domain invariants (no duplicates, valid references)
4. Provides validation for referential integrity

## The Journey: TDD Implementation

### Phase 1: RED - Writing Failing Tests First

We started by imagining how the Design aggregate should be used:

```python
# What we wanted to write:
design = Design(name="inverter")
design.add_cell(cell)
design.get_cell_by_name("XI1")  # O(1) lookup
errors = design.validate()      # Check consistency
```

This led to 63 comprehensive tests across 11 test classes:

| Test Class | Purpose | Test Count |
|------------|---------|------------|
| `TestDesignCreation` | Construction and initialization | 3 |
| `TestAddCell` | Adding cells with duplicate detection | 5 |
| `TestAddNet` | Adding nets with duplicate detection | 4 |
| `TestAddPin` | Adding pins with duplicate detection | 4 |
| `TestAddPort` | Adding ports with duplicate detection | 4 |
| `TestGettersById` | O(1) lookup by typed ID | 8 |
| `TestGettersByName` | O(1) lookup by name string | 6 |
| `TestCollectionAccessors` | Defensive copies of collections | 10 |
| `TestStatistics` | Count methods | 6 |
| `TestValidation` | Referential integrity checks | 9 |
| `TestIntegration` | Complete design building | 2 |

**Key Test Design Decisions:**

1. **Factory helpers** - Keep tests DRY with `create_test_cell()`, `create_test_net()`, etc.
2. **Positive and negative cases** - Test both success paths and error conditions
3. **Edge cases** - Empty designs, None values, collection modifications

### Phase 2: GREEN - Making Tests Pass

The implementation followed the test requirements exactly. Key insights:

#### Insight 1: Dual-Index Architecture

We needed fast lookups by both ID and name. The solution:

```python
@dataclass
class Design:
    # Primary storage: ID -> Entity (for type safety)
    _cells: dict[CellId, Cell] = field(default_factory=dict)

    # Secondary index: Name -> ID (for user-facing queries)
    _cell_name_index: dict[str, CellId] = field(default_factory=dict)

    def add_cell(self, cell: Cell) -> None:
        # Update both atomically
        self._cells[cell.id] = cell
        self._cell_name_index[cell.name] = cell.id

    def get_cell_by_name(self, name: str) -> Cell | None:
        # Two-step lookup through index
        cell_id = self._cell_name_index.get(name)
        return self._cells.get(cell_id) if cell_id else None
```

**Why this matters**: Graph traversal uses IDs for efficiency, but users search by name. Dual indexes serve both use cases at O(1).

#### Insight 2: Pins Don't Get Name Index

Unlike cells, nets, and ports, pins share names across different cells (many cells have an "A" pin). So we only index pins by ID:

```python
def add_pin(self, pin: Pin) -> None:
    # No name index for pins - names not globally unique
    if pin.id in self._pins:
        raise ValueError(f"Pin with id {pin.id} already exists")
    self._pins[pin.id] = pin
```

**Why this matters**: Trying to index pin names would create confusing overwrites (which "A" pin do you mean?). The full PinId (e.g., "XI1.A") is the unique identifier.

#### Insight 3: Eager vs Lazy Validation

We chose different validation strategies for different checks:

**Eager (fail immediately):**
- Duplicate ID detection
- Duplicate name detection

```python
def add_cell(self, cell: Cell) -> None:
    if cell.id in self._cells:
        raise ValueError(f"Cell with id {cell.id} already exists")
    if cell.name in self._cell_name_index:
        raise ValueError(f"Cell with name {cell.name} already exists")
```

**Lazy (check after construction):**
- Pin → Net references
- Cell → Pin references
- Net → Pin references
- Port → Net references

```python
def validate(self) -> list[str]:
    errors = []
    for pin in self._pins.values():
        if pin.net_id and pin.net_id not in self._nets:
            errors.append(f"Pin {pin.id} references non-existent net")
    # ... more checks
    return errors
```

**Why this split**: During parsing, entities arrive in arbitrary order. A pin might reference a net that hasn't been added yet. Lazy validation allows the parser to add entities in any order, then validate the complete design.

### Phase 3: REFACTOR - Cleaning Up

The implementation was already clean from TDD, but we identified one major refactoring need:

#### The ParsedDesign Separation

When running the full test suite, we discovered that the CDL parser tests failed:

```
TypeError: Design.__init__() got an unexpected keyword argument 'subcircuit_defs'
```

**The Problem**: The CDL parser was using the old Design class that worked with value objects (`CellInstance`, `NetInfo`, `SubcircuitDefinition`). Our new Design works with domain entities (`Cell`, `Pin`, `Net`, `Port`).

**The Solution**: Create two separate classes:

1. **`ParsedDesign`** (infrastructure layer) - Output of CDL parser
   - Works with value objects from parsing
   - Lives in `src/ink/infrastructure/parsing/`

2. **`Design`** (domain layer) - Aggregate for domain operations
   - Works with domain entities
   - Lives in `src/ink/domain/model/`

```
Parsing Pipeline:
CDL File → CDLParser → ParsedDesign → [Future: DesignBuilder] → Design
```

This follows the DDD layer separation:
```
Infrastructure (ParsedDesign)
      ↓
Application (Builder) [Future: E01-F03-T03]
      ↓
Domain (Design)
```

## The Code: A Deep Dive

### File: `src/ink/domain/model/design.py`

This is the heart of the implementation. Let's walk through the key sections:

#### Module Docstring (lines 1-57)

```python
"""Design aggregate root for the domain layer.

This module defines the Design class, which serves as the aggregate root for
managing all domain entities in a netlist: Cell, Pin, Net, and Port.
...
"""
```

The docstring explains:
- Architectural context (domain layer, aggregate root)
- Key design decisions (mutable aggregate, dual indexes, hybrid validation)
- Usage examples

#### Class Definition (lines 72-112)

```python
@dataclass
class Design:
    """Aggregate root managing all netlist entities.
    ...
    """
    name: str

    # Primary Storage
    _cells: dict[CellId, Cell] = field(default_factory=dict, repr=False)
    _nets: dict[NetId, Net] = field(default_factory=dict, repr=False)
    _pins: dict[PinId, Pin] = field(default_factory=dict, repr=False)
    _ports: dict[PortId, Port] = field(default_factory=dict, repr=False)

    # Secondary Indexes
    _cell_name_index: dict[str, CellId] = field(default_factory=dict, repr=False)
    _net_name_index: dict[str, NetId] = field(default_factory=dict, repr=False)
    _port_name_index: dict[str, PortId] = field(default_factory=dict, repr=False)
```

Notice:
- Using `@dataclass` for concise constructor
- `field(default_factory=dict)` for mutable defaults
- `repr=False` keeps `__repr__` clean
- Private attributes with `_` prefix

#### Add Methods (lines 153-191, etc.)

```python
def add_cell(self, cell: Cell) -> None:
    """Add a cell to the design.
    ...
    """
    # Eager validation: check for duplicate ID first
    if cell.id in self._cells:
        raise ValueError(f"Cell with id {cell.id} already exists")

    # Check for duplicate name in the index
    if cell.name in self._cell_name_index:
        raise ValueError(f"Cell with name {cell.name} already exists")

    # Add to primary storage and update name index atomically
    self._cells[cell.id] = cell
    self._cell_name_index[cell.name] = cell.id
```

The pattern is consistent across all add methods:
1. Check ID uniqueness
2. Check name uniqueness (except pins)
3. Add to primary storage
4. Update secondary index

#### Validation Method (lines 482-538)

```python
def validate(self) -> list[str]:
    """Validate design referential integrity.
    ...
    """
    errors: list[str] = []

    # Check pin → net references
    for pin in self._pins.values():
        if pin.net_id is not None and pin.net_id not in self._nets:
            errors.append(
                f"Pin {pin.id} references non-existent net {pin.net_id}"
            )

    # Check cell → pin references
    for cell in self._cells.values():
        for pin_id in cell.pin_ids:
            if pin_id not in self._pins:
                errors.append(
                    f"Cell {cell.id} references non-existent pin {pin_id}"
                )

    # ... more checks

    return errors
```

The validation is:
- Comprehensive: checks all reference types
- Non-destructive: returns errors, doesn't throw
- Aggregating: collects ALL errors, not just the first

### File: `src/ink/infrastructure/parsing/parsed_design.py`

This file mirrors the old Design API for backward compatibility with the parser:

```python
@dataclass
class ParsedDesign:
    """Infrastructure representation of parsed CDL data.
    ...
    """
    name: str
    subcircuit_defs: dict[str, SubcircuitDefinition] = field(default_factory=dict)
    instances: dict[str, CellInstance] = field(default_factory=dict)
    nets: dict[str, NetInfo] = field(default_factory=dict)
    top_level_ports: list[str] = field(default_factory=list)
```

Notice the difference from Design:
- Uses `SubcircuitDefinition`, `CellInstance`, `NetInfo` (value objects)
- Has `instances` instead of `cells`
- Has `top_level_ports` as strings instead of `Port` entities

## Testing Strategy

### Test Organization

```
tests/unit/domain/model/test_design_aggregate.py
├── Test Fixtures (factory functions)
├── TestDesignCreation
├── TestAddCell
├── TestAddNet
├── TestAddPin
├── TestAddPort
├── TestGettersById
├── TestGettersByName
├── TestCollectionAccessors
├── TestStatistics
├── TestValidation
├── TestRepr
└── TestIntegration
```

### Test Coverage Highlights

**Positive Cases:**
```python
def test_add_cell_success(self) -> None:
    """Should add cell to design and update indexes."""
    design = Design(name="test")
    cell = create_test_cell("XI1")
    design.add_cell(cell)
    assert design.get_cell(CellId("XI1")) == cell
    assert design.get_cell_by_name("XI1") == cell
```

**Negative Cases:**
```python
def test_add_cell_duplicate_id_raises_error(self) -> None:
    """Should raise ValueError when adding cell with duplicate ID."""
    design = Design(name="test")
    design.add_cell(create_test_cell("XI1"))

    with pytest.raises(ValueError, match=r"Cell with id .* already exists"):
        design.add_cell(create_test_cell("XI1"))
```

**Edge Cases:**
```python
def test_validate_pin_with_none_net_is_valid(self) -> None:
    """Floating pin (net_id=None) should be valid."""
    design = Design(name="test")
    floating_pin = create_test_pin("XI1.NC", net_id=None)
    design.add_pin(floating_pin)

    errors = design.validate()
    assert errors == []
```

## Debugging Tips

### Common Issues

**1. "Cell with id X already exists"**
- Cause: Trying to add the same cell twice
- Fix: Check if cell exists before adding, or use a unique ID generator

**2. "Pin X references non-existent net Y"**
- Cause: Adding pin before adding the net it references
- Fix: Add nets first, or call `validate()` only after all entities are added

**3. Collection modification during iteration**
- Cause: Modifying `get_all_*()` results affects iteration
- Fix: The aggregate returns copies, so this shouldn't happen. If it does, you're modifying internal state directly.

### Debugging Checklist

1. Check entity IDs are unique
2. Check entity names are unique (except pins)
3. Call `validate()` to find reference errors
4. Use `repr(design)` for quick status check

## Integration Points

### Current

| Component | Method | Description |
|-----------|--------|-------------|
| CDL Parser | Returns `ParsedDesign` | Raw parsed data from CDL files |
| Domain Tests | Uses `Design` directly | Unit tests for aggregate behavior |

### Future (E01-F03-T03)

| Component | Method | Description |
|-----------|--------|-------------|
| DesignBuilder | `build(parsed: ParsedDesign) -> Design` | Transform parsed data to domain |
| Graph Service | `build_graph(design: Design) -> nx.DiGraph` | Create NetworkX graph for traversal |
| Expansion Service | `expand(design: Design, cell_id: CellId)` | Find connected cells |

## Conclusion

The Design aggregate implementation demonstrates:

1. **TDD Benefits**: Tests defined the API clearly before implementation
2. **DDD Patterns**: Aggregate root pattern ensures consistency
3. **Layer Separation**: Infrastructure (ParsedDesign) vs Domain (Design)
4. **Performance**: Dual indexes provide O(1) lookups for all use cases
5. **Maintainability**: Comprehensive documentation and tests

The implementation is ready for integration with the Graph Builder (E01-F03-T03) to complete the netlist loading pipeline.
