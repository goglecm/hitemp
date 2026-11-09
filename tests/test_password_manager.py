"""Tests for the password encryption manager."""

from __future__ import annotations

from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from homeassistant.const import CONF_PASSWORD
from homeassistant.core import HomeAssistant
import pytest

from custom_components.aqua_temp.common.consts import CONFIGURATION_FILE
from custom_components.aqua_temp.managers.password_manager import PasswordManager

from .conftest import ENCRYPTION_KEY, encrypt


async def test_round_trip_generates_and_stores_key(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """A fresh install generates a key, stores it and can decrypt its output."""
    data = {CONF_PASSWORD: "secret"}

    await PasswordManager.encrypt(hass, data)

    assert data[CONF_PASSWORD] != "secret"
    key = hass_storage[CONFIGURATION_FILE]["data"]["key"]
    assert Fernet(key.encode()).decrypt(data[CONF_PASSWORD].encode()) == b"secret"

    await PasswordManager.decrypt(hass, data)

    assert data == {CONF_PASSWORD: "secret"}


@pytest.mark.usefixtures("encryption_key")
async def test_decrypt_uses_stored_key(hass: HomeAssistant) -> None:
    """Passwords encrypted with the stored key are decrypted."""
    data = {CONF_PASSWORD: encrypt("secret")}

    await PasswordManager.decrypt(hass, data, "entry")

    assert data[CONF_PASSWORD] == "secret"


async def test_decrypt_imports_legacy_key(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """The key from the legacy .aqua_temp store is migrated."""
    legacy_key = Fernet.generate_key().decode()
    hass_storage[".aqua_temp"] = {
        "version": 1,
        "minor_version": 1,
        "key": ".aqua_temp",
        "data": {"key": legacy_key},
    }
    data = {CONF_PASSWORD: encrypt("secret", legacy_key)}

    await PasswordManager.decrypt(hass, data, "entry")

    assert data[CONF_PASSWORD] == "secret"
    assert ".aqua_temp" not in hass_storage
    assert hass_storage[CONFIGURATION_FILE]["data"]["key"] == legacy_key


async def test_decrypt_uses_entry_level_key(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Keys stored under an entry ID by older versions are still found."""
    hass_storage[CONFIGURATION_FILE] = {
        "version": 1,
        "minor_version": 1,
        "key": CONFIGURATION_FILE,
        "data": {"entry": {"key": ENCRYPTION_KEY}},
    }
    data = {CONF_PASSWORD: encrypt("secret")}

    await PasswordManager.decrypt(hass, data, "entry")

    assert data[CONF_PASSWORD] == "secret"
    assert hass_storage[CONFIGURATION_FILE]["data"]["key"] == ENCRYPTION_KEY


@pytest.mark.usefixtures("encryption_key")
async def test_decrypt_with_wrong_key_raises(hass: HomeAssistant) -> None:
    """A password encrypted with another key is reported, not returned."""
    data = {CONF_PASSWORD: encrypt("secret", Fernet.generate_key().decode())}

    with pytest.raises(InvalidToken):
        await PasswordManager.decrypt(hass, data, "entry")


@pytest.mark.usefixtures("encryption_key")
@pytest.mark.parametrize("password", [None, ""])
async def test_empty_password_is_left_alone(
    hass: HomeAssistant, password: str | None
) -> None:
    """Missing passwords are neither encrypted nor decrypted."""
    data = {CONF_PASSWORD: password}

    await PasswordManager.decrypt(hass, data, "entry")
    assert data[CONF_PASSWORD] == password

    await PasswordManager.encrypt(hass, {})
