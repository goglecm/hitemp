"""Tests for the climate entity."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.climate import (
    ATTR_CURRENT_TEMPERATURE,
    ATTR_FAN_MODE,
    ATTR_FAN_MODES,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    HVACMode,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import CONFIGURATION_FILE

from .conftest import (
    AQUATEMP_FIXTURE,
    GENERIC_FIXTURE,
    HITEMP_FIXTURE,
    entity_id,
    setup_entry,
)
from .fake_cloud import FakeCloud, FakeDevice


async def _setup(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    fixture: str = HITEMP_FIXTURE,
    **data: Any,
) -> tuple[FakeDevice, MockConfigEntry, str]:
    device = add_device(fixture)
    device.data.update(data)
    entry = make_entry()
    await setup_entry(hass, entry)
    return device, entry, entity_id(hass, "climate", "Mode", device.code)


async def _call(hass: HomeAssistant, service: str, data: dict[str, Any]) -> None:
    await hass.services.async_call(CLIMATE_DOMAIN, service, data, blocking=True)


@pytest.mark.usefixtures("fake_cloud")
async def test_hitemp_state(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """HiTemp state maps mode_real, R01, T10 and M17."""
    _, _, climate = await _setup(hass, add_device, make_entry)

    state = hass.states.get(climate)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_HVAC_MODES] == [HVACMode.OFF, HVACMode.HEAT]
    assert state.attributes[ATTR_TEMPERATURE] == 50.0
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 44.0
    assert state.attributes[ATTR_FAN_MODE] == "low"
    assert state.attributes[ATTR_FAN_MODES] == ["off", "low", "high"]


@pytest.mark.usefixtures("fake_cloud")
async def test_aquatemp_state(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """AquaTemp uses per-mode targets and limits."""
    _, _, climate = await _setup(hass, add_device, make_entry, AQUATEMP_FIXTURE)

    state = hass.states.get(climate)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_HVAC_MODES] == [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.AUTO,
    ]
    assert state.attributes[ATTR_TEMPERATURE] == 28.0
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 24.5
    assert state.attributes["min_temp"] == 15.0
    assert state.attributes["max_temp"] == 40.0
    assert state.attributes[ATTR_FAN_MODE] == "auto"


@pytest.mark.usefixtures("fake_cloud")
async def test_power_off_shows_off_with_target(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A powered-off device is OFF but still reports its target temperature."""
    _, _, climate = await _setup(hass, add_device, make_entry, Power="0")

    state = hass.states.get(climate)
    assert state.state == HVACMode.OFF
    assert state.attributes[ATTR_TEMPERATURE] == 50.0


@pytest.mark.usefixtures("fake_cloud")
async def test_unknown_mode_is_reported_as_off(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A mode value missing from the mapping is shown as OFF, not an error."""
    _, _, climate = await _setup(
        hass, add_device, make_entry, AQUATEMP_FIXTURE, Mode="9"
    )

    assert hass.states.get(climate).state == HVACMode.OFF


@pytest.mark.usefixtures("fake_cloud")
async def test_fahrenheit_device_is_converted(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Values from a device set to °F are converted to the system unit."""
    device = add_device(GENERIC_FIXTURE)
    device.data.update(Power="1", R01="80", T02="68")
    entry = make_entry()
    hass_storage[CONFIGURATION_FILE]["data"][entry.entry_id] = {
        CONF_TEMPERATURE_UNIT: {device.code: UnitOfTemperature.FAHRENHEIT}
    }
    await setup_entry(hass, entry)

    state = hass.states.get(entity_id(hass, "climate", "Mode", device.code))
    assert state.state == HVACMode.COOL
    assert state.attributes[ATTR_TEMPERATURE] == pytest.approx(26.7)
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == pytest.approx(20.0)


async def test_set_temperature(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Setting the target writes R01 and the new value is read back."""
    device, _, climate = await _setup(hass, add_device, make_entry)

    await _call(
        hass, SERVICE_SET_TEMPERATURE, {ATTR_ENTITY_ID: climate, ATTR_TEMPERATURE: 55}
    )

    assert device.data["R01"] == "55.0"
    assert hass.states.get(climate).attributes[ATTR_TEMPERATURE] == 55.0
    for params in fake_cloud.control_requests():
        for param in params:
            assert param["protocolCode"] == "R01"
            assert param["value"] == 55.0


async def test_set_temperature_out_of_range_is_rejected(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Targets outside the device limits never reach the cloud."""
    _, _, climate = await _setup(hass, add_device, make_entry, AQUATEMP_FIXTURE)

    with pytest.raises(ServiceValidationError):
        await _call(
            hass,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: climate, ATTR_TEMPERATURE: 41},
        )

    assert not fake_cloud.control_requests()


async def test_set_temperature_with_hvac_mode(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A mode passed with the temperature is applied first."""
    device, _, climate = await _setup(hass, add_device, make_entry, AQUATEMP_FIXTURE)

    await _call(
        hass,
        SERVICE_SET_TEMPERATURE,
        {
            ATTR_ENTITY_ID: climate,
            ATTR_TEMPERATURE: 25,
            ATTR_HVAC_MODE: HVACMode.COOL,
        },
    )

    assert device.data["Mode"] == "0"
    assert device.data["R01"] == "25.0"


async def test_turn_off_and_on(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Turning on resumes the device's own mode instead of forcing heat."""
    device, entry, climate = await _setup(
        hass, add_device, make_entry, AQUATEMP_FIXTURE, Mode="0"
    )

    await _call(hass, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: climate})
    assert device.data["Power"] == "0"
    assert hass.states.get(climate).state == HVACMode.OFF

    fake_cloud.clear_requests()
    await _call(hass, SERVICE_TURN_ON, {ATTR_ENTITY_ID: climate})
    await entry.runtime_data.async_refresh()

    assert device.data["Power"] == "1"
    assert device.data["Mode"] == "0"
    assert len(fake_cloud.control_requests()) == 1
    assert hass.states.get(climate).state == HVACMode.COOL


async def test_set_hvac_mode_from_off_powers_on(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Selecting heat on a powered-off HiTemp powers it on."""
    device, _, climate = await _setup(hass, add_device, make_entry, Power="0")

    await _call(
        hass,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: climate, ATTR_HVAC_MODE: HVACMode.HEAT},
    )

    assert device.data["Power"] == "1"
    assert hass.states.get(climate).state == HVACMode.HEAT


@pytest.mark.parametrize(
    ("fixture", "fan_mode", "code", "value"),
    [
        (HITEMP_FIXTURE, "high", "M17", "2"),
        (HITEMP_FIXTURE, "off", "M17", "0"),
        (AQUATEMP_FIXTURE, "low", "Manual-mute", "1"),
    ],
)
async def test_set_fan_mode(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    fixture: str,
    fan_mode: str,
    code: str,
    value: str,
) -> None:
    """Fan modes use the product's own codes."""
    device, _, climate = await _setup(hass, add_device, make_entry, fixture)

    await _call(
        hass, SERVICE_SET_FAN_MODE, {ATTR_ENTITY_ID: climate, ATTR_FAN_MODE: fan_mode}
    )

    assert device.data[code] == value
    assert hass.states.get(climate).attributes[ATTR_FAN_MODE] == fan_mode


@pytest.mark.usefixtures("fake_cloud")
async def test_invalid_fan_mode_is_rejected(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Home Assistant rejects fan modes the product does not support."""
    _, _, climate = await _setup(hass, add_device, make_entry, AQUATEMP_FIXTURE)

    with pytest.raises(ServiceValidationError):
        await _call(
            hass, SERVICE_SET_FAN_MODE, {ATTR_ENTITY_ID: climate, ATTR_FAN_MODE: "high"}
        )
