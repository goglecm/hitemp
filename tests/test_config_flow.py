"""Tests for the config and options flows."""

from __future__ import annotations

from collections.abc import Callable

from cryptography.fernet import Fernet
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import (
    CONF_API_TYPE,
    CONF_TITLE,
    CONFIGURATION_FILE,
    DOMAIN,
)

from .conftest import PASSWORD, USERNAME
from .fake_cloud import FakeCloud

USER_INPUT = {
    CONF_TITLE: "My Heat Pump",
    CONF_USERNAME: USERNAME,
    CONF_PASSWORD: PASSWORD,
    CONF_API_TYPE: "hi_temp",
}


async def test_user_flow_creates_entry(
    hass: HomeAssistant, hass_storage: dict, fake_cloud: FakeCloud
) -> None:
    """Valid credentials create an entry with an encrypted password."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert {str(key) for key in result["data_schema"].schema} == set(USER_INPUT)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Heat Pump"
    data = result["data"]
    assert data[CONF_USERNAME] == USERNAME
    assert data[CONF_API_TYPE] == "hi_temp"
    assert CONF_TITLE not in data

    key = hass_storage[CONFIGURATION_FILE]["data"]["key"]
    assert Fernet(key.encode()).decrypt(data[CONF_PASSWORD].encode()) == (
        PASSWORD.encode()
    )


async def test_user_flow_invalid_credentials(
    hass: HomeAssistant, fake_cloud: FakeCloud
) -> None:
    """Rejected credentials show an error and keep the form open."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_PASSWORD: "wrong"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_credentials"}


@pytest.mark.usefixtures("fake_cloud")
async def test_options_flow_shows_current_settings(
    hass: HomeAssistant, make_entry: Callable[..., MockConfigEntry]
) -> None:
    """The options form opens with the entry's current settings."""
    entry = make_entry(title="Heat Pump")

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    defaults = {str(key): key.default() for key in result["data_schema"].schema}
    assert defaults[CONF_TITLE] == "Heat Pump"
    assert defaults[CONF_USERNAME] == USERNAME
    assert defaults[CONF_API_TYPE] == "hi_temp"
