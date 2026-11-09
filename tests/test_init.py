"""Tests for setting up, unloading and removing the integration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
import importlib
from typing import Any
from unittest.mock import patch

from cryptography.fernet import Fernet
from homeassistant import config_entries
from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntity,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_TEMPERATURE_UNIT,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    deprecation,
    device_registry as dr,
    entity_registry as er,
    frame,
)
from homeassistant.util import dt as dt_util, slugify
import pytest
from pytest_homeassistant.common import MockConfigEntry, async_fire_time_changed

from custom_components.aqua_temp.common.consts import CONFIGURATION_FILE, DOMAIN
from custom_components.aqua_temp.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)
from custom_components.aqua_temp.managers.aqua_temp_coordinator import (
    AquaTempCoordinator,
)

from .conftest import (
    AQUATEMP_FIXTURE,
    HITEMP_FIXTURE,
    encrypt,
    entity_id,
    setup_entry,
)
from .fake_cloud import FakeCloud, FakeDevice


async def test_setup_creates_entities(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A loaded entry exposes the devices found during the first refresh."""
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry()

    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, AquaTempCoordinator)
    assert hass.states.get(entity_id(hass, "climate", "Mode", device.code))
    assert hass.states.get(entity_id(hass, "sensor", "T02", device.code))


@pytest.mark.usefixtures("encryption_key")
async def test_setup_retries_when_cloud_is_unreachable(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A cloud outage at start-up is retried instead of failing permanently."""
    add_device(HITEMP_FIXTURE)
    fake_cloud.network_down = True
    entry = make_entry()

    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_RETRY

    fake_cloud.network_down = False
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=10))
    await hass.async_block_till_done(wait_background_tasks=True)

    assert entry.state is ConfigEntryState.LOADED


async def test_setup_fails_with_corrupted_key(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A password that cannot be decrypted stops the setup with an error."""
    entry = make_entry()
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            "password": encrypt("secret", Fernet.generate_key().decode()),
        },
    )

    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.SETUP_ERROR
    assert "encryption key" in entry.reason
    assert not fake_cloud.requests


async def test_unload_keeps_preferences_and_remove_deletes_them(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Reloading keeps the temperature unit; removing the entry deletes it."""
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry()
    await setup_entry(hass, entry)
    await entry.runtime_data.set_temperature_unit(
        device.code, UnitOfTemperature.FAHRENHEIT
    )

    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    stored = hass_storage[CONFIGURATION_FILE]["data"][entry.entry_id]
    assert stored[CONF_TEMPERATURE_UNIT] == {device.code: UnitOfTemperature.FAHRENHEIT}

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.entry_id not in hass_storage[CONFIGURATION_FILE]["data"]
    assert hass_storage[CONFIGURATION_FILE]["data"]["key"]


async def test_new_device_is_added_after_relogin(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Devices added to the account later appear without a reload."""
    add_device(HITEMP_FIXTURE)
    entry = make_entry()
    await setup_entry(hass, entry)

    pool = add_device(AQUATEMP_FIXTURE)
    fake_cloud.expire_tokens()
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(entity_id(hass, "climate", "Mode", pool.code))


async def test_migration_disables_installer_parameters(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Existing installs get the new opt-in default for installer parameters."""
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry(minor_version=1)
    registry = er.async_get(hass)

    def register(platform: str, key: str, disabled_by=None) -> str:
        return registry.async_get_or_create(
            platform,
            DOMAIN,
            slugify(f"{DOMAIN}_{platform}_{key}_{device.code}"),
            config_entry=entry,
            disabled_by=disabled_by,
        ).entity_id

    e01 = register("number", "E01")
    h99 = register("number", "H99")
    e02 = register("number", "E02", er.RegistryEntryDisabler.USER)
    r01 = register("number", "R01")
    e01_sensor = register("sensor", "E01")

    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert (entry.version, entry.minor_version) == (1, 2)
    integration = er.RegistryEntryDisabler.INTEGRATION
    assert registry.async_get(e01).disabled_by is integration
    assert registry.async_get(h99).disabled_by is integration
    assert registry.async_get(e02).disabled_by is er.RegistryEntryDisabler.USER
    assert registry.async_get(r01).disabled_by is None
    assert registry.async_get(e01_sensor).disabled_by is None
    assert hass.states.get(r01).state == "50.0"


async def test_migration_restores_api_type_from_options(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Entries whose API type was moved to the options by older versions recover."""
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry(api_type=None, minor_version=1, options={"api_type": "hi_temp"})

    await setup_entry(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert entry.data["api_type"] == "hi_temp"
    assert entry.options == {}
    assert entry.unique_id == "hi_temp_owner@example.com"
    assert fake_cloud.requests[0].style == "camel"
    assert hass.states.get(entity_id(hass, "climate", "Mode", device.code))


async def test_migration_skips_unique_id_already_in_use(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A duplicate account keeps working but gets no unique ID."""
    make_entry(unique_id="hi_temp_owner@example.com")
    entry = make_entry(minor_version=1)

    await setup_entry(hass, entry)

    assert entry.minor_version == 2
    assert entry.unique_id is None


class _ClimateUsingDeprecatedAttribute(ClimateEntity):
    """Entity used to prove the deprecation spy works."""

    def __init__(self) -> None:
        self._attr_target_temperature = 20


@pytest.fixture
def deprecation_reports() -> Any:
    """Record every deprecated Home Assistant API use, ignoring de-duplication."""
    reports: list[str] = []
    original_member_report = deprecation._DeprecatedEntityMember._report_usage
    original_report = frame._report_usage

    def entity_member_spy(self, instance: object, action: str) -> None:
        reports.append(f"{action} {type(instance).__name__}.{self.name}")
        original_member_report(self, instance, action)

    def constant_spy(obj_name: str, module_name: str, *args, **kwargs) -> None:
        reports.append(f"constant {module_name}.{obj_name}")

    def report_spy(hass: HomeAssistant, what: str, **kwargs: Any) -> None:
        # Every frame.report_usage call ends here, however it was imported
        integration_frame = kwargs.get("integration_frame")
        if kwargs.get("integration_domain") == DOMAIN or (
            integration_frame is not None and integration_frame.integration == DOMAIN
        ):
            reports.append(what)
        original_report(hass, what, **kwargs)

    with (
        patch.object(
            deprecation._DeprecatedEntityMember, "_report_usage", entity_member_spy
        ),
        patch.object(deprecation, "_print_deprecation_warning_internal", constant_spy),
        patch.object(frame, "_report_usage", report_spy),
    ):
        yield reports


async def test_deprecation_spy_detects_usage(
    hass: HomeAssistant, deprecation_reports: list[str]
) -> None:
    """The spy catches every kind of usage report Home Assistant raises."""
    _ClimateUsingDeprecatedAttribute()
    _ = config_entries.CONN_CLASS_LOCAL_POLL
    frame.report_usage(
        "uses something deprecated",
        integration_domain=DOMAIN,
        core_behavior=frame.ReportBehavior.LOG,
    )

    assert deprecation_reports == [
        "writes _ClimateUsingDeprecatedAttribute._attr_target_temperature",
        "constant homeassistant.config_entries.CONN_CLASS_LOCAL_POLL",
        "uses something deprecated",
    ]


async def test_no_deprecated_home_assistant_usage(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    deprecation_reports: list[str],
) -> None:
    """Loading and using the integration touches no deprecated HA API."""
    from custom_components.aqua_temp import config_flow  # noqa: PLC0415

    importlib.reload(config_flow)

    hitemp = add_device(HITEMP_FIXTURE)
    pool = add_device(AQUATEMP_FIXTURE)
    entry = make_entry()
    await setup_entry(hass, entry)

    for device in (hitemp, pool):
        climate = entity_id(hass, "climate", "Mode", device.code)
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_TEMPERATURE,
            {ATTR_ENTITY_ID: climate, ATTR_TEMPERATURE: 40},
            blocking=True,
        )
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_HVAC_MODE,
            {ATTR_ENTITY_ID: climate, ATTR_HVAC_MODE: HVACMode.HEAT},
            blocking=True,
        )
        await hass.services.async_call(
            CLIMATE_DOMAIN,
            SERVICE_SET_FAN_MODE,
            {ATTR_ENTITY_ID: climate, ATTR_FAN_MODE: "low"},
            blocking=True,
        )

    await entry.runtime_data.async_refresh()
    for device in (hitemp, pool):
        state = hass.states.get(entity_id(hass, "climate", "Mode", device.code))
        assert state.attributes[ATTR_TEMPERATURE] == 40

    await async_get_config_entry_diagnostics(hass, entry)
    device_entry = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, hitemp.device_id), entry.entry_id
    )
    await async_get_device_diagnostics(hass, entry, device_entry)

    assert await hass.config_entries.async_unload(entry.entry_id)

    assert deprecation_reports == []
