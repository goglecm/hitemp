"""The Aqua Temp / HiTemp heat pump integration."""

from __future__ import annotations

import logging

from cryptography.fernet import InvalidToken
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError

from .common.consts import DOMAIN, INVALID_TOKEN_SECTION
from .managers.aqua_temp_config_manager import AquaTempConfigManager
from .managers.aqua_temp_coordinator import AquaTempCoordinator
from .managers.password_manager import PasswordManager

_LOGGER = logging.getLogger(__name__)

type AquaTempConfigEntry = ConfigEntry[AquaTempCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: AquaTempConfigEntry) -> None:
    """Set up an Aqua Temp account."""
    entry_config = dict(entry.data)

    try:
        await PasswordManager.decrypt(hass, entry_config, entry.entry_id)
    except InvalidToken as ex:
        raise ConfigEntryError(
            translation_domain=DOMAIN,
            translation_key="corrupted_encryption_key",
            translation_placeholders={"invalid_token_url": INVALID_TOKEN_SECTION},
        ) from ex

    config_manager = AquaTempConfigManager(hass, entry)
    await config_manager.initialize(entry_config)

    coordinator = AquaTempCoordinator(hass, entry, config_manager)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry, config_manager.platforms
    )


async def async_unload_entry(hass: HomeAssistant, entry: AquaTempConfigEntry) -> None:
    """Unload an Aqua Temp account."""
    _LOGGER.info(f"Unloading {DOMAIN} integration, Entry ID: {entry.entry_id}")

    await hass.config_entries.async_unload_platforms_or_raise(
        entry, entry.runtime_data.config_manager.platforms
    )


async def async_remove_entry(hass: HomeAssistant, entry: AquaTempConfigEntry) -> None:
    """Delete the stored preferences of a removed account."""
    config_manager = AquaTempConfigManager(hass, entry)

    await config_manager.remove(entry.entry_id)
