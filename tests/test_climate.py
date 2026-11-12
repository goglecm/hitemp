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
    assert state.attributes[ATTR_TEMPERATURE] == 60.0
    assert state.attributes[ATTR_CURRENT_TEMPERATURE] == 32.5
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
    assert state.attributes[ATTR_TEMPERATURE] == 60.0


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
    """Setting the target writes R01 once and the new value is read back."""
    device, _, climate = await _setup(hass, add_device, make_entry)

    await _call(
        hass, SERVICE_SET_TEMPERATURE, {ATTR_ENTITY_ID: climate, ATTR_TEMPERATURE: 55}
    )

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": "R01", "value": 55.0}]
    ]
    assert device.data["R01"] == "55.0"
    assert hass.states.get(climate).attributes[ATTR_TEMPERATURE] == 55.0


@pytest.mark.usefixtures("fake_cloud")
async def test_hitemp_limits_match_r01(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """The climate card is limited to the 38-60 °C range of R01 in steps of 0.5."""
    _, _, climate = await _setup(hass, add_device, make_entry)

    attributes = hass.states.get(climate).attributes
    assert attributes["min_temp"] == 38.0
    assert attributes["max_temp"] == 60.0
    assert attributes["target_temp_step"] == 0.5


@pytest.mark.parametrize("temperature", [37, 61, 75, 90])
async def test_hitemp_rejects_unsafe_targets(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    temperature: float,
) -> None:
    """Targets outside 38-60 °C never reach the heat pump."""
    _, _, climate = await _setup(hass, add_device, make_entry)

    with pytest.raises(ServiceValidationError):
        await _call(
            hass,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: climate, ATTR_TEMPERATURE: temperature},
        )

    assert not fake_cloud.control_requests()


async def test_hitemp_target_is_rounded_to_half_degrees(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Targets between steps are rounded to the 0.5 °C step of R01."""
    device, _, climate = await _setup(hass, add_device, make_entry)

    await _call(
        hass,
        SERVICE_SET_TEMPERATURE,
        {ATTR_ENTITY_ID: climate, ATTR_TEMPERATURE: 45.4},
    )

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": "R01", "value": 45.5}]
    ]


@pytest.mark.usefixtures("fake_cloud")
async def test_hitemp_limits_in_fahrenheit(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A device reporting °F gets the R01 range converted and narrowed to whole °F."""
    device = add_device(HITEMP_FIXTURE)
    device.data.update(R01="122")
    entry = make_entry()
    hass_storage[CONFIGURATION_FILE]["data"][entry.entry_id] = {
        CONF_TEMPERATURE_UNIT: {device.code: UnitOfTemperature.FAHRENHEIT}
    }
    await setup_entry(hass, entry)

    attributes = hass.states.get(
        entity_id(hass, "climate", "Mode", device.code)
    ).attributes
    # 101-140 °F shown in the system's °C
    assert attributes["min_temp"] == pytest.approx(38.3)
    assert attributes["max_temp"] == pytest.approx(60.0)
    assert attributes[ATTR_TEMPERATURE] == pytest.approx(50.0)


async def test_aquatemp_set_temperature_writes_mode_target_and_setpoint(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """In heat mode the heat target R02 and the active setpoint are written."""
    device, _, climate = await _setup(hass, add_device, make_entry, AQUATEMP_FIXTURE)

    await _call(
        hass, SERVICE_SET_TEMPERATURE, {ATTR_ENTITY_ID: climate, ATTR_TEMPERATURE: 30}
    )

    assert fake_cloud.control_requests() == [
        [
            {"deviceCode": device.code, "protocolCode": "R02", "value": 30.0},
            {"deviceCode": device.code, "protocolCode": "Set_Temp", "value": 30.0},
        ]
    ]


async def test_mode_switch_uses_new_mode_setpoint(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Switching heat to cool sets the active setpoint to the cool target R01."""
    device, _, climate = await _setup(hass, add_device, make_entry, AQUATEMP_FIXTURE)

    await _call(
        hass,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: climate, ATTR_HVAC_MODE: HVACMode.COOL},
    )

    assert fake_cloud.control_requests() == [
        [
            {"deviceCode": device.code, "protocolCode": "Set_Temp", "value": 26.0},
            {"deviceCode": device.code, "protocolCode": "Mode", "value": "0"},
        ]
    ]
    state = hass.states.get(climate)
    assert state.state == HVACMode.COOL
    assert state.attributes[ATTR_TEMPERATURE] == 26.0


async def test_mode_already_active_is_not_rewritten(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Selecting heat on a stopped HiTemp only switches the power on."""
    device, _, climate = await _setup(hass, add_device, make_entry, Power="0")

    await _call(
        hass,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: climate, ATTR_HVAC_MODE: HVACMode.HEAT},
    )

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": "power", "value": "1"}]
    ]


async def test_unknown_mode_writes_only_the_setpoint(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Without a mode-specific target only the generic setpoint is written."""
    device, _, climate = await _setup(
        hass, add_device, make_entry, AQUATEMP_FIXTURE, Mode="9"
    )
    assert hass.states.get(climate).attributes[ATTR_TEMPERATURE] == 28.0

    await _call(
        hass, SERVICE_SET_TEMPERATURE, {ATTR_ENTITY_ID: climate, ATTR_TEMPERATURE: 30}
    )

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": "Set_Temp", "value": 30.0}]
    ]


@pytest.mark.parametrize("power", [1, "1", True, "true"])
@pytest.mark.usefixtures("fake_cloud")
async def test_power_values_are_normalised(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    power: Any,
) -> None:
    """Power reported as a number or boolean is still recognised as on."""
    _, _, climate = await _setup(hass, add_device, make_entry, Power=power)

    assert hass.states.get(climate).state == HVACMode.HEAT


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


@pytest.mark.parametrize("mode", ["0", "3", "4"])
async def test_hitemp_other_heating_modes_are_kept(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    mode: str,
) -> None:
    """Intelligent, Standard and High demand show as heat and are not switched to Eco."""
    device, _, climate = await _setup(hass, add_device, make_entry, mode_real=mode)

    assert hass.states.get(climate).state == HVACMode.HEAT

    await _call(
        hass,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: climate, ATTR_HVAC_MODE: HVACMode.HEAT},
    )

    assert fake_cloud.control_requests() == []
    assert device.data["mode_real"] == mode


async def test_hitemp_unknown_mode_is_switched_to_heat(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A mode value outside the mapping is still replaced when heat is chosen."""
    device, _, climate = await _setup(hass, add_device, make_entry, mode_real="7")

    await _call(
        hass,
        SERVICE_SET_HVAC_MODE,
        {ATTR_ENTITY_ID: climate, ATTR_HVAC_MODE: HVACMode.HEAT},
    )

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": "mode_real", "value": "2"}]
    ]
