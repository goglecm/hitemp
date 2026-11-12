import logging

from homeassistant.components.select import SelectEntity
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from . import AquaTempConfigEntry
from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.entity_descriptions import AquaTempSelectEntityDescription
from .common.utils import format_option, raw_value_key
from .managers.aqua_temp_coordinator import AquaTempCoordinator

_LOGGER = logging.getLogger(__name__)


def _create_select(
    entity_description: AquaTempSelectEntityDescription,
    coordinator: AquaTempCoordinator,
    device_code: str,
) -> SelectEntity:
    if entity_description.value_labels is None:
        return AquaTempTemperatureUnitSelectEntity(
            entity_description, coordinator, device_code
        )

    return AquaTempParameterSelectEntity(entity_description, coordinator, device_code)


async def async_setup_entry(
    hass: HomeAssistant, entry: AquaTempConfigEntry, async_add_entities
):
    await async_setup_base_entry(
        hass,
        entry,
        Platform.SELECT,
        _create_select,
        async_add_entities,
    )


class AquaTempTemperatureUnitSelectEntity(BaseEntity, SelectEntity):
    """Select for the unit the device reports temperatures in."""

    def __init__(
        self,
        entity_description: AquaTempSelectEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)

        self._attr_current_option = self._get_temperature_unit()

    def _get_temperature_unit(self):
        coordinator = self.local_coordinator
        temperature_unit = coordinator.get_temperature_unit(self._device_code)

        return temperature_unit

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.local_coordinator.set_temperature_unit(self._device_code, option)

    def _update_attributes(self) -> None:
        self._attr_current_option = self._get_temperature_unit()


class AquaTempParameterSelectEntity(BaseEntity, SelectEntity):
    """Select for a device parameter with a fixed set of values."""

    entity_description: AquaTempSelectEntityDescription

    def __init__(
        self,
        entity_description: AquaTempSelectEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(entity_description, coordinator, device_code)

        self._raw_values = {
            format_option(raw, label): raw
            for raw, label in entity_description.value_labels.items()
        }

    async def async_select_option(self, option: str) -> None:
        """Send the raw value of the option to the device."""
        await self.local_coordinator.set_protocol_code_value(
            self.device_code, self.entity_description.key, self._raw_values[option]
        )

    def _update_attributes(self) -> None:
        raw_value = self._get_raw_value()
        raw = raw_value_key(raw_value)
        labels = self.entity_description.value_labels

        # A value the app does not list cannot be shown as one of the options
        option = None if raw not in labels else format_option(raw, labels[raw])

        self._has_value = option is not None
        self._attr_current_option = option
        self._set_raw_value_attribute(raw_value)
