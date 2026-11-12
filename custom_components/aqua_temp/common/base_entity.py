from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from ..managers.aqua_temp_config_manager import PARAMETER_INFO_ATTRIBUTES
from ..managers.aqua_temp_coordinator import AquaTempCoordinator
from .consts import ADD_COMPONENT_SIGNALS, DOMAIN
from .entity_descriptions import AquaTempEntityDescription

if TYPE_CHECKING:
    from .. import AquaTempConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_base_entry(
    hass: HomeAssistant,
    entry: AquaTempConfigEntry,
    platform: Platform,
    entity_type: type,
    async_add_entities,
):
    coordinator = entry.runtime_data

    @callback
    def _async_handle_device(entry_id: str, device_code: str):
        if entry.entry_id != entry_id:
            return

        try:
            config_manager = coordinator.config_manager

            entity_descriptions = config_manager.get_entity_descriptions(device_code)

            entities = [
                entity_type(entity_description, coordinator, device_code)
                for entity_description in entity_descriptions
                if entity_description.platform == platform
            ]

            _LOGGER.debug(f"Setting up {platform} entities: {entities}")

            async_add_entities(entities)

        except Exception as ex:
            exc_type, exc_obj, tb = sys.exc_info()
            line_number = tb.tb_lineno

            _LOGGER.error(
                f"Failed to initialize {platform}, Error: {ex}, Line: {line_number}"
            )

    for add_component_signal in ADD_COMPONENT_SIGNALS:
        entry.async_on_unload(
            async_dispatcher_connect(hass, add_component_signal, _async_handle_device)
        )

    for device_code in coordinator.device_codes:
        _async_handle_device(entry.entry_id, device_code)


class BaseEntity(CoordinatorEntity):
    _device_code: str
    _entity_description: AquaTempEntityDescription
    _translations: dict

    # The explanation of a parameter never changes, so it is not recorded
    _unrecorded_attributes = frozenset(
        {"code", "calculated_from", *PARAMETER_INFO_ATTRIBUTES.values()}
    )

    def __init__(
        self,
        entity_description: AquaTempEntityDescription,
        coordinator: AquaTempCoordinator,
        device_code: str,
    ):
        super().__init__(coordinator)

        self._entity_description = entity_description
        self.entity_description = entity_description

        device_info = coordinator.get_device(device_code)

        entity_name = coordinator.config_manager.get_entity_name(
            entity_description, device_info
        )

        unique_id_parts = [
            DOMAIN,
            entity_description.platform,
            entity_description.key,
            device_code,
        ]

        unique_id = slugify("_".join(unique_id_parts))

        self._attr_device_info = device_info
        self._attr_name = entity_name
        self._attr_unique_id = unique_id
        self._attr_extra_state_attributes = dict(
            entity_description.parameter_info or {}
        )

        self._data = {}
        self._device_code = device_code
        self._has_value = False

    @property
    def device_code(self):
        return self._device_code

    @property
    def local_coordinator(self) -> AquaTempCoordinator:
        return self.coordinator

    @property
    def data(self) -> dict | None:
        return self._data

    @property
    def available(self) -> bool:
        """Device data is unavailable while the cloud reports the device offline."""
        if self._entity_description.always_available:
            return True

        if not super().available:
            return False

        if self._entity_description.requires_value and not self._has_value:
            return False

        if self._entity_description.available_when_offline:
            return True

        return self.local_coordinator.is_device_online(self.device_code)

    def _get_raw_value(self, key: str | None = None):
        """Return the value the cloud last reported for a protocol code."""
        device_data = self.local_coordinator.get_device_data(self.device_code)

        return device_data.get(key or self._entity_description.key)

    def _set_raw_value_attribute(self, value) -> None:
        """Show the raw cloud value next to a labelled state."""
        self._attr_extra_state_attributes = {
            **self._attr_extra_state_attributes,
            "raw_value": value,
        }

    async def async_added_to_hass(self) -> None:
        """Populate the state from the coordinator before it is first written."""
        await super().async_added_to_hass()

        self._safe_update_attributes()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Refresh the state from the coordinator."""
        self._safe_update_attributes()

        self.async_write_ha_state()

    def _safe_update_attributes(self) -> None:
        try:
            self._update_attributes()
        except Exception as ex:
            _LOGGER.error(f"Failed to update {self.entity_description.key}: {ex}")

    def _update_attributes(self) -> None:
        """Copy the coordinator's data into the entity attributes."""
