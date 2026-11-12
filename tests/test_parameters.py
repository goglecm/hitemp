"""Integrity checks for the per-product parameter files."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate import HVACMode
from homeassistant.components.number import NumberDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
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
    Platform.SELECT,
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
def test_device_classes_are_valid(product_id: str) -> None:
    """Device classes must exist for their platform; sensors compare them as enums."""
    device_classes = {
        Platform.SENSOR: SensorDeviceClass,
        Platform.BINARY_SENSOR: BinarySensorDeviceClass,
        Platform.NUMBER: NumberDeviceClass,
    }

    for item in _descriptions(product_id):
        if (device_class := item.get("device_class")) is not None:
            device_classes[item["platform"]](device_class)


@pytest.mark.parametrize("product_id", PRODUCTS_WITH_FILES)
def test_temperature_parameters_are_in_celsius(product_id: str) -> None:
    """Ranges of temperature parameters are written in °C and converted later."""
    for item in _descriptions(product_id):
        if item.get("device_class") in ("temperature", "temperature_delta"):
            assert item["unit_of_measurement"] == "°C", item


HITEMP = "1245226668902080512"

# Ranges and steps exactly as the HiTemp app offers them. Only these may be written.
HITEMP_NUMBERS = {
    "R01": (38, 60, 0.5),
    "R03": (1, 20, 0.5),
    "R05": (30, 90, 0.5),
    "R06": (0, 450, 1),
    "E02": (-20, 20, 0.5),
    "E03": (0, 500, 1),
    "E04": (0, 500, 1),
    "D01": (-30, 0, 0.5),
    "D02": (0, 30, 0.5),
    "D03": (30, 90, 1),
    "D04": (1, 20, 1),
    "D05": (1, 8, 1),
    "D07": (-10, 20, 0.5),
    "G01": (30, 70, 0.5),
    "G02": (0, 90, 1),
    "G03": (0, 23, 1),
    "G04": (1, 99, 1),
    "R08": (-20, 10, 0.5),
    "R09": (0, 30, 0.5),
    "R10": (10, 40, 0.5),
    "H32": (1, 255, 1),
}
HITEMP_SELECTS = {
    "R04": {"0": "NO", "1": "YES"},
    "M17": {"0": "Off", "1": "Low", "2": "High"},
    "E01": {"0": "Manual", "1": "Automatic"},
    "H99": {"0": "NO", "1": "YES"},
    "D06": {"0": "Standard", "1": "Economic", "2": "Intelligent"},
    "R07": {"0": "NO", "1": "YES"},
    "H01": {"0": "NO", "1": "YES"},
}
# Writable codes shown without enabling them first
HITEMP_DAILY = {"R01", "R03", "R04", "R05", "R06", "M17"}

# Every code the HiTemp app shows, by password level
HITEMP_APP_CODES = {
    "002 (user)": {
        *("E01", "E02", "E03", "E04", "H98", "H99"),
        *("R01", "R03", "R04", "R05", "R06"),
        *("T01", "T02", "T03", "T04", "T05", "T10", "O07"),
    },
    "066 (installer)": {
        *("/01", "/02", "E05", "H01", "H03", "H07", "H30", "H31", "H32"),
        *(f"D0{index}" for index in range(1, 8)),
        *(f"G0{index}" for index in range(1, 5)),
        *(f"N{index:02}" for index in range(1, 12)),
        *("R07", "R08", "R09", "R10", "R12", "R14", "R15"),
        *("R17", "R18", "R19", "R20"),
        *("S01", "S03", "S04", "S05", "S06"),
        *("O01", "O02", "O03", "O04", "O05", "O06", "O08", "O09"),
    },
    "App settings": {"M17"},
}
CONFIDENCE_LEVELS = {"documented", "observed", "uncertain"}


def _hitemp_items() -> dict[str, dict[str, Any]]:
    return {item["key"]: item for item in _descriptions(HITEMP)}


def test_hitemp_writable_parameters_match_the_app() -> None:
    """Only the well understood parameters are writable, with the app's ranges."""
    items = _hitemp_items()
    numbers = {key for key, item in items.items() if item["platform"] == "number"}
    selects = {key for key, item in items.items() if item["platform"] == "select"}

    assert numbers == set(HITEMP_NUMBERS)
    assert selects == set(HITEMP_SELECTS)

    for key, (minimum, maximum, step) in HITEMP_NUMBERS.items():
        item = items[key]
        assert (
            item["native_min_value"],
            item["native_max_value"],
            item["native_step"],
        ) == (minimum, maximum, step), key

    for key, options in HITEMP_SELECTS.items():
        assert items[key]["options"] == options, key

    for key in numbers | selects:
        item = items[key]
        if key in HITEMP_DAILY:
            assert item.get("enabled_by_default", True) is True, key
            assert item["entity_category"] is None, key
        else:
            assert item["enabled_by_default"] is False, key
            assert item["entity_category"] == "config", key


def test_hitemp_model_selection_is_read_only() -> None:
    """H98 selects the unit model and must never be written from Home Assistant."""
    h98 = _hitemp_items()["H98"]

    assert h98["platform"] == Platform.SENSOR
    assert h98["name"] == "H98 Model selection"
    assert h98["options"] == {"2": "0X08", "3": "0X18"}


def test_hitemp_every_app_code_is_described() -> None:
    """Every code from the app is present with its level and an explanation."""
    items = _hitemp_items()

    for level, codes in HITEMP_APP_CODES.items():
        for code in codes:
            item = items[code]
            assert item["level"] == level, code
            assert item["app_name"], code
            assert item["app_value"], code


def test_hitemp_entities_are_explained() -> None:
    """Exposed entities have a code-first name, a description and a confidence."""
    for key, item in _hitemp_items().items():
        if item["platform"] is None:
            assert item["description"], key
            continue

        assert item["confidence"] in CONFIDENCE_LEVELS, key
        assert item["description"], key

        if "difference_of" in item:
            first, second = item["difference_of"]
            assert item["name"].endswith(f"({first} - {second})"), key
        elif key != "Power":
            assert item["name"].startswith(f"{key} "), key


def test_hitemp_uncertain_parameters_are_opt_in() -> None:
    """Writable codes whose effect is not documented are hidden until enabled."""
    uncertain_writable = {
        key
        for key, item in _hitemp_items().items()
        if item["platform"] in ("number", "select")
        and item["confidence"] == "uncertain"
    }

    assert uncertain_writable == {"D07", "H99"}

    for key in uncertain_writable:
        assert _hitemp_items()[key]["enabled_by_default"] is False, key


def test_hitemp_options_use_raw_cloud_values() -> None:
    """Value labels are keyed by the whole-number raw value the cloud reports."""
    for key, item in _hitemp_items().items():
        for raw in item.get("options", {}):
            assert raw == str(int(raw)), key

        if "app_options" in item:
            assert item["options"] == {}, key


def test_hitemp_live_values_are_recorded_for_graphs() -> None:
    """Live readings keep long-term statistics; settings do not."""
    items = _hitemp_items()
    live = {"T01", "T02", "T03", "T04", "T05", "T06", "T10", "O07"}

    for key in live | {"superheat", "water_delta_t"}:
        assert items[key]["state_class"] == "measurement", key

    for key in ("O08", "O09"):
        assert items[key]["state_class"] == "total_increasing", key
        assert items[key]["device_class"] == "duration", key

    assert items["O07"]["unit_of_measurement"] == "steps"

    for key, item in items.items():
        if key not in live and item.get("state_class") == "measurement":
            assert "difference_of" in item, key


def test_hitemp_calculated_sensors_use_requested_codes() -> None:
    """Calculated sensors subtract codes that are requested from the cloud."""
    items = _hitemp_items()

    assert items["superheat"]["difference_of"] == ["T05", "T04"]
    assert items["water_delta_t"]["difference_of"] == ["T03", "T02"]

    for key in ("superheat", "water_delta_t"):
        for code in items[key]["difference_of"]:
            assert items[code]["platform"] == "sensor"


def test_hitemp_differences_use_temperature_delta() -> None:
    """Hysteresis and superheat are temperature differences, not temperatures."""
    classes = {item["key"]: item.get("device_class") for item in _descriptions(HITEMP)}

    for key in ("R03", "R18", "N03", "N08", "E02", "superheat", "water_delta_t"):
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
