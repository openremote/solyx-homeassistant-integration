"""Home Assistant utility functions for the Solyx Energy integration."""

import re


def camel_to_snake(name: str) -> str:
    """Convert a camelCase attribute name to a snake_case translation key."""
    return re.compile(r"(?<!^)(?=[A-Z])").sub("_", name).lower()
