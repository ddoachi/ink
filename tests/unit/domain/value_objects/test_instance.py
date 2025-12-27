"""Unit tests for CellInstance value object.

This test module validates the CellInstance domain model, which represents
a cell instantiation parsed from CDL X-prefixed lines. Tests follow TDD
principles - they were written before the implementation.

Test Categories:
1. Basic Construction - Valid instances with complete data
2. Name Validation - X-prefix requirement, empty name handling
3. Cell Type Validation - Empty cell type handling
4. Connection Immutability - MappingProxyType enforcement
5. Edge Cases - Empty connections, special characters

Architecture:
    CellInstance is a frozen dataclass (value object) in the domain layer.
    It has no dependencies on infrastructure components.
"""

from __future__ import annotations

from types import MappingProxyType

import pytest


class TestCellInstanceConstruction:
    """Tests for basic CellInstance construction and properties."""

    def test_create_simple_instance(self) -> None:
        """Test creating a basic cell instance with all required fields.

        Given a valid instance name, cell type, and connections,
        When we create a CellInstance,
        Then all properties should be accessible and correct.
        """
        from ink.domain.value_objects.instance import CellInstance

        connections = {"A": "net1", "Y": "net2", "VDD": "VDD", "VSS": "VSS"}
        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections=connections,
        )

        assert instance.name == "XI1"
        assert instance.cell_type == "INV"
        assert instance.connections["A"] == "net1"
        assert instance.connections["Y"] == "net2"
        assert instance.connections["VDD"] == "VDD"
        assert instance.connections["VSS"] == "VSS"

    def test_create_instance_with_hierarchical_name(self) -> None:
        """Test instance with hierarchical path in name using '/' separator.

        Some CDL files use hierarchical naming for instances, e.g.,
        U_CORE/U_ALU/XI_ADD to indicate hierarchy.
        """
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI_CORE/U_ALU/XI_ADD",
            cell_type="ADDER",
            connections={"A": "in1", "B": "in2", "Y": "out"},
        )

        assert instance.name == "XI_CORE/U_ALU/XI_ADD"
        assert "/" in instance.name

    def test_create_instance_with_underscore_name(self) -> None:
        """Test instance name with underscores (common in cell libraries)."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI_BUFFER_1",
            cell_type="BUFX4",
            connections={"A": "in", "Y": "out"},
        )

        assert instance.name == "XI_BUFFER_1"

    def test_create_instance_lowercase_x_prefix(self) -> None:
        """Test that lowercase 'x' prefix is also valid for instance names.

        CDL format is case-insensitive for element prefixes.
        """
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="xI1",
            cell_type="INV",
            connections={"A": "net1"},
        )

        assert instance.name == "xI1"


class TestCellInstanceNameValidation:
    """Tests for instance name validation rules."""

    def test_empty_name_raises_value_error(self) -> None:
        """Test that empty instance name raises ValueError.

        Instance names are required for proper identification.
        """
        from ink.domain.value_objects.instance import CellInstance

        with pytest.raises(ValueError, match="Instance name cannot be empty"):
            CellInstance(
                name="",
                cell_type="INV",
                connections={"A": "net1"},
            )

    def test_name_missing_x_prefix_raises_error(self) -> None:
        """Test that instance name without X prefix raises ValueError.

        CDL convention requires instance names to start with 'X' (or 'x').
        """
        from ink.domain.value_objects.instance import CellInstance

        with pytest.raises(ValueError, match="must start with 'X'"):
            CellInstance(
                name="I1",
                cell_type="INV",
                connections={"A": "net1"},
            )

    def test_name_with_number_prefix_raises_error(self) -> None:
        """Test that instance name starting with number raises ValueError."""
        from ink.domain.value_objects.instance import CellInstance

        with pytest.raises(ValueError, match="must start with 'X'"):
            CellInstance(
                name="1XI",
                cell_type="INV",
                connections={"A": "net1"},
            )


class TestCellInstanceCellTypeValidation:
    """Tests for cell type validation rules."""

    def test_empty_cell_type_raises_value_error(self) -> None:
        """Test that empty cell type raises ValueError.

        Cell type is required to know which subcircuit definition to use.
        """
        from ink.domain.value_objects.instance import CellInstance

        with pytest.raises(ValueError, match="missing cell type"):
            CellInstance(
                name="XI1",
                cell_type="",
                connections={"A": "net1"},
            )

    def test_cell_type_with_underscores_and_numbers(self) -> None:
        """Test cell type with underscores and numbers (standard library naming)."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI1",
            cell_type="NAND2_X1",
            connections={"A1": "net1", "A2": "net2", "ZN": "out"},
        )

        assert instance.cell_type == "NAND2_X1"


class TestCellInstanceConnectionsImmutability:
    """Tests for connections dictionary immutability."""

    def test_connections_is_immutable(self) -> None:
        """Test that connections dict cannot be modified after creation.

        CellInstance is a value object - it should be immutable.
        The connections dict should be wrapped in MappingProxyType.
        """
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1", "Y": "net2"},
        )

        # Verify it's a MappingProxyType (read-only view)
        assert isinstance(instance.connections, MappingProxyType)

        # Attempting to modify should raise TypeError
        with pytest.raises(TypeError):
            instance.connections["A"] = "modified"  # type: ignore[index]

    def test_connections_cannot_add_new_key(self) -> None:
        """Test that new keys cannot be added to connections dict."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1"},
        )

        with pytest.raises(TypeError):
            instance.connections["NEW_PORT"] = "new_net"  # type: ignore[index]

    def test_original_dict_modification_does_not_affect_instance(self) -> None:
        """Test that modifying the original dict doesn't affect the instance.

        The CellInstance should store a copy, not a reference.
        """
        from ink.domain.value_objects.instance import CellInstance

        original_connections = {"A": "net1", "Y": "net2"}
        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections=original_connections,
        )

        # Modify original dict
        original_connections["A"] = "modified"
        original_connections["Z"] = "new_port"

        # Instance should be unaffected
        assert instance.connections["A"] == "net1"
        assert "Z" not in instance.connections


class TestCellInstanceEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_connections_dict(self) -> None:
        """Test instance with empty connections (rare but possible).

        Some cell types might have no ports (e.g., power/ground cells).
        """
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI_FILLER",
            cell_type="FILL_X1",
            connections={},
        )

        assert len(instance.connections) == 0

    def test_instance_with_bus_net_names(self) -> None:
        """Test connections with bus notation net names like data<7>."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI1",
            cell_type="MUX2",
            connections={"D0": "data<0>", "D1": "data<1>", "Y": "out<0>"},
        )

        assert instance.connections["D0"] == "data<0>"
        assert instance.connections["D1"] == "data<1>"
        assert instance.connections["Y"] == "out<0>"

    def test_instance_with_all_same_net(self) -> None:
        """Test instance where all ports connect to same net (valid, e.g., tie-off)."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI_TIE",
            cell_type="TIEHI_X1",
            connections={"Z1": "VDD", "Z2": "VDD", "Z3": "VDD"},
        )

        # All connections to same net is valid
        assert all(net == "VDD" for net in instance.connections.values())

    def test_instance_with_power_ground_nets(self) -> None:
        """Test standard power and ground net naming."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={
                "A": "input_sig",
                "Y": "output_sig",
                "VDD": "VDD",
                "VSS": "VSS",
            },
        )

        assert instance.connections["VDD"] == "VDD"
        assert instance.connections["VSS"] == "VSS"

    def test_instance_frozen_dataclass(self) -> None:
        """Test that CellInstance is a frozen (immutable) dataclass."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1"},
        )

        # Attempting to change name should raise FrozenInstanceError
        with pytest.raises(AttributeError):
            instance.name = "XI2"  # type: ignore[misc]

        # Attempting to change cell_type should raise FrozenInstanceError
        with pytest.raises(AttributeError):
            instance.cell_type = "NAND2"  # type: ignore[misc]


class TestCellInstanceRepresentation:
    """Tests for string representation of CellInstance."""

    def test_repr_contains_all_fields(self) -> None:
        """Test that repr shows all important fields."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1", "Y": "net2"},
        )

        repr_str = repr(instance)
        assert "XI1" in repr_str
        assert "INV" in repr_str

    def test_str_human_readable(self) -> None:
        """Test that str provides human-readable output."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1", "Y": "net2"},
        )

        str_output = str(instance)
        # Should be readable - exact format is implementation-defined
        assert "XI1" in str_output or "INV" in str_output


class TestCellInstanceEquality:
    """Tests for equality and hashing of CellInstance value objects."""

    def test_equal_instances_are_equal(self) -> None:
        """Test that two instances with same data are equal."""
        from ink.domain.value_objects.instance import CellInstance

        instance1 = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1", "Y": "net2"},
        )
        instance2 = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1", "Y": "net2"},
        )

        assert instance1 == instance2

    def test_different_name_not_equal(self) -> None:
        """Test that instances with different names are not equal."""
        from ink.domain.value_objects.instance import CellInstance

        instance1 = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1"},
        )
        instance2 = CellInstance(
            name="XI2",
            cell_type="INV",
            connections={"A": "net1"},
        )

        assert instance1 != instance2

    def test_hashable_for_set_usage(self) -> None:
        """Test that CellInstance can be used in sets and as dict keys."""
        from ink.domain.value_objects.instance import CellInstance

        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1"},
        )

        # Should be hashable
        instance_set = {instance}
        assert instance in instance_set

        # Same data should have same hash
        instance2 = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1"},
        )
        assert hash(instance) == hash(instance2)
