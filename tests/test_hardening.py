"""Tests for branches the main flows do not reach."""

from __future__ import annotations

from collections.abc import Callable
from unittest.mock import patch

from homeassistant.const import CONF_USERNAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import SIGNAL_AQUA_TEMP_DEVICE_NEW
from custom_components.aqua_temp.common.utils import (
    DEVICE_CLASS_TEMPERATURE,
    convert_temperature,
    label_value,
    normalize_state,
    raw_value_key,
)
from custom_components.aqua_temp.models.config_data import ConfigData
from custom_components.aqua_temp.sensor import AquaTempSensorEntity

from .conftest import HITEMP_FIXTURE, entity_id, setup_entry
from .fake_cloud import FakeDevice


def test_value_helpers_cover_empty_and_plain_text() -> None:
    """Empty, non-numeric and unconverted values take the plain branches."""
    assert raw_value_key("warm") == "warm"
    assert label_value(None, {"1": "On"}) is None
    assert normalize_state(None) is None
    assert (
        convert_temperature(
            21.0, None, UnitOfTemperature.CELSIUS, UnitOfTemperature.FAHRENHEIT
        )
        == 21.0
    )
    assert (
        convert_temperature(
            21.0,
            DEVICE_CLASS_TEMPERATURE,
            UnitOfTemperature.CELSIUS,
            UnitOfTemperature.CELSIUS,
        )
        == 21.0
    )


def test_config_data_describes_itself() -> None:
    """The account object prints its public fields and accepts an empty form."""
    data = ConfigData()

    assert CONF_USERNAME in repr(data)
    ConfigData.default_schema(None)


@pytest.mark.usefixtures("fake_cloud")
async def test_device_info_and_command_errors(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Device info covers both URL choices, and a Home Assistant error is re-raised."""
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry()
    await setup_entry(hass, entry)
    coordinator = entry.runtime_data

    assert coordinator.login_details is not None
    assert coordinator.config_manager.entry is entry
    assert coordinator.config_manager.entry_title
    assert coordinator.config_manager.is_initialized

    mac = coordinator.get_device("AABBCCDDEEFF")
    assert mac["connections"]
    other = coordinator.get_device("not-a-mac")
    assert "connections" not in other

    async def rejected() -> None:
        raise HomeAssistantError("rejected")

    with pytest.raises(HomeAssistantError, match="rejected"):
        await coordinator._async_send(device.code, rejected)

    sensor = hass.data["sensor"].get_entity(
        entity_id(hass, "sensor", "T01", device.code)
    )
    with patch.object(
        AquaTempSensorEntity, "_update_attributes", side_effect=RuntimeError("boom")
    ):
        sensor._safe_update_attributes()

    with (
        patch.object(
            coordinator.config_manager,
            "get_entity_descriptions",
            side_effect=RuntimeError("setup"),
        ),
        patch("custom_components.aqua_temp.common.base_entity._LOGGER.error") as logged,
    ):
        async_dispatcher_send(
            hass, SIGNAL_AQUA_TEMP_DEVICE_NEW, "other-entry", device.code
        )
        async_dispatcher_send(
            hass, SIGNAL_AQUA_TEMP_DEVICE_NEW, entry.entry_id, device.code
        )

    assert logged.called
