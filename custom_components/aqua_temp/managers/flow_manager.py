"""Config flow to configure."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import ClientError
from cryptography.fernet import InvalidToken
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowHandler

from ..common.consts import (
    CONF_API_TYPE,
    CONF_LIVE_DATA,
    CONF_TITLE,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    HITEMP_GUIDE_URL,
    INVALID_TOKEN_SECTION,
)
from ..models.config_data import ConfigData
from ..models.exceptions import (
    CloudConnectionError,
    CloudError,
    InvalidCredentialsError,
    LoginError,
)
from .aqua_temp_api import AquaTempAPI
from .aqua_temp_config_manager import AquaTempConfigManager
from .password_manager import PasswordManager

_LOGGER = logging.getLogger(__name__)

ERROR_INVALID_CREDENTIALS = "invalid_credentials"
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_CORRUPTED_ENCRYPTION_KEY = "corrupted_encryption_key"
ERROR_UNKNOWN = "unknown"


class IntegrationFlowManager:
    _hass: HomeAssistant
    _entry: ConfigEntry | None

    _flow_handler: FlowHandler
    _flow_id: str

    def __init__(
        self,
        hass: HomeAssistant,
        flow_handler: FlowHandler,
        entry: ConfigEntry | None = None,
    ):
        self._hass = hass
        self._flow_handler = flow_handler
        self._entry = entry
        self._flow_id = "user" if entry is None else "init"

    async def async_step(self, user_input: dict | None = None):
        """Show and handle the account form of the user and options flows."""
        _LOGGER.info(f"Config flow started, Step: {self._flow_id}")

        form_errors = None

        if user_input is None:
            user_input = self._current_settings()

        else:
            credentials = dict(user_input)
            error_key = None

            if self._entry is None:
                # Before logging in: a second login would end the session of
                # the entry already using this account
                await self._async_abort_if_configured(credentials)

            elif not credentials.get(CONF_PASSWORD):
                try:
                    credentials[CONF_PASSWORD] = await self._async_stored_password()
                except InvalidToken:
                    error_key = ERROR_CORRUPTED_ENCRYPTION_KEY

            if error_key is None:
                error_key = await self._async_validate(credentials)

            if error_key is None:
                if self._entry is None:
                    return await self._async_create_entry(credentials)

                return await self._async_update_entry(credentials)

            form_errors = {"base": error_key}

            _LOGGER.warning(f"Failed to validate the account, Error Key: {error_key}")

        schema = ConfigData.default_schema(
            user_input, password_required=self._entry is None
        )

        return self._flow_handler.async_show_form(
            step_id=self._flow_id,
            data_schema=schema,
            errors=form_errors,
            description_placeholders={
                "invalid_token_url": INVALID_TOKEN_SECTION,
                "guide_url": HITEMP_GUIDE_URL,
            },
        )

    async def async_step_reauth(self, user_input: dict | None = None):
        """Ask for a new password after the cloud rejected the stored one."""
        entry = self._entry
        form_errors = None

        if user_input is not None:
            credentials = {
                CONF_USERNAME: entry.data.get(CONF_USERNAME),
                CONF_API_TYPE: entry.data.get(CONF_API_TYPE),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }

            error_key = await self._async_validate(credentials)

            if error_key is None:
                data = {**entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}

                await PasswordManager.encrypt(self._hass, data)

                return self._flow_handler.async_update_reload_and_abort(
                    entry, data=data
                )

            form_errors = {"base": error_key}

        return self._flow_handler.async_show_form(
            step_id="reauth_confirm",
            data_schema=ConfigData.password_schema(),
            errors=form_errors,
            description_placeholders={
                "username": entry.data.get(CONF_USERNAME),
                "invalid_token_url": INVALID_TOKEN_SECTION,
            },
        )

    def _current_settings(self) -> dict[str, Any]:
        if self._entry is None:
            return {}

        config_data = ConfigData.from_dict(self._entry.data)

        return {
            CONF_TITLE: self._entry.title,
            CONF_USERNAME: self._entry.data.get(CONF_USERNAME),
            CONF_API_TYPE: config_data.api_type,
            CONF_LIVE_DATA: config_data.live_data,
            CONF_UPDATE_INTERVAL: config_data.update_interval,
        }

    async def _async_stored_password(self) -> str | None:
        data = {CONF_PASSWORD: self._entry.data.get(CONF_PASSWORD)}

        await PasswordManager.decrypt(self._hass, data, self._entry.entry_id)

        return data[CONF_PASSWORD]

    async def _async_validate(self, credentials: dict[str, Any]) -> str | None:
        """Log in with the credentials, returning an error key on failure."""
        config_manager = AquaTempConfigManager(self._hass, None)
        await config_manager.initialize(credentials)

        api = AquaTempAPI(self._hass, config_manager, auto_cleanup=False)

        try:
            await api.initialize(True)

        except InvalidCredentialsError:
            return ERROR_INVALID_CREDENTIALS

        except (
            LoginError,
            CloudConnectionError,
            CloudError,
            ClientError,
            TimeoutError,
        ) as ex:
            _LOGGER.warning(f"Cannot connect to the cloud, Error: {ex}")

            return ERROR_CANNOT_CONNECT

        except Exception:
            _LOGGER.exception("Unexpected error while validating the account")

            return ERROR_UNKNOWN

        finally:
            api.terminate()

        _LOGGER.debug("User inputs are valid")

        return None

    async def _async_abort_if_configured(self, credentials: dict[str, Any]) -> None:
        config_data = ConfigData.from_dict(credentials)

        await self._flow_handler.async_set_unique_id(config_data.unique_id)
        self._flow_handler._abort_if_unique_id_configured()  # noqa: SLF001

    async def _async_create_entry(self, credentials: dict[str, Any]):
        config_data = ConfigData.from_dict(credentials)

        data = self._entry_data(credentials, config_data)

        await PasswordManager.encrypt(self._hass, data)

        title = credentials.get(CONF_TITLE) or DEFAULT_NAME

        return self._flow_handler.async_create_entry(title=title, data=data)

    async def _async_update_entry(self, credentials: dict[str, Any]):
        entry = self._entry
        config_data = ConfigData.from_dict(credentials)

        data = self._entry_data(credentials, config_data)

        await PasswordManager.encrypt(self._hass, data, entry.entry_id)

        self._hass.config_entries.async_update_entry(
            entry,
            data=data,
            title=credentials.get(CONF_TITLE) or DEFAULT_NAME,
        )
        self._hass.config_entries.async_schedule_reload(entry.entry_id)

        return self._flow_handler.async_create_entry(data={})

    @staticmethod
    def _entry_data(
        credentials: dict[str, Any], config_data: ConfigData
    ) -> dict[str, Any]:
        return {
            CONF_USERNAME: credentials[CONF_USERNAME],
            CONF_PASSWORD: credentials[CONF_PASSWORD],
            CONF_API_TYPE: config_data.api_type,
            CONF_LIVE_DATA: config_data.live_data,
            CONF_UPDATE_INTERVAL: config_data.update_interval,
        }
