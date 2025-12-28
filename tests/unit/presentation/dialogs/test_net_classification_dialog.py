"""Unit tests for NetClassificationDialog.

This module tests the Qt dialog for editing power/ground net classification.
The tests follow TDD methodology - written BEFORE the implementation.

Test Categories:
    1. Dialog Creation: Tests for dialog instantiation and initial state
    2. UI Components: Tests for expected widgets (tabs, lists, buttons)
    3. Config Display: Tests that dialog shows current configuration
    4. Config Editing: Tests for add/remove functionality
    5. Config Retrieval: Tests for get_config() method

Note: These tests use pytest-qt's qtbot fixture for Qt widget testing.

See Also:
    - Spec E01-F01-T06 for requirements
    - src/ink/presentation/dialogs/net_classification_dialog.py for implementation
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialogButtonBox,
    QListWidget,
    QTabWidget,
)

from ink.infrastructure.config.net_classification_config import (
    NetClassificationConfig,
)


class TestNetClassificationDialogCreation:
    """Tests for dialog instantiation and basic properties."""

    def test_dialog_creates_successfully(self, qtbot) -> None:
        """Test that dialog can be created with a config."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        assert dialog is not None

    def test_dialog_has_correct_title(self, qtbot) -> None:
        """Test that dialog has the expected window title."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        assert dialog.windowTitle() == "Net Classification Settings"

    def test_dialog_has_minimum_size(self, qtbot) -> None:
        """Test that dialog has a reasonable minimum size."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        # Should be at least 500 pixels wide
        assert dialog.minimumWidth() >= 500


class TestNetClassificationDialogUIComponents:
    """Tests for UI widget structure."""

    def test_dialog_has_tab_widget(self, qtbot) -> None:
        """Test that dialog contains a tab widget for Power/Ground."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        tab_widget = dialog.findChild(QTabWidget)
        assert tab_widget is not None

    def test_dialog_has_power_tab(self, qtbot) -> None:
        """Test that dialog has a Power Nets tab."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        tab_widget = dialog.findChild(QTabWidget)
        assert tab_widget is not None

        # Find Power Nets tab
        power_tab_index = -1
        for i in range(tab_widget.count()):
            if "Power" in tab_widget.tabText(i):
                power_tab_index = i
                break

        assert power_tab_index >= 0, "Power Nets tab not found"

    def test_dialog_has_ground_tab(self, qtbot) -> None:
        """Test that dialog has a Ground Nets tab."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        tab_widget = dialog.findChild(QTabWidget)
        assert tab_widget is not None

        # Find Ground Nets tab
        ground_tab_index = -1
        for i in range(tab_widget.count()):
            if "Ground" in tab_widget.tabText(i):
                ground_tab_index = i
                break

        assert ground_tab_index >= 0, "Ground Nets tab not found"

    def test_dialog_has_override_checkbox(self, qtbot) -> None:
        """Test that dialog has an override defaults checkbox."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        checkbox = dialog.findChild(QCheckBox)
        assert checkbox is not None

    def test_dialog_has_ok_cancel_buttons(self, qtbot) -> None:
        """Test that dialog has OK and Cancel buttons."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        button_box = dialog.findChild(QDialogButtonBox)
        assert button_box is not None

        # Check for OK and Cancel buttons
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        cancel_button = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        assert ok_button is not None
        assert cancel_button is not None

    def test_dialog_has_list_widgets_for_names(self, qtbot) -> None:
        """Test that dialog has list widgets for net names."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        # Should have at least 4 list widgets:
        # power names, power patterns, ground names, ground patterns
        list_widgets = dialog.findChildren(QListWidget)
        assert len(list_widgets) >= 4


class TestNetClassificationDialogConfigDisplay:
    """Tests that dialog displays current configuration correctly."""

    def test_dialog_displays_power_names(self, qtbot) -> None:
        """Test that power names from config are shown in the list."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig(
            power_names=["AVDD", "DVDD", "VDD_CORE"],
        )
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        # Get power names list items
        power_names = dialog.get_power_names()
        assert "AVDD" in power_names
        assert "DVDD" in power_names
        assert "VDD_CORE" in power_names

    def test_dialog_displays_power_patterns(self, qtbot) -> None:
        """Test that power patterns from config are shown in the list."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig(
            power_patterns=["^PWR_.*$", "^VDDQ[0-9]*$"],
        )
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        power_patterns = dialog.get_power_patterns()
        assert "^PWR_.*$" in power_patterns
        assert "^VDDQ[0-9]*$" in power_patterns

    def test_dialog_displays_ground_names(self, qtbot) -> None:
        """Test that ground names from config are shown in the list."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig(
            ground_names=["AVSS", "DVSS"],
        )
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        ground_names = dialog.get_ground_names()
        assert "AVSS" in ground_names
        assert "DVSS" in ground_names

    def test_dialog_displays_ground_patterns(self, qtbot) -> None:
        """Test that ground patterns from config are shown in the list."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig(
            ground_patterns=["^GND_.*$"],
        )
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        ground_patterns = dialog.get_ground_patterns()
        assert "^GND_.*$" in ground_patterns

    def test_dialog_displays_override_defaults(self, qtbot) -> None:
        """Test that override defaults checkbox reflects config."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig(override_defaults=True)
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        checkbox = dialog.findChild(QCheckBox)
        assert checkbox is not None
        assert checkbox.isChecked()


class TestNetClassificationDialogGetConfig:
    """Tests for retrieving the edited configuration."""

    def test_get_config_returns_config_object(self, qtbot) -> None:
        """Test that get_config returns a NetClassificationConfig."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        result = dialog.get_config()
        assert isinstance(result, NetClassificationConfig)

    def test_get_config_preserves_power_names(self, qtbot) -> None:
        """Test that get_config preserves power names."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig(
            power_names=["AVDD", "DVDD"],
        )
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        result = dialog.get_config()
        assert "AVDD" in result.power_names
        assert "DVDD" in result.power_names

    def test_get_config_preserves_override_defaults(self, qtbot) -> None:
        """Test that get_config preserves override_defaults flag."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig(override_defaults=True)
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        result = dialog.get_config()
        assert result.override_defaults is True

    def test_get_config_reflects_checkbox_change(self, qtbot) -> None:
        """Test that toggling the checkbox is reflected in get_config."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig(override_defaults=False)
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        # Find and toggle the checkbox
        checkbox = dialog.findChild(QCheckBox)
        assert checkbox is not None
        checkbox.setChecked(True)

        result = dialog.get_config()
        assert result.override_defaults is True


class TestNetClassificationDialogEmptyConfig:
    """Tests for dialog with empty configuration."""

    def test_dialog_handles_empty_config(self, qtbot) -> None:
        """Test that dialog works with empty config."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        assert len(dialog.get_power_names()) == 0
        assert len(dialog.get_power_patterns()) == 0
        assert len(dialog.get_ground_names()) == 0
        assert len(dialog.get_ground_patterns()) == 0

    def test_empty_config_override_false(self, qtbot) -> None:
        """Test that empty config has override_defaults=False."""
        from ink.presentation.dialogs.net_classification_dialog import (
            NetClassificationDialog,
        )

        config = NetClassificationConfig()
        dialog = NetClassificationDialog(config)
        qtbot.addWidget(dialog)

        checkbox = dialog.findChild(QCheckBox)
        assert checkbox is not None
        assert not checkbox.isChecked()
