"""Tests for the writable device parameters."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.components.number import (
    ATTR_MAX,
    ATTR_MIN,
    ATTR_STEP,
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_TEMPERATURE_UNIT,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import CONFIGURATION_FILE, DOMAIN

from .conftest import HITEMP_FIXTURE, entity_id, setup_entry
from .fake_cloud import FakeCloud, FakeDevice


async def _setup(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> FakeDevice:
    device = add_device(HITEMP_FIXTURE)
    await setup_entry(hass, make_entry())
    return device


async def _set(hass: HomeAssistant, entity: str, value: float) -> None:
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: entity, ATTR_VALUE: value},
        blocking=True,
    )


@pytest.mark.usefixtures("fake_cloud")
async def test_r01_range(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """R01 accepts 38-60 °C in steps of 0.5, as in the app."""
    device = await _setup(hass, add_device, make_entry)

    state = hass.states.get(entity_id(hass, "number", "R01", device.code))
    assert state.state == "60.0"
    assert state.attributes[ATTR_MIN] == 38
    assert state.attributes[ATTR_MAX] == 60
    assert state.attributes[ATTR_STEP] == 0.5
    assert state.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.CELSIUS


@pytest.mark.parametrize("value", [37, 61, 75])
async def test_out_of_range_values_are_not_sent(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    value: float,
) -> None:
    """Values outside the confirmed range never reach the heat pump."""
    device = await _setup(hass, add_device, make_entry)

    with pytest.raises(ServiceValidationError):
        await _set(hass, entity_id(hass, "number", "R01", device.code), value)

    assert not fake_cloud.control_requests()


async def test_value_is_rounded_to_step(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Values between steps are rounded before being sent."""
    device = await _setup(hass, add_device, make_entry)

    await _set(hass, entity_id(hass, "number", "R01", device.code), 45.6)

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": "R01", "value": 45.5}]
    ]


async def test_r06_accepts_factory_default(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """The booster delay covers the app's 0-450 min range in 5-minute steps."""
    device = await _setup(hass, add_device, make_entry)
    r06 = entity_id(hass, "number", "R06", device.code)

    assert hass.states.get(r06).attributes[ATTR_MAX] == 450
    assert hass.states.get(r06).attributes[ATTR_STEP] == 5

    await _set(hass, r06, 450)
    await _set(hass, r06, 203)

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": "R06", "value": "450"}],
        [{"deviceCode": device.code, "protocolCode": "R06", "value": "205"}],
    ]
    assert device.data["R06"] == "205"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
@pytest.mark.parametrize(
    ("key", "value", "sent"),
    [("H32", 2, "2"), ("E03", 250, "250"), ("R03", 6.5, 6.5), ("D04", 9, 9.0)],
)
async def test_values_are_written_in_the_form_the_heat_pump_reports(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    key: str,
    value: float,
    sent: str | float,
) -> None:
    """Whole-number codes are sent as '2', not 2.0; decimal codes stay decimal."""
    device = await _setup(hass, add_device, make_entry)

    await _set(hass, entity_id(hass, "number", key, device.code), value)

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": key, "value": sent}]
    ]


@pytest.mark.usefixtures("fake_cloud")
async def test_installer_parameters_are_disabled_by_default(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Installer parameters are opt-in configuration; daily controls are not."""
    device = await _setup(hass, add_device, make_entry)
    registry = er.async_get(hass)

    for platform, keys in (
        ("number", ("E02", "E03", "E04", "D01", "G02", "R08", "H32")),
        ("select", ("E01", "H99", "D06", "R07", "H01")),
    ):
        for key in keys:
            entry = registry.async_get(entity_id(hass, platform, key, device.code))
            assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION, key
            assert entry.entity_category is EntityCategory.CONFIG, key

    for platform, keys in (
        ("number", ("R01", "R03", "R05", "R06")),
        ("select", ("R04", "M17")),
    ):
        for key in keys:
            entry = registry.async_get(entity_id(hass, platform, key, device.code))
            assert entry.disabled_by is None, key
            assert entry.entity_category is None, key


@pytest.mark.usefixtures("fake_cloud", "entity_registry_enabled_by_default")
async def test_enabled_installer_parameter_can_be_written(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Once enabled by the user, an installer parameter works like the others."""
    device = await _setup(hass, add_device, make_entry)

    await _set(hass, entity_id(hass, "number", "E04", device.code), 120)

    assert device.data["E04"] == "120"


@pytest.mark.usefixtures("fake_cloud")
async def test_unverified_parameters_are_read_only(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Parameters that are not well understood are sensors, H98 included."""
    device = await _setup(hass, add_device, make_entry)
    registry = er.async_get(hass)

    for key in ("E05", "H30", "H31", "H98", "N09", "R12", "R15", "/01"):
        for platform in ("number", "select"):
            unique_id = slugify(f"{DOMAIN}_{platform}_{key}_{device.code}")
            assert registry.async_get_entity_id(platform, DOMAIN, unique_id) is None
        assert registry.async_get(entity_id(hass, "sensor", key, device.code)), key

    assert hass.states.get(entity_id(hass, "sensor", "H98", device.code)).state == (
        "0X08 (2)"
    )


@pytest.mark.usefixtures("fake_cloud")
async def test_ranges_follow_fahrenheit_device(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Temperatures and differences are converted for a device set to °F."""
    hass.config.units = US_CUSTOMARY_SYSTEM
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry()
    hass_storage[CONFIGURATION_FILE]["data"][entry.entry_id] = {
        CONF_TEMPERATURE_UNIT: {device.code: UnitOfTemperature.FAHRENHEIT}
    }
    await setup_entry(hass, entry)

    r01 = hass.states.get(entity_id(hass, "number", "R01", device.code))
    assert r01.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTemperature.FAHRENHEIT
    assert (r01.attributes[ATTR_MIN], r01.attributes[ATTR_MAX]) == (101, 140)

    hysteresis = hass.states.get(entity_id(hass, "number", "R03", device.code))
    assert (hysteresis.attributes[ATTR_MIN], hysteresis.attributes[ATTR_MAX]) == (2, 36)
