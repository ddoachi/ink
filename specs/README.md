# Ink Specifications Index

## Overview

This directory contains the hierarchical specification structure for the Ink Incremental Schematic Viewer project. Specs are organized by Epic → Feature → Task → Subtask.

## PRD Reference

- [Product Requirements Document](../docs/prd.md)

---

## Epic Summary

| ID | Epic | Priority | Status | Description |
|----|------|----------|--------|-------------|
| [E01](E01/E01.spec.md) | Input Parsing & Data Model | P0 | Draft | CDL parsing, graph construction, latch identification |
| [E02](E02/E02.spec.md) | Schematic Rendering | P0 | Draft | Cell symbols, Sugiyama layout, net routing, LOD |
| [E03](E03/E03.spec.md) | Incremental Expansion | P0 | Draft | Hop-based expansion, collapse, boundary expansion |
| [E04](E04/E04.spec.md) | Object Interaction | P0 | Draft | Selection, property panel, undo/redo, shortcuts |
| [E05](E05/E05.spec.md) | Search & Navigation | P0 | Draft | Search, wildcards, navigation, history |
| [E06](E06/E06.spec.md) | User Interface Shell | P0 | Draft | Main window, menus, toolbar, panels |

---

## Priority Legend

| Priority | Description |
|----------|-------------|
| P0 | MVP - Must have for initial release |
| P1 | Important - Second phase features |
| P2 | Nice to have - Future enhancements |

---

## Status Legend

| Status | Description |
|--------|-------------|
| Draft | Initial specification written |
| Review | Under review for approval |
| Approved | Approved for implementation |
| In Progress | Implementation started |
| Complete | Implementation finished |

---

## Dependency Graph

```
E01 (Data Model) ──┬──► E02 (Rendering) ──┬──► E03 (Expansion)
                   │                      │
                   │                      └──► E04 (Interaction) ──► E05 (Search)
                   │
                   └──► E06 (UI Shell) ◄─────────────────────────────────┘
```

### Dependency Details

| Epic | Depends On | Required By |
|------|------------|-------------|
| E01 | - | E02, E03, E04, E05, E06 |
| E02 | E01 | E03, E04 |
| E03 | E01, E02 | E04 |
| E04 | E01, E02, E03 | E05 |
| E05 | E01, E03, E04 | - |
| E06 | - | E02, E04, E05 |

---

## Implementation Order (Recommended)

### Wave 1: Foundation
1. **E06-F01**: Main Window Shell (provides canvas container)
2. **E01-F01**: CDL Parser (enables data loading)
3. **E01-F02**: Pin Direction Parser

### Wave 2: Core Data
4. **E01-F03**: Graph Construction
5. **E01-F04**: Latch Identification

### Wave 3: Basic Rendering
6. **E02-F01**: Cell Symbol Rendering
7. **E02-F02**: Sugiyama Layout Engine
8. **E02-F05**: Pan/Zoom Controls

### Wave 4: Routing & LOD
9. **E02-F03**: Orthogonal Net Routing
10. **E02-F04**: Zoom Level of Detail

### Wave 5: Expansion
11. **E03-F01**: Hop-Based Expansion
12. **E03-F02**: Collapse Functionality
13. **E03-F04**: Expansion State Management

### Wave 6: Interaction
14. **E04-F01**: Selection System
15. **E04-F02**: Property Panel
16. **E04-F03**: Undo/Redo System
17. **E04-F04**: Keyboard Shortcuts

### Wave 7: Search
18. **E05-F02**: Search Engine
19. **E05-F01**: Search Panel UI
20. **E05-F03**: Wildcard Matching
21. **E05-F04**: Navigation
22. **E05-F05**: Search History

### Wave 8: Polish
23. **E06-F02**: Menu System
24. **E06-F03**: Toolbar
25. **E06-F04**: Status Bar
26. **E06-F05**: Panel Management
27. **E06-F06**: Settings Persistence

---

## File Naming Convention

```
specs/
├── E{NN}/                           # Epic folder
│   ├── E{NN}.spec.md               # Epic specification
│   ├── E{NN}.pre-docs.md           # Pre-implementation planning
│   ├── E{NN}.context.md            # Implementation context log
│   └── F{NN}/                       # Feature folder
│       ├── E{NN}-F{NN}.spec.md     # Feature specification
│       └── T{NN}/                   # Task folder
│           └── E{NN}-F{NN}-T{NN}.spec.md  # Task specification
```

---

## Quick Commands

```bash
# Split epic into features
/spec_work E01 --split features

# Generate pre-docs for epic
/spec_work E01 --pre-docs

# Check status
/spec_work E01 --status

# Start implementation
/spec_work E01-F01-T01 --tdd
```

---

*Last Updated: 2025-12-26*
