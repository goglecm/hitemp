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
    ATTR_TEMPERATURE,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import API_STATUS, LAST_ERROR

from .conftest import GENERIC_FIXTURE, HITEMP_FIXTURE, entity_id, setup_entry
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

    assert hass.states.get(entity_id(hass, "sensor", "H07", code)).state == (
        "Celsius degree (0)"
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


@pytest.mark.parametrize("value", ["abc", "", None])
async def test_values_without_a_number_are_unavailable(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    value: str | None,
) -> None:
    """Values that are not numbers make the entity unavailable, never unknown."""
    device = add_device(HITEMP_FIXTURE)
    device.data.update(T02=value, R01=value)
    await setup_entry(hass, make_entry())

    assert hass.states.get(entity_id(hass, "sensor", "T02", device.code)).state == (
        STATE_UNAVAILABLE
    )
    assert hass.states.get(entity_id(hass, "number", "R01", device.code)).state == (
        STATE_UNAVAILABLE
    )


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


async def test_select_changes_units_without_reload(
    hass: HomeAssistant, hitemp: FakeDevice
) -> None:
    """Choosing °F is stored and applied to climate, sensors and numbers at once."""
    code = hitemp.code
    select = entity_id(hass, "select", "temperature_unit", code)

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: select, ATTR_OPTION: UnitOfTemperature.FAHRENHEIT},
        blocking=True,
    )

    assert hass.states.get(select).state == UnitOfTemperature.FAHRENHEIT

    # 50 °F reported by the device, shown in the system's °C
    climate = hass.states.get(entity_id(hass, "climate", "Mode", code))
    assert climate.attributes[ATTR_TEMPERATURE] == pytest.approx(10.0)

    bottom = hass.states.get(entity_id(hass, "sensor", "T02", code))
    assert float(bottom.state) == pytest.approx(3.6, abs=0.1)

    r01 = hass.states.get(entity_id(hass, "number", "R01", code))
    assert r01.attributes["min"] == pytest.approx(38.3, abs=0.1)


async def test_diagnostic_entities_stay_available_when_polling_fails(
    hass: HomeAssistant, fake_cloud: FakeCloud, hitemp: FakeDevice
) -> None:
    """API Status and Last Error explain a failure instead of going unavailable."""
    code = hitemp.code
    entry = hass.config_entries.async_entries("aqua_temp")[0]
    last_error = entity_id(hass, "sensor", LAST_ERROR, code)
    assert hass.states.get(last_error).state == STATE_UNKNOWN

    fake_cloud.network_down = True
    fake_cloud.expire_tokens()
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(last_error).state == "Cloud unreachable"
    assert hass.states.get(
        entity_id(hass, "binary_sensor", API_STATUS, code)
    ).state == (STATE_OFF)
    assert hass.states.get(entity_id(hass, "sensor", "T02", code)).state == (
        STATE_UNAVAILABLE
    )
    assert hass.states.get(
        entity_id(hass, "binary_sensor", "is_fault", code)
    ).state == (STATE_UNAVAILABLE)

    fake_cloud.network_down = False
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(last_error).state == STATE_UNKNOWN
    assert hass.states.get(
        entity_id(hass, "binary_sensor", API_STATUS, code)
    ).state == (STATE_ON)


@pytest.mark.usefixtures("fake_cloud")
async def test_device_without_nickname_uses_device_code(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Devices without a nickname are named after their device code."""
    device = add_device(GENERIC_FIXTURE)
    await setup_entry(hass, make_entry())

    climate = hass.states.get(entity_id(hass, "climate", "Mode", device.code))
    assert climate.name == device.code
    sensor = hass.states.get(entity_id(hass, "sensor", "T02", device.code))
    assert sensor.name.startswith(device.code)
