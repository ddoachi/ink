# Product Requirements Document (PRD)

## Incremental Schematic Viewer

**Platform:** Linux
**UI Framework:** PySide6 (Qt6)
**Project Name:** Ink

---

## 1. Overview

* GUI tool for schematic exploration targeting gate-level netlists.
* Incremental exploration model starting from user-selected points instead of full schematic rendering.
* Objective of minimizing rendering overhead and maximizing analysis efficiency in large-scale netlists.
* Visual companion tool for TCL-based analysis workflows in Synopsys PrimeTime and NanoTime.

---

## 2. Goals

* Enable intuitive understanding of connectivity structure and signal flow in large gate-level netlists.
* Provide fanin and fanout–centric incremental exploration.
* Provide visual representation of TCL-based analysis results.
* Support integration with external schematic tools.

---

## 3. Input and Data Model

### 3.1 Input

* Gate-level CDL (Circuit Description Language) netlist file (`.ckt` extension) as input.
* SPICE-like CDL syntax with:
  - Subcircuit definitions (`.SUBCKT` / `.ENDS`)
  - Cell instance declarations with `X` prefix (e.g., `XI1 net1 net2 net3 VDD VSS AND2_X1`)
  - Positional pin connections (order defined by subcircuit definition)
  - Explicit power/ground nets (VDD, VSS)
  - Comment lines starting with `*`
* Netlist must include cell instance information, pin direction information, net connectivity, and top-level input/output port information.
* Pin direction information derived from a custom pin direction file (`.pindir`).

### 3.2 Internal Data Model

* Conversion of input netlist into a graph-based internal representation.
* Graph library: NetworkX for MVP, with potential migration to rustworkx for performance optimization.
* Representation of cells, pins, and ports as nodes.
* Representation of net connectivity as edges.
* Execution of all GUI rendering and exploration operations based on graph query results.

### 3.3 Latch Identification

* A latch is a level-sensitive sequential storage element that captures and holds a logic value while an enable signal is asserted.
* Latch identification based on cell type naming patterns (configurable, e.g., `*LATCH*`, `*DFF*`, `*FF*`).
* Used as semantic boundaries for expansion stopping conditions.

---

## 4. Schematic Rendering

### 4.1 Basic Rendering

* Use of symbols, pins, and nets as primary rendering elements.
* Display of minimal objects centered around user selection in the initial view.

### 4.2 Zoom-Based Rendering (Level of Detail)

* Display of cells as simple bounding boxes with hidden pin details when zoomed out.
* Display of pin names and direction information when zoomed in.
* Smooth transitions between detail levels.

### 4.3 Layout Algorithm

* Sugiyama (hierarchical/layered) algorithm for automatic schematic layout.
* Left-to-right signal flow direction (inputs on left, outputs on right).
* Layer assignment based on logic depth from primary inputs.
* Edge crossing minimization within layers.

### 4.4 Net Routing

* Orthogonal routing for all net connections.
* Automatic routing with minimal bends and crossings.
* Visual distinction for multi-fanout nets.

---

## 5. Incremental Expansion

### 5.1 Basic Behavior

* Trigger of incremental expansion via double-click on symbols, pins, or nets.
* Execution of expansion through internal graph queries.
* Prevention of duplicate generation of already expanded objects.

### 5.2 Expansion Scope Control

* Support for hop-based expansion with 1-hop or N-hop fanin and fanout traversal.
* Support for semantic boundary–based expansion up to the nearest latch or input port.

### 5.3 Collapse Functionality

* Ability to collapse (hide) previously expanded nodes.
* Right-click context menu or keyboard shortcut for collapse.
* Collapse to selected node or collapse entire subtree.

### 5.4 Expansion Settings Dialog

* Management of expansion-related configuration through a dedicated settings dialog.
* Configuration of default expansion mode, direction, maximum depth, and latch/port identification rules.

---

## 6. Signal Path and Clock Analysis Features

### 6.1 Input–Output Path Highlighting

* Analysis of signal paths between specified input and output ports.
* Visual highlighting of analyzed signal paths within the schematic.
* Selective rendering of only required circuitry through integration with incremental rendering.

### 6.2 Clock Tree Dedicated View

* Provision of a dedicated clock tree view based on clock sources.
* Display of clock nets, clock buffers, inverters, and sequential cells only.
* Hiding of data-path logic elements.
* Objective of clock structure simplification and visibility enhancement.

---

## 7. Object Interaction

### 7.1 Selection

* Transition to selected state upon single-click on an object.
* Multi-select support with Ctrl+click and drag selection box.
* Display of detailed information of selected objects in a property panel.

### 7.2 Undo/Redo

* Full undo/redo support for expansion and collapse operations.
* Keyboard shortcuts: Ctrl+Z (undo), Ctrl+Shift+Z (redo).

### 7.3 Keyboard Shortcuts

* Essential keyboard shortcuts for power users:
  - `Ctrl+F`: Open search
  - `Ctrl+Z` / `Ctrl+Shift+Z`: Undo/Redo
  - `Delete` or `Backspace`: Collapse selected
  - `Space`: Fit view to selection
  - `+` / `-`: Zoom in/out

---

## 8. Search and Navigation

* Search functionality based on symbol, pin, and net names.
* Incremental search with real-time filtering.
* Support for wildcard patterns (e.g., `*clk*`, `U_ALU_*`).
* Automatic panning and zooming upon selection of search results.
* Search history for quick re-access.

---

## 9. Synopsys PrimeTime / NanoTime TCL Integration

* Limitation of analysis visibility due to absence of GUI in NanoTime.
* Embedded TCL parser and interpreter within Ink application.
* Support for common TCL commands: `get_cells`, `get_pins`, `get_nets`, `all_inputs`, `all_outputs`.
* Visual reflection of TCL command execution results within the schematic (selection/highlighting).
* TCL console panel for interactive command execution.

---

## 10. Cross Probing

* Support for cross probing with external tools such as Virtuoso schematic viewer.
* Objective of maintaining continuous exploration flow across multiple tools.
* Protocol: Socket-based communication for real-time cross-probing.

---

## 11. Performance Requirements

* Capability to handle netlists containing hundreds of thousands of cells.
* Use of incremental and lazy loading instead of full schematic rendering.
* Mandatory maintenance of UI responsiveness.
* Background threading for graph queries and layout computation.
* Caching of expansion results to avoid re-computation.

---

## 12. Export and Persistence

### 12.1 Image Export

* Export current view as PNG or SVG.
* Configurable resolution and viewport selection.

### 12.2 Session Save/Load

* Save current exploration state (expanded nodes, positions, selections).
* Load previous session to continue analysis.

---

## 13. User Interface

### 13.1 Main Window Layout

* Central schematic canvas with pan/zoom.
* Left panel: Design hierarchy / object tree.
* Right panel: Property inspector for selected objects.
* Bottom panel: TCL console (P1), search results, messages.

### 13.2 Theming

* Dark mode support (default for long analysis sessions).
* Light mode option.
* Configurable color schemes for nets, cells, and highlights.

---

## 14. Error Handling

* Graceful handling of malformed netlists with clear error messages.
* Partial loading support - display parseable portions on error.
* Validation warnings for unconnected pins or floating nets.

---

## 15. Feature Prioritization

### P0 (MVP)

* Netlist parsing (gate-level CDL `.ckt`) and graph construction.
* Basic schematic rendering with Sugiyama layout.
* Orthogonal net routing.
* Hop-based incremental expansion (double-click).
* Collapse functionality.
* Object selection and property display.
* **Search and navigation.**
* Undo/redo for expansion/collapse.
* Keyboard shortcuts.
* Basic zoom-based level of detail.

### P1

* Semantic boundary–based expansion (stop at latch/port).
* Expansion settings dialog.
* PrimeTime / NanoTime TCL integration (embedded interpreter).
* Session save/load.
* Image export (PNG/SVG).
* Dark/light theme support.

### P2

* Input–output path highlighting.
* Dedicated clock tree view.
* Expansion history visualization.
* Annotation functionality.
* Cross probing support.
* Design hierarchy panel.

---

## Appendix A: Sample `.ckt` File Format (CDL)

```spice
* CDL netlist for top-level design

.SUBCKT INV_X1 A Y VDD VSS
M1 Y A VDD VDD PMOS W=1u L=0.1u
M2 Y A VSS VSS NMOS W=0.5u L=0.1u
.ENDS INV_X1

.SUBCKT NAND2_X1 A B Y VDD VSS
M1 Y A VDD VDD PMOS W=1u L=0.1u
M2 Y B VDD VDD PMOS W=1u L=0.1u
M3 Y A N1  VSS NMOS W=0.5u L=0.1u
M4 N1 B VSS VSS NMOS W=0.5u L=0.1u
.ENDS NAND2_X1

.SUBCKT DFFR_X1 D CK RN Q VDD VSS
* ... transistor definitions
.ENDS DFFR_X1

.SUBCKT top clk rst data_in<0> data_out<0> VDD VSS

* Cell instances (X prefix, positional pins, cell type at end)
XI1 rst n1 VDD VSS INV_X1
XI2 clk n1 n2 VDD VSS NAND2_X1
XI3 data_in<0> clk n1 internal<0> VDD VSS DFFR_X1
* ... more instances

.ENDS top
```

### CDL Format Notes

| Element | Description |
|---------|-------------|
| `.SUBCKT` / `.ENDS` | Subcircuit definition block |
| `M` prefix | Transistor instances (PMOS/NMOS) |
| `X` prefix | Cell instances (XI1, XU_ALU, etc.) |
| Positional pins | Net connections in order matching `.SUBCKT` definition |
| Cell type | Last token in instance line |
| `<N>` notation | Bus bit notation (e.g., `data<7>`, `addr<0>`) |
| `VDD` / `VSS` | Power and ground nets (typically last two pins) |

### Pin Direction File Format (`.pindir`)

Since CDL does not include pin direction information, Ink reads direction from a separate file:

```
* Pin direction file
* Format: PIN_NAME  DIRECTION
* Directions: INPUT, OUTPUT, INOUT

A       INPUT
B       INPUT
Y       OUTPUT
Q       OUTPUT
D       INPUT
CK      INPUT
RN      INPUT
SE      INPUT
SI      INPUT
ZN      OUTPUT
```

- Whitespace-separated (spaces or tabs)
- Comment lines start with `*`
- Directions: `INPUT`, `OUTPUT`, `INOUT`
- Applies globally to all cells (pin name matching)

---

## Appendix B: Technology Dependencies

| Component | Library/Tool | Purpose |
|-----------|-------------|---------|
| UI Framework | PySide6 | Qt6 bindings for Python |
| Graph | NetworkX / rustworkx | Graph data structure and algorithms |
| Layout | grandalf / custom | Sugiyama hierarchical layout |
| CDL Parser | Custom | Gate-level CDL netlist parsing |
| TCL Interpreter | tkinter.Tcl / tclpy | Embedded TCL execution |
