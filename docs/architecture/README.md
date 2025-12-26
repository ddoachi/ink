# Ink Architecture Documentation

## Overview

This directory contains the architectural documentation for Ink, an incremental schematic viewer for gate-level netlists. The architecture follows **Domain-Driven Design (DDD)** principles to create a maintainable, extensible, and domain-focused codebase.

## Documents

| Document | Description |
|----------|-------------|
| [System Overview](./system-overview.md) | High-level system architecture and component diagram |
| [DDD Architecture](./ddd-architecture.md) | Domain-Driven Design structure and bounded contexts |
| [Layer Architecture](./layer-architecture.md) | Layered architecture with dependency rules |
| [Data Flow](./data-flow.md) | Data flow diagrams for key operations |
| [Component Specifications](./components.md) | Detailed component specifications |

## Quick Reference

### Bounded Contexts

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              INK APPLICATION                             │
├─────────────────┬─────────────────┬─────────────────┬───────────────────┤
│   NETLIST       │    SCHEMATIC    │   EXPLORATION   │      QUERY        │
│   CONTEXT       │    CONTEXT      │   CONTEXT       │      CONTEXT      │
│                 │                 │                 │                   │
│ • CDL Parsing   │ • Cell Symbols  │ • Expansion     │ • Search Engine   │
│ • Pin Parsing   │ • Layout Engine │ • Collapse      │ • Pattern Match   │
│ • Graph Build   │ • Net Routing   │ • State Mgmt    │ • Navigation      │
│ • Latch ID      │ • LOD Rendering │ • History       │ • Indexing        │
└─────────────────┴─────────────────┴─────────────────┴───────────────────┘
```

### Layer Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION LAYER                               │
│                    (PySide6 UI Components)                               │
├─────────────────────────────────────────────────────────────────────────┤
│                         APPLICATION LAYER                                │
│                    (Use Cases & Services)                                │
├─────────────────────────────────────────────────────────────────────────┤
│                          DOMAIN LAYER                                    │
│              (Entities, Value Objects, Domain Services)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                       INFRASTRUCTURE LAYER                               │
│              (Parsers, Persistence, External Adapters)                   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **DDD for Domain Complexity**: Gate-level netlists have rich domain concepts that benefit from explicit modeling
2. **Hexagonal Architecture**: Core domain is isolated from infrastructure concerns
3. **CQRS-lite**: Separation of expansion commands from search queries
4. **Event-Driven UI**: Qt signals propagate domain events to UI components

## Technology Stack

| Layer | Technology |
|-------|------------|
| UI Framework | PySide6 (Qt6) |
| Graph Library | NetworkX (MVP) → rustworkx (performance) |
| Layout Algorithm | grandalf / custom Sugiyama |
| Persistence | QSettings / JSON |
| Platform | Linux |

---

*Last Updated: 2025-12-26*
