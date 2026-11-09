"""Tests for the config, options and reauth flows."""

from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any
from unittest.mock import patch

from cryptography.fernet import Fernet
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.selector import TextSelector, TextSelectorType
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import (
    CONF_API_TYPE,
    CONF_TITLE,
    CONFIGURATION_FILE,
    DOMAIN,
)

from .conftest import ENCRYPTION_KEY, HITEMP_FIXTURE, PASSWORD, USERNAME, setup_entry
from .fake_cloud import FakeCloud, FakeDevice

USER_INPUT = {
    CONF_TITLE: "My Heat Pump",
    CONF_USERNAME: USERNAME,
    CONF_PASSWORD: PASSWORD,
    CONF_API_TYPE: "hi_temp",
}


def _decrypt(value: str, key: str = ENCRYPTION_KEY) -> str:
    return Fernet(key.encode()).decrypt(value.encode()).decode()


def _schema_keys(result: dict[str, Any]) -> dict[str, Any]:
    return {str(key): key for key in result["data_schema"].schema}


async def _start_user_flow(hass: HomeAssistant) -> dict[str, Any]:
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )


async def test_user_flow_creates_entry(
    hass: HomeAssistant,
    hass_storage: dict,
    fake_cloud: FakeCloud,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Valid credentials create an entry with an encrypted password."""
    caplog.set_level(logging.DEBUG)
    result = await _start_user_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    keys = _schema_keys(result)
    assert set(keys) == set(USER_INPUT)
    password_selector = result["data_schema"].schema[keys[CONF_PASSWORD]]
    assert isinstance(password_selector, TextSelector)
    assert password_selector.config["type"] == TextSelectorType.PASSWORD

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "My Heat Pump"
    assert result["result"].unique_id == f"hi_temp_{USERNAME}"
    data = result["data"]
    assert set(data) == {CONF_USERNAME, CONF_PASSWORD, CONF_API_TYPE}
    assert data[CONF_USERNAME] == USERNAME
    assert data[CONF_API_TYPE] == "hi_temp"

    key = hass_storage[CONFIGURATION_FILE]["data"]["key"]
    assert _decrypt(data[CONF_PASSWORD], key) == PASSWORD
    assert PASSWORD not in caplog.text

    # The session used to validate the account is released by the flow
    assert fake_cloud.sessions[0].connector is None


@pytest.mark.parametrize(
    ("cloud_setup", "error"),
    [
        (lambda cloud: None, "invalid_credentials"),
        (lambda cloud: setattr(cloud, "network_down", True), "cannot_connect"),
        (
            lambda cloud: setattr(
                cloud, "login_response", {"error_code": "500", "error_msg": "Busy"}
            ),
            "cannot_connect",
        ),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    cloud_setup: Callable[[FakeCloud], None],
    error: str,
) -> None:
    """Rejected credentials and cloud problems are reported separately."""
    cloud_setup(fake_cloud)
    result = await _start_user_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_PASSWORD: "wrong"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert result["description_placeholders"]["invalid_token_url"]
    assert _schema_keys(result)[CONF_USERNAME].default() == USERNAME
    assert "default" not in repr(_schema_keys(result)[CONF_PASSWORD].default)


@pytest.mark.usefixtures("fake_cloud")
async def test_user_flow_unexpected_error(hass: HomeAssistant) -> None:
    """Unexpected failures show a generic error instead of crashing the flow."""
    result = await _start_user_flow(hass)

    with patch(
        "custom_components.aqua_temp.managers.flow_manager.AquaTempAPI.initialize",
        side_effect=RuntimeError("boom"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], USER_INPUT
        )

    assert result["errors"] == {"base": "unknown"}


async def test_user_flow_rejects_duplicate_account(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """The same account cannot be added twice; its logins would kick each other out."""
    make_entry(unique_id=f"hi_temp_{USERNAME}")

    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_USERNAME: f" {USERNAME.upper()}"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert not fake_cloud.endpoint_requests("app/user/login")


@pytest.fixture
async def loaded_entry(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> MockConfigEntry:
    """Set up an entry with one device."""
    add_device(HITEMP_FIXTURE)
    entry = make_entry(title="Heat Pump", unique_id=f"hi_temp_{USERNAME}")
    await setup_entry(hass, entry)
    return entry


async def test_options_flow_shows_current_settings(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """The options form shows the settings but never the stored password."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    keys = _schema_keys(result)
    assert keys[CONF_TITLE].default() == "Heat Pump"
    assert keys[CONF_USERNAME].default() == USERNAME
    assert keys[CONF_API_TYPE].default() == "hi_temp"
    assert PASSWORD not in repr(result)


async def test_options_flow_keeps_password_and_api_type(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    loaded_entry: MockConfigEntry,
) -> None:
    """Saving the options without a password keeps the account working."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)
    fake_cloud.clear_requests()

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_TITLE: "Renamed", CONF_USERNAME: USERNAME, CONF_API_TYPE: "hi_temp"},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert loaded_entry.title == "Renamed"
    assert loaded_entry.options == {}
    assert loaded_entry.data[CONF_API_TYPE] == "hi_temp"
    assert _decrypt(loaded_entry.data[CONF_PASSWORD]) == PASSWORD
    assert loaded_entry.state is ConfigEntryState.LOADED
    # validated, then reloaded with the same credentials
    assert len(fake_cloud.endpoint_requests("app/user/login")) == 2


async def test_options_flow_changes_password(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    loaded_entry: MockConfigEntry,
) -> None:
    """A new password is validated, stored encrypted and used after the reload."""
    fake_cloud.add_account(USERNAME, "new password")
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TITLE: "Heat Pump",
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: "new password",
            CONF_API_TYPE: "hi_temp",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert _decrypt(loaded_entry.data[CONF_PASSWORD]) == "new password"
    assert loaded_entry.state is ConfigEntryState.LOADED


async def test_options_flow_rejects_invalid_password(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """A wrong new password is rejected and the stored one kept."""
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_TITLE: "Heat Pump",
            CONF_USERNAME: USERNAME,
            CONF_PASSWORD: "wrong",
            CONF_API_TYPE: "hi_temp",
        },
    )

    assert result["errors"] == {"base": "invalid_credentials"}
    assert _decrypt(loaded_entry.data[CONF_PASSWORD]) == PASSWORD


async def test_options_flow_reports_corrupted_key(
    hass: HomeAssistant,
    hass_storage: dict,
    loaded_entry: MockConfigEntry,
) -> None:
    """Keeping a password that cannot be decrypted shows the recovery steps."""
    hass_storage[CONFIGURATION_FILE]["data"]["key"] = Fernet.generate_key().decode()
    result = await hass.config_entries.options.async_init(loaded_entry.entry_id)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_TITLE: "Heat Pump", CONF_USERNAME: USERNAME, CONF_API_TYPE: "hi_temp"},
    )

    assert result["errors"] == {"base": "corrupted_encryption_key"}


async def test_rejected_password_starts_reauth(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A password changed in the app prompts for the new one and then resumes."""
    add_device(HITEMP_FIXTURE)
    fake_cloud.add_account(USERNAME, "changed in the app")
    entry = make_entry()

    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    flow = flows[0]
    assert flow["context"]["source"] == "reauth"

    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {CONF_PASSWORD: "still wrong"}
    )
    assert result["errors"] == {"base": "invalid_credentials"}
    assert result["description_placeholders"]["username"] == USERNAME

    result = await hass.config_entries.flow.async_configure(
        flow["flow_id"], {CONF_PASSWORD: "changed in the app"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert _decrypt(entry.data[CONF_PASSWORD]) == "changed in the app"
    assert entry.data[CONF_API_TYPE] == "hi_temp"
    assert entry.state is ConfigEntryState.LOADED


async def test_password_change_while_running_starts_reauth(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    loaded_entry: MockConfigEntry,
) -> None:
    """Polling stops and asks for the password once the cloud rejects it."""
    fake_cloud.add_account(USERNAME, "changed in the app")
    fake_cloud.expire_tokens()

    await loaded_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert [flow["context"]["source"] for flow in flows] == ["reauth"]
    assert not loaded_entry.runtime_data.last_update_success


async def test_cloud_outage_does_not_start_reauth(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    loaded_entry: MockConfigEntry,
) -> None:
    """Connection problems keep retrying instead of asking for the password."""
    fake_cloud.expire_tokens()
    fake_cloud.network_down = True

    await loaded_entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert not hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert not loaded_entry.runtime_data.last_update_success
