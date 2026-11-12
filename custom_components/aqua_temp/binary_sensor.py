import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import AquaTempConfigEntry
from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.consts import API_STATUS
from .common.entity_descriptions import AquaTempBinarySensorEntityDescription
from .common.utils import normalize_state
from .managers.aqua_temp_coordinator import AquaTempCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: AquaTempConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.BINARY_SENSOR,
        AquaTempBinarySensorEntity,
        async_add_entities,
    )


class AquaTempBinarySensorEntity(BaseEntity, BinarySensorEntity):
    """Representation of a binary sensor."""

    def __init__(
        self,
        entity_description: AquaTempBinarySensorEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)

        self._attr_device_class = entity_description.device_class
        self._entity_attributes = entity_description.attributes
        self._entity_on_value = entity_description.on_value

    def _update_attributes(self) -> None:
        device_data = self.local_coordinator.get_device_data(self.device_code)

        if self.entity_description.key == API_STATUS:
            state = self.local_coordinator.api_status

        else:
            state = device_data.get(self.entity_description.key)

        if state is None:
            is_on = None
        else:
            is_on = normalize_state(state) == normalize_state(self._entity_on_value)

        attributes = dict(self.entity_description.parameter_info or {})
        if self._entity_attributes is not None:
            for attribute_key in self._entity_attributes:
                value = device_data.get(attribute_key)

                attributes[attribute_key] = value

        self._has_value = is_on is not None
        self._attr_is_on = is_on
        self._attr_extra_state_attributes = attributes
