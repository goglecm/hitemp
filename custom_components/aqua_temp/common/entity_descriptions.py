from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.climate import ClimateEntityDescription, HVACMode
from homeassistant.components.number import NumberEntityDescription
from homeassistant.components.select import SelectEntityDescription
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.const import EntityCategory, Platform, UnitOfTemperature
from homeassistant.helpers.entity import EntityDescription

from custom_components.aqua_temp.common.consts import (
    API_STATUS,
    DEVICE_IS_FAULT,
    DEVICE_STATUS,
    LAST_ERROR,
    POWER_MODE_ON,
)


@dataclass(frozen=True, kw_only=True)
class AquaTempEntityDescription(EntityDescription):
    platform: Platform | None = None
    is_protocol_code: bool = True
    # Diagnostic entities that must stay visible while the heat pump is offline
    available_when_offline: bool = False
    # Entities describing the connection itself, needed most when polling fails
    always_available: bool = False


@dataclass(frozen=True, kw_only=True)
class AquaTempClimateEntityDescription(
    ClimateEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.CLIMATE
    fan_modes: list[str] | None = None
    hvac_modes: list[HVACMode] | list[str] = None


@dataclass(frozen=True, kw_only=True)
class AquaTempBinarySensorEntityDescription(
    BinarySensorEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.BINARY_SENSOR
    on_value: str | bool | None = None
    attributes: list[str] | None = None


@dataclass(frozen=True, kw_only=True)
class AquaTempSensorEntityDescription(
    SensorEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.SENSOR


@dataclass(frozen=True, kw_only=True)
class AquaTempNumberEntityDescription(
    NumberEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.NUMBER


@dataclass(frozen=True, kw_only=True)
class AquaTempSelectEntityDescription(
    SelectEntityDescription, AquaTempEntityDescription
):
    platform: Platform | None = Platform.SELECT


DEFAULT_ENTITY_DESCRIPTIONS: list[AquaTempEntityDescription] = [
    AquaTempBinarySensorEntityDescription(
        key=API_STATUS,
        name="API Status",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_protocol_code=False,
        available_when_offline=True,
        always_available=True,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        on_value=True,
        translation_key=API_STATUS,
    ),
    AquaTempSelectEntityDescription(
        key="temperature_unit",
        name="Temperature Unit",
        options=[UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT],
        entity_category=EntityCategory.CONFIG,
        is_protocol_code=False,
        available_when_offline=True,
        translation_key="temperature_unit",
    ),
    AquaTempBinarySensorEntityDescription(
        key=DEVICE_IS_FAULT,
        name="Fault",
        on_value=POWER_MODE_ON,
        is_protocol_code=False,
        available_when_offline=True,
        device_class=BinarySensorDeviceClass.PROBLEM,
        attributes=["fault"],
        translation_key="is_fault",
    ),
    AquaTempBinarySensorEntityDescription(
        key=DEVICE_STATUS,
        name="Status",
        on_value="ONLINE",
        is_protocol_code=False,
        available_when_offline=True,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        translation_key="device_status",
    ),
    AquaTempClimateEntityDescription(key="Mode", name=None, translation_key="mode"),
    AquaTempSensorEntityDescription(
        key=LAST_ERROR,
        name="Last Error",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_protocol_code=False,
        available_when_offline=True,
        always_available=True,
        translation_key=LAST_ERROR,
    ),
]
