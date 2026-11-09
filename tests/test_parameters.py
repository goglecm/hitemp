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
