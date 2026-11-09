import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import AquaTempConfigEntry
from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.consts import LAST_ERROR
from .common.entity_descriptions import AquaTempSensorEntityDescription
from .common.utils import TEMPERATURE_DEVICE_CLASSES, safe_float
from .managers.aqua_temp_coordinator import AquaTempCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: AquaTempConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.SENSOR,
        AquaTempSensorEntity,
        async_add_entities,
    )


class AquaTempSensorEntity(BaseEntity, SensorEntity):
    """Representation of a sensor."""

    def __init__(
        self,
        entity_description: AquaTempSensorEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)

        self._attr_device_class = entity_description.device_class
        self._attr_native_unit_of_measurement = (
            entity_description.native_unit_of_measurement
        )

        if entity_description.device_class in TEMPERATURE_DEVICE_CLASSES:
            self._attr_native_unit_of_measurement = coordinator.get_temperature_unit(
                device_code
            )

    def _update_attributes(self) -> None:
        if self.entity_description.key == LAST_ERROR:
            self._attr_native_value = self.local_coordinator.last_error
        else:
            device_data = self.local_coordinator.get_device_data(self.device_code)

            state = device_data.get(self.entity_description.key)

            if isinstance(state, str):
                state = safe_float(state)

            self._attr_native_value = state
