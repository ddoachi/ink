"""Unit tests for Cell domain entity.

This module tests the Cell entity which represents a gate-level cell instance.
Cell is a frozen dataclass with helper methods for identifying sequential elements.

The Cell entity is a core domain concept representing gate instances in a netlist.
"""

import pytest
from dataclasses import FrozenInstanceError

from ink.domain.model.cell import Cell
from ink.domain.value_objects.identifiers import CellId, PinId


class TestCellCreation:
    """Test suite for Cell entity creation."""

    def test_cell_creation_with_all_fields(self) -> None:
        """Should create Cell with all required and optional fields."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
            pin_ids=[PinId("XI1.A"), PinId("XI1.Y")],
            is_sequential=False,
        )

        assert cell.id == CellId("XI1")
        assert cell.name == "XI1"
        assert cell.cell_type == "INV_X1"
        assert len(cell.pin_ids) == 2
        assert cell.is_sequential is False

    def test_cell_creation_with_minimal_fields(self) -> None:
        """Should create Cell with only required fields (defaults for others)."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
        )

        assert cell.id == CellId("XI1")
        assert cell.name == "XI1"
        assert cell.cell_type == "INV_X1"
        assert cell.pin_ids == ()  # Default empty tuple
        assert cell.is_sequential is False  # Default False

    def test_cell_creation_as_sequential(self) -> None:
        """Should create Cell with is_sequential=True for flip-flops."""
        cell = Cell(
            id=CellId("XFF1"),
            name="XFF1",
            cell_type="DFF_X1",
            pin_ids=[PinId("XFF1.D"), PinId("XFF1.CLK"), PinId("XFF1.Q")],
            is_sequential=True,
        )

        assert cell.is_sequential is True

    def test_cell_creation_with_many_pins(self) -> None:
        """Should create Cell with many pins (e.g., NAND4, MUX)."""
        cell = Cell(
            id=CellId("XNAND4"),
            name="XNAND4",
            cell_type="NAND4_X1",
            pin_ids=[
                PinId("XNAND4.A"),
                PinId("XNAND4.B"),
                PinId("XNAND4.C"),
                PinId("XNAND4.D"),
                PinId("XNAND4.Y"),
            ],
        )

        assert len(cell.pin_ids) == 5


class TestCellIsLatch:
    """Test suite for Cell.is_latch() helper method."""

    def test_is_latch_true_for_sequential_cell(self) -> None:
        """is_latch() should return True when is_sequential is True."""
        cell = Cell(
            id=CellId("XFF1"),
            name="XFF1",
            cell_type="DFF_X1",
            is_sequential=True,
        )

        assert cell.is_latch() is True

    def test_is_latch_false_for_combinational_cell(self) -> None:
        """is_latch() should return False when is_sequential is False."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
            is_sequential=False,
        )

        assert cell.is_latch() is False

    def test_is_latch_false_by_default(self) -> None:
        """is_latch() should return False for cells created with defaults."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
        )

        assert cell.is_latch() is False


class TestCellImmutability:
    """Test suite for Cell frozen dataclass immutability."""

    def test_cell_id_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign id on frozen Cell."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
        )

        with pytest.raises(FrozenInstanceError):
            cell.id = CellId("XI2")  # type: ignore[misc]

    def test_cell_name_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign name on frozen Cell."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
        )

        with pytest.raises(FrozenInstanceError):
            cell.name = "XI2"  # type: ignore[misc]

    def test_cell_type_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign cell_type on frozen Cell."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
        )

        with pytest.raises(FrozenInstanceError):
            cell.cell_type = "NAND2_X1"  # type: ignore[misc]

    def test_cell_pin_ids_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign pin_ids on frozen Cell."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
            pin_ids=[PinId("XI1.A")],
        )

        with pytest.raises(FrozenInstanceError):
            cell.pin_ids = [PinId("XI1.B")]  # type: ignore[misc]

    def test_cell_is_sequential_cannot_be_reassigned(self) -> None:
        """Should raise error when trying to reassign is_sequential on frozen Cell."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
            is_sequential=False,
        )

        with pytest.raises(FrozenInstanceError):
            cell.is_sequential = True  # type: ignore[misc]

    def test_cell_pin_ids_tuple_is_immutable(self) -> None:
        """pin_ids should be a tuple (immutable)."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
            pin_ids=[PinId("XI1.A")],
        )

        # Tuple doesn't have append method
        assert not hasattr(cell.pin_ids, "append")


class TestCellEquality:
    """Test suite for Cell equality comparisons."""

    def test_cells_with_same_values_are_equal(self) -> None:
        """Two Cells with identical values should be equal."""
        cell1 = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
            pin_ids=[PinId("XI1.A"), PinId("XI1.Y")],
            is_sequential=False,
        )
        cell2 = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
            pin_ids=[PinId("XI1.A"), PinId("XI1.Y")],
            is_sequential=False,
        )

        assert cell1 == cell2

    def test_cells_with_different_ids_are_not_equal(self) -> None:
        """Cells with different ids should not be equal."""
        cell1 = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
        )
        cell2 = Cell(
            id=CellId("XI2"),
            name="XI2",
            cell_type="INV_X1",
        )

        assert cell1 != cell2


class TestCellHashability:
    """Test suite for Cell as hashable object (for use in sets/dicts)."""

    def test_cell_is_hashable(self) -> None:
        """Cell should be usable as dictionary key."""
        cell = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
        )

        d: dict[Cell, str] = {cell: "inverter"}
        assert d[cell] == "inverter"

    def test_equal_cells_have_same_hash(self) -> None:
        """Equal Cells should have the same hash."""
        cell1 = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
            pin_ids=[PinId("XI1.A")],
        )
        cell2 = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
            pin_ids=[PinId("XI1.A")],
        )

        assert hash(cell1) == hash(cell2)

    def test_cells_can_be_used_in_sets(self) -> None:
        """Cells should be usable in sets with proper deduplication."""
        cell1 = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
        )
        cell2 = Cell(
            id=CellId("XI1"),
            name="XI1",
            cell_type="INV_X1",
        )
        cell3 = Cell(
            id=CellId("XI2"),
            name="XI2",
            cell_type="NAND2_X1",
        )

        cell_set = {cell1, cell2, cell3}
        # cell1 and cell2 are equal, so set should have 2 elements
        assert len(cell_set) == 2
