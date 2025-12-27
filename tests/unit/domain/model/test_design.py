"""Unit tests for the Design aggregate root.

This module tests the Design entity, which is the root aggregate for a circuit
design. It contains:
- Subcircuit definitions (cell types)
- Instances (cell instantiations)
- Nets (connectivity information)
- Top-level ports

TDD: These tests are written first (RED phase) to define the expected behavior.
"""

from __future__ import annotations

import pytest

from ink.domain.model.design import Design
from ink.domain.value_objects.instance import CellInstance
from ink.domain.value_objects.net import NetInfo, NetType
from ink.domain.value_objects.subcircuit import SubcircuitDefinition


class TestDesignCreation:
    """Tests for Design construction and initialization."""

    def test_create_empty_design(self) -> None:
        """Create a Design with just a name and empty collections."""
        design = Design(name="test_design")

        assert design.name == "test_design"
        assert design.subcircuit_defs == {}
        assert design.instances == {}
        assert design.nets == {}
        assert design.top_level_ports == []

    def test_create_design_with_subcircuits(self) -> None:
        """Create a Design with subcircuit definitions."""
        inv_def = SubcircuitDefinition(name="INV", ports=["A", "Y", "VDD", "VSS"])
        nand_def = SubcircuitDefinition(name="NAND2", ports=["A", "B", "Y", "VDD", "VSS"])

        design = Design(
            name="test_design",
            subcircuit_defs={"INV": inv_def, "NAND2": nand_def},
        )

        assert len(design.subcircuit_defs) == 2
        assert "INV" in design.subcircuit_defs
        assert "NAND2" in design.subcircuit_defs
        assert design.subcircuit_defs["INV"].ports == ("A", "Y", "VDD", "VSS")

    def test_create_design_with_instances(self) -> None:
        """Create a Design with cell instances."""
        instance1 = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1", "Y": "net2"},
        )
        instance2 = CellInstance(
            name="XI2",
            cell_type="INV",
            connections={"A": "net2", "Y": "net3"},
        )

        design = Design(
            name="test_design",
            instances={"XI1": instance1, "XI2": instance2},
        )

        assert len(design.instances) == 2
        assert "XI1" in design.instances
        assert "XI2" in design.instances
        assert design.instances["XI1"].cell_type == "INV"

    def test_create_design_with_nets(self) -> None:
        """Create a Design with net information."""
        net1 = NetInfo(
            original_name="data<0>",
            normalized_name="data[0]",
            net_type=NetType.SIGNAL,
            is_bus=True,
            bus_index=0,
        )
        vdd = NetInfo(
            original_name="VDD",
            normalized_name="VDD",
            net_type=NetType.POWER,
            is_bus=False,
        )

        design = Design(
            name="test_design",
            nets={"data<0>": net1, "VDD": vdd},
        )

        assert len(design.nets) == 2
        assert "data<0>" in design.nets
        assert "VDD" in design.nets
        assert design.nets["VDD"].net_type == NetType.POWER

    def test_create_design_with_top_level_ports(self) -> None:
        """Create a Design with top-level ports."""
        design = Design(
            name="top_design",
            top_level_ports=["IN", "OUT", "VDD", "VSS"],
        )

        assert len(design.top_level_ports) == 4
        assert "IN" in design.top_level_ports
        assert "OUT" in design.top_level_ports


class TestDesignInstanceManagement:
    """Tests for adding and retrieving instances."""

    def test_add_instance(self) -> None:
        """Add an instance to an existing design."""
        design = Design(name="test_design")
        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1", "Y": "net2"},
        )

        design.add_instance(instance)

        assert "XI1" in design.instances
        assert design.instances["XI1"] == instance

    def test_add_instance_duplicate_raises_error(self) -> None:
        """Adding an instance with duplicate name raises ValueError."""
        design = Design(name="test_design")
        instance1 = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1", "Y": "net2"},
        )
        instance2 = CellInstance(
            name="XI1",
            cell_type="NAND2",
            connections={"A": "net3", "B": "net4", "Y": "net5"},
        )

        design.add_instance(instance1)

        with pytest.raises(ValueError, match="Duplicate instance name"):
            design.add_instance(instance2)

    def test_get_instance_existing(self) -> None:
        """Retrieve an instance by name."""
        instance = CellInstance(
            name="XI1",
            cell_type="INV",
            connections={"A": "net1", "Y": "net2"},
        )
        design = Design(name="test_design", instances={"XI1": instance})

        result = design.get_instance("XI1")

        assert result is not None
        assert result.name == "XI1"
        assert result.cell_type == "INV"

    def test_get_instance_nonexistent(self) -> None:
        """Retrieve a non-existent instance returns None."""
        design = Design(name="test_design")

        result = design.get_instance("NONEXISTENT")

        assert result is None

    def test_get_instances_by_type(self) -> None:
        """Retrieve all instances of a specific cell type."""
        inst1 = CellInstance(name="XI1", cell_type="INV", connections={"A": "n1", "Y": "n2"})
        inst2 = CellInstance(name="XI2", cell_type="INV", connections={"A": "n2", "Y": "n3"})
        inst3 = CellInstance(
            name="XN1", cell_type="NAND2", connections={"A": "n1", "B": "n2", "Y": "n4"}
        )

        design = Design(
            name="test_design",
            instances={"XI1": inst1, "XI2": inst2, "XN1": inst3},
        )

        inv_instances = design.get_instances_by_type("INV")
        nand_instances = design.get_instances_by_type("NAND2")
        unknown_instances = design.get_instances_by_type("UNKNOWN")

        assert len(inv_instances) == 2
        assert len(nand_instances) == 1
        assert len(unknown_instances) == 0
        assert all(inst.cell_type == "INV" for inst in inv_instances)


class TestDesignNetManagement:
    """Tests for net-related operations."""

    def test_add_net(self) -> None:
        """Add a net to an existing design."""
        design = Design(name="test_design")
        net_info = NetInfo(
            original_name="clk",
            normalized_name="clk",
            net_type=NetType.SIGNAL,
            is_bus=False,
        )

        design.add_net("clk", net_info)

        assert "clk" in design.nets
        assert design.nets["clk"].normalized_name == "clk"

    def test_get_net_existing(self) -> None:
        """Retrieve a net by name."""
        net_info = NetInfo(
            original_name="data<0>",
            normalized_name="data[0]",
            net_type=NetType.SIGNAL,
            is_bus=True,
            bus_index=0,
        )
        design = Design(name="test_design", nets={"data<0>": net_info})

        result = design.get_net("data<0>")

        assert result is not None
        assert result.is_bus is True
        assert result.bus_index == 0

    def test_get_net_nonexistent(self) -> None:
        """Retrieve a non-existent net returns None."""
        design = Design(name="test_design")

        result = design.get_net("NONEXISTENT")

        assert result is None

    def test_get_power_nets(self) -> None:
        """Get all power nets from design."""
        vdd = NetInfo("VDD", "VDD", NetType.POWER, False)
        vss = NetInfo("VSS", "VSS", NetType.GROUND, False)
        clk = NetInfo("clk", "clk", NetType.SIGNAL, False)

        design = Design(name="test", nets={"VDD": vdd, "VSS": vss, "clk": clk})

        power_nets = design.get_nets_by_type(NetType.POWER)
        ground_nets = design.get_nets_by_type(NetType.GROUND)
        signal_nets = design.get_nets_by_type(NetType.SIGNAL)

        assert len(power_nets) == 1
        assert len(ground_nets) == 1
        assert len(signal_nets) == 1
        assert power_nets[0].original_name == "VDD"


class TestDesignSubcircuitManagement:
    """Tests for subcircuit definition operations."""

    def test_get_subcircuit_definition_existing(self) -> None:
        """Retrieve a subcircuit definition by name."""
        inv_def = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        design = Design(name="test", subcircuit_defs={"INV": inv_def})

        result = design.get_subcircuit_def("INV")

        assert result is not None
        assert result.name == "INV"
        assert result.ports == ("A", "Y")

    def test_get_subcircuit_definition_nonexistent(self) -> None:
        """Retrieve a non-existent subcircuit definition returns None."""
        design = Design(name="test")

        result = design.get_subcircuit_def("NONEXISTENT")

        assert result is None


class TestDesignStatistics:
    """Tests for design statistics and summary methods."""

    def test_instance_count(self) -> None:
        """Get total instance count."""
        inst1 = CellInstance(name="XI1", cell_type="INV", connections={})
        inst2 = CellInstance(name="XI2", cell_type="INV", connections={})
        design = Design(name="test", instances={"XI1": inst1, "XI2": inst2})

        assert design.instance_count == 2

    def test_net_count(self) -> None:
        """Get total net count."""
        net1 = NetInfo("n1", "n1", NetType.SIGNAL, False)
        net2 = NetInfo("n2", "n2", NetType.SIGNAL, False)
        design = Design(name="test", nets={"n1": net1, "n2": net2})

        assert design.net_count == 2

    def test_subcircuit_count(self) -> None:
        """Get total subcircuit definition count."""
        inv = SubcircuitDefinition(name="INV", ports=["A", "Y"])
        nand = SubcircuitDefinition(name="NAND2", ports=["A", "B", "Y"])
        design = Design(name="test", subcircuit_defs={"INV": inv, "NAND2": nand})

        assert design.subcircuit_count == 2


class TestDesignRepr:
    """Tests for string representation."""

    def test_repr(self) -> None:
        """Test __repr__ for debugging."""
        design = Design(name="my_design")

        result = repr(design)

        assert "Design" in result
        assert "my_design" in result

    def test_str(self) -> None:
        """Test __str__ for human-readable output."""
        inst = CellInstance(name="XI1", cell_type="INV", connections={})
        net = NetInfo("n1", "n1", NetType.SIGNAL, False)
        design = Design(
            name="my_design",
            instances={"XI1": inst},
            nets={"n1": net},
        )

        result = str(design)

        assert "my_design" in result
        # Should include summary info
        assert "1" in result  # instance count or net count
