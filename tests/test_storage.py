"""Tests for the shared configuration store."""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from typing import Any
from unittest.mock import patch

from cryptography.fernet import Fernet
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_TEMPERATURE_UNIT,
    CONF_USERNAME,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import CONFIGURATION_FILE, DOMAIN
from custom_components.aqua_temp.managers.aqua_temp_config_manager import (
    AquaTempConfigManager,
)
from custom_components.aqua_temp.managers.password_manager import PasswordManager


@pytest.fixture
def slow_store() -> Generator[None]:
    """Let other tasks run while the store is read, as real file access does."""
    original = Store.async_load

    async def async_load(self: Store) -> Any:
        data = await original(self)
        await asyncio.sleep(0)
        return data

    with patch.object(Store, "async_load", async_load):
        yield


async def _manager(hass: HomeAssistant, entry_id: str) -> AquaTempConfigManager:
    manager = AquaTempConfigManager(
        hass, MockConfigEntry(domain=DOMAIN, entry_id=entry_id)
    )
    await manager.initialize(
        {CONF_USERNAME: "user", CONF_PASSWORD: "pass", "api_type": "hi_temp"}
    )
    return manager


async def test_legacy_credentials_are_removed_from_store(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Credentials stored by old versions are dropped and saving keeps working."""
    hass_storage[CONFIGURATION_FILE] = {
        "version": 1,
        "minor_version": 1,
        "key": CONFIGURATION_FILE,
        "data": {
            "entry": {
                CONF_TEMPERATURE_UNIT: {},
                CONF_USERNAME: "user",
                CONF_PASSWORD: "plain",
            }
        },
    }

    manager = await _manager(hass, "entry")
    await manager.update_temperature_unit("dev", UnitOfTemperature.FAHRENHEIT)
    await manager.update_temperature_unit("dev", UnitOfTemperature.CELSIUS)

    stored = hass_storage[CONFIGURATION_FILE]["data"]["entry"]
    assert stored == {CONF_TEMPERATURE_UNIT: {"dev": UnitOfTemperature.CELSIUS}}


@pytest.mark.usefixtures("slow_store")
async def test_concurrent_first_encryptions_share_one_key(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Two entries set up at once on a fresh install end up with the same key."""
    first = {CONF_PASSWORD: "first"}
    second = {CONF_PASSWORD: "second"}

    await asyncio.gather(
        PasswordManager.encrypt(hass, first, "one"),
        PasswordManager.encrypt(hass, second, "two"),
    )

    key = Fernet(hass_storage[CONFIGURATION_FILE]["data"]["key"].encode())
    assert key.decrypt(first[CONF_PASSWORD].encode()) == b"first"
    assert key.decrypt(second[CONF_PASSWORD].encode()) == b"second"


@pytest.mark.usefixtures("slow_store")
async def test_concurrent_entries_keep_their_preferences(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Preferences written by two entries at the same time are both kept."""
    await PasswordManager.encrypt(hass, {CONF_PASSWORD: "x"})
    one, two = await asyncio.gather(_manager(hass, "one"), _manager(hass, "two"))

    await asyncio.gather(
        one.update_temperature_unit("a", UnitOfTemperature.FAHRENHEIT),
        two.update_temperature_unit("b", UnitOfTemperature.FAHRENHEIT),
    )

    data = hass_storage[CONFIGURATION_FILE]["data"]
    assert data["one"][CONF_TEMPERATURE_UNIT] == {"a": UnitOfTemperature.FAHRENHEIT}
    assert data["two"][CONF_TEMPERATURE_UNIT] == {"b": UnitOfTemperature.FAHRENHEIT}
    assert data["key"]
