from dataclasses import dataclass

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

@dataclass
class SolyxEnergyData:
    """Snapshot of all Solyx Energy integration values """

class SolyxEnergyCoordinator(DataUpdateCoordinator[SolyxEnergyData]):
    """Coordinator that fetches and sends data over HTTPS"""