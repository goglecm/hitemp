"""Tests for the cloud status, fault details, device info and entity cleanup."""

from __future__ import annotations

from collections.abc import Callable
import logging
from unittest.mock import patch

from aiohttp import ClientConnectionError
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import slugify
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import (
    CLOUD_STATUS,
    DEVICE_FAULT,
    DOMAIN,
    FAULT_WITHOUT_DESCRIPTION,
    HITEMP_GUIDE_URL,
    NO_FAULT,
    PRODUCT_ID_HITEMP,
)
from custom_components.aqua_temp.diagnostics import (
    async_get_device_diagnostics,
)
from custom_components.aqua_temp.managers.aqua_temp_api import (
    describe_cloud_message,
)
from custom_components.aqua_temp.models.exceptions import (
    CloudConnectionError,
    CloudError,
    InvalidTokenError,
)

from .conftest import HITEMP_FIXTURE, USERNAME, entity_id, setup_entry
from .fake_cloud import FakeCloud, FakeDevice, md5


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


def _device_entry(hass: HomeAssistant, entry: MockConfigEntry) -> dr.DeviceEntry:
    """Return the registry entry of the fixture device, found by its MAC."""
    device_entry = dr.async_get(hass).async_get_device_by_connection(
        (dr.CONNECTION_NETWORK_MAC, "a1:b2:c3:d4:e5:f6"), entry.entry_id
    )
    assert device_entry is not None
    return device_entry


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (InvalidTokenError("Fetch data"), "session_expired"),
        (CloudConnectionError(ClientConnectionError("down")), "cannot_connect"),
        (ClientConnectionError("down"), "cannot_connect"),
        (TimeoutError(), "cannot_connect"),
        (CloudError("Fetch data", "-3: Busy"), "cloud_error"),
    ],
)
async def test_cloud_status_names_the_failure(
    hass: HomeAssistant,
    setup: tuple[FakeDevice, MockConfigEntry],
    error: Exception,
    status: str,
) -> None:
    """A failed poll is classified, with the error as the message."""
    device, entry = setup
    cloud_status = entity_id(hass, "sensor", CLOUD_STATUS, device.code)

    with patch(
        "custom_components.aqua_temp.managers.aqua_temp_api.AquaTempAPI.update",
        side_effect=error,
    ):
        await _refresh(hass, entry)

    state = hass.states.get(cloud_status)
    assert state.state == status
    assert state.attributes["message"] == (str(error) or type(error).__name__)

    await _refresh(hass, entry)

    assert hass.states.get(cloud_status).state == "ok"


async def test_cloud_status_reports_a_rejected_login(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    setup: tuple[FakeDevice, MockConfigEntry],
) -> None:
    """A changed password shows as a rejected login while reauthentication starts."""
    device, entry = setup
    fake_cloud.accounts[USERNAME] = md5("new password")
    fake_cloud.expire_tokens()

    await _refresh(hass, entry)

    state = hass.states.get(entity_id(hass, "sensor", CLOUD_STATUS, device.code))
    assert state.state == "login_rejected"
    assert "rejected" in state.attributes["message"]


async def test_cloud_status_keeps_its_start_time(
    hass: HomeAssistant, setup: tuple[FakeDevice, MockConfigEntry]
) -> None:
    """The 'since' time only moves when the status changes."""
    device, entry = setup
    cloud_status = entity_id(hass, "sensor", CLOUD_STATUS, device.code)
    since = hass.states.get(cloud_status).attributes["since"]

    await _refresh(hass, entry)

    assert hass.states.get(cloud_status).attributes["since"] == since


def test_chinese_cloud_messages_are_explained() -> None:
    """The session-expired reply is shown with its meaning."""
    assert describe_cloud_message("请重新登录") == (
        "请重新登录 (session expired, please log in again)"
    )
    assert describe_cloud_message("Busy") == "Busy"


async def test_command_after_session_expiry_logs_in_again(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    setup: tuple[FakeDevice, MockConfigEntry],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A command answered with the session-expired reply is resent after login."""
    device, entry = setup
    fake_cloud.expire_tokens()
    caplog.set_level(logging.DEBUG)

    await entry.runtime_data.set_fan_mode(device.code, "high")

    assert device.data["M17"] == "2"
    assert "session expired, please log in again" in caplog.text
    assert "logging in again" in caplog.text


async def test_cloud_errors_include_the_meaning_of_chinese_messages(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    setup: tuple[FakeDevice, MockConfigEntry],
) -> None:
    """A Chinese error message reaches the cloud status in readable form."""
    device, entry = setup
    fake_cloud.data_error = "请重新登录"

    await _refresh(hass, entry)

    state = hass.states.get(entity_id(hass, "sensor", CLOUD_STATUS, device.code))
    assert state.state == "cloud_error"
    assert "session expired, please log in again" in state.attributes["message"]


async def test_fault_details(
    hass: HomeAssistant, setup: tuple[FakeDevice, MockConfigEntry]
) -> None:
    """The fault text says 'No fault', the cloud's description, or that it has none."""
    device, entry = setup
    fault = entity_id(hass, "sensor", DEVICE_FAULT, device.code)

    state = hass.states.get(fault)
    assert state.state == NO_FAULT
    assert state.attributes == {**state.attributes, "Fault1": "0"}

    device.is_fault = True
    device.fault_description = "P01 Water inlet sensor failure"
    await _refresh(hass, entry)
    assert hass.states.get(fault).state == "P01 Water inlet sensor failure"

    device.fault_description = None
    await _refresh(hass, entry)
    assert hass.states.get(fault).state == FAULT_WITHOUT_DESCRIPTION

    device.is_fault = None
    await _refresh(hass, entry)
    assert hass.states.get(fault).state == STATE_UNAVAILABLE


async def test_device_info(
    hass: HomeAssistant, setup: tuple[FakeDevice, MockConfigEntry]
) -> None:
    """The device page shows the MAC, serial, versions and a link to the guide."""
    device, entry = setup

    device_entry = _device_entry(hass, entry)

    assert device_entry.serial_number == device.code
    assert (
        device_entry.sw_version
        == "PCB 679 (version 1.0), display 741 (version 1.0), Wi-Fi V1.1"
    )
    assert device_entry.model_id == PRODUCT_ID_HITEMP
    assert device_entry.configuration_url == HITEMP_GUIDE_URL


async def test_software_version_follows_the_heat_pump(
    hass: HomeAssistant, setup: tuple[FakeDevice, MockConfigEntry]
) -> None:
    """A new board version reported later updates the device page."""
    device, entry = setup
    device.live_data["code_version"] = "1.1"

    await _refresh(hass, entry)

    assert (
        _device_entry(hass, entry).sw_version
        == "PCB 679 (version 1.1), display 741 (version 1.0), Wi-Fi V1.1"
    )


@pytest.mark.parametrize(
    ("live_data", "list_extra", "sw_version"),
    [
        ({"MainBoard Version": "679"}, {}, "PCB 679"),
        (
            {"code_version": "1.0"},
            {"wifiSoftwareVer": "V1.1"},
            "PCB version 1.0, Wi-Fi V1.1",
        ),
        ({}, {"wifiSoftwareVer": "V1.1"}, "Wi-Fi V1.1"),
        (
            {"2012": "679", "2011": "1.0", "2014": "741", "2013": "1.0"},
            {},
            "PCB 679 (version 1.0), display 741 (version 1.0)",
        ),
        ({"2011": "1.0"}, {}, "PCB version 1.0"),
        ({}, {}, None),
    ],
)
@pytest.mark.usefixtures("fake_cloud")
async def test_software_version_shows_what_is_known(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    live_data: dict[str, str],
    list_extra: dict[str, str],
    sw_version: str | None,
) -> None:
    """Only the versions the heat pump reported are shown."""
    device = add_device(HITEMP_FIXTURE)
    for code in ("2011", "2012", "2013", "2014"):
        device.data.pop(code)
    device.live_data = live_data
    device.list_extra = list_extra
    entry = make_entry()
    await setup_entry(hass, entry)

    assert _device_entry(hass, entry).sw_version == sw_version


@pytest.mark.usefixtures("fake_cloud")
async def test_entities_no_longer_provided_are_removed(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Old entities of a discovered device go; other devices' entities stay."""
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry()
    registry = er.async_get(hass)

    def register(platform: str, key: str, device_code: str = device.code) -> str:
        return registry.async_get_or_create(
            platform,
            DOMAIN,
            slugify(f"{DOMAIN}_{platform}_{key}_{device_code}"),
            config_entry=entry,
        ).entity_id

    last_error = register("sensor", "last_error")
    e01_number = register("number", "E01")
    r01 = register("number", "R01")
    absent_device = register("sensor", "T02", "FFFFFFFFFFFF")

    await setup_entry(hass, entry)

    assert registry.async_get(last_error) is None
    assert registry.async_get(e01_number) is None
    assert registry.async_get(r01) is not None
    assert registry.async_get(absent_device) is not None


async def test_bitwords_are_shown_raw_in_diagnostics(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Packed switch words are listed as value, hex and bits for decoding."""
    device = add_device(HITEMP_FIXTURE)
    device.live_data.update({"S01~S06": "13", "O01~015": "on"})
    entry = make_entry()
    await setup_entry(hass, entry)

    diagnostics = await async_get_device_diagnostics(
        hass, entry, _device_entry(hass, entry)
    )

    bitwords = diagnostics["device"]["live_data"]["bitwords"]
    assert bitwords["1129"]["bits_set"] == []
    assert {code: bitwords[code] for code in ("O01~015", "S01~S06")} == {
        "O01~015": {"value": "on"},
        "S01~S06": {
            "value": "13",
            "hex": "0x000D",
            "bits": "0000000000001101",
            "bits_set": [0, 2, 3],
        },
    }
