# E01-F02-T02: Direction Lookup Service - Implementation Narrative

## Overview

This document tells the story of implementing the Direction Lookup Service for the Ink schematic viewer. It provides a comprehensive technical walkthrough that enables developers to fully understand the implementation without reading source code.

---

## 1. The Problem We're Solving

### Business Context

Ink is a schematic viewer for gate-level netlists. When building the schematic graph, we need to know the **direction** of each pin (INPUT, OUTPUT, or INOUT) to:
- Determine fanin/fanout traversal paths
- Render pins correctly (inputs on left, outputs on right)
- Validate connectivity

### Technical Challenge

The `.pindir` file parser (E01-F02-T01) produces a `PinDirectionMap` - a simple dictionary wrapper. But the rest of the application needs a **service API** with:
- Type-safe protocol for dependency injection
- Default behavior for unknown pins
- Logging for troubleshooting
- Utility methods for statistics and filtering

### Solution

Create a **domain service interface** (`PinDirectionService` protocol) with an **infrastructure implementation** (`PinDirectionServiceImpl`), following Clean Architecture principles.

---

## 2. Architecture Decision: Protocol Pattern

### Why Protocol over ABC?

We chose Python's `typing.Protocol` instead of `abc.ABC`:

```python
# Protocol approach (what we chose):
from typing import Protocol

class PinDirectionService(Protocol):
    def get_direction(self, pin_name: str) -> PinDirection:
        ...
```

**Benefits**:
1. **Structural typing**: Any class with matching methods satisfies the protocol
2. **Easier testing**: Mock classes don't need inheritance
3. **No runtime overhead**: Protocol is purely a type-checking construct
4. **Pythonic**: Aligns with duck typing philosophy

**Trade-off**: Slightly less explicit than ABC, but Python's type checkers handle this well.

### Layer Separation

```
┌─────────────────────────────────┐
│  Domain Layer                   │
│  pin_direction_service.py       │
│  (Protocol - just the contract) │
└───────────────┬─────────────────┘
                │ depends on
                ▼
┌─────────────────────────────────┐
│  Infrastructure Layer           │
│  pin_direction_service_impl.py  │
│  (Concrete implementation)      │
└─────────────────────────────────┘
```

This enables:
- Domain layer has no infrastructure dependencies
- Easy to swap implementations (database-backed, cached, etc.)
- Testing can use simple mock classes

---

## 3. Implementation Walkthrough

### 3.1 Domain Protocol (`pin_direction_service.py`)

**Location**: `src/ink/domain/services/pin_direction_service.py`

The protocol defines three core methods:

```python
class PinDirectionService(Protocol):
    def get_direction(self, pin_name: str) -> PinDirection:
        """Get direction for a pin name. Returns INOUT if not found."""
        ...

    def has_pin(self, pin_name: str) -> bool:
        """Check if pin name exists in the direction mapping."""
        ...

    def get_all_pins(self) -> dict[str, PinDirection]:
        """Get all pin name to direction mappings."""
        ...
```

**Design Rationale**:
- `get_direction()`: Core lookup - returns default INOUT to avoid exceptions
- `has_pin()`: Distinguishes "not found" from "explicitly INOUT"
- `get_all_pins()`: Bulk access for UI/debugging

### 3.2 Infrastructure Implementation (`pin_direction_service_impl.py`)

**Location**: `src/ink/infrastructure/services/pin_direction_service_impl.py`

The implementation wraps `PinDirectionMap` from the parser:

```python
@dataclass
class PinDirectionServiceImpl:
    _direction_map: PinDirectionMap
    _logger: logging.Logger | None = field(default=None)

    def __post_init__(self) -> None:
        if self._logger is None:
            self._logger = logging.getLogger(__name__)
```

**Key Implementation Details**:

1. **Dataclass Pattern**: Simple, immutable-ish structure with automatic `__init__`

2. **Logger Injection**: Optional logger for testing:
   ```python
   # Production: auto-creates logger
   service = PinDirectionServiceImpl(_direction_map=map)

   # Testing: inject mock logger
   mock_logger = MagicMock()
   service = PinDirectionServiceImpl(_direction_map=map, _logger=mock_logger)
   ```

3. **Default INOUT Behavior**:
   ```python
   def get_direction(self, pin_name: str) -> PinDirection:
       direction = self._direction_map.get_direction(pin_name)

       if not self.has_pin(pin_name):
           self._logger.debug(
               f"Pin '{pin_name}' not found in direction mapping. "
               f"Defaulting to INOUT."
           )

       return direction
   ```

4. **Copy Protection in `get_all_pins()`**:
   ```python
   def get_all_pins(self) -> dict[str, PinDirection]:
       return self._direction_map.directions.copy()  # Returns copy!
   ```

### 3.3 Extended Methods

The implementation adds utility methods not in the protocol:

```python
def get_pin_count(self) -> int:
    """Get total number of pins with defined directions."""
    return len(self._direction_map.directions)

def get_pins_by_direction(self, direction: PinDirection) -> list[str]:
    """Get all pin names with a specific direction."""
    return [
        pin_name
        for pin_name, pin_dir in self._direction_map.directions.items()
        if pin_dir == direction
    ]
```

These are useful for:
- Logging: "Loaded 150 pin directions"
- Debugging: "Show all OUTPUT pins"
- Statistics: Direction distribution

---

## 4. Test-Driven Development Journey

### 4.1 RED Phase: Writing Failing Tests

We wrote 32 unit tests covering:

**Core Functionality** (15 tests):
- `get_direction()` for INPUT, OUTPUT, INOUT pins
- `get_direction()` for unknown pins (default INOUT)
- `has_pin()` for existing and missing pins
- `get_all_pins()` returning complete mapping

**Edge Cases** (5 tests):
- Empty direction map
- Large direction map (1000+ pins)
- Special characters in pin names (`net[0]`, `data<31>`)
- Numeric pin names (`"0"`, `"123"`)

**Behavior** (12 tests):
- Case sensitivity (`CLK` vs `clk`)
- Logging for unknown pins
- Immutability of returned data
- Performance (O(1) lookup)

### 4.2 GREEN Phase: Making Tests Pass

The implementation was straightforward because:
1. `PinDirectionMap` already had `get_direction()` and `has_pin()`
2. We just wrapped it with logging and utility methods
3. Dataclass pattern made initialization trivial

All 32 tests passed on first implementation.

### 4.3 REFACTOR Phase

Minor refactoring:
- Fixed import sorting (ruff auto-fix)
- Removed unused `Optional` import (replaced with `| None` syntax)
- Verified 100% code coverage

---

## 5. Data Flow Diagram

```
┌────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  .pindir file  │────▶│ PinDirectionParser│────▶│   PinDirectionMap   │
│                │     │                  │     │ {pin: direction}    │
└────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                           │
                                                           ▼
                       ┌───────────────────────────────────────────────┐
                       │         PinDirectionServiceImpl               │
                       │  ┌─────────────────────────────────────────┐  │
                       │  │ get_direction("A") → PinDirection.INPUT │  │
                       │  │ has_pin("A") → True                     │  │
                       │  │ get_all_pins() → {dict copy}            │  │
                       │  │ get_pin_count() → 150                   │  │
                       │  │ get_pins_by_direction(INPUT) → ["A",...] │  │
                       │  └─────────────────────────────────────────┘  │
                       └───────────────────────────────────────────────┘
                                           │
                                           ▼
                       ┌───────────────────────────────────────────────┐
                       │  Graph Construction (E01-F03)                 │
                       │  - Creates Pin entities with directions       │
                       │  - Determines fanin/fanout traversal          │
                       └───────────────────────────────────────────────┘
```

---

## 6. Performance Characteristics

| Operation | Complexity | Notes |
|-----------|------------|-------|
| `get_direction()` | O(1) | Dictionary lookup |
| `has_pin()` | O(1) | Dictionary `in` check |
| `get_all_pins()` | O(n) | Dictionary copy |
| `get_pin_count()` | O(1) | `len()` on dict |
| `get_pins_by_direction()` | O(n) | Filter through all pins |

**Benchmarks** (from integration tests):
- Service creation: < 0.001ms average
- 1000 lookups on 10000-pin map: same time as 100-pin map (O(1) verified)
- `get_all_pins()` copy overhead: < 1ms for 1000 pins

---

## 7. Error Handling Strategy

**Philosophy**: No exceptions for normal operation

| Scenario | Behavior |
|----------|----------|
| Unknown pin | Return INOUT, log DEBUG |
| Empty map | All lookups return INOUT |
| Case mismatch | Treated as unknown pin |

This design choice ensures:
- Graph construction never fails due to missing pins
- Debug logging helps identify configuration issues
- Consistent behavior across all code paths

---

## 8. Integration Points

### 8.1 Upstream Dependency

**E01-F02-T01: Pindir Parser**
```python
from ink.infrastructure.parsing.pindir_parser import (
    PinDirectionParser,
    PinDirectionMap,
)
```

### 8.2 Downstream Usage

**E01-F03: Graph Construction** (planned)
```python
def create_pin(name: str, service: PinDirectionService) -> Pin:
    direction = service.get_direction(name)
    return Pin(name=name, direction=direction)
```

**Application Layer: FileService** (planned)
```python
def load_pin_directions(self, path: Path) -> PinDirectionServiceImpl:
    parser = PinDirectionParser()
    direction_map = parser.parse_file(path)
    return PinDirectionServiceImpl(_direction_map=direction_map)
```

---

## 9. Debugging Tips

### Enable Debug Logging

```python
import logging
logging.getLogger("ink.infrastructure.services").setLevel(logging.DEBUG)

# Now unknown pin lookups will log:
# DEBUG: Pin 'UNKNOWN' not found in direction mapping. Defaulting to INOUT.
```

### Check What's Loaded

```python
service = PinDirectionServiceImpl(_direction_map=map)
print(f"Loaded {service.get_pin_count()} pins")
print(f"Inputs: {service.get_pins_by_direction(PinDirection.INPUT)}")
print(f"Outputs: {service.get_pins_by_direction(PinDirection.OUTPUT)}")
```

### Verify Pin Exists

```python
if not service.has_pin("CLK"):
    print("Warning: CLK not in pindir file!")
```

---

## 10. Lessons Learned

### What Went Well

1. **TDD Worked Perfectly**: Tests written first made implementation trivial
2. **Protocol Pattern**: Clean separation, easy testing
3. **Dataclass**: Minimal boilerplate for simple wrapper

### What Could Be Better

1. **No Caching**: Repeated unknown pin lookups log multiple times
2. **No Statistics**: Could track query patterns for optimization
3. **No Validation**: Doesn't detect pins with conflicting directions

These are documented as future enhancements in the spec.

---

## 11. Checklist for Similar Tasks

When implementing a domain service:

- [ ] Define Protocol in domain layer
- [ ] Implement in infrastructure layer
- [ ] Use dataclass for simple state
- [ ] Provide safe defaults (don't throw exceptions)
- [ ] Return copies for mutable data
- [ ] Add optional logger for testing
- [ ] Write comprehensive tests (edge cases!)
- [ ] Document design decisions
- [ ] Consider performance implications

---

## 12. References

- [E01-F02-T02.spec.md](./E01-F02-T02.spec.md) - Original specification
- [E01-F02-T02.post-docs.md](./E01-F02-T02.post-docs.md) - Quick reference
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html) - Architecture pattern
- [Python Protocols](https://docs.python.org/3/library/typing.html#typing.Protocol) - Official docs
