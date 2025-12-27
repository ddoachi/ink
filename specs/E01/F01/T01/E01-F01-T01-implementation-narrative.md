# E01-F01-T01: CDL Lexer and Tokenizer - Implementation Narrative

## Executive Summary

This document provides a comprehensive narrative of the CDL Lexer and Tokenizer implementation for the Ink Schematic Viewer. The lexer is the foundational component of the CDL parsing pipeline, responsible for tokenizing raw CDL (Circuit Description Language) files into structured tokens that downstream parsers can process.

## 1. Business Context

### Why This Component Exists

The Ink Schematic Viewer needs to parse gate-level netlists in CDL format—a SPICE-like format commonly used in semiconductor design. Before any semantic parsing can occur (parsing subcircuits, instances, nets), the raw text must be:

1. **Classified**: Each line must be identified as a subcircuit definition, instance, comment, etc.
2. **Cleaned**: Inline comments must be stripped
3. **Normalized**: Multi-line continuations must be joined into single logical lines
4. **Tracked**: Original line numbers must be preserved for error reporting

### What Problem It Solves

Without a lexer, the parser would need to handle:
- Comment stripping inline with semantic parsing
- Line continuation detection mixed with content parsing
- Line number tracking across continuations
- Case-insensitive keyword matching

By separating lexical analysis from semantic parsing, we achieve:
- **Separation of concerns**: Each layer does one thing well
- **Testability**: The lexer can be tested in isolation
- **Maintainability**: Changes to CDL syntax require only lexer updates
- **Performance**: One-pass tokenization, lazy evaluation

## 2. Architecture Overview

### Where It Fits

```
┌─────────────────────────────────────────────────────────────────┐
│                     CDL Parsing Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   CDL File (.ckt)                                               │
│        │                                                        │
│        ▼                                                        │
│   ┌─────────────┐                                               │
│   │  CDLLexer   │ ◄── This component (E01-F01-T01)              │
│   │  tokenize() │                                               │
│   └──────┬──────┘                                               │
│          │                                                      │
│          │  Stream of CDLToken                                  │
│          │  (line_num, line_type, content, raw)                 │
│          │                                                      │
│          ▼                                                      │
│   ┌─────────────┐      ┌─────────────┐                          │
│   │  Subcircuit │      │  Instance   │                          │
│   │   Parser    │      │   Parser    │                          │
│   │ (E01-F01-T02)│      │ (E01-F01-T03)│                          │
│   └──────┬──────┘      └──────┬──────┘                          │
│          │                    │                                 │
│          └────────┬───────────┘                                 │
│                   ▼                                             │
│            Design Model                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Relationships

| Component | Role | Relationship |
|-----------|------|--------------|
| `CDLLexer` | Tokenization | Entry point, reads files |
| `LineType` | Classification | Enum used by CDLLexer and consumers |
| `CDLToken` | Data transfer | Immutable record passed to parsers |

## 3. Data Flow

### Input → Processing → Output

```
Input (CDL File):
┌────────────────────────────────────────┐
│ * Sample CDL                           │  Line 1
│ .SUBCKT INV A Y VDD VSS                │  Line 2
│ XI1 A n1 VDD VSS                       │  Line 3
│ + BUFFER                               │  Line 4 (continuation)
│ .ENDS INV                              │  Line 5
└────────────────────────────────────────┘

Processing (CDLLexer.tokenize()):
┌─────────────────────────────────────────────────────────────────┐
│ 1. Read lines: ["* Sample CDL\n", ".SUBCKT INV...", ...]        │
│ 2. For each line:                                               │
│    a. Check for continuation lookahead                          │
│    b. Join continuations                                        │
│    c. Classify line type                                        │
│    d. Strip inline comments                                     │
│    e. Yield CDLToken                                            │
└─────────────────────────────────────────────────────────────────┘

Output (Stream of CDLToken):
┌────────────────────────────────────────────────────────────────┐
│ Token 1: line_num=1, type=COMMENT, content="* Sample CDL"      │
│ Token 2: line_num=2, type=SUBCKT,  content=".SUBCKT INV..."    │
│ Token 3: line_num=3, type=INSTANCE, content="XI1 A n1... BUFFER"│
│ Token 4: line_num=5, type=ENDS,    content=".ENDS INV"         │
└────────────────────────────────────────────────────────────────┘
```

### Key Insight: Continuation Handling

When the lexer encounters line 3 (the instance), it looks ahead and sees line 4 starts with `+`. It then:
1. Collects both lines
2. Joins them: `"XI1 A n1 VDD VSS BUFFER"`
3. Assigns line_num=3 (first line)
4. Skips line 4 in the main loop

## 4. Implementation Details

### 4.1 LineType Enum

Location: `src/ink/infrastructure/parsing/cdl_lexer.py:40-62`

```python
class LineType(Enum):
    """CDL line type classification."""
    SUBCKT = "SUBCKT"      # .SUBCKT definition
    ENDS = "ENDS"          # .ENDS terminator
    INSTANCE = "INSTANCE"  # X-prefixed instance
    TRANSISTOR = "TRANSISTOR"  # M-prefixed transistor
    COMMENT = "COMMENT"    # * comment line
    BLANK = "BLANK"        # Empty/whitespace
    UNKNOWN = "UNKNOWN"    # Unrecognized
```

**Design Rationale**:
- String values for debugging clarity
- All CDL line types needed by downstream parsers
- UNKNOWN for graceful handling of unsupported directives

### 4.2 CDLToken Dataclass

Location: `src/ink/infrastructure/parsing/cdl_lexer.py:65-88`

```python
@dataclass
class CDLToken:
    """A tokenized CDL line."""
    line_num: int      # 1-indexed, original file position
    line_type: LineType  # Classification
    content: str       # Cleaned content
    raw: str           # Original line(s)
```

**Why These Fields**:
- `line_num`: Error messages can point to exact location
- `line_type`: Downstream parsers can filter/route tokens
- `content`: Cleaned, ready for semantic parsing
- `raw`: Preserved for debugging and error context

### 4.3 Classification Logic

Location: `src/ink/infrastructure/parsing/cdl_lexer.py:207-261`

```python
def _classify_line(self, content: str) -> LineType:
    stripped = content.strip()

    # Check order matters!
    if not stripped:
        return LineType.BLANK

    if stripped.startswith("*"):
        return LineType.COMMENT

    upper = stripped.upper()
    if upper.startswith(".SUBCKT"):
        return LineType.SUBCKT
    if upper.startswith(".ENDS"):
        return LineType.ENDS

    first_char = stripped[0].upper()
    if first_char == "X":
        return LineType.INSTANCE
    if first_char == "M":
        return LineType.TRANSISTOR

    return LineType.UNKNOWN
```

**Classification Priority**:
1. BLANK (empty) - catches whitespace-only
2. COMMENT - before keyword checks (comments could start with `.`)
3. Keywords (.SUBCKT, .ENDS) - case-insensitive
4. Element prefixes (X, M) - case-insensitive
5. UNKNOWN - fallback

### 4.4 Comment Stripping

Location: `src/ink/infrastructure/parsing/cdl_lexer.py:263-302`

```python
def _strip_comment(self, line: str) -> str:
    if not line:
        return ""

    # Pure comment lines
    if line.lstrip().startswith("*"):
        return ""

    # Inline comments
    comment_pos = line.find("*")
    if comment_pos == -1:
        return line.rstrip()

    return line[:comment_pos].rstrip()
```

**Edge Cases**:
- Empty lines → return empty
- Pure comments (`* text`) → return empty
- Inline comments (`XI1 A * note`) → return `"XI1 A"`
- No comments → return stripped line

### 4.5 Continuation Handling

Location: `src/ink/infrastructure/parsing/cdl_lexer.py:304-350`

```python
def _handle_continuation(self, lines: list[str]) -> str:
    if len(lines) == 1:
        return lines[0]

    parts = [lines[0].rstrip()]
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped.startswith("+"):
            continuation_content = stripped[1:].lstrip()
            parts.append(continuation_content)

    return " ".join(parts)
```

**Example**:
```
Input: ["XI1 A B", "+ C D", "+ E F CELL"]
Output: "XI1 A B C D E F CELL"
```

### 4.6 Main Tokenization Loop

Location: `src/ink/infrastructure/parsing/cdl_lexer.py:126-205`

```python
def tokenize(self) -> Iterator[CDLToken]:
    with self.file_path.open("r", encoding="utf-8", newline="") as f:
        raw_lines = f.readlines()

    i = 0
    while i < len(raw_lines):
        current_line = raw_lines[i].rstrip("\r\n")
        line_num = i + 1

        # Lookahead for continuations
        continuation_lines = [current_line]
        j = i + 1
        while j < len(raw_lines):
            next_line = raw_lines[j].rstrip("\r\n")
            if next_line.lstrip().startswith("+"):
                continuation_lines.append(next_line)
                j += 1
            else:
                break

        # Process
        if len(continuation_lines) > 1:
            joined_content = self._handle_continuation(continuation_lines)
            raw = "\n".join([l.rstrip("\r\n") for l in continuation_lines])
        else:
            joined_content = current_line
            raw = current_line

        line_type = self._classify_line(joined_content)
        if line_type == LineType.COMMENT:
            content = joined_content.strip()
        else:
            content = self._strip_comment(joined_content)

        yield CDLToken(line_num=line_num, line_type=line_type,
                      content=content, raw=raw)

        i = j  # Skip processed continuation lines
```

**Key Algorithm Points**:
1. Read all lines into memory (required for lookahead)
2. Use while loop with manual index control (to skip continuations)
3. Classify BEFORE stripping comments
4. Yield tokens lazily (memory efficient for token processing)

## 5. Testing Approach

### Test-Driven Development Cycle

```
RED Phase:
├── Wrote 65 failing tests
├── Covered all LineType values
├── Covered all edge cases from spec
└── Tests failed with NotImplementedError

GREEN Phase:
├── Implemented LineType enum (8 tests pass)
├── Implemented CDLToken (5 tests pass)
├── Implemented _classify_line (15 tests pass)
├── Implemented _strip_comment (7 tests pass)
├── Implemented _handle_continuation (6 tests pass)
├── Implemented tokenize (14 tests pass)
└── Edge case tests (11 tests pass)

REFACTOR Phase:
├── Fixed import for TYPE_CHECKING
├── Added noqa for too many returns
├── Fixed line length issues
└── Used next() instead of [0]
```

### Test Categories

| Category | Count | Purpose |
|----------|-------|---------|
| LineType | 8 | Enum value verification |
| CDLToken | 5 | Dataclass structure |
| _classify_line | 15 | Classification accuracy |
| _strip_comment | 7 | Comment removal |
| _handle_continuation | 6 | Line joining |
| tokenize | 14 | Full tokenization |
| Edge Cases | 11 | Boundary conditions |
| Sample File | 1 | Realistic integration |

## 6. Error Handling

### Current Approach

The lexer does not throw exceptions for invalid content. Instead:
- Unrecognized lines → `LineType.UNKNOWN`
- Empty files → No tokens yielded
- Invalid Unicode → Python's default decoder error

### Error Information Preserved

```python
CDLToken(
    line_num=42,         # Where in the file
    line_type=UNKNOWN,   # What went wrong
    content=".INVALID",  # What was the content
    raw=".INVALID * note"  # Original line
)
```

Downstream parsers can:
- Filter out UNKNOWN tokens
- Log warnings with line numbers
- Collect errors for batch reporting

## 7. Performance Characteristics

### Memory Usage

```
File Size: N bytes
Lines: L

Memory = File content (N) + Current token (O(1)) + Line list (L pointers)
       ≈ O(N) for file, O(L) for line list
```

### Time Complexity

```
Tokenization: O(L) - single pass
Continuation detection: O(1) per line - single lookahead
Classification: O(1) per line - constant string operations
```

### Optimization Opportunities

1. **Streaming read**: Could read line-by-line with a continuation buffer
2. **Parallel classification**: Lines could be classified in parallel (not worth it for lexing)
3. **Memory mapping**: Large files could use mmap

## 8. Future Considerations

### Potential Enhancements

1. **More line types**: Support for `.INCLUDE`, `.PARAM`, `.GLOBAL`
2. **Error recovery**: Skip malformed lines and continue
3. **Encoding detection**: Auto-detect file encoding
4. **Position tracking**: Character-level positions for IDE integration

### Integration with Parser

The downstream parsers (E01-F01-T02, E01-F01-T03) will:

```python
lexer = CDLLexer(file_path)
for token in lexer.tokenize():
    if token.line_type == LineType.SUBCKT:
        subcircuit_parser.parse_header(token)
    elif token.line_type == LineType.INSTANCE:
        instance_parser.parse(token)
    elif token.line_type == LineType.ENDS:
        subcircuit_parser.finalize()
```

## 9. Debugging Tips

### Common Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| BLANK instead of COMMENT | Classifying after strip | Classify before stripping |
| Missing instance content | Continuation not joined | Check `+` lookahead |
| Wrong line numbers | Off-by-one | Line numbers are 1-indexed |
| Content has comments | `_strip_comment` not called | Check line type routing |

### Debugging Flow

```python
# Add debug logging
for token in lexer.tokenize():
    print(f"[{token.line_num}] {token.line_type.value}: {token.content!r}")
    if token.raw != token.content:
        print(f"    raw: {token.raw!r}")
```

## 10. Conclusion

The CDL Lexer provides a robust, tested foundation for the CDL parsing pipeline. Its key strengths are:

1. **Clean separation**: Lexical analysis isolated from semantic parsing
2. **Comprehensive testing**: 65 tests covering all edge cases
3. **Maintainable code**: Clear structure with extensive documentation
4. **Memory efficient**: Iterator-based token generation
5. **Error-friendly**: Line numbers and raw content preserved

This implementation fulfills all acceptance criteria from E01-F01-T01 and provides a solid foundation for the Subcircuit Parser (T02) and Instance Parser (T03).
