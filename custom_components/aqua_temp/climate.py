"""Platform for climate integration."""

import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    FAN_AUTO,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, Platform, UnitOfTemperature
from homeassistant.core import HomeAssistant

from . import AquaTempConfigEntry
from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.entity_descriptions import AquaTempClimateEntityDescription
from .common.utils import DEVICE_CLASS_TEMPERATURE, convert_temperature, round_to_step
from .managers.aqua_temp_coordinator import AquaTempCoordinator

_LOGGER = logging.getLogger(__name__)

# Only used until the device or its parameter files provide limits
FALLBACK_MIN_TEMP_CELSIUS = 5.0
FALLBACK_MAX_TEMP_CELSIUS = 90.0


async def async_setup_entry(
    hass: HomeAssistant, entry: AquaTempConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.CLIMATE,
        AquaTempClimateEntity,
        async_add_entities,
    )


class AquaTempClimateEntity(BaseEntity, ClimateEntity):
    """Representation of a climate entity."""

    def __init__(
        self,
        entity_description: AquaTempClimateEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        """Initialize the climate entity."""
        super().__init__(entity_description, coordinator, device_code)

        self._attr_supported_features = (
            ClimateEntityFeature.TURN_OFF
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
        )
        self._attr_fan_modes = list(coordinator.get_fan_modes(device_code))
        self._attr_hvac_modes = list(coordinator.get_hvac_modes(device_code))

        self._attr_hvac_mode = HVACMode.OFF
        self._attr_fan_mode = FAN_AUTO

        temperature_unit = coordinator.get_temperature_unit(device_code)

        self._attr_native_temperature_unit = temperature_unit
        self._attr_min_temp = convert_temperature(
            FALLBACK_MIN_TEMP_CELSIUS,
            DEVICE_CLASS_TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            temperature_unit,
        )
        self._attr_max_temp = convert_temperature(
            FALLBACK_MAX_TEMP_CELSIUS,
            DEVICE_CLASS_TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            temperature_unit,
        )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature, and the HVAC mode if one is given."""
        if (hvac_mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            await self.async_set_hvac_mode(hvac_mode)

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return

        temperature = round_to_step(temperature, self.target_temperature_step)

        _LOGGER.debug(f"Set target temperature to: {temperature}")

        await self.local_coordinator.set_temperature(self.device_code, temperature)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        _LOGGER.debug(f"Set HVAC Mode to: {hvac_mode}")

        await self.local_coordinator.set_hvac_mode(self.device_code, hvac_mode)

    async def async_turn_on(self) -> None:
        """Power on, resuming the mode the device was last running in."""
        await self.local_coordinator.turn_on(self.device_code)

    async def async_turn_off(self) -> None:
        """Power off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        _LOGGER.debug(f"Set Fan Mode to: {fan_mode}")

        await self.local_coordinator.set_fan_mode(self.device_code, fan_mode)

    def _update_attributes(self) -> None:
        coordinator = self.local_coordinator
        device_code = self.device_code

        hvac_mode = coordinator.get_device_hvac_mode(device_code)
        is_power_on = coordinator.get_device_power(device_code)
        fan_mode = coordinator.get_device_fan_mode(device_code)
        current_temperature = coordinator.get_device_current_temperature(device_code)
        target_temperature = coordinator.get_device_target_temperature(device_code)
        minimum_temperature, maximum_temperature, step = (
            coordinator.get_target_temperature_limits(device_code)
        )

        if not is_power_on:
            hvac_mode = HVACMode.OFF

        self._attr_native_temperature_unit = coordinator.get_temperature_unit(
            device_code
        )
        if minimum_temperature is not None:
            self._attr_min_temp = minimum_temperature
        if maximum_temperature is not None:
            self._attr_max_temp = maximum_temperature
        self._attr_target_temperature_step = step
        self._attr_hvac_mode = hvac_mode
        self._attr_fan_mode = fan_mode
        self._attr_native_target_temperature = target_temperature
        self._attr_native_current_temperature = current_temperature

        _LOGGER.debug(
            f"{device_code}: hvac_mode={hvac_mode}, "
            f"target_temperature={target_temperature}, fan_mode={fan_mode}, "
            f"min_temp={self._attr_min_temp}, max_temp={self._attr_max_temp}"
        )
