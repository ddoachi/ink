# Ink - Incremental Schematic Viewer

A GUI tool for schematic exploration targeting gate-level netlists. Uses an incremental exploration model starting from user-selected points instead of full schematic rendering.

## Tech Stack

- **Language:** Python 3.10+
- **UI Framework:** PySide6 (Qt6)
- **Platform:** Linux

## Quick Start

```bash
# Install dependencies
uv sync --all-extras

# Run application
uv run python -m ink

# Run tests
uv run pytest

# Type checking
uv run mypy src/
uv run pyright src/

# Linting
uv run ruff check src/
```

## Development

See [CLAUDE.md](./CLAUDE.md) for development guidelines and architecture documentation.
