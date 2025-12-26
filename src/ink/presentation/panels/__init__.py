"""Panel widgets for supporting UI areas.

This package provides placeholder panel widgets that will be used as
content for the dock widgets in the main window. Each panel displays
placeholder text indicating the epic where full implementation will occur.

Panel widgets are separated from dock widgets to:
- Maintain separation of concerns (container vs content)
- Allow panels to be used in other contexts if needed
- Follow Qt's standard pattern for dock widgets
- Enable independent testing of panel content

Exports:
    HierarchyPanel: Left dock area - design object tree (E04-F01)
    PropertyPanel: Right dock area - object property inspector (E04-F04)
    MessagePanel: Bottom dock area - search results and logs (E04-F03)

See Also:
    - Spec E06-F01-T03 for dock widget requirements
    - Spec E04-F01 for full HierarchyPanel implementation
    - Spec E04-F03 for full MessagePanel implementation
    - Spec E04-F04 for full PropertyPanel implementation
"""

from ink.presentation.panels.hierarchy_panel import HierarchyPanel
from ink.presentation.panels.message_panel import MessagePanel
from ink.presentation.panels.property_panel import PropertyPanel

__all__ = ["HierarchyPanel", "MessagePanel", "PropertyPanel"]
