# Implementation Narrative: E01-F01-T04 - Net Name Normalization

> A comprehensive technical story of how net name normalization was designed and implemented for the Ink schematic viewer.

---

## 1. The Problem Space

### Why Net Name Normalization Matters

CDL (Circuit Description Language) netlists are text files that describe electronic circuit connectivity. When parsing these files, we encounter net names in various formats:

```
* Example CDL snippet
XI1 data<7> clk VDD! VSS output1 / AND2
XI2 data<6> clk VDD! VSS output2 / AND2
XI3 VDDA VSSA analog_in analog_out / OPAMP
```

**The Challenge**: The same logical net can appear with different representations:
- `VDD!` and `VDD` should be treated as the same power net
- `data<7>` (angle brackets) needs to match `data[7]` (square brackets)
- Power and ground nets need special handling (filtering, highlighting)

Without normalization, the schematic viewer would:
- Fail to connect instances that should be connected
- Display duplicate nets for the same signal
- Have no way to filter power/ground connections

---

## 2. Solution Design

### Domain Model: Value Objects

Following Domain-Driven Design principles, we created two value objects that represent normalized net information:

#### NetType Enumeration

```python
# src/ink/domain/value_objects/net.py:23-39

class NetType(Enum):
    """Classification of net types in a CDL netlist."""

    SIGNAL = "signal"   # Normal signal net (data, clock, control)
    POWER = "power"     # Power supply (VDD, VDDA, VCC, VPWR, etc.)
    GROUND = "ground"   # Ground reference (VSS, VSSA, GND, VGND, etc.)
```

**Design Rationale**: Using an enum instead of string constants:
- Provides IDE autocomplete and type checking
- Prevents typos (the compiler catches invalid values)
- Makes the domain concepts explicit in code

#### NetInfo Dataclass

```python
# src/ink/domain/value_objects/net.py:42-81

@dataclass(frozen=True)
class NetInfo:
    """Immutable value object representing normalized net information."""

    original_name: str          # "data<7>" - raw from CDL
    normalized_name: str        # "data[7]" - standardized
    net_type: NetType          # SIGNAL, POWER, or GROUND
    is_bus: bool               # True if part of a bus
    bus_index: int | None = None  # 7 for data<7>, None otherwise
```

**Why Immutable?**
1. **Thread Safety**: The normalizer cache can be accessed from multiple threads
2. **Hash Stability**: Can be used as dictionary keys (normalized name lookups)
3. **No Defensive Copying**: Safe to share references without cloning

---

## 3. The Normalization Algorithm

### High-Level Flow

```
Input: "data<7>!"
         │
         ▼
┌─────────────────────────────┐
│ 1. Strip trailing chars     │  "data<7>!" → "data<7>"
│    (!, ?)                   │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 2. Match bus pattern        │  Regex: ^(.+)<(\d+)>$
│    <N> or <M:N>             │  Match found!
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 3. Convert to [N] format    │  "data<7>" → "data[7]"
│    Extract bus_index        │  bus_index = 7
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ 4. Classify net type        │  "data" → SIGNAL
│    (check base name only)   │  (not VDD/VCC/VSS/GND)
└─────────────────────────────┘
         │
         ▼
Output: NetInfo(
    original_name="data<7>!",
    normalized_name="data[7]",
    net_type=NetType.SIGNAL,
    is_bus=True,
    bus_index=7
)
```

### Code Implementation

```python
# src/ink/infrastructure/parsing/net_normalizer.py:143-200

def _do_normalize(self, net_name: str) -> NetInfo:
    """Perform the actual normalization logic."""

    # Step 1: Strip trailing special characters
    # CDL uses ! to mark nets, but it doesn't affect identity
    cleaned = net_name.rstrip("!?")

    # Step 2: Check for bus notation
    bus_match = self.BUS_PATTERN.match(cleaned)
    if bus_match:
        base_name = bus_match.group(1)   # "data"
        bit_index = int(bus_match.group(2))  # 7
        normalized = f"{base_name}[{bit_index}]"
        net_type = self._classify_type(base_name)

        return NetInfo(
            original_name=net_name,
            normalized_name=normalized,
            net_type=net_type,
            is_bus=True,
            bus_index=bit_index,
        )

    # Step 3: Non-bus net - just classify
    net_type = self._classify_type(cleaned)
    return NetInfo(
        original_name=net_name,
        normalized_name=cleaned,
        net_type=net_type,
        is_bus=False,
    )
```

---

## 4. Power/Ground Detection

### Pattern Matching Strategy

We use regex patterns with case-insensitive matching:

```python
# src/ink/infrastructure/parsing/net_normalizer.py:67-87

POWER_PATTERNS: ClassVar[set[str]] = {
    r"^VDD[A-Z]*$",  # VDD, VDDA, VDDIO, VDDCORE
    r"^VCC[A-Z]*$",  # VCC, VCCA, VCCIO
    r"^VPWR$",       # VPWR
}

GROUND_PATTERNS: ClassVar[set[str]] = {
    r"^VSS[A-Z]*$",  # VSS, VSSA, VSSIO
    r"^GND[A-Z]*$",  # GND, GNDA, GNDIO
    r"^VGND$",       # VGND
}
```

**Pattern Explanation**:
- `^` - Start of string (full match required)
- `VDD` - Literal characters
- `[A-Z]*` - Zero or more uppercase letters (for suffixes)
- `$` - End of string

**Why These Patterns?**
- Covers common PDK (Process Design Kit) naming conventions
- Suffix matching handles domain-specific variants (VDDIO for I/O power)
- Case-insensitive handles both `VDD` and `vdd`

### Classification Logic

```python
# src/ink/infrastructure/parsing/net_normalizer.py:202-235

def _classify_type(self, net_name: str) -> NetType:
    """Classify a net name as POWER, GROUND, or SIGNAL."""

    # Check power patterns first
    for pattern in self.POWER_PATTERNS:
        if re.match(pattern, net_name, re.IGNORECASE):
            return NetType.POWER

    # Then ground patterns
    for pattern in self.GROUND_PATTERNS:
        if re.match(pattern, net_name, re.IGNORECASE):
            return NetType.GROUND

    # Default: regular signal
    return NetType.SIGNAL
```

**Important**: We classify the **base name** for bus signals. For `VDD<0>` (rare but possible), we extract `VDD` and classify it as POWER.

---

## 5. Performance Optimization: Caching

### The Problem

Large netlists can have millions of instances. Common nets like VDD and VSS appear on every cell:

```
* 1 million cells, each with VDD and VSS
XI1 ... VDD VSS ... / CELL
XI2 ... VDD VSS ... / CELL
...
XI1000000 ... VDD VSS ... / CELL
```

Without caching, we'd run regex matching 2 million times for just power/ground.

### The Solution

```python
# src/ink/infrastructure/parsing/net_normalizer.py:96-141

def __init__(self) -> None:
    """Initialize with empty cache."""
    self._net_cache: dict[str, NetInfo] = {}

def normalize(self, net_name: str) -> NetInfo:
    """Main entry point with caching."""

    # Cache hit - return immediately
    if net_name in self._net_cache:
        return self._net_cache[net_name]

    # Cache miss - normalize and store
    info = self._do_normalize(net_name)
    self._net_cache[net_name] = info
    return info
```

**Cache Characteristics**:
- Per-instance: Each `NetNormalizer` has its own cache
- Key: Original net name (before normalization)
- Value: Complete `NetInfo` object
- Identity preserved: Same object returned for same input

### Verification in Tests

```python
# tests/unit/infrastructure/parsing/test_net_normalizer.py

def test_cache_returns_same_object(self) -> None:
    """Test that repeated calls return cached object."""
    normalizer = NetNormalizer()

    info1 = normalizer.normalize("data<7>")
    info2 = normalizer.normalize("data<7>")

    # Identity check - same object in memory
    assert info1 is info2
```

---

## 6. Edge Case Handling

### Empty Net Names

```python
# Input: ""
# Output: NetInfo(normalized_name="", net_type=SIGNAL, is_bus=False)
```
Empty strings pass through unchanged. The caller should validate input.

### Only Special Characters

```python
# Input: "!?"
# Output: NetInfo(normalized_name="", net_type=SIGNAL, is_bus=False)
```
After stripping trailing `!?`, we get an empty string.

### No Base Name Before Bus Index

```python
# Input: "<5>"
# Output: NetInfo(normalized_name="<5>", is_bus=False)
```
The regex `^(.+)<...` requires at least one character before `<`. This is intentional - `<5>` alone is not a valid bus notation.

### Nested Angle Brackets

```python
# Input: "a<<7>>"
# Output: NetInfo(normalized_name="a<<7>>", is_bus=False)
```
Doesn't match the bus pattern. Preserved as-is.

---

## 7. TDD Development Process

### RED Phase: Write Failing Tests First

We started by writing 63 tests covering all functionality:

```python
# Test bus notation
def test_normalize_simple_bus_bit():
    info = normalizer.normalize("data<7>")
    assert info.normalized_name == "data[7]"
    assert info.is_bus is True
    assert info.bus_index == 7

# Test power detection
@pytest.mark.parametrize("net_name", ["VDD", "VDDA", "VDDIO", ...])
def test_power_net_detection(net_name):
    info = normalizer.normalize(net_name)
    assert info.net_type == NetType.POWER
```

All tests failed initially (no implementation).

### GREEN Phase: Make Tests Pass

Implemented the minimum code to pass all tests:

1. Created `NetType` enum
2. Created `NetInfo` dataclass
3. Implemented `NetNormalizer._do_normalize()`
4. Implemented `NetNormalizer._classify_type()`

After implementation: 63 tests passing.

### REFACTOR Phase: Improve Code Quality

1. Added `ClassVar` annotations for class attributes
2. Changed `Optional[int]` to `int | None` (modern Python)
3. Changed `Dict` to `dict` (built-in generics)
4. Added comprehensive docstrings

All tests still passing after refactoring.

---

## 8. Integration Points

### How Other Components Will Use This

```python
# Future CDL Parser usage
class CDLParser:
    def __init__(self):
        self.normalizer = NetNormalizer()

    def parse_instance(self, line: str) -> Instance:
        nets = extract_nets(line)

        connections = []
        for net_name in nets:
            net_info = self.normalizer.normalize(net_name)

            # Skip power/ground in certain views
            if not net_info.net_type == NetType.SIGNAL:
                continue

            # Use normalized name for connectivity matching
            connections.append(Connection(
                net_id=net_info.normalized_name,
                is_bus=net_info.is_bus,
                bus_index=net_info.bus_index,
            ))

        return Instance(connections=connections)
```

### Downstream Dependencies

This task is a dependency for:
- **E01-F01-T03** (Instance Parser): Uses normalization for net connections
- **E01-F01-T05** (Parser Integration): Uses net type for global net identification

---

## 9. Quality Assurance

### Test Results

```
============================= test session starts ==============================
collected 63 items

tests/unit/domain/value_objects/test_net.py .............. (14 passed)
tests/unit/infrastructure/parsing/test_net_normalizer.py ............... (49 passed)

============================== 63 passed in 0.05s ==============================
```

### Linting and Type Checking

```bash
$ ruff check src/ink/domain/ src/ink/infrastructure/parsing/
All checks passed!

$ mypy src/ink/domain/ src/ink/infrastructure/parsing/
Success: no issues found in 5 source files
```

---

## 10. Summary

### What We Built

A complete net name normalization system with:
- **Domain value objects** following DDD principles
- **Infrastructure normalizer** with clean separation of concerns
- **Comprehensive test suite** with 63 passing tests
- **Performance optimization** through intelligent caching

### Key Takeaways

1. **Immutable value objects** simplify caching and concurrency
2. **Regex patterns with ClassVar** avoid recreating patterns per instance
3. **TDD** caught edge cases early (like `<5>` without base name)
4. **Separation of concerns**: Domain models know nothing about parsing

### Next Steps

The `NetNormalizer` is ready for integration with:
1. The CDL parser (E01-F01-T03)
2. The connectivity graph builder
3. The schematic renderer (for filtering power/ground)
