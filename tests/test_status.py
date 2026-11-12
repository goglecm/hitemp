"""Tests for fault, online status and stale-data handling."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.climate import (
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_TEMPERATURE,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import pytest
from pytest_homeassistant.common import MockConfigEntry

from .conftest import HITEMP_FIXTURE, entity_id, setup_entry
from .fake_cloud import FakeCloud, FakeDevice


@pytest.fixture
async def setup(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> tuple[FakeDevice, MockConfigEntry]:
    """Set up one HiTemp device."""
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry()
    await setup_entry(hass, entry)
    return device, entry


async def _refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


@pytest.mark.parametrize("is_fault", [True, "true", 1, "1"])
async def test_fault_is_reported_on_next_poll(
    hass: HomeAssistant,
    setup: tuple[FakeDevice, MockConfigEntry],
    is_fault: object,
) -> None:
    """A fault raised after start-up turns the Fault sensor on with its description."""
    device, entry = setup
    fault = entity_id(hass, "binary_sensor", "is_fault", device.code)
    assert hass.states.get(fault).state == STATE_OFF

    device.is_fault = is_fault
    device.fault_description = "E03 Water flow failure"
    await _refresh(hass, entry)

    state = hass.states.get(fault)
    assert state.state == STATE_ON
    assert state.attributes["fault"] == "E03 Water flow failure"

    device.is_fault = False
    await _refresh(hass, entry)

    state = hass.states.get(fault)
    assert state.state == STATE_OFF
    assert state.attributes["fault"] is None


async def test_fault_stays_on_when_description_fails(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    setup: tuple[FakeDevice, MockConfigEntry],
) -> None:
    """A failing fault-detail request does not hide the fault itself."""
    device, entry = setup
    device.is_fault = True
    fake_cloud.http_status["app/device/getFaultDataByDeviceCode"] = 500

    await _refresh(hass, entry)

    state = hass.states.get(entity_id(hass, "binary_sensor", "is_fault", device.code))
    assert state.state == STATE_ON


async def test_unknown_fault_flag_is_unknown(
    hass: HomeAssistant, setup: tuple[FakeDevice, MockConfigEntry]
) -> None:
    """A missing fault flag is shown as unknown, not as 'no fault'."""
    device, entry = setup
    device.is_fault = None

    await _refresh(hass, entry)

    state = hass.states.get(entity_id(hass, "binary_sensor", "is_fault", device.code))
    assert state.state == STATE_UNKNOWN


async def test_offline_device_becomes_unavailable(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    setup: tuple[FakeDevice, MockConfigEntry],
) -> None:
    """Device data is unavailable while offline; diagnostics stay visible."""
    device, entry = setup
    code = device.code

    device.status = "OFFLINE"
    await _refresh(hass, entry)

    for platform, key in (
        ("climate", "Mode"),
        ("sensor", "T02"),
        ("number", "R01"),
        ("binary_sensor", "Power"),
    ):
        state = hass.states.get(entity_id(hass, platform, key, code))
        assert state.state == STATE_UNAVAILABLE, key

    assert hass.states.get(
        entity_id(hass, "binary_sensor", "device_status", code)
    ).state == (STATE_OFF)
    assert hass.states.get(
        entity_id(hass, "binary_sensor", "is_fault", code)
    ).state == (STATE_OFF)
    assert hass.states.get(
        entity_id(hass, "binary_sensor", "api_status", code)
    ).state == (STATE_ON)
    assert hass.states.get(
        entity_id(hass, "select", "temperature_unit", code)
    ).state != (STATE_UNAVAILABLE)

    with pytest.raises(HomeAssistantError) as err:
        await entry.runtime_data.set_temperature(code, 45)
    assert err.value.translation_key == "device_offline"
    assert not fake_cloud.control_requests()

    device.status = "ONLINE"
    await _refresh(hass, entry)

    assert hass.states.get(entity_id(hass, "climate", "Mode", code)).state == "heat"


async def test_failed_data_request_marks_entities_unavailable(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    setup: tuple[FakeDevice, MockConfigEntry],
) -> None:
    """When the data cannot be read, old values are not shown as current."""
    device, entry = setup
    sensor = entity_id(hass, "sensor", "T02", device.code)
    assert hass.states.get(sensor).state == "29.0"

    fake_cloud.data_error = "Server busy"
    await _refresh(hass, entry)

    assert hass.states.get(sensor).state == STATE_UNAVAILABLE
    assert not entry.runtime_data.last_update_success
    main_reads = [codes for codes in fake_cloud.data_requests() if "R01" in codes]
    assert len(main_reads) == 4

    fake_cloud.data_error = None
    await _refresh(hass, entry)

    assert hass.states.get(sensor).state == "29.0"


async def test_values_missing_from_response_are_cleared(
    hass: HomeAssistant, setup: tuple[FakeDevice, MockConfigEntry]
) -> None:
    """A code the cloud stops returning becomes unavailable instead of stale."""
    device, entry = setup
    sensor = entity_id(hass, "sensor", "T02", device.code)

    del device.data["T02"]
    await _refresh(hass, entry)

    assert hass.states.get(sensor).state == STATE_UNAVAILABLE


async def test_expired_token_is_renewed_without_losing_state(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    setup: tuple[FakeDevice, MockConfigEntry],
) -> None:
    """An expired token triggers a new login and the poll still succeeds."""
    device, entry = setup
    device.is_fault = True
    await _refresh(hass, entry)

    fake_cloud.expire_tokens()
    await _refresh(hass, entry)

    assert entry.runtime_data.last_update_success
    assert len(fake_cloud.endpoint_requests("app/user/login")) == 2
    state = hass.states.get(entity_id(hass, "binary_sensor", "is_fault", device.code))
    assert state.state == STATE_ON


async def test_rejected_command_raises_readable_error(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    setup: tuple[FakeDevice, MockConfigEntry],
) -> None:
    """A command the cloud rejects is retried, then reported to the user."""
    device, _ = setup
    fake_cloud.control_error = "Device busy"

    with pytest.raises(HomeAssistantError) as err:
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {
                ATTR_ENTITY_ID: entity_id(hass, "climate", "Mode", device.code),
                ATTR_TEMPERATURE: 45,
            },
            blocking=True,
        )

    assert err.value.translation_key == "command_failed"
    assert "Device busy" in str(err.value)
    assert len(fake_cloud.control_requests()) == 3
    assert device.data["R01"] == "60.0"
