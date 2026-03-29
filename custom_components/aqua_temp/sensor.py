import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.consts import LAST_ERROR
from .common.entity_descriptions import AquaTempSensorEntityDescription
from .common.utils import safe_float
from .managers.aqua_temp_coordinator import AquaTempCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
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

        if entity_description.device_class == SensorDeviceClass.TEMPERATURE:
            self._attr_native_unit_of_measurement = coordinator.get_temperature_unit(
                device_code
            )

    def _handle_coordinator_update(self) -> None:
        """Fetch new state parameters for the sensor."""
        try:
            if self.entity_description.key == LAST_ERROR:
                self._attr_native_value = self.local_coordinator.last_error
            else:
                device_data = self.local_coordinator.get_device_data(self.device_code)

                state = device_data.get(self.entity_description.key)

                if isinstance(state, str):
                    state = safe_float(state)

                self._attr_native_value = state
        except Exception as ex:
            _LOGGER.error(f"Failed to update {self.entity_description.key}: {ex}")

        self.async_write_ha_state()
