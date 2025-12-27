"""Unit tests for SubcircuitDefinition value object.

This module tests the domain model for subcircuit definitions parsed from CDL files.
SubcircuitDefinition is an immutable value object that represents a cell type with
its port interface.

Tests cover:
- Basic creation and attribute access
- Immutability enforcement (frozen=True)
- Validation in __post_init__ (name, ports, duplicates)
- Equality comparison
- Edge cases (special characters, long port lists)
"""

from __future__ import annotations

import pytest

from ink.domain.value_objects.subcircuit import SubcircuitDefinition


class TestSubcircuitDefinitionCreation:
    """Tests for SubcircuitDefinition creation and attribute access."""

    def test_create_simple_subcircuit(self) -> None:
        """Create a simple subcircuit with name and ports."""
        defn = SubcircuitDefinition(name="INV", ports=["A", "Y", "VDD", "VSS"])
        assert defn.name == "INV"
        assert defn.ports == ("A", "Y", "VDD", "VSS")

    def test_create_minimal_subcircuit(self) -> None:
        """Create a subcircuit with minimum required ports (1 port)."""
        defn = SubcircuitDefinition(name="BUF", ports=["A"])
        assert defn.name == "BUF"
        assert defn.ports == ("A",)

    def test_create_subcircuit_with_many_ports(self) -> None:
        """Create a subcircuit with many ports (e.g., 20 ports)."""
        port_names = [f"P{i}" for i in range(20)]
        defn = SubcircuitDefinition(name="BIG_CELL", ports=port_names)
        assert defn.name == "BIG_CELL"
        assert len(defn.ports) == 20
        assert defn.ports[0] == "P0"
        assert defn.ports[19] == "P19"

    def test_ports_are_converted_to_tuple(self) -> None:
        """Ports list should be converted to tuple for immutability."""
        defn = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        assert isinstance(defn.ports, tuple)

    def test_name_preserves_case(self) -> None:
        """Cell names should preserve case exactly as provided."""
        defn = SubcircuitDefinition(name="MyCell_X1", ports=["A"])
        assert defn.name == "MyCell_X1"


class TestSubcircuitDefinitionImmutability:
    """Tests for immutability of SubcircuitDefinition."""

    def test_cannot_modify_name(self) -> None:
        """Attempting to modify name should raise an error."""
        defn = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        with pytest.raises(AttributeError):
            defn.name = "NEW_NAME"  # type: ignore[misc]

    def test_cannot_modify_ports(self) -> None:
        """Attempting to modify ports should raise an error."""
        defn = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        with pytest.raises(AttributeError):
            defn.ports = ("X", "Z")  # type: ignore[misc]


class TestSubcircuitDefinitionValidation:
    """Tests for validation in SubcircuitDefinition.__post_init__."""

    def test_empty_name_raises_error(self) -> None:
        """Empty string name should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            SubcircuitDefinition(name="", ports=["A", "Y"])

    def test_empty_port_list_raises_error(self) -> None:
        """Empty port list should raise ValueError."""
        with pytest.raises(ValueError, match="at least one port"):
            SubcircuitDefinition(name="INV", ports=[])

    def test_duplicate_port_names_raises_error(self) -> None:
        """Duplicate port names should raise ValueError."""
        with pytest.raises(ValueError, match="duplicate port"):
            SubcircuitDefinition(name="INV", ports=["A", "Y", "A"])

    def test_duplicate_port_names_error_shows_duplicates(self) -> None:
        """Error message should indicate which ports are duplicated."""
        with pytest.raises(ValueError) as exc_info:
            SubcircuitDefinition(name="CELL", ports=["A", "B", "A", "C", "B"])
        error_msg = str(exc_info.value)
        assert "A" in error_msg or "B" in error_msg


class TestSubcircuitDefinitionEquality:
    """Tests for equality comparison of SubcircuitDefinition."""

    def test_equal_subcircuits(self) -> None:
        """Two subcircuits with same name and ports should be equal."""
        defn1 = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        defn2 = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        assert defn1 == defn2

    def test_different_names_not_equal(self) -> None:
        """Subcircuits with different names should not be equal."""
        defn1 = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        defn2 = SubcircuitDefinition(name="BUF", ports=["A", "Y"])
        assert defn1 != defn2

    def test_different_ports_not_equal(self) -> None:
        """Subcircuits with different ports should not be equal."""
        defn1 = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        defn2 = SubcircuitDefinition(name="INV", ports=["A", "Z"])
        assert defn1 != defn2

    def test_port_order_matters(self) -> None:
        """Port order should matter for equality."""
        defn1 = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        defn2 = SubcircuitDefinition(name="INV", ports=["Y", "A"])
        assert defn1 != defn2


class TestSubcircuitDefinitionEdgeCases:
    """Tests for edge cases in SubcircuitDefinition."""

    def test_port_names_with_underscores(self) -> None:
        """Port names with underscores should be accepted."""
        defn = SubcircuitDefinition(name="CELL", ports=["VDD_CORE", "VSS_IO"])
        assert defn.ports == ("VDD_CORE", "VSS_IO")

    def test_port_names_with_numbers(self) -> None:
        """Port names with numbers should be accepted."""
        defn = SubcircuitDefinition(name="MUX", ports=["A0", "A1", "B0", "B1", "Y"])
        assert "A0" in defn.ports
        assert "B1" in defn.ports

    def test_port_names_with_brackets(self) -> None:
        """Port names with brackets (bus notation) should be accepted."""
        defn = SubcircuitDefinition(name="REG", ports=["D<0>", "D<1>", "Q<0>", "Q<1>"])
        assert "D<0>" in defn.ports

    def test_very_long_port_list(self) -> None:
        """Subcircuit with 100+ ports should be handled."""
        ports = [f"P{i}" for i in range(150)]
        defn = SubcircuitDefinition(name="HUGE_CELL", ports=ports)
        assert len(defn.ports) == 150

    def test_single_character_name(self) -> None:
        """Single character cell name should be valid."""
        defn = SubcircuitDefinition(name="X", ports=["A"])
        assert defn.name == "X"

    def test_cell_name_with_numbers(self) -> None:
        """Cell name with numbers should be valid."""
        defn = SubcircuitDefinition(name="INV_X1", ports=["A", "Y"])
        assert defn.name == "INV_X1"


class TestSubcircuitDefinitionHashability:
    """Tests for hashability of SubcircuitDefinition (required for dict keys)."""

    def test_is_hashable(self) -> None:
        """SubcircuitDefinition should be hashable (can be used in sets/dicts)."""
        defn = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        # Should not raise
        hash_val = hash(defn)
        assert isinstance(hash_val, int)

    def test_can_be_used_in_set(self) -> None:
        """SubcircuitDefinition should work in a set."""
        defn1 = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        defn2 = SubcircuitDefinition(name="BUF", ports=["A", "Y"])
        defn3 = SubcircuitDefinition(name="INV", ports=["A", "Y"])  # Same as defn1

        defn_set = {defn1, defn2, defn3}
        assert len(defn_set) == 2  # defn1 and defn3 are equal

    def test_can_be_used_as_dict_key(self) -> None:
        """SubcircuitDefinition should work as dictionary key."""
        defn = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        d = {defn: "inverter"}
        assert d[defn] == "inverter"
