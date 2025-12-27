# Implementation Narrative: E01-F01-T03 - Cell Instance Parser

## 1. The Problem We're Solving

When working with gate-level netlists in CDL (Circuit Description Language) format, one of the most fundamental operations is parsing cell instances. Every digital circuit is built from instances of standard cells - inverters, NAND gates, flip-flops, and more complex blocks. The challenge is to take a raw text line like:

```
XI1 net1 net2 VDD VSS INV
```

And transform it into structured data that our schematic viewer can use to build connectivity graphs and visualize the design.

### Why This Matters

The instance parser is the bridge between raw CDL text and the domain model. Without it, we can't:
- Know which cells exist in the design
- Understand how cells are connected via nets
- Build the graph structure needed for schematic visualization
- Support fanin/fanout exploration

### The Core Challenge

The trickiest part of instance parsing is **port mapping**. CDL instance lines use positional notation - the nets are listed in order matching the subcircuit definition. If we have:

```
.SUBCKT INV A Y VDD VSS
```

Then in `XI1 net1 net2 VDD VSS INV`:
- `net1` connects to port `A` (position 0)
- `net2` connects to port `Y` (position 1)
- `VDD` connects to port `VDD` (position 2)
- `VSS` connects to port `VSS` (position 3)

This requires coordination with the SubcircuitParser - we need the port list before we can interpret instance lines.

---

## 2. Designing the Solution

### Architecture Overview

Following the project's DDD architecture, we split the implementation into two layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    DOMAIN LAYER                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ CellInstance (Value Object)                           │  │
│  │ - name: str                                           │  │
│  │ - cell_type: str                                      │  │
│  │ - connections: MappingProxyType[str, str]             │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                 INFRASTRUCTURE LAYER                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ InstanceParser                                        │  │
│  │ - _subcircuit_defs: Dict[str, SubcircuitDefinition]  │  │
│  │ - _warnings: List[str]                                │  │
│  │ + parse_instance_line(token) -> CellInstance          │  │
│  │ + get_warnings() -> List[str]                         │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Why this split?**

- `CellInstance` is a pure domain concept - it represents the *idea* of a cell instance without any knowledge of CDL syntax or file parsing
- `InstanceParser` is infrastructure - it knows about CDL format, tokens, and how to parse them

This separation means we could later support other netlist formats (Verilog, EDIF) by adding new parsers that produce the same `CellInstance` objects.

### Key Design Decisions

#### 1. Immutability via MappingProxyType

The `CellInstance.connections` dictionary must be immutable because:
- Value objects should not change after creation
- The same instance may be referenced from multiple places
- Accidental mutation could corrupt the design graph

We use `MappingProxyType` from the standard library:

```python
from types import MappingProxyType

frozen_connections = MappingProxyType(dict(connections))
```

This gives us a read-only view that still supports dict-like access (`instance.connections["A"]`) but raises `TypeError` on modification attempts.

#### 2. Graceful Degradation for Unknown Cells

Real-world CDL files often reference cells from libraries that aren't included. Rather than failing the entire parse, we:
1. Log a warning with the unknown cell type
2. Create generic port names (`port0`, `port1`, etc.)
3. Continue parsing

This enables partial design loading - users can view known portions while being alerted to missing definitions.

#### 3. TDD-First Development

We used strict TDD for this implementation:

```
RED:   Write failing tests (22 for CellInstance, 28 for InstanceParser)
GREEN: Implement minimal code to pass
REFACTOR: Clean up while tests stay green
```

This approach caught several edge cases early:
- Lowercase 'x' prefix should be valid
- Empty connections dict should be allowed (filler cells)
- Bus notation in net names (`data<7>`) should work

---

## 3. The CellInstance Value Object

### Location: `src/ink/domain/value_objects/instance.py`

### Core Implementation

```python
@dataclass(frozen=True)
class CellInstance:
    """Immutable cell instance from CDL X-prefixed lines."""

    name: str
    cell_type: str
    connections: MappingProxyType[str, str]

    def __init__(
        self,
        name: str,
        cell_type: str,
        connections: Mapping[str, str],
    ) -> None:
        # Validate name is not empty
        if not name:
            raise ValueError("Instance name cannot be empty")

        # Validate name starts with X (case-insensitive)
        if not name[0].upper() == "X":
            raise ValueError(f"Instance name {name!r} must start with 'X'")

        # Validate cell_type is not empty
        if not cell_type:
            raise ValueError(f"Instance {name!r} missing cell type")

        # Create immutable copy of connections
        frozen_connections = MappingProxyType(dict(connections))

        # Use object.__setattr__ because frozen=True
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "cell_type", cell_type)
        object.__setattr__(self, "connections", frozen_connections)
```

### Why Custom `__init__`?

Normally, `@dataclass` generates `__init__` automatically. We override it because:

1. **Validation**: We need to check invariants before storing values
2. **Transformation**: We convert the `connections` dict to `MappingProxyType`
3. **Frozen workaround**: `frozen=True` prevents normal assignment, so we use `object.__setattr__`

### Equality and Hashing

Value objects should be comparable by value, not identity:

```python
def __hash__(self) -> int:
    # MappingProxyType isn't hashable, so convert to frozenset
    conn_items = frozenset(self.connections.items())
    return hash((self.name, self.cell_type, conn_items))

def __eq__(self, other: object) -> bool:
    if not isinstance(other, CellInstance):
        return NotImplemented
    return (
        self.name == other.name
        and self.cell_type == other.cell_type
        and dict(self.connections) == dict(other.connections)
    )
```

This enables using `CellInstance` in sets and as dict keys.

---

## 4. The InstanceParser

### Location: `src/ink/infrastructure/parsing/instance_parser.py`

### Initialization

```python
class InstanceParser:
    def __init__(self, subcircuit_defs: dict[str, SubcircuitDefinition]) -> None:
        self._subcircuit_defs = subcircuit_defs
        self._warnings: list[str] = []
```

The parser needs subcircuit definitions to map nets to ports. These come from the `SubcircuitParser` after processing `.SUBCKT` lines.

### Main Parsing Method

```python
def parse_instance_line(self, token: CDLToken) -> CellInstance:
    content = token.content.strip()

    if not content:
        raise ValueError(f"Empty instance line at line {token.line_num}")

    parts = content.split()

    if len(parts) < 2:  # Need at least name + cell_type
        raise ValueError(f"Invalid instance format at line {token.line_num}")

    # Extract components
    instance_name = parts[0]      # First token
    cell_type = parts[-1]         # Last token
    net_list = parts[1:-1]        # Everything in between

    # Map nets to ports
    connections = self._map_connections(
        net_list, cell_type, instance_name, token.line_num
    )

    return CellInstance(
        name=instance_name,
        cell_type=cell_type,
        connections=connections,
    )
```

### The Port Mapping Algorithm

This is the heart of the parser:

```python
def _map_connections(
    self,
    nets: list[str],
    cell_type: str,
    instance_name: str,
    line_num: int,
) -> dict[str, str]:
    definition = self._subcircuit_defs.get(cell_type)

    if definition is None:
        # Unknown cell type - warn and use generic ports
        self._warnings.append(
            f"Line {line_num}: Unknown cell type '{cell_type}' "
            f"for instance '{instance_name}'"
        )
        return {f"port{i}": net for i, net in enumerate(nets)}

    ports = definition.ports

    # Validate and log mismatches
    self._validate_connection_count(len(nets), len(ports), instance_name, line_num)

    # Map based on count comparison
    if len(nets) < len(ports):
        return dict(zip(ports[:len(nets)], nets, strict=True))
    elif len(nets) > len(ports):
        return dict(zip(ports, nets[:len(ports)], strict=True))
    else:
        return dict(zip(ports, nets, strict=True))
```

**Key insight**: We use `strict=True` in `zip()` after pre-slicing to ensure lengths match. This catches programming errors while still handling mismatches gracefully.

---

## 5. Data Flow Visualization

### Complete Parsing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CDL FILE                                        │
│  .SUBCKT INV A Y VDD VSS                                                │
│  .ENDS INV                                                              │
│  XI1 net1 net2 VDD VSS INV                                              │
└───────────────────────────────────────────┬─────────────────────────────┘
                                            │
                                            ▼
┌───────────────────────────────────────────────────────────────────────┐
│                         CDLLexer                                        │
│  Tokenizes file into CDLToken objects                                   │
│  Token(line_num=3, line_type=INSTANCE, content="XI1 net1...")          │
└───────────────────────────────────────────┬─────────────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    │                                               │
                    ▼                                               ▼
┌───────────────────────────────────┐     ┌─────────────────────────────────┐
│        SubcircuitParser           │     │        InstanceParser           │
│  Parses .SUBCKT/.ENDS blocks      │     │  (depends on SubcircuitParser)  │
│                                   │     │                                 │
│  Output:                          │────▶│  Uses definitions for mapping   │
│  SubcircuitDefinition("INV",      │     │                                 │
│    ["A", "Y", "VDD", "VSS"])      │     │  Output:                        │
└───────────────────────────────────┘     │  CellInstance(                  │
                                          │    name="XI1",                  │
                                          │    cell_type="INV",             │
                                          │    connections={                │
                                          │      "A": "net1",               │
                                          │      "Y": "net2",               │
                                          │      "VDD": "VDD",              │
                                          │      "VSS": "VSS"               │
                                          │    }                            │
                                          │  )                              │
                                          └─────────────────────────────────┘
```

### Connection Mapping Detail

```
Input: "XI1 net1 net2 VDD VSS INV"

┌─────────────────────────────────────────────────────────────────────────┐
│ Step 1: Split on whitespace                                             │
│                                                                         │
│ parts = ["XI1", "net1", "net2", "VDD", "VSS", "INV"]                   │
│           │       │       │       │       │      │                      │
│           │       └───────┴───────┴───────┘      │                      │
│           │               net_list               │                      │
│           │         (middle elements)            │                      │
│           │                                      │                      │
│           └──────────────────────────────────────┘                      │
│              instance_name          cell_type                           │
│                (first)               (last)                             │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Step 2: Look up SubcircuitDefinition for "INV"                          │
│                                                                         │
│ definition.ports = ("A", "Y", "VDD", "VSS")                            │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ Step 3: Zip ports with nets                                             │
│                                                                         │
│ ports: ["A",    "Y",    "VDD",  "VSS"]                                 │
│           │       │       │       │                                     │
│           ▼       ▼       ▼       ▼                                     │
│ nets:  ["net1", "net2", "VDD", "VSS"]                                  │
│                                                                         │
│ Result: {"A": "net1", "Y": "net2", "VDD": "VDD", "VSS": "VSS"}         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Error Handling Philosophy

### Recoverable vs Unrecoverable Errors

| Situation | Action | Reason |
|-----------|--------|--------|
| Empty line content | Raise `ValueError` | Malformed CDL, can't continue |
| Missing cell type | Raise `ValueError` | Line structure is invalid |
| Invalid instance name | Raise `ValueError` | Violates CDL spec |
| Unknown cell type | Warning + generic ports | Design may still be useful |
| Connection mismatch | Warning + partial map | May be intentional |

### Warning Message Format

Warnings include context for debugging:

```
Line 42: Unknown cell type 'UNKNOWN_CELL' for instance 'XI1'
Line 55: Instance 'XI_BUF' has too few connections: expected 4, got 2
```

---

## 7. Testing Strategy

### Test Organization

```
tests/
└── unit/
    ├── domain/
    │   └── value_objects/
    │       └── test_instance.py      # 22 tests for CellInstance
    └── infrastructure/
        └── parsing/
            └── test_instance_parser.py  # 28 tests for InstanceParser
```

### Test Categories and Examples

#### CellInstance Tests

```python
# Construction
def test_create_simple_instance():
    instance = CellInstance(name="XI1", cell_type="INV", connections={...})
    assert instance.name == "XI1"

# Validation
def test_name_missing_x_prefix_raises_error():
    with pytest.raises(ValueError, match="must start with 'X'"):
        CellInstance(name="I1", cell_type="INV", connections={})

# Immutability
def test_connections_is_immutable():
    instance = CellInstance(...)
    assert isinstance(instance.connections, MappingProxyType)
    with pytest.raises(TypeError):
        instance.connections["A"] = "modified"
```

#### InstanceParser Tests

```python
# Basic parsing
def test_parse_simple_instance():
    defs = {"INV": SubcircuitDefinition("INV", ["A", "Y", "VDD", "VSS"])}
    parser = InstanceParser(defs)
    token = CDLToken(5, LineType.INSTANCE, "XI1 net1 net2 VDD VSS INV", "...")
    instance = parser.parse_instance_line(token)
    assert instance.connections == {"A": "net1", "Y": "net2", ...}

# Unknown cells
def test_unknown_cell_type_warning():
    parser = InstanceParser({})
    token = CDLToken(5, LineType.INSTANCE, "XI1 net1 net2 UNKNOWN", "...")
    instance = parser.parse_instance_line(token)
    assert len(parser.get_warnings()) > 0
    assert "UNKNOWN" in parser.get_warnings()[0]
```

---

## 8. Integration with Existing Code

### Import from Package

After implementation, the new components are accessible via package imports:

```python
# Domain layer
from ink.domain.value_objects import CellInstance

# Infrastructure layer
from ink.infrastructure.parsing import InstanceParser
```

### Updated `__init__.py` Files

**`src/ink/domain/value_objects/__init__.py`**:
```python
from ink.domain.value_objects.instance import CellInstance
__all__ = ["CellInstance", "NetInfo", "NetType", "SubcircuitDefinition"]
```

**`src/ink/infrastructure/parsing/__init__.py`**:
```python
from ink.infrastructure.parsing.instance_parser import InstanceParser
__all__ = [..., "InstanceParser", ...]
```

---

## 9. Future Extensions

### Potential Enhancements

1. **Warning Deduplication**: If 1000 instances reference unknown cell `MISSING_X1`, we could consolidate to a single warning with a count.

2. **Strict Mode**: Add an optional `strict=True` parameter to raise errors instead of warnings, useful for development/debugging.

3. **Alternative Hierarchy Separators**: Some tools use `.` or `_` instead of `/` for hierarchy. Could add configuration.

4. **Port Direction Tracking**: Currently we only track port names. We could integrate with the PinDirection service to know which ports are inputs/outputs.

---

## 10. Conclusion

The Cell Instance Parser implementation successfully achieves its goals:

- **Correct Parsing**: Handles standard CDL instance format
- **Robust Mapping**: Uses subcircuit definitions for named ports
- **Graceful Degradation**: Unknown cells and mismatches produce warnings, not crashes
- **Clean Architecture**: Separates domain concepts from infrastructure concerns
- **Well Tested**: 50 tests cover normal operation, edge cases, and error conditions

The implementation follows TDD principles, DDD architecture, and the project's established patterns, making it consistent with the rest of the codebase and easy to maintain.
