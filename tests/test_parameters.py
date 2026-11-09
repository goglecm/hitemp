"""Integrity checks for the per-product parameter files."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from homeassistant.components.climate import HVACMode
from homeassistant.const import Platform
import pytest

from custom_components.aqua_temp.common.api_types import API_TYPES, APIParam
from custom_components.aqua_temp.common.consts import PRODUCT_IDS

PARAMETERS = (
    Path(__file__).parent.parent / "custom_components" / "aqua_temp" / "parameters"
)

PRODUCTS_WITH_FILES = sorted(
    {
        match.group(1)
        for path in PARAMETERS.glob("*.json")
        if (match := re.match(r"(?:mapping|entity_description)\.(.+)\.json", path.name))
    }
)

ALLOWED_PLATFORMS = {
    None,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.NUMBER,
}


def _load(name: str) -> Any:
    return json.loads((PARAMETERS / name).read_text(encoding="utf-8"))


def _descriptions(product_id: str) -> list[dict[str, Any]]:
    return _load(f"entity_description.{product_id}.json")


def test_every_product_has_both_files() -> None:
    """Each product needs an entity description file and a mapping file."""
    for product_id in PRODUCTS_WITH_FILES:
        assert (PARAMETERS / f"entity_description.{product_id}.json").is_file()
        assert (PARAMETERS / f"mapping.{product_id}.json").is_file()


def test_products_with_files_are_requested_from_the_cloud() -> None:
    """The cloud only lists devices whose product ID is requested."""
    for product_id in PRODUCTS_WITH_FILES:
        assert product_id == "default" or product_id in PRODUCT_IDS


@pytest.mark.parametrize("api_type", API_TYPES)
def test_api_files_define_every_parameter(api_type: str) -> None:
    """Every API parameter used by the code is defined for each API type."""
    config = _load(f"api.{api_type}.json")

    for param in APIParam:
        assert str(param) in config, f"{param} missing in api.{api_type}.json"

    assert config["url"].startswith("https://")


@pytest.mark.parametrize("product_id", PRODUCTS_WITH_FILES)
def test_entity_descriptions_are_well_formed(product_id: str) -> None:
    """Keys are unique and every entry has a supported platform."""
    descriptions = _descriptions(product_id)
    keys = [item["key"] for item in descriptions]

    assert len(keys) == len(set(keys)), "duplicate protocol codes"

    for item in descriptions:
        assert item["key"]
        assert item["name"]
        assert item.get("platform") in ALLOWED_PLATFORMS, item


@pytest.mark.parametrize("product_id", PRODUCTS_WITH_FILES)
def test_number_descriptions_have_valid_ranges(product_id: str) -> None:
    """Writable parameters need a non-empty range and a positive step."""
    for item in _descriptions(product_id):
        if item.get("platform") != Platform.NUMBER:
            continue

        minimum = item["native_min_value"]
        maximum = item["native_max_value"]
        step = item["native_step"]

        assert isinstance(minimum, int | float), item
        assert isinstance(maximum, int | float), item
        assert minimum < maximum, item
        assert step > 0, item
        assert ((maximum - minimum) / step) == pytest.approx(
            round((maximum - minimum) / step)
        ), f"range of {item['key']} is not a multiple of its step"


@pytest.mark.parametrize("product_id", PRODUCTS_WITH_FILES)
def test_temperature_parameters_are_in_celsius(product_id: str) -> None:
    """Ranges of temperature parameters are written in °C and converted later."""
    for item in _descriptions(product_id):
        if item.get("device_class") in ("temperature", "temperature_delta"):
            assert item["unit_of_measurement"] == "°C", item


HITEMP = "1245226668902080512"

# Ranges confirmed from the HiTemp app. Only these may be written.
HITEMP_WRITABLE = {
    "R01": (38, 60, 1),
    "R03": (1, 20, 1),
    "R04": (0, 1, 1),
    "R05": (30, 90, 1),
    "R06": (0, 450, 1),
    "E01": (0, 1, 1),
    "E02": (-20, 20, 1),
    "E03": (0, 500, 1),
    "E04": (0, 500, 1),
    "H99": (0, 1, 1),
}
HITEMP_INSTALLER = {"E01", "E02", "E03", "E04", "H99"}


def test_hitemp_only_confirmed_parameters_are_writable() -> None:
    """Parameters whose range was not confirmed on the device are read-only."""
    numbers = {
        item["key"]: item
        for item in _descriptions(HITEMP)
        if item.get("platform") == Platform.NUMBER
    }

    assert set(numbers) == set(HITEMP_WRITABLE)

    for key, (minimum, maximum, step) in HITEMP_WRITABLE.items():
        item = numbers[key]
        assert (
            item["native_min_value"],
            item["native_max_value"],
            item["native_step"],
        ) == (minimum, maximum, step), key

        if key in HITEMP_INSTALLER:
            assert item["enabled_by_default"] is False, key
            assert item["entity_category"] == "config", key
        else:
            assert item.get("enabled_by_default", True) is True, key
            assert "entity_category" not in item, key


def test_hitemp_model_selection_is_read_only() -> None:
    """H98 selects the unit model and must never be written from Home Assistant."""
    h98 = next(item for item in _descriptions(HITEMP) if item["key"] == "H98")

    assert h98["platform"] == Platform.SENSOR
    assert h98["name"] == "Model selection [H98]"


def test_hitemp_differences_use_temperature_delta() -> None:
    """Hysteresis and superheat are temperature differences, not temperatures."""
    classes = {item["key"]: item.get("device_class") for item in _descriptions(HITEMP)}

    for key in ("R03", "R18", "N03", "N08", "E02"):
        assert classes[key] == "temperature_delta", key


@pytest.mark.parametrize("product_id", PRODUCTS_WITH_FILES)
def test_mapping_codes_are_fetched(product_id: str) -> None:
    """Every protocol code used by the climate mapping must be requested."""
    mapping = _load(f"mapping.{product_id}.json")
    fetched = {item["key"] for item in _descriptions(product_id)}

    referenced = [
        mapping[key]
        for key in ("mode", "power", "temperature", "fan", "current_temperature")
    ]
    for mode in mapping["hvac_modes"].values():
        referenced.extend(
            mode[key]
            for key in ("target", "minimum", "maximum")
            if mode.get(key) is not None
        )

    for code in referenced:
        assert code in fetched, f"{code} is used by the mapping but never fetched"


@pytest.mark.parametrize("product_id", PRODUCTS_WITH_FILES)
def test_mapping_modes_are_consistent(product_id: str) -> None:
    """Mode values must be unique so the reverse mapping is unambiguous."""
    mapping = _load(f"mapping.{product_id}.json")
    hvac_modes = mapping["hvac_modes"]

    assert HVACMode.OFF in hvac_modes
    for mode in hvac_modes:
        HVACMode(mode)

    set_values = [mode["set"] for mode in hvac_modes.values()]
    assert len(set_values) == len(set(set_values))
    assert hvac_modes[HVACMode.OFF]["set"] is None
    for name, mode in hvac_modes.items():
        if name != HVACMode.OFF:
            assert mode["set"] is not None
            assert mode["target"] is not None

    fan_values = list(mapping["fan_modes"].values())
    assert fan_values
    assert len(fan_values) == len(set(fan_values))
