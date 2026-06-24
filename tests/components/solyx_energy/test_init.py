"""Tests for the Solyx Energy integration setup."""
from unittest.mock import MagicMock

import pytest
from homeassistant.components.solyx_energy import DOMAIN, async_setup

@pytest.mark.asyncio
async def test_setup_returns_true():
    """It should return True on success."""
    hass = MagicMock()
    result = await setup(hass, {})
    assert result is True

@pytest.mark.asyncio
async def test_setup_creates_hello_world_state():
    """It should set the solyx_energy.Hello_World state."""
    hass = MagicMock()
    await setup(hass, {})
    hass.states.set.assert_called_once_with(
        f"{DOMAIN}.Hello_World", "Works!"
    )

def test_domain_constant():
    """It should export the correct DOMAIN constant."""
    assert DOMAIN == "solyx_energy"
