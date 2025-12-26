"""Ink - Incremental Schematic Viewer for gate-level netlists.

A GUI tool for schematic exploration targeting gate-level netlists.
Uses incremental exploration model starting from user-selected points
instead of full schematic rendering, designed to minimize rendering
overhead and maximize analysis efficiency in large-scale netlists.

Example:
    >>> # Run application
    >>> from ink import main
    >>> main()

    >>> # Check version
    >>> from ink import __version__
    >>> print(__version__)
    0.1.0

See Also:
    - CLAUDE.md for project overview and architecture
    - docs/architecture/README.md for detailed design
"""

from __future__ import annotations

from ink.main import main

__version__ = "0.1.0"
__author__ = "InkProject"

__all__ = ["__author__", "__version__", "main"]
