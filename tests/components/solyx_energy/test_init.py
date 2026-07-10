"""Tests for the Solyx Energy integration setup."""
from homeassistant.components.solyx_energy import DOMAIN

def test_domain_constant():
    """It should export the correct DOMAIN constant."""
    assert DOMAIN == "solyx_energy"
