"""LOCAL DEVELOPMENT HELPER - DO NOT COPY this file to the home-assistant/core fork.

HA Core ships its own ``tests/conftest.py``. This file only exists to enable
custom integration loading via ``pytest-homeassistant-custom-component``.
"""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integration loading for all tests."""
