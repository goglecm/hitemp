"""Tests for the diagnostics download."""

from __future__ import annotations

from collections.abc import Callable
import json

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
import pytest
from pytest_homeassistant.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from custom_components.aqua_temp.common.consts import DOMAIN
from custom_components.aqua_temp.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)

from .conftest import HITEMP_FIXTURE, PASSWORD, USERNAME, setup_entry
from .fake_cloud import FakeCloud, FakeDevice, md5

VOLATILE = props("last_changed", "last_reported", "last_updated", "time", "since")


@pytest.fixture
async def device(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> FakeDevice:
    """Set up one HiTemp device."""
    device = add_device(HITEMP_FIXTURE)
    await setup_entry(hass, make_entry(entry_id="01TESTENTRY"))
    return device


def _assert_no_secrets(fake_cloud: FakeCloud, diagnostics: dict) -> None:
    text = json.dumps(diagnostics, default=str)

    assert USERNAME not in text
    assert PASSWORD not in text
    assert md5(PASSWORD) not in text
    assert f"uid-{USERNAME}" not in text
    for token in fake_cloud.tokens:
        assert token not in text


async def test_entry_diagnostics(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    device: FakeDevice,
    snapshot: SnapshotAssertion,
) -> None:
    """Entry diagnostics include every device and no credentials."""
    entry = hass.config_entries.async_get_entry("01TESTENTRY")

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    _assert_no_secrets(fake_cloud, diagnostics)
    assert len(diagnostics["devices"]) == 1
    assert diagnostics == snapshot(exclude=VOLATILE)


async def test_device_diagnostics(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    device: FakeDevice,
    snapshot: SnapshotAssertion,
) -> None:
    """Device diagnostics work and describe the device's entities."""
    entry = hass.config_entries.async_get_entry("01TESTENTRY")
    device_entry = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, device.device_id), entry.entry_id
    )

    diagnostics = await async_get_device_diagnostics(hass, entry, device_entry)

    _assert_no_secrets(fake_cloud, diagnostics)
    assert diagnostics["device"]["data"]["R01"] == "50.0"
    assert diagnostics["device"]["entities"]
    assert diagnostics == snapshot(exclude=VOLATILE)
