"""Infrastructure layer for Ink application.

The infrastructure layer provides concrete implementations of domain interfaces
and external adapters. It contains:
- Persistence: Settings, session storage, file I/O
- Parsing: CDL netlist parsers
- Graph: Graph library adapters (NetworkX, rustworkx)
- Layout: Sugiyama layout engine implementations
- Routing: Net routing implementations
"""
