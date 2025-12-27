"""Net name normalization for CDL parsing.

This module provides the NetNormalizer class that processes raw net names from CDL
netlists into a normalized, consistent format. This normalization is critical for:

1. **Connectivity Matching**: Ensures that nets with different representations
   (e.g., "data<7>" vs "data[7]") are correctly identified as the same net.

2. **Power/Ground Identification**: Automatically classifies power and ground nets
   to enable filtering, highlighting, or special handling in the UI.

3. **Performance**: Caches normalized results to avoid repeated regex processing
   for the same net names (common in large netlists with many instances).

CDL Netlist Net Name Patterns:
- Bus notation: signal<N> where N is a bit index (e.g., data<7>, addr<0>)
- Power nets: VDD, VDDA, VCC, VPWR and variants
- Ground nets: VSS, VSSA, GND, VGND and variants
- Trailing markers: ! or ? suffixes (e.g., VDD!, clk?)
- Escaped names: Names with special characters (handled by preserving)

Example Usage:
    >>> normalizer = NetNormalizer()
    >>> info = normalizer.normalize("data<7>")
    >>> print(info.normalized_name)  # "data[7]"
    >>> print(info.is_bus)  # True
    >>> print(info.bus_index)  # 7

    >>> info = normalizer.normalize("VDD!")
    >>> print(info.net_type)  # NetType.POWER
    >>> print(info.normalized_name)  # "VDD"
"""

import re
from typing import ClassVar

from ink.domain.value_objects.net import NetInfo, NetType


class NetNormalizer:
    """Normalize and classify net names from CDL netlists.

    This class performs two main functions:
    1. **Normalization**: Converts net names to a standard format
       - Bus notation <N> → [N] (e.g., "data<7>" → "data[7]")
       - Strips trailing special characters (!, ?)
    2. **Classification**: Identifies net type (SIGNAL, POWER, GROUND)
       based on pattern matching against known power/ground net names.

    Results are cached for performance - repeated calls with the same net name
    return the same NetInfo object without reprocessing.

    Attributes:
        POWER_PATTERNS: Regex patterns matching power supply net names.
        GROUND_PATTERNS: Regex patterns matching ground reference net names.
        BUS_PATTERN: Compiled regex for detecting bus notation.

    Example:
        >>> normalizer = NetNormalizer()
        >>> info = normalizer.normalize("VDDA!")
        >>> info.net_type == NetType.POWER
        True
        >>> info.normalized_name
        'VDDA'
    """

    # Known power net patterns - case insensitive matching
    # These patterns match common power supply naming conventions:
    # - VDD: Core digital power (with optional suffix letters like A, IO, CORE)
    # - VCC: Alternative power naming (legacy from bipolar/TTL)
    # - VPWR: Another common power naming style
    POWER_PATTERNS: ClassVar[set[str]] = {
        r"^VDD[A-Z]*$",  # VDD, VDDA, VDDIO, VDDCORE, etc.
        r"^VCC[A-Z]*$",  # VCC, VCCA, VCCIO, etc.
        r"^VPWR$",  # VPWR (common in some PDKs)
    }

    # Known ground net patterns - case insensitive matching
    # These patterns match common ground reference naming conventions:
    # - VSS: Core digital ground (with optional suffix letters)
    # - GND: Generic ground naming
    # - VGND: Another ground naming style
    GROUND_PATTERNS: ClassVar[set[str]] = {
        r"^VSS[A-Z]*$",  # VSS, VSSA, VSSIO, VSSCORE, etc.
        r"^GND[A-Z]*$",  # GND, GNDA, GNDIO, etc.
        r"^VGND$",  # VGND (common in some PDKs)
    }

    # Bus notation pattern: matches net<N> or net<M:N> formats
    # Group 1: Base net name (e.g., "data" in "data<7>")
    # Group 2: Bit index or start of range (e.g., "7" in "data<7>")
    # Group 3: Optional end of range (e.g., "0" in "data<7:0>")
    # Note: Currently only single-bit bus notation is fully supported
    BUS_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^(.+)<(\d+)(?::(\d+))?>$")

    def __init__(self) -> None:
        """Initialize the NetNormalizer with an empty cache.

        The cache stores NetInfo objects keyed by original net name to avoid
        repeated processing of the same net names.
        """
        # Cache for normalized net info - maps original name to NetInfo
        # This significantly improves performance for large netlists where
        # the same net names appear many times (e.g., VDD, VSS on every cell)
        self._net_cache: dict[str, NetInfo] = {}

    def normalize(self, net_name: str) -> NetInfo:
        """Normalize a net name and return classification information.

        This is the main entry point for net normalization. It handles:
        1. Cache lookup for previously processed nets
        2. Delegation to _do_normalize for actual processing
        3. Cache storage for new results

        Args:
            net_name: Raw net name from CDL file.
                Examples: "data<7>", "VDD!", "clk", "addr_15"

        Returns:
            NetInfo value object containing:
            - original_name: The input net_name unchanged
            - normalized_name: Standardized form (bus notation converted,
              trailing special chars stripped)
            - net_type: Classification as SIGNAL, POWER, or GROUND
            - is_bus: True if this is a bus bit
            - bus_index: Bit index if is_bus, None otherwise

        Example:
            >>> normalizer = NetNormalizer()
            >>> info = normalizer.normalize("data<7>")
            >>> print(f"{info.normalized_name}, bus={info.is_bus}, idx={info.bus_index}")
            data[7], bus=True, idx=7
        """
        # Check cache first for performance
        if net_name in self._net_cache:
            return self._net_cache[net_name]

        # Perform normalization and cache the result
        info = self._do_normalize(net_name)
        self._net_cache[net_name] = info
        return info

    def _do_normalize(self, net_name: str) -> NetInfo:
        """Perform the actual normalization logic.

        This method implements the core normalization algorithm:
        1. Strip trailing special characters (!, ?)
        2. Check for bus notation and convert <N> to [N]
        3. Classify as POWER, GROUND, or SIGNAL

        Args:
            net_name: Raw net name to normalize.

        Returns:
            NetInfo with all fields populated.

        Note:
            This is an internal method called by normalize().
            Always use normalize() for the caching benefit.
        """
        # Step 1: Strip trailing special characters (!, ?)
        # These are often used in CDL to mark nets but don't affect identity
        # Examples: "VDD!" -> "VDD", "net1?" -> "net1", "VDD!?" -> "VDD"
        cleaned = net_name.rstrip("!?")

        # Step 2: Check for and process bus notation
        # Bus notation uses angle brackets: data<7>, addr<15:0>
        # We convert to square brackets for consistency: data[7]
        bus_match = self.BUS_PATTERN.match(cleaned)
        if bus_match:
            # Extract bus components from regex groups
            base_name = bus_match.group(1)  # "data" from "data<7>"
            bit_index = int(bus_match.group(2))  # 7 from "data<7>"
            # Note: bus_match.group(3) would be range end (e.g., 0 from <7:0>)
            # Currently not used - we only support single-bit notation

            # Convert angle brackets to square brackets for normalized form
            normalized = f"{base_name}[{bit_index}]"

            # Classify the base name (without bus index) for type detection
            net_type = self._classify_type(base_name)

            return NetInfo(
                original_name=net_name,
                normalized_name=normalized,
                net_type=net_type,
                is_bus=True,
                bus_index=bit_index,
            )

        # Step 3: For non-bus nets, classify and return
        net_type = self._classify_type(cleaned)

        return NetInfo(
            original_name=net_name,
            normalized_name=cleaned,
            net_type=net_type,
            is_bus=False,
            bus_index=None,
        )

    def _classify_type(self, net_name: str) -> NetType:
        """Classify a net name as POWER, GROUND, or SIGNAL.

        Uses regex pattern matching against known power and ground net patterns.
        Matching is case-insensitive to handle variations like VDD, Vdd, vdd.

        Args:
            net_name: Net name to classify (should be already cleaned of
                trailing special characters).

        Returns:
            NetType.POWER if matches power patterns (VDD, VCC, VPWR, etc.)
            NetType.GROUND if matches ground patterns (VSS, GND, VGND, etc.)
            NetType.SIGNAL otherwise (default for all other nets)

        Example:
            >>> normalizer = NetNormalizer()
            >>> normalizer._classify_type("VDD")
            <NetType.POWER: 'power'>
            >>> normalizer._classify_type("clk")
            <NetType.SIGNAL: 'signal'>
        """
        # Check against all power patterns (case-insensitive)
        for pattern in self.POWER_PATTERNS:
            if re.match(pattern, net_name, re.IGNORECASE):
                return NetType.POWER

        # Check against all ground patterns (case-insensitive)
        for pattern in self.GROUND_PATTERNS:
            if re.match(pattern, net_name, re.IGNORECASE):
                return NetType.GROUND

        # Default: regular signal net
        return NetType.SIGNAL

    def is_power_or_ground(self, net_name: str) -> bool:
        """Quick check if a net is a power or ground net.

        This is a convenience method for common use cases where you just need
        to know if a net should be filtered or treated specially, without
        needing the full NetInfo object.

        Args:
            net_name: Net name to check.

        Returns:
            True if the net is classified as POWER or GROUND.
            False if the net is a regular SIGNAL.

        Example:
            >>> normalizer = NetNormalizer()
            >>> normalizer.is_power_or_ground("VDD")
            True
            >>> normalizer.is_power_or_ground("clk")
            False
        """
        info = self.normalize(net_name)
        return info.net_type in (NetType.POWER, NetType.GROUND)
