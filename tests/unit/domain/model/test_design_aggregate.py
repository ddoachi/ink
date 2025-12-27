"""Unit tests for the Design aggregate root with domain entities.

This module tests the Design aggregate, which is the root aggregate for managing
domain entities: Cell, Pin, Net, and Port. The Design aggregate enforces domain
invariants, provides O(1) lookup by ID and name, and validates referential integrity.

TDD: These tests are written first (RED phase) to define the expected behavior.

Test Structure:
- TestDesignCreation: Construction and initialization
- TestAddCell: Adding cells with duplicate detection
- TestAddNet: Adding nets with duplicate detection
- TestAddPin: Adding pins with duplicate detection
- TestAddPort: Adding ports with duplicate detection
- TestGettersById: O(1) lookup by ID
- TestGettersByName: O(1) lookup by name (via index)
- TestCollectionAccessors: get_all_* methods returning copies
- TestStatistics: Count methods
- TestValidation: Referential integrity validation
- TestRepr: String representations

Coverage Target: 95%+
"""

from __future__ import annotations

import pytest

from ink.domain.model.cell import Cell
from ink.domain.model.design import Design
from ink.domain.model.net import Net
from ink.domain.model.pin import Pin
from ink.domain.model.port import Port
from ink.domain.value_objects.identifiers import CellId, NetId, PinId, PortId
from ink.domain.value_objects.pin_direction import PinDirection

# -- Test Fixtures ------------------------------------------------------------


def create_test_cell(
    cell_id: str = "XI1",
    name: str | None = None,
    cell_type: str = "INV_X1",
    pin_ids: list[str] | None = None,
    is_sequential: bool = False,
) -> Cell:
    """Factory helper to create test cells with sensible defaults."""
    return Cell(
        id=CellId(cell_id),
        name=name or cell_id,
        cell_type=cell_type,
        pin_ids=[PinId(p) for p in (pin_ids or [])],
        is_sequential=is_sequential,
    )


def create_test_net(
    net_id: str = "net1",
    name: str | None = None,
    pin_ids: list[str] | None = None,
) -> Net:
    """Factory helper to create test nets with sensible defaults."""
    return Net(
        id=NetId(net_id),
        name=name or net_id,
        connected_pin_ids=[PinId(p) for p in (pin_ids or [])],
    )


def create_test_pin(
    pin_id: str = "XI1.A",
    name: str = "A",
    direction: PinDirection = PinDirection.INPUT,
    net_id: str | None = None,
) -> Pin:
    """Factory helper to create test pins with sensible defaults."""
    return Pin(
        id=PinId(pin_id),
        name=name,
        direction=direction,
        net_id=NetId(net_id) if net_id else None,
    )


def create_test_port(
    port_id: str = "IN",
    name: str | None = None,
    direction: PinDirection = PinDirection.INPUT,
    net_id: str | None = None,
) -> Port:
    """Factory helper to create test ports with sensible defaults."""
    return Port(
        id=PortId(port_id),
        name=name or port_id,
        direction=direction,
        net_id=NetId(net_id) if net_id else None,
    )




class TestDesignCreation:
    """Tests for Design construction and initialization."""

    def test_create_empty_design(self) -> None:
        """Create a Design with just a name and empty collections."""
        design = Design(name="test_design")

        assert design.name == "test_design"
        assert design.cell_count() == 0
        assert design.net_count() == 0
        assert design.pin_count() == 0
        assert design.port_count() == 0

    def test_design_name_stored_correctly(self) -> None:
        """Design name is stored exactly as provided."""
        design = Design(name="my_circuit_v2")
        assert design.name == "my_circuit_v2"

    def test_design_collections_are_private(self) -> None:
        """Internal collections are not directly accessible."""
        design = Design(name="test")

        # These should be private (prefixed with _)
        # The design should only expose via methods
        assert hasattr(design, "_cells")
        assert hasattr(design, "_nets")
        assert hasattr(design, "_pins")
        assert hasattr(design, "_ports")


# TestAddCell: Adding Cells with Duplicate Detection


class TestAddCell:
    """Tests for add_cell method with duplicate detection."""

    def test_add_cell_success(self) -> None:
        """Should add cell to design and update indexes."""
        design = Design(name="test")
        cell = create_test_cell("XI1", cell_type="INV_X1")

        design.add_cell(cell)

        assert design.cell_count() == 1
        assert design.get_cell(CellId("XI1")) == cell
        assert design.get_cell_by_name("XI1") == cell

    def test_add_multiple_cells(self) -> None:
        """Should add multiple cells without conflict."""
        design = Design(name="test")
        cell1 = create_test_cell("XI1", cell_type="INV_X1")
        cell2 = create_test_cell("XI2", cell_type="AND2_X1")
        cell3 = create_test_cell("XFF1", cell_type="DFF_X1", is_sequential=True)

        design.add_cell(cell1)
        design.add_cell(cell2)
        design.add_cell(cell3)

        assert design.cell_count() == 3
        assert design.get_cell(CellId("XI1")) == cell1
        assert design.get_cell(CellId("XI2")) == cell2
        assert design.get_cell(CellId("XFF1")) == cell3

    def test_add_cell_duplicate_id_raises_error(self) -> None:
        """Should raise ValueError when adding cell with duplicate ID."""
        design = Design(name="test")
        cell1 = create_test_cell("XI1", name="first_cell", cell_type="INV_X1")
        cell2 = create_test_cell("XI1", name="second_cell", cell_type="AND2_X1")

        design.add_cell(cell1)

        with pytest.raises(ValueError, match=r"Cell with id .* already exists"):
            design.add_cell(cell2)

    def test_add_cell_duplicate_name_raises_error(self) -> None:
        """Should raise ValueError when adding cell with duplicate name."""
        design = Design(name="test")
        cell1 = Cell(
            id=CellId("cell_id_1"),
            name="SHARED_NAME",
            cell_type="INV_X1",
        )
        cell2 = Cell(
            id=CellId("cell_id_2"),
            name="SHARED_NAME",
            cell_type="AND2_X1",
        )

        design.add_cell(cell1)

        with pytest.raises(ValueError, match=r"Cell with name .* already exists"):
            design.add_cell(cell2)

    def test_add_cell_preserves_immutability(self) -> None:
        """Cell added to design should remain unchanged."""
        design = Design(name="test")
        cell = create_test_cell("XI1", cell_type="INV_X1")

        design.add_cell(cell)
        retrieved = design.get_cell(CellId("XI1"))

        assert retrieved is cell  # Same object (frozen, so safe)
        assert retrieved == cell


# TestAddNet: Adding Nets with Duplicate Detection


class TestAddNet:
    """Tests for add_net method with duplicate detection."""

    def test_add_net_success(self) -> None:
        """Should add net to design and update indexes."""
        design = Design(name="test")
        net = create_test_net("net1")

        design.add_net(net)

        assert design.net_count() == 1
        assert design.get_net(NetId("net1")) == net
        assert design.get_net_by_name("net1") == net

    def test_add_multiple_nets(self) -> None:
        """Should add multiple nets without conflict."""
        design = Design(name="test")
        net1 = create_test_net("clk")
        net2 = create_test_net("data_in")
        net3 = create_test_net("data_out")

        design.add_net(net1)
        design.add_net(net2)
        design.add_net(net3)

        assert design.net_count() == 3

    def test_add_net_duplicate_id_raises_error(self) -> None:
        """Should raise ValueError when adding net with duplicate ID."""
        design = Design(name="test")
        net1 = create_test_net("net1", name="first_net")
        net2 = create_test_net("net1", name="second_net")

        design.add_net(net1)

        with pytest.raises(ValueError, match=r"Net with id .* already exists"):
            design.add_net(net2)

    def test_add_net_duplicate_name_raises_error(self) -> None:
        """Should raise ValueError when adding net with duplicate name."""
        design = Design(name="test")
        net1 = Net(id=NetId("net_id_1"), name="SHARED_NAME")
        net2 = Net(id=NetId("net_id_2"), name="SHARED_NAME")

        design.add_net(net1)

        with pytest.raises(ValueError, match=r"Net with name .* already exists"):
            design.add_net(net2)


# TestAddPin: Adding Pins with Duplicate Detection


class TestAddPin:
    """Tests for add_pin method with duplicate detection."""

    def test_add_pin_success(self) -> None:
        """Should add pin to design."""
        design = Design(name="test")
        pin = create_test_pin("XI1.A", "A", PinDirection.INPUT)

        design.add_pin(pin)

        assert design.pin_count() == 1
        assert design.get_pin(PinId("XI1.A")) == pin

    def test_add_multiple_pins(self) -> None:
        """Should add multiple pins without conflict."""
        design = Design(name="test")
        pin1 = create_test_pin("XI1.A", "A", PinDirection.INPUT)
        pin2 = create_test_pin("XI1.Y", "Y", PinDirection.OUTPUT)
        pin3 = create_test_pin("XI2.A", "A", PinDirection.INPUT)

        design.add_pin(pin1)
        design.add_pin(pin2)
        design.add_pin(pin3)

        assert design.pin_count() == 3

    def test_add_pin_duplicate_id_raises_error(self) -> None:
        """Should raise ValueError when adding pin with duplicate ID."""
        design = Design(name="test")
        pin1 = create_test_pin("XI1.A", "A", PinDirection.INPUT)
        pin2 = create_test_pin("XI1.A", "A", PinDirection.OUTPUT)  # Same ID

        design.add_pin(pin1)

        with pytest.raises(ValueError, match=r"Pin with id .* already exists"):
            design.add_pin(pin2)

    def test_pins_no_name_index(self) -> None:
        """Pins do not have name-based lookup (names not unique globally)."""
        design = Design(name="test")
        # Multiple pins can have same local name (e.g., "A" on different cells)
        pin1 = create_test_pin("XI1.A", "A", PinDirection.INPUT)
        pin2 = create_test_pin("XI2.A", "A", PinDirection.INPUT)

        design.add_pin(pin1)
        design.add_pin(pin2)

        # Both should be added successfully (no name uniqueness for pins)
        assert design.pin_count() == 2


# TestAddPort: Adding Ports with Duplicate Detection


class TestAddPort:
    """Tests for add_port method with duplicate detection."""

    def test_add_port_success(self) -> None:
        """Should add port to design and update indexes."""
        design = Design(name="test")
        port = create_test_port("IN", direction=PinDirection.INPUT)

        design.add_port(port)

        assert design.port_count() == 1
        assert design.get_port(PortId("IN")) == port
        assert design.get_port_by_name("IN") == port

    def test_add_multiple_ports(self) -> None:
        """Should add multiple ports without conflict."""
        design = Design(name="test")
        port1 = create_test_port("IN", direction=PinDirection.INPUT)
        port2 = create_test_port("OUT", direction=PinDirection.OUTPUT)
        port3 = create_test_port("CLK", direction=PinDirection.INPUT)

        design.add_port(port1)
        design.add_port(port2)
        design.add_port(port3)

        assert design.port_count() == 3

    def test_add_port_duplicate_id_raises_error(self) -> None:
        """Should raise ValueError when adding port with duplicate ID."""
        design = Design(name="test")
        port1 = create_test_port("IN", name="first", direction=PinDirection.INPUT)
        port2 = create_test_port("IN", name="second", direction=PinDirection.OUTPUT)

        design.add_port(port1)

        with pytest.raises(ValueError, match=r"Port with id .* already exists"):
            design.add_port(port2)

    def test_add_port_duplicate_name_raises_error(self) -> None:
        """Should raise ValueError when adding port with duplicate name."""
        design = Design(name="test")
        port1 = Port(
            id=PortId("port_id_1"),
            name="SHARED_NAME",
            direction=PinDirection.INPUT,
            net_id=None,
        )
        port2 = Port(
            id=PortId("port_id_2"),
            name="SHARED_NAME",
            direction=PinDirection.OUTPUT,
            net_id=None,
        )

        design.add_port(port1)

        with pytest.raises(ValueError, match=r"Port with name .* already exists"):
            design.add_port(port2)


# TestGettersById: O(1) Lookup by ID


class TestGettersById:
    """Tests for ID-based getter methods (O(1) lookup)."""

    def test_get_cell_returns_cell_when_exists(self) -> None:
        """Should return cell when ID exists."""
        design = Design(name="test")
        cell = create_test_cell("XI1", cell_type="INV_X1")
        design.add_cell(cell)

        result = design.get_cell(CellId("XI1"))

        assert result == cell

    def test_get_cell_returns_none_when_not_exists(self) -> None:
        """Should return None when ID does not exist."""
        design = Design(name="test")

        result = design.get_cell(CellId("nonexistent"))

        assert result is None

    def test_get_net_returns_net_when_exists(self) -> None:
        """Should return net when ID exists."""
        design = Design(name="test")
        net = create_test_net("clk")
        design.add_net(net)

        result = design.get_net(NetId("clk"))

        assert result == net

    def test_get_net_returns_none_when_not_exists(self) -> None:
        """Should return None when ID does not exist."""
        design = Design(name="test")

        result = design.get_net(NetId("nonexistent"))

        assert result is None

    def test_get_pin_returns_pin_when_exists(self) -> None:
        """Should return pin when ID exists."""
        design = Design(name="test")
        pin = create_test_pin("XI1.A", "A", PinDirection.INPUT)
        design.add_pin(pin)

        result = design.get_pin(PinId("XI1.A"))

        assert result == pin

    def test_get_pin_returns_none_when_not_exists(self) -> None:
        """Should return None when ID does not exist."""
        design = Design(name="test")

        result = design.get_pin(PinId("nonexistent"))

        assert result is None

    def test_get_port_returns_port_when_exists(self) -> None:
        """Should return port when ID exists."""
        design = Design(name="test")
        port = create_test_port("IN", direction=PinDirection.INPUT)
        design.add_port(port)

        result = design.get_port(PortId("IN"))

        assert result == port

    def test_get_port_returns_none_when_not_exists(self) -> None:
        """Should return None when ID does not exist."""
        design = Design(name="test")

        result = design.get_port(PortId("nonexistent"))

        assert result is None


# TestGettersByName: O(1) Lookup by Name (via Index)


class TestGettersByName:
    """Tests for name-based getter methods (O(1) lookup via index)."""

    def test_get_cell_by_name_returns_cell_when_exists(self) -> None:
        """Should return cell when name exists in index."""
        design = Design(name="test")
        cell = create_test_cell("XI1", name="inverter_1", cell_type="INV_X1")
        design.add_cell(cell)

        result = design.get_cell_by_name("inverter_1")

        assert result == cell

    def test_get_cell_by_name_returns_none_when_not_exists(self) -> None:
        """Should return None when name does not exist in index."""
        design = Design(name="test")

        result = design.get_cell_by_name("nonexistent")

        assert result is None

    def test_get_net_by_name_returns_net_when_exists(self) -> None:
        """Should return net when name exists in index."""
        design = Design(name="test")
        net = create_test_net("net_id", name="clock_signal")
        design.add_net(net)

        result = design.get_net_by_name("clock_signal")

        assert result == net

    def test_get_net_by_name_returns_none_when_not_exists(self) -> None:
        """Should return None when name does not exist in index."""
        design = Design(name="test")

        result = design.get_net_by_name("nonexistent")

        assert result is None

    def test_get_port_by_name_returns_port_when_exists(self) -> None:
        """Should return port when name exists in index."""
        design = Design(name="test")
        port = create_test_port("port_id", name="data_input")
        design.add_port(port)

        result = design.get_port_by_name("data_input")

        assert result == port

    def test_get_port_by_name_returns_none_when_not_exists(self) -> None:
        """Should return None when name does not exist in index."""
        design = Design(name="test")

        result = design.get_port_by_name("nonexistent")

        assert result is None


# TestCollectionAccessors: get_all_* Methods Returning Copies


class TestCollectionAccessors:
    """Tests for collection accessor methods returning immutable copies."""

    def test_get_all_cells_returns_list(self) -> None:
        """Should return a list of all cells."""
        design = Design(name="test")
        cell1 = create_test_cell("XI1")
        cell2 = create_test_cell("XI2")
        design.add_cell(cell1)
        design.add_cell(cell2)

        result = design.get_all_cells()

        assert isinstance(result, list)
        assert len(result) == 2
        assert cell1 in result
        assert cell2 in result

    def test_get_all_cells_returns_copy(self) -> None:
        """Modifying returned list should not affect internal storage."""
        design = Design(name="test")
        cell = create_test_cell("XI1")
        design.add_cell(cell)

        result = design.get_all_cells()
        result.clear()  # Modify the returned list

        # Internal storage should be unaffected
        assert design.cell_count() == 1
        assert design.get_cell(CellId("XI1")) == cell

    def test_get_all_nets_returns_list(self) -> None:
        """Should return a list of all nets."""
        design = Design(name="test")
        net1 = create_test_net("net1")
        net2 = create_test_net("net2")
        design.add_net(net1)
        design.add_net(net2)

        result = design.get_all_nets()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_all_nets_returns_copy(self) -> None:
        """Modifying returned list should not affect internal storage."""
        design = Design(name="test")
        net = create_test_net("net1")
        design.add_net(net)

        result = design.get_all_nets()
        result.clear()

        assert design.net_count() == 1

    def test_get_all_pins_returns_list(self) -> None:
        """Should return a list of all pins."""
        design = Design(name="test")
        pin1 = create_test_pin("XI1.A")
        pin2 = create_test_pin("XI1.Y", "Y", PinDirection.OUTPUT)
        design.add_pin(pin1)
        design.add_pin(pin2)

        result = design.get_all_pins()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_all_pins_returns_copy(self) -> None:
        """Modifying returned list should not affect internal storage."""
        design = Design(name="test")
        pin = create_test_pin("XI1.A")
        design.add_pin(pin)

        result = design.get_all_pins()
        result.clear()

        assert design.pin_count() == 1

    def test_get_all_ports_returns_list(self) -> None:
        """Should return a list of all ports."""
        design = Design(name="test")
        port1 = create_test_port("IN")
        port2 = create_test_port("OUT", direction=PinDirection.OUTPUT)
        design.add_port(port1)
        design.add_port(port2)

        result = design.get_all_ports()

        assert isinstance(result, list)
        assert len(result) == 2

    def test_get_all_ports_returns_copy(self) -> None:
        """Modifying returned list should not affect internal storage."""
        design = Design(name="test")
        port = create_test_port("IN")
        design.add_port(port)

        result = design.get_all_ports()
        result.clear()

        assert design.port_count() == 1

    def test_get_all_cells_empty_design(self) -> None:
        """Should return empty list for empty design."""
        design = Design(name="test")

        result = design.get_all_cells()

        assert result == []

    def test_get_all_nets_empty_design(self) -> None:
        """Should return empty list for empty design."""
        design = Design(name="test")

        result = design.get_all_nets()

        assert result == []


# TestStatistics: Count Methods


class TestStatistics:
    """Tests for statistics and count methods."""

    def test_cell_count_returns_correct_count(self) -> None:
        """Should return number of cells in design."""
        design = Design(name="test")
        assert design.cell_count() == 0

        design.add_cell(create_test_cell("XI1"))
        assert design.cell_count() == 1

        design.add_cell(create_test_cell("XI2"))
        assert design.cell_count() == 2

    def test_net_count_returns_correct_count(self) -> None:
        """Should return number of nets in design."""
        design = Design(name="test")
        assert design.net_count() == 0

        design.add_net(create_test_net("net1"))
        assert design.net_count() == 1

    def test_pin_count_returns_correct_count(self) -> None:
        """Should return number of pins in design."""
        design = Design(name="test")
        assert design.pin_count() == 0

        design.add_pin(create_test_pin("XI1.A"))
        assert design.pin_count() == 1

    def test_port_count_returns_correct_count(self) -> None:
        """Should return number of ports in design."""
        design = Design(name="test")
        assert design.port_count() == 0

        design.add_port(create_test_port("IN"))
        assert design.port_count() == 1

    def test_sequential_cell_count_counts_only_sequential(self) -> None:
        """Should count only cells where is_sequential=True."""
        design = Design(name="test")

        # Add combinational cells
        design.add_cell(create_test_cell("XI1", cell_type="INV_X1", is_sequential=False))
        design.add_cell(create_test_cell("XI2", cell_type="AND2_X1", is_sequential=False))

        # Add sequential cells
        design.add_cell(create_test_cell("XFF1", cell_type="DFF_X1", is_sequential=True))
        design.add_cell(create_test_cell("XFF2", cell_type="DFF_X1", is_sequential=True))

        assert design.cell_count() == 4
        assert design.sequential_cell_count() == 2

    def test_sequential_cell_count_zero_when_no_sequential(self) -> None:
        """Should return 0 when no sequential cells exist."""
        design = Design(name="test")
        design.add_cell(create_test_cell("XI1", is_sequential=False))

        assert design.sequential_cell_count() == 0


# TestValidation: Referential Integrity Validation


class TestValidation:
    """Tests for validate() method checking referential integrity."""

    def test_validate_empty_design_returns_no_errors(self) -> None:
        """Empty design should be valid."""
        design = Design(name="test")

        errors = design.validate()

        assert errors == []

    def test_validate_detects_pin_referencing_nonexistent_net(self) -> None:
        """Should detect when pin references non-existent net."""
        design = Design(name="test")
        pin = create_test_pin("XI1.A", "A", PinDirection.INPUT, net_id="nonexistent_net")
        design.add_pin(pin)

        errors = design.validate()

        assert len(errors) == 1
        assert "Pin" in errors[0]
        assert "XI1.A" in errors[0]
        assert "nonexistent" in errors[0].lower() or "non-existent" in errors[0].lower()

    def test_validate_detects_cell_referencing_nonexistent_pin(self) -> None:
        """Should detect when cell references non-existent pin."""
        design = Design(name="test")
        cell = create_test_cell("XI1", pin_ids=["XI1.A", "XI1.Y"])  # Pins don't exist
        design.add_cell(cell)

        errors = design.validate()

        assert len(errors) >= 1
        # Should report both missing pins
        error_text = " ".join(errors)
        assert "Cell" in error_text
        assert "XI1" in error_text

    def test_validate_detects_net_referencing_nonexistent_pin(self) -> None:
        """Should detect when net references non-existent pin."""
        design = Design(name="test")
        net = create_test_net("net1", pin_ids=["XI1.A", "XI2.A"])  # Pins don't exist
        design.add_net(net)

        errors = design.validate()

        assert len(errors) >= 1
        error_text = " ".join(errors)
        assert "Net" in error_text
        assert "net1" in error_text

    def test_validate_detects_port_referencing_nonexistent_net(self) -> None:
        """Should detect when port references non-existent net."""
        design = Design(name="test")
        port = create_test_port("IN", net_id="nonexistent_net")
        design.add_port(port)

        errors = design.validate()

        assert len(errors) == 1
        assert "Port" in errors[0]
        assert "IN" in errors[0]

    def test_validate_valid_design_returns_empty_list(self) -> None:
        """Should return empty list when design is valid (all references valid)."""
        design = Design(name="test")

        # Create valid structure: net -> pin, cell -> pin, port -> net
        net = create_test_net("net1", pin_ids=["XI1.A"])
        pin = create_test_pin("XI1.A", "A", PinDirection.INPUT, net_id="net1")
        cell = create_test_cell("XI1", pin_ids=["XI1.A"])
        port = create_test_port("IN", net_id="net1")

        # Add in dependency order
        design.add_net(net)
        design.add_pin(pin)
        design.add_cell(cell)
        design.add_port(port)

        errors = design.validate()

        assert errors == []

    def test_validate_multiple_errors(self) -> None:
        """Should collect all validation errors, not just the first."""
        design = Design(name="test")

        # Multiple invalid references
        pin1 = create_test_pin("p1", net_id="missing_net1")
        pin2 = create_test_pin("p2", net_id="missing_net2")
        design.add_pin(pin1)
        design.add_pin(pin2)

        errors = design.validate()

        assert len(errors) >= 2

    def test_validate_pin_with_none_net_is_valid(self) -> None:
        """Floating pin (net_id=None) should be valid."""
        design = Design(name="test")
        floating_pin = create_test_pin("XI1.NC", "NC", PinDirection.INPUT, net_id=None)
        design.add_pin(floating_pin)

        errors = design.validate()

        assert errors == []

    def test_validate_port_with_none_net_is_valid(self) -> None:
        """Unconnected port (net_id=None) should be valid."""
        design = Design(name="test")
        port = create_test_port("UNUSED", direction=PinDirection.INPUT, net_id=None)
        design.add_port(port)

        errors = design.validate()

        assert errors == []


# TestRepr: String Representations


class TestRepr:
    """Tests for __repr__ and string representation."""

    def test_repr_shows_design_summary(self) -> None:
        """__repr__ should show design name and counts."""
        design = Design(name="test_design")
        design.add_cell(create_test_cell("XI1"))
        design.add_net(create_test_net("net1"))

        result = repr(design)

        assert "Design" in result
        assert "test_design" in result
        assert "cells=1" in result or "1" in result
        assert "nets=1" in result or "1" in result

    def test_repr_empty_design(self) -> None:
        """__repr__ should work for empty design."""
        design = Design(name="empty")

        result = repr(design)

        assert "Design" in result
        assert "empty" in result


# Integration Test: Build Complete Design


class TestIntegration:
    """Integration tests building complete valid designs."""

    def test_build_simple_inverter_design(self) -> None:
        """Should build complete design with cell, pins, nets, ports."""
        design = Design(name="inverter")

        # Create nets
        net_in = create_test_net("in", pin_ids=["XI1.A"])
        net_out = create_test_net("out", pin_ids=["XI1.Y"])
        design.add_net(net_in)
        design.add_net(net_out)

        # Create pins
        pin_a = create_test_pin("XI1.A", "A", PinDirection.INPUT, net_id="in")
        pin_y = create_test_pin("XI1.Y", "Y", PinDirection.OUTPUT, net_id="out")
        design.add_pin(pin_a)
        design.add_pin(pin_y)

        # Create cell
        cell = create_test_cell("XI1", cell_type="INV_X1", pin_ids=["XI1.A", "XI1.Y"])
        design.add_cell(cell)

        # Create ports
        port_in = create_test_port("IN", direction=PinDirection.INPUT, net_id="in")
        port_out = create_test_port("OUT", direction=PinDirection.OUTPUT, net_id="out")
        design.add_port(port_in)
        design.add_port(port_out)

        # Validate
        errors = design.validate()
        assert len(errors) == 0

        # Verify structure
        assert design.cell_count() == 1
        assert design.net_count() == 2
        assert design.pin_count() == 2
        assert design.port_count() == 2

        # Verify lookups work
        assert design.get_cell_by_name("XI1") == cell
        assert design.get_net_by_name("in") == net_in
        assert design.get_port_by_name("IN") == port_in

    def test_build_design_with_sequential_cells(self) -> None:
        """Should correctly track sequential cells."""
        design = Design(name="sequential_test")

        # Add mix of combinational and sequential cells
        design.add_cell(create_test_cell("XI1", cell_type="INV_X1", is_sequential=False))
        design.add_cell(create_test_cell("XFF1", cell_type="DFF_X1", is_sequential=True))
        design.add_cell(create_test_cell("XFF2", cell_type="LATCH_X1", is_sequential=True))

        assert design.cell_count() == 3
        assert design.sequential_cell_count() == 2

        # Verify individual cells
        ff1 = design.get_cell_by_name("XFF1")
        assert ff1 is not None
        assert ff1.is_latch() is True

        inv = design.get_cell_by_name("XI1")
        assert inv is not None
        assert inv.is_latch() is False
