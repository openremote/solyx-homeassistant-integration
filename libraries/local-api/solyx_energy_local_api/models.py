"""Typed responses of the local API of the Solyx Energy Sensorbox."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Self

from .exceptions import SolyxEnergyDataError


class ControlSource(StrEnum):
    """Who may change the operating mode of the Nymo."""

    CLOUD = "CLOUD"
    LOCAL = "LOCAL"


class OperationMode(StrEnum):
    """Operating mode a local client can set; DIRECT takes a power percentage."""

    NORMAL = "NORMAL"
    MUTED = "MUTED"
    DIRECT = "DIRECT"


def _section(data: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Return a nested object, or None when the Sensorbox has not read it from the Nymo yet."""
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise SolyxEnergyDataError(f"Invalid status from the Sensorbox: {key} is not an object")
    return value


def _number[T: (int, float)](data: dict[str, Any], key: str, kind: type[T]) -> T | None:
    """Return a number, or None when it is unknown; booleans and other types are invalid."""
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise SolyxEnergyDataError(f"Invalid status from the Sensorbox: {key} is not a number")
    return kind(value)


def _required_number[T: (int, float)](data: dict[str, Any], key: str, kind: type[T]) -> T:
    value = _number(data, key, kind)
    if value is None:
        raise SolyxEnergyDataError(f"Invalid status from the Sensorbox: {key} is missing")
    return value


def _string(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SolyxEnergyDataError(f"Invalid response from the Sensorbox: {key} is not a string")
    return value


def _numbers(data: dict[str, Any], key: str) -> tuple[int, ...]:
    values = data.get(key)
    if not isinstance(values, list) or any(
        isinstance(value, bool) or not isinstance(value, int) for value in values
    ):
        raise SolyxEnergyDataError(f"Invalid status from the Sensorbox: {key} is not a list of numbers")
    return tuple(values)


@dataclass(frozen=True, kw_only=True)
class LocalInfo:
    """Identity and firmware versions of the Sensorbox and its Nymo."""

    device_id: str
    model: str | None
    esp_firmware_version: str | None
    firmware_version: str | None
    sensorbox_firmware_version: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Parse the /info response."""
        device_id = _string(data, "deviceId")
        if not device_id:
            raise SolyxEnergyDataError("Invalid response from the Sensorbox: deviceId is missing")
        return cls(
            device_id=device_id,
            model=_string(data, "model"),
            esp_firmware_version=_string(data, "espFirmwareVersion"),
            firmware_version=_string(data, "firmwareVersion"),
            sensorbox_firmware_version=_string(data, "sensorBoxFirmwareVersion"),
        )


@dataclass(frozen=True, kw_only=True)
class Command:
    """The operating mode last set locally since the Sensorbox started."""

    operation_mode: OperationMode | None
    power_percent: int | None


@dataclass(frozen=True, kw_only=True)
class Boiler:
    """Electrical values of the boiler."""

    power: int  # W
    voltage: int  # V
    current: float  # A


@dataclass(frozen=True, kw_only=True)
class Grid:
    """Values of the grid connection; power is negative when exporting."""

    power: int  # W
    line_voltages: tuple[int, ...]  # V
    line_currents: tuple[int, ...]  # A


@dataclass(frozen=True, kw_only=True)
class Temperatures:
    """Temperatures inside the Nymo in °C."""

    heat_sink: int
    main_pcb: int
    front_pcb: int


@dataclass(frozen=True, kw_only=True)
class NymoStatus:
    """The latest measurements of the Nymo; None until the Sensorbox has read them."""

    connected: bool | None
    mode: str | None
    control_value: int | None  # %
    boiler: Boiler | None
    grid: Grid | None
    temperatures: Temperatures | None
    radio_signal: float | None  # dBm
    age: int | None  # seconds since the values were read


@dataclass(frozen=True, kw_only=True)
class Savings:
    """Energy saved in Wh."""

    today: int
    yesterday: int
    this_week: int
    last_week: int
    this_month: int
    last_month: int
    this_year: int
    last_year: int
    total: int
    age: int | None  # seconds since the values were read


@dataclass(frozen=True, kw_only=True)
class Legionella:
    """Legionella prevention: the boiler is heated to its maximum temperature every interval."""

    enabled: bool
    interval_days: int
    days_since_max_temperature: int


@dataclass(frozen=True, kw_only=True)
class Settings:
    """Settings of the Nymo."""

    threshold1: int  # W
    threshold2: int  # W
    power_limit: int  # W
    boost_minutes: int
    legionella: Legionella
    age: int | None  # seconds since the values were read


@dataclass(frozen=True, kw_only=True)
class LocalStatus:
    """Everything the local API reports about the Nymo."""

    control_source: ControlSource
    command: Command
    nymo: NymoStatus
    savings: Savings | None
    settings: Settings | None
    wifi_signal: int | None  # dBm, of the Sensorbox

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Parse the /status response."""
        try:
            control_source = ControlSource(str(data.get("controlSource")))
        except ValueError:
            raise SolyxEnergyDataError("Invalid status from the Sensorbox: unknown controlSource") from None
        return cls(
            control_source=control_source,
            command=_command(_section(data, "command") or {}),
            nymo=_nymo(_section(data, "nymo") or {}),
            savings=_savings(_section(data, "savings")),
            settings=_settings(_section(data, "settings")),
            wifi_signal=_number(_section(data, "sensorbox") or {}, "wifiSignal", int),
        )


def _command(data: dict[str, Any]) -> Command:
    mode = data.get("operationMode")
    try:
        operation_mode = OperationMode(mode) if mode is not None else None
    except ValueError:
        raise SolyxEnergyDataError("Invalid status from the Sensorbox: unknown operationMode") from None
    return Command(operation_mode=operation_mode, power_percent=_number(data, "powerPercent", int))


def _nymo(data: dict[str, Any]) -> NymoStatus:
    connected = data.get("connected")
    if connected is not None and not isinstance(connected, bool):
        raise SolyxEnergyDataError("Invalid status from the Sensorbox: connected is not a boolean")
    boiler = _section(data, "boiler")
    grid = _section(data, "grid")
    temperatures = _section(data, "temperatures")
    return NymoStatus(
        connected=connected,
        mode=_string(data, "mode"),
        control_value=_number(data, "controlValue", int),
        boiler=None if boiler is None else Boiler(
            power=_required_number(boiler, "power", int),
            voltage=_required_number(boiler, "voltage", int),
            current=_required_number(boiler, "current", float),
        ),
        grid=None if grid is None else Grid(
            power=_required_number(grid, "power", int),
            line_voltages=_numbers(grid, "lineVoltages"),
            line_currents=_numbers(grid, "lineCurrents"),
        ),
        temperatures=None if temperatures is None else Temperatures(
            heat_sink=_required_number(temperatures, "heatSink", int),
            main_pcb=_required_number(temperatures, "mainPcb", int),
            front_pcb=_required_number(temperatures, "frontPcb", int),
        ),
        radio_signal=_number(data, "radioSignal", float),
        age=_number(data, "age", int),
    )


def _savings(data: dict[str, Any] | None) -> Savings | None:
    if data is None:
        return None
    return Savings(
        today=_required_number(data, "today", int),
        yesterday=_required_number(data, "yesterday", int),
        this_week=_required_number(data, "thisWeek", int),
        last_week=_required_number(data, "lastWeek", int),
        this_month=_required_number(data, "thisMonth", int),
        last_month=_required_number(data, "lastMonth", int),
        this_year=_required_number(data, "thisYear", int),
        last_year=_required_number(data, "lastYear", int),
        total=_required_number(data, "total", int),
        age=_number(data, "age", int),
    )


def _settings(data: dict[str, Any] | None) -> Settings | None:
    if data is None:
        return None
    legionella = _section(data, "legionella")
    if legionella is None or not isinstance(legionella.get("enabled"), bool):
        raise SolyxEnergyDataError("Invalid status from the Sensorbox: legionella is missing")
    return Settings(
        threshold1=_required_number(data, "threshold1", int),
        threshold2=_required_number(data, "threshold2", int),
        power_limit=_required_number(data, "powerLimit", int),
        boost_minutes=_required_number(data, "boostMinutes", int),
        legionella=Legionella(
            enabled=legionella["enabled"],
            interval_days=_required_number(legionella, "intervalDays", int),
            days_since_max_temperature=_required_number(legionella, "daysSinceMaxTemperature", int),
        ),
        age=_number(data, "age", int),
    )
