"""Entry point for executing Ink as a module.

This module enables running Ink via: python -m ink

The module simply imports the main function and calls it, propagating
the exit code to the system. This is the standard Python pattern for
module execution.

Example:
    $ python -m ink
    $ uv run python -m ink

See Also:
    - ink.main: Contains the actual application initialization
    - E06-F01-T04 spec for requirements
"""

from __future__ import annotations

import sys

from ink.main import main

if __name__ == "__main__":
    sys.exit(main())
