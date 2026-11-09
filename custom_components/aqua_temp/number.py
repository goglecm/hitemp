import logging

from homeassistant.components.number import NumberEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import AquaTempConfigEntry
from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.entity_descriptions import AquaTempNumberEntityDescription
from .common.utils import safe_float
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

    def __init__(
        self,
        entity_description: AquaTempNumberEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)

        self._attr_native_min_value = entity_description.native_min_value
        self._attr_native_max_value = entity_description.native_max_value
        self._attr_native_step = entity_description.native_step
        self._attr_native_unit_of_measurement = (
            entity_description.native_unit_of_measurement
        )
        self._attr_device_class = entity_description.device_class

    async def async_set_native_value(self, value: float) -> None:
        """Set new value for this parameter on the device."""
        await self.local_coordinator.set_protocol_code_value(
            self.device_code, self.entity_description.key, value
        )

    def _update_attributes(self) -> None:
        device_data = self.local_coordinator.get_device_data(self.device_code)

        state = device_data.get(self.entity_description.key)

        if isinstance(state, str):
            state = safe_float(state)

        self._attr_native_value = state
