"""
LOCAL DEVELOPMENT HELPER — DO NOT COPY this file to the home-assistant/core fork.
HA Core has its own ``tests/conftest.py`` with proper fixtures.
"""
from pathlib import Path

import homeassistant.components

_local = str(Path(__file__).resolve().parent.parent / "homeassistant" / "components")
if _local not in homeassistant.components.__path__:
    homeassistant.components.__path__.insert(0, _local)
