"""Centralized entity descriptions for all Solyx Energy Nymo entity platforms."""

from __future__ import annotations

from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)

from .const import (
    ATTRIBUTE_CONTROL_VALUE,
    ATTRIBUTE_ENERGY_BOILER,
    ATTRIBUTE_GRID_POWER,
    ATTRIBUTE_OPERATING_MODE,
    ATTRIBUTE_POWER_BOILER,
)

SENSOR_DESCRIPTIONS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=ATTRIBUTE_POWER_BOILER,
        translation_key=ATTRIBUTE_POWER_BOILER,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        native_unit_of_measurement="W",
    ),
    SensorEntityDescription(
        key=ATTRIBUTE_ENERGY_BOILER,
        translation_key=ATTRIBUTE_ENERGY_BOILER,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        native_unit_of_measurement="Wh",
    ),
    SensorEntityDescription(
        key=ATTRIBUTE_GRID_POWER,
        translation_key=ATTRIBUTE_GRID_POWER,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        native_unit_of_measurement="W",
    ),
)

SELECT_DESCRIPTIONS: tuple[SelectEntityDescription, ...] = (
    SelectEntityDescription(
        key=ATTRIBUTE_OPERATING_MODE,
        translation_key=ATTRIBUTE_OPERATING_MODE,
        options=["DIRECT", "MUTED"],
    ),
)

NUMBER_DESCRIPTIONS: tuple[NumberEntityDescription, ...] = (
    NumberEntityDescription(
        key=ATTRIBUTE_CONTROL_VALUE,
        translation_key=ATTRIBUTE_CONTROL_VALUE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
    ),
)
