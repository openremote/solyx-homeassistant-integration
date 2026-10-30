"""Coordinator that polls the local API of the Sensorbox."""

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, override

from solyx_energy_local_api.exceptions import (
    SolyxEnergyAuthError,
    SolyxEnergyCertificateError,
    SolyxEnergyDataError,
    SolyxEnergyLocalControlDisabledError,
    SolyxEnergyWriteError,
)
from solyx_energy_local_api.models import OperationMode

from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DATA_INTERVAL_SECONDS, DEFAULT_DIRECT_PERCENT, DOMAIN

if TYPE_CHECKING:
    from solyx_energy_local_api.client import SolyxEnergyLocalApiClient
    from solyx_energy_local_api.models import LocalStatus

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

type SolyxEnergyLocalConfigEntry = ConfigEntry[SolyxEnergyLocalCoordinator]


@dataclass(frozen=True)
class SolyxEnergyData:
    """Hold a snapshot of the values of a Nymo, the same as the Solyx Energy Cloud integration."""

    boiler_current: float | None
    boiler_power: float | None
    boiler_voltage: float | None
    days_since_maximum_temperature: float | None
    grid_power: float | None
    legionella_days: float | None
    saved_this_month: float | None
    saved_this_week: float | None
    saved_today: float | None


@dataclass(frozen=True)
class SolyxEnergyLocalData:
    """The values shared with the cloud integration, and the full status for control."""

    values: SolyxEnergyData
    status: LocalStatus


def _kilowatt_hours(watt_hours: int) -> float:
    """Convert Wh to whole kWh, rounded down like the Sensorbox reports them to the cloud."""
    return float(watt_hours // 1000)


def to_cloud_values(status: LocalStatus) -> SolyxEnergyData:
    """Map the local status to the values and units the Solyx Energy cloud reports."""
    boiler = status.nymo.boiler
    grid = status.nymo.grid
    savings = status.savings
    legionella = status.settings.legionella if status.settings else None
    return SolyxEnergyData(
        boiler_current=boiler.current if boiler else None,
        boiler_power=float(boiler.power) if boiler else None,
        boiler_voltage=float(boiler.voltage) if boiler else None,
        days_since_maximum_temperature=(
            float(legionella.days_since_max_temperature) if legionella else None
        ),
        grid_power=float(grid.power) if grid else None,
        legionella_days=float(legionella.interval_days) if legionella else None,
        saved_this_month=_kilowatt_hours(savings.this_month) if savings else None,
        saved_this_week=_kilowatt_hours(savings.this_week) if savings else None,
        saved_today=float(savings.today) if savings else None,
    )


class SolyxEnergyLocalCoordinator(DataUpdateCoordinator[SolyxEnergyLocalData]):
    """Coordinator that fetches the status of a Nymo from its Sensorbox."""

    config_entry: SolyxEnergyLocalConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api_client: SolyxEnergyLocalApiClient,
        config_entry: SolyxEnergyLocalConfigEntry,
    ) -> None:
        """Initialize the coordinator for a single Nymo."""
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=DATA_INTERVAL_SECONDS),
        )
        self.api_client = api_client
        # The config entry's unique ID is the device ID reported by the Sensorbox.
        self.device_id: str = config_entry.unique_id or ""
        # The power used for direct mode; kept so it can be set before switching to direct.
        self.direct_percent = DEFAULT_DIRECT_PERCENT
        # The mode last set here or reported by the Sensorbox. The Sensorbox only reports a mode
        # once the Nymo confirmed it, which can take a while.
        self.requested_mode: OperationMode | None = None

    @override
    async def _async_update_data(self) -> SolyxEnergyLocalData:
        """Fetch the status from the Sensorbox and map it to the entity values."""
        try:
            _LOGGER.debug("Retrieving the status from the Sensorbox")
            status = await self.api_client.async_get_status()
        except (SolyxEnergyAuthError, SolyxEnergyCertificateError) as err:
            raise ConfigEntryAuthFailed(f"Auth error: {err}") from err
        except SolyxEnergyDataError as err:
            raise UpdateFailed(f"API error: {err}") from err
        command = status.command
        if command.operation_mode is not None:
            self.requested_mode = command.operation_mode
        if command.operation_mode is OperationMode.DIRECT and command.power_percent is not None:
            self.direct_percent = command.power_percent
        return SolyxEnergyLocalData(values=to_cloud_values(status), status=status)

    async def async_set_operation_mode(self, mode: OperationMode, power_percent: int | None = None) -> None:
        """Set the operating mode of the Nymo; direct mode uses the given or the kept power."""
        if mode is OperationMode.DIRECT:
            power_percent = self.direct_percent if power_percent is None else power_percent
        try:
            await self.api_client.async_set_operation_mode(
                mode, power_percent if mode is OperationMode.DIRECT else None,
            )
        except SolyxEnergyLocalControlDisabledError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="local_control_disabled",
            ) from err
        except (SolyxEnergyAuthError, SolyxEnergyCertificateError) as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="authentication_failed",
            ) from err
        except (SolyxEnergyWriteError, SolyxEnergyDataError) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="set_operation_mode_failed",
            ) from err
        self.requested_mode = mode
        if power_percent is not None:
            self.direct_percent = power_percent
        # Show the new power level now; refreshes requested close together are delayed.
        self.async_update_listeners()
        # The Sensorbox reports the mode once the Nymo confirmed it, which can take a while.
        await self.async_request_refresh()
