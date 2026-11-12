import logging

from homeassistant.components.number import NumberEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import AquaTempConfigEntry
from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.entity_descriptions import AquaTempNumberEntityDescription
from .common.utils import (
    TEMPERATURE_DEVICE_CLASSES,
    convert_range,
    round_to_step,
    safe_float,
)
from .managers.aqua_temp_coordinator import AquaTempCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: AquaTempConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.NUMBER,
        AquaTempNumberEntity,
        async_add_entities,
    )


class AquaTempNumberEntity(BaseEntity, NumberEntity):
    """Representation of a number entity for writable device parameters."""

    entity_description: AquaTempNumberEntityDescription

    def __init__(
        self,
        entity_description: AquaTempNumberEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)

        self._attr_native_step = entity_description.native_step
        self._attr_device_class = entity_description.device_class

        self._update_unit()

    def _update_unit(self) -> None:
        """Express the unit and range in the unit the device reports in."""
        description = self.entity_description
        unit = description.native_unit_of_measurement
        minimum = description.native_min_value
        maximum = description.native_max_value

        if description.device_class in TEMPERATURE_DEVICE_CLASSES:
            device_unit = self.local_coordinator.get_temperature_unit(self.device_code)

            minimum, maximum = convert_range(
                minimum, maximum, description.device_class, unit, device_unit
            )
            unit = device_unit

        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum

    async def async_set_native_value(self, value: float) -> None:
        """Set new value for this parameter on the device."""
        minimum = self.native_min_value
        maximum = self.native_max_value

        value = round_to_step(value, self.native_step, minimum)
        value = float(min(max(value, minimum), maximum))

        if self.entity_description.send_as_integer:
            value = str(round(value))

        await self.local_coordinator.set_protocol_code_value(
            self.device_code, self.entity_description.key, value
        )

    def _update_attributes(self) -> None:
        self._update_unit()

        state = self._get_raw_value()

        if isinstance(state, str):
            state = safe_float(state)

        self._has_value = state is not None
        self._attr_native_value = state
