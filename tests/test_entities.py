"""Tests for the sensor, binary sensor, number and select entities."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant.common import MockConfigEntry

from .conftest import HITEMP_FIXTURE, entity_id, setup_entry
from .fake_cloud import FakeCloud, FakeDevice


@pytest.fixture
async def hitemp(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> FakeDevice:
    """Set up the integration with one HiTemp device."""
    device = add_device(HITEMP_FIXTURE)
    await setup_entry(hass, make_entry())
    return device


async def test_initial_states(hass: HomeAssistant, hitemp: FakeDevice) -> None:
    """Every entity has its state as soon as it is added."""
    code = hitemp.code

    bottom = hass.states.get(entity_id(hass, "sensor", "T02", code))
    assert bottom.state == "38.5"
    assert bottom.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS

    assert hass.states.get(entity_id(hass, "sensor", "T06", code)).state == (
        STATE_UNKNOWN
    )
    assert hass.states.get(entity_id(hass, "binary_sensor", "Power", code)).state == (
        STATE_ON
    )
    assert hass.states.get(
        entity_id(hass, "binary_sensor", "api_status", code)
    ).state == (STATE_ON)
    assert hass.states.get(
        entity_id(hass, "binary_sensor", "device_status", code)
    ).state == (STATE_ON)
    assert hass.states.get(
        entity_id(hass, "binary_sensor", "is_fault", code)
    ).state == (STATE_OFF)
    assert hass.states.get(entity_id(hass, "number", "R01", code)).state == "50.0"
    assert hass.states.get(
        entity_id(hass, "select", "temperature_unit", code)
    ).state == (UnitOfTemperature.CELSIUS)


async def test_number_writes_parameter(
    hass: HomeAssistant, fake_cloud: FakeCloud, hitemp: FakeDevice
) -> None:
    """A writable parameter is sent to the device and read back."""
    number = entity_id(hass, "number", "R03", hitemp.code)

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: number, ATTR_VALUE: 7},
        blocking=True,
    )

    assert fake_cloud.control_requests()[-1] == [
        {"deviceCode": hitemp.code, "protocolCode": "R03", "value": 7.0}
    ]
    assert hass.states.get(number).state == "7.0"


async def test_select_stores_temperature_unit(
    hass: HomeAssistant, hitemp: FakeDevice
) -> None:
    """Choosing a temperature unit is stored for the device."""
    select = entity_id(hass, "select", "temperature_unit", hitemp.code)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: select, ATTR_OPTION: UnitOfTemperature.FAHRENHEIT},
        blocking=True,
    )

    assert hass.states.get(select).state == UnitOfTemperature.FAHRENHEIT
