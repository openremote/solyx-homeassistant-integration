"""Utility file with several parsing functions for the Solyx Energy Nymo integration."""
from typing import Any
import logging

_LOGGER = logging.getLogger(__name__)

def parse_attr_value(raw: dict, attr_name: str) -> Any:
    """Extract value from an Solyx device attribute."""
    val = raw.get("attributes", {}).get(attr_name, {}).get("value")
    _LOGGER.debug("Extracting %s.. New value: %s", attr_name, val)
    return val

def parse_float(raw: dict, attr_name: str) -> float | None:
    """Parse a float value from an Solyx device attribute."""
    val = parse_attr_value(raw, attr_name)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
