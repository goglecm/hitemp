"""The Aqua Temp / HiTemp heat pump integration."""

from __future__ import annotations

import logging

from cryptography.fernet import InvalidToken
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import slugify

from .common.consts import CONF_API_TYPE, DOMAIN, INVALID_TOKEN_SECTION
from .managers.aqua_temp_config_manager import (
    AquaTempConfigManager,
    load_disabled_by_default_number_keys,
)
from .managers.aqua_temp_coordinator import AquaTempCoordinator
from .managers.password_manager import PasswordManager
from .models.config_data import ConfigData

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


async def async_migrate_entry(hass: HomeAssistant, entry: AquaTempConfigEntry) -> None:
    """Migrate an entry created by an older version of the integration."""
    if entry.version == 1 and entry.minor_version < 2:
        await _async_disable_installer_parameters(hass, entry)

        data, options = _restore_api_type(entry)
        unique_id = entry.unique_id or _free_unique_id(hass, entry, data)

        hass.config_entries.async_update_entry(
            entry,
            data=data,
            options=options,
            unique_id=unique_id,
            minor_version=2,
        )

    _LOGGER.info(
        f"Migrated {entry.title} to version {entry.version}.{entry.minor_version}"
    )


def _restore_api_type(entry: AquaTempConfigEntry) -> tuple[dict, dict]:
    """Move the API type back into the entry data.

    Editing the options of older versions moved it into the options, where
    setup did not read it, so the default API was used after a restart.
    """
    data = dict(entry.data)
    options = dict(entry.options)

    if CONF_API_TYPE in options:
        api_type = options.pop(CONF_API_TYPE)

        if CONF_API_TYPE not in data:
            _LOGGER.warning(f"Restoring API type {api_type} of {entry.title}")

            data[CONF_API_TYPE] = api_type

    return data, options


def _free_unique_id(
    hass: HomeAssistant, entry: AquaTempConfigEntry, data: dict
) -> str | None:
    unique_id = ConfigData.from_dict(data).unique_id

    for other_entry in hass.config_entries.async_entries(DOMAIN):
        if other_entry is not entry and other_entry.unique_id == unique_id:
            return None

    return unique_id


async def _async_disable_installer_parameters(
    hass: HomeAssistant, entry: AquaTempConfigEntry
) -> None:
    """Disable writable installer parameters that existing installs have enabled.

    New installs create them disabled; this applies the same default to
    entities created before 4.0.0. Entities disabled by the user stay as they are.
    """
    keys = await hass.async_add_executor_job(load_disabled_by_default_number_keys)
    prefixes = tuple(slugify(f"{DOMAIN}_{Platform.NUMBER}_{key}") + "_" for key in keys)

    registry = er.async_get(hass)

    for registry_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        if (
            registry_entry.domain == Platform.NUMBER
            and registry_entry.disabled_by is None
            and registry_entry.unique_id.startswith(prefixes)
        ):
            _LOGGER.info(f"Disabling installer parameter {registry_entry.entity_id}")

            registry.async_update_entity(
                registry_entry.entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
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
