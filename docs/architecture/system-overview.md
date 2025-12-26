# System Overview

## 1. High-Level Architecture

Ink is an incremental schematic viewer built with Domain-Driven Design principles. The system transforms gate-level CDL netlists into interactive, explorable schematic visualizations.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                    INK                                           │
│                      Incremental Schematic Viewer                                │
│                                                                                  │
│  ┌─────────────┐    ┌─────────────────────────────────────────────────────────┐ │
│  │   INPUT     │    │                    CORE SYSTEM                          │ │
│  │             │    │                                                         │ │
│  │  .ckt file  │───►│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   │ │
│  │  (CDL)      │    │  │  Netlist    │   │  Schematic  │   │ Exploration │   │ │
│  │             │    │  │  Context    │──►│  Context    │──►│  Context    │   │ │
│  │  .pindir    │───►│  │             │   │             │   │             │   │ │
│  │  file       │    │  │ • Parser    │   │ • Layout    │   │ • Expand    │   │ │
│  │             │    │  │ • Graph     │   │ • Routing   │   │ • Collapse  │   │ │
│  └─────────────┘    │  │ • Model     │   │ • Render    │   │ • Navigate  │   │ │
│                     │  └─────────────┘   └─────────────┘   └─────────────┘   │ │
│                     │         │                 │                 │          │ │
│                     │         ▼                 ▼                 ▼          │ │
│                     │  ┌─────────────────────────────────────────────────┐   │ │
│                     │  │              SHARED KERNEL                       │   │ │
│                     │  │  • Domain Events  • Ubiquitous Language         │   │ │
│                     │  │  • Core Entities  • Value Objects               │   │ │
│                     │  └─────────────────────────────────────────────────┘   │ │
│                     └─────────────────────────────────────────────────────────┘ │
│                                            │                                     │
│                                            ▼                                     │
│  ┌───────────────────────────────────────────────────────────────────────────┐  │
│  │                           USER INTERFACE                                   │  │
│  │  ┌─────────────┐  ┌─────────────────────────────┐  ┌─────────────────┐    │  │
│  │  │  Hierarchy  │  │     Schematic Canvas        │  │    Property     │    │  │
│  │  │   Panel     │  │                             │  │     Panel       │    │  │
│  │  │             │  │   [Cell]──[Cell]──[Cell]    │  │                 │    │  │
│  │  │  ├─ cell1   │  │      │       │       │      │  │  Name: XI1      │    │  │
│  │  │  ├─ cell2   │  │   [Cell]──[Cell]──[Cell]    │  │  Type: AND2_X1  │    │  │
│  │  │  └─ cell3   │  │                             │  │  Pins: 3        │    │  │
│  │  └─────────────┘  └─────────────────────────────┘  └─────────────────┘    │  │
│  │                   ┌─────────────────────────────────────────────────┐     │  │
│  │                   │  Search / TCL Console / Messages                │     │  │
│  │                   └─────────────────────────────────────────────────┘     │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                                   │
│                                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ MainWindow   │  │ Schematic    │  │ Property     │  │ Search       │          │
│  │              │  │ Canvas       │  │ Panel        │  │ Panel        │          │
│  │ • Menu       │  │              │  │              │  │              │          │
│  │ • Toolbar    │  │ • Pan/Zoom   │  │ • Cell Info  │  │ • Query      │          │
│  │ • StatusBar  │  │ • Selection  │  │ • Pin Info   │  │ • Results    │          │
│  │ • Docking    │  │ • Rendering  │  │ • Net Info   │  │ • History    │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                 │                   │
│         └─────────────────┴─────────────────┴─────────────────┘                   │
│                                    │                                              │
│                                    ▼ Qt Signals                                   │
├──────────────────────────────────────────────────────────────────────────────────┤
│                              APPLICATION LAYER                                    │
│                                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                │
│  │ ExpansionService │  │ SelectionService │  │ SearchService    │                │
│  │                  │  │                  │  │                  │                │
│  │ • expand_fanout  │  │ • select         │  │ • search         │                │
│  │ • expand_fanin   │  │ • multi_select   │  │ • navigate_to    │                │
│  │ • collapse       │  │ • clear          │  │ • get_history    │                │
│  │ • undo/redo      │  │                  │  │                  │                │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘                │
│           │                     │                     │                           │
│           └─────────────────────┴─────────────────────┘                           │
│                                 │                                                 │
│                                 ▼ Commands / Queries                              │
├──────────────────────────────────────────────────────────────────────────────────┤
│                               DOMAIN LAYER                                        │
│                                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                           AGGREGATES                                         │ │
│  │                                                                              │ │
│  │  ┌────────────────────┐    ┌────────────────────┐    ┌──────────────────┐   │ │
│  │  │ Design (Root)      │    │ Cell               │    │ Net              │   │ │
│  │  │                    │    │                    │    │                  │   │ │
│  │  │ • name             │    │ • instance_name    │    │ • name           │   │ │
│  │  │ • cells            │◄───│ • cell_type        │    │ • connected_pins │   │ │
│  │  │ • nets             │    │ • pins[]           │───►│ • is_power       │   │ │
│  │  │ • ports            │    │ • is_sequential    │    │ • is_ground      │   │ │
│  │  │ • subcircuits      │    │ • position         │    │                  │   │ │
│  │  └────────────────────┘    └────────────────────┘    └──────────────────┘   │ │
│  │                                     │                                        │ │
│  │                                     ▼                                        │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐│ │
│  │  │                         ENTITIES                                         ││ │
│  │  │                                                                          ││ │
│  │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   ││ │
│  │  │  │ Pin          │  │ Port         │  │ Subcircuit   │                   ││ │
│  │  │  │              │  │              │  │              │                   ││ │
│  │  │  │ • name       │  │ • name       │  │ • name       │                   ││ │
│  │  │  │ • direction  │  │ • direction  │  │ • pins[]     │                   ││ │
│  │  │  │ • net        │  │ • net        │  │ • instances  │                   ││ │
│  │  │  │ • cell (ref) │  │              │  │              │                   ││ │
│  │  │  └──────────────┘  └──────────────┘  └──────────────┘                   ││ │
│  │  └─────────────────────────────────────────────────────────────────────────┘│ │
│  │                                                                              │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐│ │
│  │  │                       VALUE OBJECTS                                      ││ │
│  │  │                                                                          ││ │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐         ││ │
│  │  │  │PinDirection│  │ Position   │  │ BoundingBox│  │ CellType   │         ││ │
│  │  │  │            │  │            │  │            │  │            │         ││ │
│  │  │  │ • INPUT    │  │ • x        │  │ • x, y     │  │ • name     │         ││ │
│  │  │  │ • OUTPUT   │  │ • y        │  │ • width    │  │ • category │         ││ │
│  │  │  │ • INOUT    │  │            │  │ • height   │  │            │         ││ │
│  │  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘         ││ │
│  │  └─────────────────────────────────────────────────────────────────────────┘│ │
│  │                                                                              │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────┐│ │
│  │  │                      DOMAIN SERVICES                                     ││ │
│  │  │                                                                          ││ │
│  │  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐       ││ │
│  │  │  │ GraphTraverser   │  │ LayoutEngine     │  │ NetRouter        │       ││ │
│  │  │  │                  │  │                  │  │                  │       ││ │
│  │  │  │ • get_fanout()   │  │ • compute_layout │  │ • route_net()    │       ││ │
│  │  │  │ • get_fanin()    │  │ • assign_layers  │  │ • orthogonal()   │       ││ │
│  │  │  │ • get_cone()     │  │ • minimize_cross │  │ • minimize_bend  │       ││ │
│  │  │  └──────────────────┘  └──────────────────┘  └──────────────────┘       ││ │
│  │  └─────────────────────────────────────────────────────────────────────────┘│ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                              │
│                                    ▼ Interfaces                                   │
├──────────────────────────────────────────────────────────────────────────────────┤
│                            INFRASTRUCTURE LAYER                                   │
│                                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                │
│  │ CDLParser        │  │ PinDirParser     │  │ NetworkXAdapter  │                │
│  │                  │  │                  │  │                  │                │
│  │ • parse_file()   │  │ • parse_file()   │  │ • build_graph()  │                │
│  │ • parse_subckt() │  │ • get_direction()│  │ • query_fanout() │                │
│  │ • parse_inst()   │  │                  │  │ • query_fanin()  │                │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘                │
│                                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                │
│  │ SessionStore     │  │ SettingsStore    │  │ SearchIndex      │                │
│  │                  │  │                  │  │                  │                │
│  │ • save()         │  │ • load()         │  │ • build_index()  │                │
│  │ • load()         │  │ • save()         │  │ • search()       │                │
│  │ • export_json()  │  │                  │  │ • trie_lookup()  │                │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘                │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Flow Overview

### 3.1 File Loading Flow

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ .ckt    │────►│ CDLParser   │────►│ Design      │────►│ NetworkX    │
│ file    │     │             │     │ Aggregate   │     │ Graph       │
└─────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                      │                    │
┌─────────┐           │                    │
│ .pindir │───────────┘                    │
│ file    │                                ▼
└─────────┘                         ┌─────────────┐
                                    │ SearchIndex │
                                    │ (built)     │
                                    └─────────────┘
```

### 3.2 Expansion Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ User         │────►│ Expansion    │────►│ Graph        │────►│ Layout       │
│ Double-Click │     │ Service      │     │ Traverser    │     │ Engine       │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                            │                    │                    │
                            ▼                    ▼                    ▼
                     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
                     │ Expansion    │     │ New Cells    │     │ Positions    │
                     │ State        │     │ Retrieved    │     │ Computed     │
                     │ Updated      │     │              │     │              │
                     └──────────────┘     └──────────────┘     └──────────────┘
                                                                      │
                                                                      ▼
                                                               ┌──────────────┐
                                                               │ Canvas       │
                                                               │ Re-render    │
                                                               └──────────────┘
```

---

## 4. Technology Mapping

| Architectural Element | Technology/Library |
|-----------------------|---------------------|
| Presentation Layer | PySide6 (Qt6) |
| Application Services | Python classes |
| Domain Model | Python dataclasses / Pydantic |
| Graph Operations | NetworkX → rustworkx |
| Layout Algorithm | grandalf / custom Sugiyama |
| Persistence | QSettings, JSON |
| Event Bus | Qt Signals & Slots |

---

## 5. Key Design Principles

### 5.1 Dependency Rule

Dependencies flow inward: **Presentation → Application → Domain ← Infrastructure**

```
        ┌─────────────────────────────────┐
        │         Presentation            │
        │  (depends on Application)       │
        └─────────────┬───────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────┐
        │         Application             │
        │  (depends on Domain)            │
        └─────────────┬───────────────────┘
                      │
                      ▼
        ┌─────────────────────────────────┐
        │           Domain                │
        │  (depends on NOTHING)           │◄───────┐
        └─────────────────────────────────┘        │
                                                   │
        ┌─────────────────────────────────┐        │
        │        Infrastructure           │────────┘
        │  (implements Domain interfaces) │
        └─────────────────────────────────┘
```

### 5.2 Hexagonal Architecture (Ports & Adapters)

```
                    ┌─────────────────────────────────────────┐
                    │              DOMAIN CORE                 │
     ┌──────────┐   │                                         │   ┌──────────┐
     │ Qt UI    │◄──┤►  ┌─────────────────────────────────┐  ├──►│ NetworkX │
     │ Adapter  │   │   │                                 │   │   │ Adapter  │
     └──────────┘   │   │   Cell, Pin, Net, Port          │   │   └──────────┘
                    │   │   GraphTraverser                │   │
     ┌──────────┐   │   │   LayoutEngine                  │   │   ┌──────────┐
     │ File     │◄──┤►  │   ExpansionState                │  ├──►│ Settings │
     │ Parser   │   │   │                                 │   │   │ Store    │
     └──────────┘   │   └─────────────────────────────────┘   │   └──────────┘
                    │                                         │
                    └─────────────────────────────────────────┘
                              PORTS (Interfaces)
```

---

*See [DDD Architecture](./ddd-architecture.md) for detailed domain modeling.*
