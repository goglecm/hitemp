"""Tests for requesting live data with the app heartbeat."""

from __future__ import annotations

from collections.abc import Callable
import logging
from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import (
    CONF_LIVE_DATA,
    LIVE_DATA_SETTLE_SECONDS,
    LIVE_PROBE_CODES,
)

from .conftest import HITEMP_FIXTURE, setup_entry
from .fake_cloud import FakeCloud, FakeDevice


async def _setup(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    api_type: str = "hi_temp",
    **data,
) -> tuple[FakeDevice, MockConfigEntry]:
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry(api_type=api_type)
    if data:
        hass.config_entries.async_update_entry(entry, data={**entry.data, **data})
    await setup_entry(hass, entry)
    return device, entry


async def test_heartbeat_is_sent_before_reading(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    retry_sleep: AsyncMock,
) -> None:
    """Each poll asks for live data, waits, then reads it."""
    device, entry = await _setup(hass, add_device, make_entry)

    endpoints = [request.endpoint for request in fake_cloud.requests]
    heartbeat = endpoints.index("app/device/control")
    assert endpoints[heartbeat + 1] == "app/device/getDataByCode"
    retry_sleep.assert_any_await(LIVE_DATA_SETTLE_SECONDS)
    assert fake_cloud.heartbeat_requests()[0].body == {
        "param": [
            {
                "deviceCode": device.code,
                "protocolCode": "app_heartbeat",
                "value": "23205",
            }
        ]
    }

    await entry.runtime_data.async_refresh()

    assert device.heartbeats == 2
    assert not fake_cloud.control_requests()


async def test_live_values_arrive_after_heartbeat(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Switch, output, fault and version codes are filled by the live upload."""
    device, entry = await _setup(hass, add_device, make_entry)

    data = entry.runtime_data.get_device_data(device.code)
    assert data["S01"] == "1"
    assert data["O01"] == "1"
    assert data["Fault1"] == "0"
    assert data["code_version"] == "1.0"
    assert data["MainBoard Version"] == "679"

    report = entry.runtime_data.get_live_data_report(device.code)
    assert report["heartbeat"]["result"] == "ok"
    assert "S01" in report["codes_with_value"]
    assert "code_version" in report["codes_with_value"]
    assert "T11" in report["codes_without_value"]
    assert "S01~S10" in report["codes_without_value"]


async def test_live_data_can_be_turned_off(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Without the heartbeat only what the board uploads by itself is read."""
    device, entry = await _setup(
        hass, add_device, make_entry, **{CONF_LIVE_DATA: False}
    )

    assert not fake_cloud.heartbeat_requests()
    data = entry.runtime_data.get_device_data(device.code)
    assert data["S01"] is None
    assert data["T02"] is not None
    report = entry.runtime_data.get_live_data_report(device.code)
    assert report["heartbeat"]["result"] == "disabled"


async def test_old_api_keeps_passthrough(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """The old API keeps its keep-alive instruction and gets no heartbeat or probes."""
    await _setup(hass, add_device, make_entry, api_type="aqua_temp_old")

    assert not fake_cloud.heartbeat_requests()
    assert fake_cloud.endpoint_requests("device/sendDevicePassthroughInstruction")
    assert all("Fault1" not in codes for codes in fake_cloud.data_requests())


async def test_rejected_heartbeat_does_not_fail_the_poll(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A rejected live data request is logged once and the values are still read."""
    caplog.set_level(logging.WARNING)
    fake_cloud.heartbeat_error = "Unknown protocol code"
    device, entry = await _setup(hass, add_device, make_entry)

    await entry.runtime_data.async_refresh()

    assert entry.runtime_data.last_update_success
    assert entry.runtime_data.get_device_data(device.code)["T02"] is not None
    assert caplog.text.count("rejected the live data request") == 1
    result = entry.runtime_data.get_live_data_report(device.code)["heartbeat"]
    assert result["result"].startswith("rejected")


async def test_probe_codes_are_read_separately(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Probe codes have their own request, so they cannot break the main read."""
    await _setup(hass, add_device, make_entry)

    requests = fake_cloud.data_requests()
    assert len(requests) == 2
    assert "R01" in requests[0]
    assert not set(LIVE_PROBE_CODES) & set(requests[0])
    assert requests[1] == LIVE_PROBE_CODES


async def test_rejected_probe_codes_are_narrowed_down(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Codes the cloud rejects are dropped while the others are still read."""
    fake_cloud.rejected_codes = {"O01~023", "Fault7"}
    device, entry = await _setup(hass, add_device, make_entry)

    assert entry.runtime_data.last_update_success
    assert entry.runtime_data.get_device_data(device.code)["code_version"] == "1.0"

    fake_cloud.clear_requests()
    await entry.runtime_data.async_refresh()

    probe_request = fake_cloud.data_requests()[1]
    assert "O01~023" not in probe_request
    assert "Fault7" not in probe_request
    assert "Fault1" in probe_request


async def test_main_read_failure_still_fails_the_poll(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Only probe codes are narrowed down; the main read keeps its error handling."""
    device, entry = await _setup(hass, add_device, make_entry)
    fake_cloud.rejected_codes = {"R01"}

    await entry.runtime_data.async_refresh()

    assert not entry.runtime_data.last_update_success
