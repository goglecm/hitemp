"""Shared fixtures for the aqua_temp tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable, Generator
from typing import Any
from unittest.mock import AsyncMock, patch

from cryptography.fernet import Fernet
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import (
    CONF_API_TYPE,
    CONFIGURATION_FILE,
    DOMAIN,
)

from .fake_cloud import FakeCloud, FakeDevice

USERNAME = "owner@example.com"
PASSWORD = "correct horse"
ENCRYPTION_KEY = Fernet.generate_key().decode()

HITEMP_FIXTURE = "device_hitemp.json"
AQUATEMP_FIXTURE = "device_aquatemp.json"
GENERIC_FIXTURE = "device_generic.json"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable loading the integration from custom_components."""


@pytest.fixture(autouse=True)
def retry_sleep() -> Generator[AsyncMock]:
    """Skip the delay between API retries."""
    with patch(
        "custom_components.aqua_temp.managers.aqua_temp_api.sleep", AsyncMock()
    ) as mock_sleep:
        yield mock_sleep


def entity_id(hass: HomeAssistant, platform: str, key: str, device_code: str) -> str:
    """Return the entity ID of an integration entity from its unique ID parts."""
    unique_id = slugify(f"{DOMAIN}_{platform}_{key}_{device_code}")
    result = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique_id)
    assert result is not None, f"no {platform} entity for {key} of {device_code}"
    return result


async def setup_entry(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up a config entry and wait for its platforms."""
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


@pytest.fixture
def encryption_key(hass_storage: dict[str, Any]) -> str:
    """Store the integration's password encryption key."""
    hass_storage[CONFIGURATION_FILE] = {
        "version": 1,
        "minor_version": 1,
        "key": CONFIGURATION_FILE,
        "data": {"key": ENCRYPTION_KEY},
    }
    return ENCRYPTION_KEY


def encrypt(password: str, key: str = ENCRYPTION_KEY) -> str:
    """Encrypt a password the way the integration stores it."""
    return Fernet(key.encode()).encrypt(password.encode()).decode()


@pytest.fixture
async def fake_cloud(hass: HomeAssistant) -> AsyncGenerator[FakeCloud]:
    """Provide a fake cloud with one account and no devices."""
    cloud = FakeCloud()
    cloud.add_account(USERNAME, PASSWORD)

    with cloud.patch_sessions(hass):
        yield cloud

    await cloud.async_close()


@pytest.fixture
def add_device(fake_cloud: FakeCloud) -> Callable[..., FakeDevice]:
    """Return a helper that registers a fixture device for the default account."""

    def _add(fixture: str = HITEMP_FIXTURE, owner: str = USERNAME) -> FakeDevice:
        return fake_cloud.add_device(FakeDevice.from_fixture(fixture, owner))

    return _add


@pytest.fixture
def make_entry(
    hass: HomeAssistant, encryption_key: str
) -> Callable[..., MockConfigEntry]:
    """Return a helper that adds a config entry with an encrypted password."""

    def _make(
        api_type: str | None = "hi_temp",
        username: str = USERNAME,
        password: str = PASSWORD,
        **kwargs: Any,
    ) -> MockConfigEntry:
        data = {CONF_USERNAME: username, CONF_PASSWORD: encrypt(password)}
        if api_type is not None:
            data[CONF_API_TYPE] = api_type

        kwargs.setdefault("title", "Aqua Temp")
        entry = MockConfigEntry(domain=DOMAIN, data=data, **kwargs)
        entry.add_to_hass(hass)
        return entry

    return _make
