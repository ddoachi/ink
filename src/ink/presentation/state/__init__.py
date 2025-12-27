"""Panel state management for the Ink presentation layer.

This package provides data structures and managers for tracking the state
of dock widgets (panels) in the main window. The state management system
uses a reactive pattern based on Qt signals to maintain synchronized state.

Key Components:
    DockArea: Enum mapping Qt dock areas with a FLOATING value for undocked panels.
    PanelGeometry: Dataclass storing size (width, height) and position (x, y).
    PanelInfo: Dataclass containing complete metadata for a single panel.
    PanelState: Aggregate dataclass for all panels plus Qt native state blobs.
    PanelStateManager: QObject that tracks panel state changes via signals.

Architecture:
    The state management follows a two-tier approach:
    1. Structured State (PanelState): Queryable, serializable Python dataclasses
       for programmatic access and application logic.
    2. Qt Native State: Opaque QByteArray blobs from QMainWindow.saveState()
       for accurate complex layout restoration.

    Both are needed: PanelState enables runtime queries and logic, while Qt's
    native state ensures accurate restoration of complex dock arrangements.

Usage Example:
    >>> from ink.presentation.state import PanelStateManager, PanelState
    >>> manager = PanelStateManager(main_window)
    >>> manager.register_panel("Hierarchy", hierarchy_dock)
    >>> state = manager.capture_state()
    >>> manager.restore_state(state)

See Also:
    - Spec E06-F05-T01 for panel state management requirements
    - Pre-docs E06-F05-T01 for architecture decisions
"""

from ink.presentation.state.panel_state import (
    DockArea,
    PanelGeometry,
    PanelInfo,
    PanelState,
)

__all__ = [
    "DockArea",
    "PanelGeometry",
    "PanelInfo",
    "PanelState",
]
