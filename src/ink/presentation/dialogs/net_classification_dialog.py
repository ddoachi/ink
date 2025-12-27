"""Net classification configuration dialog.

This module provides the NetClassificationDialog class - a Qt dialog for
editing power and ground net classification settings per project.

The dialog allows users to:
    1. Add/remove exact net names for power and ground classification
    2. Add/remove regex patterns for power and ground classification
    3. Toggle whether to override default patterns (VDD, VSS, etc.)

The configuration is used by NetNormalizer to classify nets during CDL parsing.

Design Decisions:
    - Uses QTabWidget to separate Power and Ground configuration
    - Each tab has two sections: exact names and regex patterns
    - Add/Remove buttons use QInputDialog for simple item entry
    - OK/Cancel buttons use QDialogButtonBox for standard dialog behavior

See Also:
    - Spec E01-F01-T06 for requirements
    - NetClassificationConfig for the underlying data structure
    - NetNormalizer.from_config for using the configuration
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from ink.infrastructure.config.net_classification_config import (
        NetClassificationConfig,
    )


class NetClassificationDialog(QDialog):
    """Dialog for editing power/ground net classification settings.

    This dialog provides a visual editor for configuring which nets are
    classified as power or ground. Configuration can include:
    - Exact net names (case-insensitive matching)
    - Regex patterns for flexible matching
    - Option to override default patterns

    The dialog is organized with tabs for Power and Ground nets, each
    containing sections for both exact names and regex patterns.

    Attributes:
        _config: The original configuration passed to the constructor.
        _power_names_list: QListWidget for power net names.
        _power_patterns_list: QListWidget for power patterns.
        _ground_names_list: QListWidget for ground net names.
        _ground_patterns_list: QListWidget for ground patterns.
        _override_checkbox: QCheckBox for override defaults option.

    Example:
        >>> from ink.infrastructure.config.net_classification_config import (
        ...     NetClassificationConfig,
        ... )
        >>> config = NetClassificationConfig.load(project_path)
        >>> dialog = NetClassificationDialog(config)
        >>> if dialog.exec() == QDialog.Accepted:
        ...     new_config = dialog.get_config()
        ...     new_config.save(project_path)
    """

    def __init__(
        self,
        config: NetClassificationConfig,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the net classification dialog.

        Args:
            config: The current configuration to display and edit.
            parent: Optional parent widget (typically the main window).
        """
        super().__init__(parent)
        self._config = config

        # Set dialog properties
        self.setWindowTitle("Net Classification Settings")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        # Build UI
        self._setup_ui()

        # Load current config into UI
        self._load_config()

    def _setup_ui(self) -> None:
        """Set up the dialog UI layout.

        Creates:
        - Tab widget with Power Nets and Ground Nets tabs
        - Override defaults checkbox
        - OK/Cancel button box
        """
        layout = QVBoxLayout(self)

        # Tab widget for Power/Ground configuration
        tab_widget = QTabWidget()
        power_tab, self._power_names_list, self._power_patterns_list = (
            self._create_net_tab()
        )
        ground_tab, self._ground_names_list, self._ground_patterns_list = (
            self._create_net_tab()
        )
        tab_widget.addTab(power_tab, "Power Nets")
        tab_widget.addTab(ground_tab, "Ground Nets")
        layout.addWidget(tab_widget)

        # Override defaults checkbox
        self._override_checkbox = QCheckBox("Override default patterns (VDD*, VSS*, GND*, etc.)")
        layout.addWidget(self._override_checkbox)

        # Dialog buttons (OK/Cancel)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _create_net_tab(self) -> tuple[QWidget, QListWidget, QListWidget]:
        """Create a tab for power or ground net configuration.

        Each tab contains two sections:
        1. Net Names - exact match (case-insensitive)
        2. Regex Patterns - for flexible matching

        Returns:
            Tuple of (tab_widget, names_list, patterns_list).
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Names section
        names_group = QGroupBox("Net Names (exact match, case-insensitive)")
        names_layout = QVBoxLayout(names_group)
        names_list = QListWidget()
        names_layout.addWidget(names_list)

        # Add/Remove buttons for names
        names_btn_layout = QHBoxLayout()
        add_name_btn = QPushButton("Add")
        remove_name_btn = QPushButton("Remove")
        add_name_btn.clicked.connect(lambda: self._on_add_item(names_list))
        remove_name_btn.clicked.connect(lambda: self._on_remove_item(names_list))
        names_btn_layout.addWidget(add_name_btn)
        names_btn_layout.addWidget(remove_name_btn)
        names_btn_layout.addStretch()
        names_layout.addLayout(names_btn_layout)

        layout.addWidget(names_group)

        # Patterns section
        patterns_group = QGroupBox("Regex Patterns (additional)")
        patterns_layout = QVBoxLayout(patterns_group)
        patterns_list = QListWidget()
        patterns_layout.addWidget(patterns_list)

        # Add/Remove buttons for patterns
        patterns_btn_layout = QHBoxLayout()
        add_pattern_btn = QPushButton("Add")
        remove_pattern_btn = QPushButton("Remove")
        add_pattern_btn.clicked.connect(lambda: self._on_add_item(patterns_list))
        remove_pattern_btn.clicked.connect(lambda: self._on_remove_item(patterns_list))
        patterns_btn_layout.addWidget(add_pattern_btn)
        patterns_btn_layout.addWidget(remove_pattern_btn)
        patterns_btn_layout.addStretch()
        patterns_layout.addLayout(patterns_btn_layout)

        layout.addWidget(patterns_group)

        return tab, names_list, patterns_list

    def _on_add_item(self, list_widget: QListWidget) -> None:
        """Add a new item to a list via input dialog.

        Opens a text input dialog and adds the entered text to the list
        if the user confirms and the text is non-empty.

        Args:
            list_widget: The QListWidget to add the item to.
        """
        text, ok = QInputDialog.getText(
            self,
            "Add Item",
            "Enter net name or pattern:",
        )
        if ok and text.strip():
            list_widget.addItem(text.strip())

    def _on_remove_item(self, list_widget: QListWidget) -> None:
        """Remove the selected item from a list.

        Removes the currently selected item if any is selected.

        Args:
            list_widget: The QListWidget to remove the item from.
        """
        current_row = list_widget.currentRow()
        if current_row >= 0:
            list_widget.takeItem(current_row)

    def _load_config(self) -> None:
        """Load the configuration into the UI widgets.

        Populates all list widgets with items from the config and
        sets the checkbox state.
        """
        # Load power names
        for name in self._config.power_names:
            self._power_names_list.addItem(name)

        # Load power patterns
        for pattern in self._config.power_patterns:
            self._power_patterns_list.addItem(pattern)

        # Load ground names
        for name in self._config.ground_names:
            self._ground_names_list.addItem(name)

        # Load ground patterns
        for pattern in self._config.ground_patterns:
            self._ground_patterns_list.addItem(pattern)

        # Set override checkbox
        self._override_checkbox.setChecked(self._config.override_defaults)

    def get_power_names(self) -> list[str]:
        """Get the current power net names from the UI.

        Returns:
            List of power net names.
        """
        return [
            self._power_names_list.item(i).text()
            for i in range(self._power_names_list.count())
        ]

    def get_power_patterns(self) -> list[str]:
        """Get the current power net patterns from the UI.

        Returns:
            List of power net regex patterns.
        """
        return [
            self._power_patterns_list.item(i).text()
            for i in range(self._power_patterns_list.count())
        ]

    def get_ground_names(self) -> list[str]:
        """Get the current ground net names from the UI.

        Returns:
            List of ground net names.
        """
        return [
            self._ground_names_list.item(i).text()
            for i in range(self._ground_names_list.count())
        ]

    def get_ground_patterns(self) -> list[str]:
        """Get the current ground net patterns from the UI.

        Returns:
            List of ground net regex patterns.
        """
        return [
            self._ground_patterns_list.item(i).text()
            for i in range(self._ground_patterns_list.count())
        ]

    def get_config(self) -> NetClassificationConfig:
        """Get the edited configuration from the dialog.

        Creates a new NetClassificationConfig with the current values
        from all UI widgets.

        Returns:
            NetClassificationConfig with the edited values.
        """
        # Import here to avoid circular imports at module level
        # This is necessary because NetClassificationConfig is in infrastructure layer
        # and this dialog is in presentation layer
        from ink.infrastructure.config.net_classification_config import (  # noqa: PLC0415
            NetClassificationConfig,
        )

        return NetClassificationConfig(
            power_names=self.get_power_names(),
            power_patterns=self.get_power_patterns(),
            ground_names=self.get_ground_names(),
            ground_patterns=self.get_ground_patterns(),
            override_defaults=self._override_checkbox.isChecked(),
        )
