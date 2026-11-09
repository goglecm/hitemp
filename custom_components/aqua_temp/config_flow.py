"""Config flow to configure."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback

from .common.consts import DOMAIN
from .managers.flow_manager import IntegrationFlowManager

_LOGGER = logging.getLogger(__name__)


class DomainFlowHandler(ConfigFlow, domain=DOMAIN):
    """Handle a domain config flow."""

    VERSION = 1
    MINOR_VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> DomainOptionsFlowHandler:
        """Get the options flow for this handler."""
        return DomainOptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        flow_manager = IntegrationFlowManager(self.hass, self)

        return await flow_manager.async_step(user_input)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]):
        """Start re-authentication after the cloud rejected the credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Ask for the new password."""
        flow_manager = IntegrationFlowManager(self.hass, self, self._get_reauth_entry())

        return await flow_manager.async_step_reauth(user_input)


class DomainOptionsFlowHandler(OptionsFlow):
    """Handle domain options."""

    async def async_step_init(self, user_input=None):
        """Manage the domain options."""
        flow_manager = IntegrationFlowManager(self.hass, self, self.config_entry)

        return await flow_manager.async_step(user_input)
