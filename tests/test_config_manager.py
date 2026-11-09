"""Tests for the configuration manager."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_TEMPERATURE_UNIT,
    CONF_USERNAME,
    Platform,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.api_types import APIParam
from custom_components.aqua_temp.common.consts import (
    API_STATUS,
    CONF_API_TYPE,
    CONFIGURATION_FILE,
    DOMAIN,
    LAST_ERROR,
)
from custom_components.aqua_temp.managers.aqua_temp_config_manager import (
    AquaTempConfigManager,
)

HITEMP = "1245226668902080512"
AQUATEMP = "1442284873216843776"
GENERIC = "1132174963097280512"


async def _manager(
    hass: HomeAssistant, api_type: str | None = "hi_temp", entry=None
) -> AquaTempConfigManager:
    data = {CONF_USERNAME: "user", CONF_PASSWORD: "pass"}
    if api_type is not None:
        data[CONF_API_TYPE] = api_type
    manager = AquaTempConfigManager(hass, entry)
    await manager.initialize(data)
    return manager


async def test_initialize_loads_all_platforms(hass: HomeAssistant) -> None:
    """Platforms come from the default descriptions and every product file."""
    manager = await _manager(hass)

    assert manager.is_initialized
    assert set(manager.platforms) == {
        Platform.BINARY_SENSOR,
        Platform.CLIMATE,
        Platform.NUMBER,
        Platform.SELECT,
        Platform.SENSOR,
    }


@pytest.mark.parametrize(
    ("api_type", "expected_type", "url"),
    [
        ("hi_temp", "hi_temp", "https://cloud.linked-go.com:449/crmservice/api"),
        ("aqua_temp", "aqua_temp", "https://cloud.linked-go.com:449/crmservice/api"),
        (
            "aqua_temp_old",
            "aqua_temp_old",
            "https://cloud.linked-go.com/cloudservice/api",
        ),
        ("2", "hi_temp", "https://cloud.linked-go.com:449/crmservice/api"),
        (None, "aqua_temp_old", "https://cloud.linked-go.com/cloudservice/api"),
    ],
)
async def test_api_type_selection(
    hass: HomeAssistant, api_type: str | None, expected_type: str, url: str
) -> None:
    """Legacy numeric API types are translated and the right file is loaded."""
    manager = await _manager(hass, api_type)

    assert manager.config_data.api_type == expected_type
    assert manager.get_api_param(APIParam.URL) == url


@pytest.mark.parametrize(
    ("product_id", "mode_code", "current_code"),
    [
        (HITEMP, "mode_real", "T10"),
        (AQUATEMP, "Mode", "T2"),
        (GENERIC, "Mode", "T02"),
        ("unknown", "Mode", "T02"),
    ],
)
async def test_device_mapping_falls_back_to_default(
    hass: HomeAssistant, product_id: str, mode_code: str, current_code: str
) -> None:
    """Products without their own files use the default mapping."""
    manager = await _manager(hass)

    manager.set_device("dev", product_id)

    assert manager.get_pc_key("dev", "mode") == mode_code
    assert manager.get_pc_key("dev", "current_temperature") == current_code
    assert manager.get_entity_descriptions("dev")


async def test_hitemp_modes(hass: HomeAssistant) -> None:
    """HiTemp only heats and has an off/low/high fan."""
    manager = await _manager(hass)
    manager.set_device("dev", HITEMP)

    assert list(manager.get_hvac_modes("dev")) == [HVACMode.OFF, HVACMode.HEAT]
    assert manager.get_fan_modes("dev") == {"off": "0", "low": "1", "high": "2"}
    assert manager.get_hvac_reverse_mapping("dev", "2") == HVACMode.HEAT
    assert manager.get_hvac_reverse_mapping("dev", None) == HVACMode.OFF
    assert manager.get_fan_reverse_mapping("dev", "2") == "high"
    assert manager.get_hvac_mode_pc_key("dev", HVACMode.HEAT, "target") == "R01"


async def test_aquatemp_modes(hass: HomeAssistant) -> None:
    """AquaTemp cools, heats and runs in auto with per-mode limits."""
    manager = await _manager(hass)
    manager.set_device("dev", AQUATEMP)

    assert list(manager.get_hvac_modes("dev")) == [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.AUTO,
    ]
    assert manager.get_fan_modes("dev") == {"auto": "0", "low": "1"}
    assert manager.get_hvac_mode_pc_key("dev", HVACMode.COOL, "minimum") == "R08"
    assert manager.get_hvac_mode_pc_key("dev", HVACMode.HEAT, "maximum") == "R11"


async def test_protocol_codes_exclude_virtual_entities(hass: HomeAssistant) -> None:
    """Only real protocol codes are requested from the cloud."""
    manager = await _manager(hass)
    manager.set_device("dev", HITEMP)

    codes = manager.get_supported_protocol_codes("dev")

    for code in ("Power", "mode_real", "M17", "R01", "T10"):
        assert code in codes
    for virtual in (API_STATUS, LAST_ERROR, "temperature_unit", "is_fault"):
        assert virtual not in codes


async def test_temperature_unit_is_persisted(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """The temperature unit choice survives a restart."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="entry1")
    manager = await _manager(hass, entry=entry)

    assert manager.get_temperature_unit("dev") == UnitOfTemperature.CELSIUS

    await manager.update_temperature_unit("dev", UnitOfTemperature.FAHRENHEIT)

    stored = hass_storage[CONFIGURATION_FILE]["data"]["entry1"]
    assert stored[CONF_TEMPERATURE_UNIT] == {"dev": UnitOfTemperature.FAHRENHEIT}

    reloaded = await _manager(hass, entry=entry)
    assert reloaded.get_temperature_unit("dev") == UnitOfTemperature.FAHRENHEIT


async def test_remove_deletes_entry_storage(
    hass: HomeAssistant, hass_storage: dict[str, Any]
) -> None:
    """Removing an entry deletes its stored preferences only."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="entry1")
    manager = await _manager(hass, entry=entry)
    await manager.update_temperature_unit("dev", UnitOfTemperature.FAHRENHEIT)
    hass_storage[CONFIGURATION_FILE]["data"]["other"] = {CONF_TEMPERATURE_UNIT: {}}

    await manager.remove("entry1")

    data = hass_storage[CONFIGURATION_FILE]["data"]
    assert "entry1" not in data
    assert "other" in data


async def test_entity_name_uses_device_and_translation(hass: HomeAssistant) -> None:
    """Entity names are the device name followed by the parameter name."""
    manager = await _manager(hass)
    manager.set_device("dev", HITEMP)
    descriptions = {d.key: d for d in manager.get_entity_descriptions("dev")}

    device_info = {"name": "Hot Water"}

    assert (
        manager.get_entity_name(descriptions[API_STATUS], device_info)
        == "Hot Water API Status"
    )
    assert manager.get_entity_name(descriptions["Mode"], device_info).startswith(
        "Hot Water"
    )
