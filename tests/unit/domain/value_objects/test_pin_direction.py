"""Unit tests for PinDirection enum value object.

This module tests the PinDirection enum which represents the three possible
directions a pin can have: INPUT, OUTPUT, and INOUT (bidirectional/unknown).

The enum is a core value object in the domain layer used throughout the
pin direction handling workflow.
"""

import pytest

from ink.domain.value_objects.pin_direction import PinDirection


class TestPinDirectionEnum:
    """Test suite for PinDirection enum basic functionality."""

    def test_has_input_value(self) -> None:
        """PinDirection should have an INPUT member."""
        assert hasattr(PinDirection, "INPUT")
        assert PinDirection.INPUT is not None

    def test_has_output_value(self) -> None:
        """PinDirection should have an OUTPUT member."""
        assert hasattr(PinDirection, "OUTPUT")
        assert PinDirection.OUTPUT is not None

    def test_has_inout_value(self) -> None:
        """PinDirection should have an INOUT member for bidirectional/unknown pins."""
        assert hasattr(PinDirection, "INOUT")
        assert PinDirection.INOUT is not None

    def test_enum_has_exactly_three_members(self) -> None:
        """PinDirection should have exactly 3 members: INPUT, OUTPUT, INOUT."""
        members = list(PinDirection)
        assert len(members) == 3
        assert PinDirection.INPUT in members
        assert PinDirection.OUTPUT in members
        assert PinDirection.INOUT in members

    def test_input_value_is_string_input(self) -> None:
        """INPUT member value should be the string 'INPUT'."""
        assert PinDirection.INPUT.value == "INPUT"

    def test_output_value_is_string_output(self) -> None:
        """OUTPUT member value should be the string 'OUTPUT'."""
        assert PinDirection.OUTPUT.value == "OUTPUT"

    def test_inout_value_is_string_inout(self) -> None:
        """INOUT member value should be the string 'INOUT'."""
        assert PinDirection.INOUT.value == "INOUT"


class TestPinDirectionStringConversion:
    """Test suite for PinDirection string conversion."""

    def test_str_input_returns_input(self) -> None:
        """str(PinDirection.INPUT) should return 'INPUT'."""
        assert str(PinDirection.INPUT) == "INPUT"

    def test_str_output_returns_output(self) -> None:
        """str(PinDirection.OUTPUT) should return 'OUTPUT'."""
        assert str(PinDirection.OUTPUT) == "OUTPUT"

    def test_str_inout_returns_inout(self) -> None:
        """str(PinDirection.INOUT) should return 'INOUT'."""
        assert str(PinDirection.INOUT) == "INOUT"


class TestPinDirectionLookup:
    """Test suite for PinDirection lookup by name/value."""

    def test_lookup_by_name_input(self) -> None:
        """Should be able to lookup INPUT by name string."""
        assert PinDirection["INPUT"] == PinDirection.INPUT

    def test_lookup_by_name_output(self) -> None:
        """Should be able to lookup OUTPUT by name string."""
        assert PinDirection["OUTPUT"] == PinDirection.OUTPUT

    def test_lookup_by_name_inout(self) -> None:
        """Should be able to lookup INOUT by name string."""
        assert PinDirection["INOUT"] == PinDirection.INOUT

    def test_lookup_by_value_input(self) -> None:
        """Should be able to construct from value string 'INPUT'."""
        assert PinDirection("INPUT") == PinDirection.INPUT

    def test_lookup_by_value_output(self) -> None:
        """Should be able to construct from value string 'OUTPUT'."""
        assert PinDirection("OUTPUT") == PinDirection.OUTPUT

    def test_lookup_by_value_inout(self) -> None:
        """Should be able to construct from value string 'INOUT'."""
        assert PinDirection("INOUT") == PinDirection.INOUT

    def test_lookup_invalid_name_raises_key_error(self) -> None:
        """Looking up invalid name should raise KeyError."""
        with pytest.raises(KeyError):
            _ = PinDirection["INVALID"]

    def test_lookup_invalid_value_raises_value_error(self) -> None:
        """Constructing from invalid value should raise ValueError."""
        with pytest.raises(ValueError):
            _ = PinDirection("INVALID")

    def test_lookup_lowercase_name_raises_key_error(self) -> None:
        """Enum names are case-sensitive, lowercase should fail."""
        with pytest.raises(KeyError):
            _ = PinDirection["input"]


class TestPinDirectionEquality:
    """Test suite for PinDirection equality and identity."""

    def test_same_members_are_equal(self) -> None:
        """Same enum members should be equal."""
        assert PinDirection.INPUT == PinDirection.INPUT
        assert PinDirection.OUTPUT == PinDirection.OUTPUT
        assert PinDirection.INOUT == PinDirection.INOUT

    def test_same_members_are_identical(self) -> None:
        """Same enum members should be identical (singleton)."""
        assert PinDirection.INPUT is PinDirection.INPUT
        assert PinDirection.OUTPUT is PinDirection.OUTPUT
        assert PinDirection.INOUT is PinDirection.INOUT

    def test_different_members_are_not_equal(self) -> None:
        """Different enum members should not be equal."""
        # Intentionally comparing different enum members
        assert PinDirection.INPUT != PinDirection.OUTPUT  # type: ignore[comparison-overlap]
        assert PinDirection.INPUT != PinDirection.INOUT  # type: ignore[comparison-overlap]
        assert PinDirection.OUTPUT != PinDirection.INOUT  # type: ignore[comparison-overlap]


class TestPinDirectionIsInputMethod:
    """Test suite for PinDirection.is_input() helper method.

    The is_input() method returns True for INPUT and INOUT directions,
    as INOUT pins can receive signals (bidirectional).
    """

    def test_input_is_input_returns_true(self) -> None:
        """INPUT direction should return True for is_input()."""
        assert PinDirection.INPUT.is_input() is True

    def test_inout_is_input_returns_true(self) -> None:
        """INOUT direction should return True for is_input() (bidirectional)."""
        assert PinDirection.INOUT.is_input() is True

    def test_output_is_input_returns_false(self) -> None:
        """OUTPUT direction should return False for is_input()."""
        assert PinDirection.OUTPUT.is_input() is False


class TestPinDirectionIsOutputMethod:
    """Test suite for PinDirection.is_output() helper method.

    The is_output() method returns True for OUTPUT and INOUT directions,
    as INOUT pins can drive signals (bidirectional).
    """

    def test_output_is_output_returns_true(self) -> None:
        """OUTPUT direction should return True for is_output()."""
        assert PinDirection.OUTPUT.is_output() is True

    def test_inout_is_output_returns_true(self) -> None:
        """INOUT direction should return True for is_output() (bidirectional)."""
        assert PinDirection.INOUT.is_output() is True

    def test_input_is_output_returns_false(self) -> None:
        """INPUT direction should return False for is_output()."""
        assert PinDirection.INPUT.is_output() is False
