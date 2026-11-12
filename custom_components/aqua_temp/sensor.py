from datetime import date
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import MAX_LENGTH_STATE_STATE as MAX_STATE_LENGTH, Platform
from homeassistant.core import HomeAssistant

from . import AquaTempConfigEntry
from .common.base_entity import BaseEntity, async_setup_base_entry
from .common.consts import CLOUD_STATUS, CODE_CHANGES, DEVICE_FAULT, NO_CODE_CHANGES
from .common.entity_descriptions import AquaTempSensorEntityDescription
from .common.utils import (
    TEMPERATURE_DEVICE_CLASSES,
    describe_bitword,
    label_value,
    labelled_options,
    parse_bitword,
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
        Platform.SENSOR,
        AquaTempSensorEntity,
        async_add_entities,
    )


class AquaTempSensorEntity(BaseEntity, SensorEntity):
    """Representation of a sensor."""

    entity_description: AquaTempSensorEntityDescription

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

        if entity_description.value_labels is not None:
            self._attr_options = labelled_options(entity_description.value_labels)

        if entity_description.device_class in TEMPERATURE_DEVICE_CLASSES:
            self._attr_native_unit_of_measurement = coordinator.get_temperature_unit(
                device_code
            )

    def _update_attributes(self) -> None:
        description = self.entity_description

        if description.device_class in TEMPERATURE_DEVICE_CLASSES:
            self._attr_native_unit_of_measurement = (
                self.local_coordinator.get_temperature_unit(self.device_code)
            )

        if description.key == CLOUD_STATUS:
            state = self._get_cloud_status()
        elif description.key == DEVICE_FAULT:
            state = self._get_fault()
        elif description.key == CODE_CHANGES:
            state = self._get_code_changes()
        elif description.difference_of is not None:
            state = self._get_difference(*description.difference_of)
        elif description.time_of is not None:
            state = self._get_time(*description.time_of)
        elif description.date_of is not None:
            state = self._get_date(*description.date_of)
        elif description.value_labels is not None:
            state = self._get_label(description.value_labels)
        elif description.bitword:
            state = self._get_bitword()
        else:
            state = self._get_raw_value()

            if isinstance(state, str):
                state = safe_float(state)

        self._has_value = state is not None
        self._attr_native_value = state

    def _get_cloud_status(self) -> str:
        coordinator = self.local_coordinator

        self._attr_extra_state_attributes = {
            "message": coordinator.cloud_status_message,
            "since": coordinator.cloud_status_since.isoformat(),
        }

        return coordinator.cloud_status

    def _get_fault(self) -> str | None:
        state, fault_words = self.local_coordinator.get_fault_details(self.device_code)

        self._attr_extra_state_attributes = fault_words

        return state

    def _get_code_changes(self) -> str:
        """List the codes that changed at the last poll, with old and new values."""
        report = self.local_coordinator.get_code_changes(self.device_code)
        changes = report["changes"]

        self._attr_extra_state_attributes = {
            "time": report["time"],
            "changes": {
                code: f"{change['from']} -> {change['to']}"
                for code, change in changes.items()
            },
        }

        if not changes:
            return NO_CODE_CHANGES

        return ", ".join(changes)[:MAX_STATE_LENGTH]

    def _get_whole_numbers(self, *keys: str) -> list[int] | None:
        values = [safe_float(self._get_raw_value(key)) for key in keys]

        if any(value is None or not value.is_integer() for value in values):
            return None

        return [int(value) for value in values]

    def _get_time(self, hour_key: str, minute_key: str) -> str | None:
        values = self._get_whole_numbers(hour_key, minute_key)

        if values is None or not (0 <= values[0] <= 23 and 0 <= values[1] <= 59):
            return None

        return f"{values[0]:02}:{values[1]:02}"

    def _get_date(self, year_key: str, month_key: str, day_key: str) -> date | None:
        values = self._get_whole_numbers(year_key, month_key, day_key)

        if values is None:
            return None

        try:
            return date(2000 + values[0], values[1], values[2])
        except ValueError:
            return None

    def _get_bitword(self) -> str | None:
        word = parse_bitword(self._get_raw_value())

        if word is None:
            return None

        described = describe_bitword(word)
        self._attr_extra_state_attributes = {
            **self._attr_extra_state_attributes,
            "hex": described["hex"],
            "bits_set": described["bits_set"],
        }

        return described["bits"]

    def _get_difference(self, minuend_key: str, subtrahend_key: str) -> float | None:
        minuend = safe_float(self._get_raw_value(minuend_key))
        subtrahend = safe_float(self._get_raw_value(subtrahend_key))

        if minuend is None or subtrahend is None:
            return None

        return round(minuend - subtrahend, 2)

    def _get_label(self, labels: dict[str, str]) -> str | None:
        """Return the app's label of the value, keeping unlisted values as options."""
        raw_value = self._get_raw_value()
        state = label_value(raw_value, labels)
        options = labelled_options(labels)

        if state is not None and state not in options:
            options.append(state)

        self._attr_options = options
        self._set_raw_value_attribute(raw_value)

        return state
