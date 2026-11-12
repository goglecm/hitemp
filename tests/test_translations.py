"""Checks for the translation files."""

from __future__ import annotations

import json
from pathlib import Path

INTEGRATION = Path(__file__).parent.parent / "custom_components" / "aqua_temp"


def test_english_translation_matches_strings() -> None:
    """translations/en.json must be generated from strings.json."""
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    english = json.loads(
        (INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")
    )

    assert strings == english


def test_hitemp_entity_names_match_the_parameter_file() -> None:
    """The translated names of the HiTemp entities are the parameter file names."""
    product = "1245226668902080512"
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    items = json.loads(
        (INTEGRATION / "parameters" / f"entity_description.{product}.json").read_text(
            encoding="utf-8"
        )
    )

    expected = {
        (item["platform"], f"{product}_{item['key']}".replace("/", "").lower()): item[
            "name"
        ]
        for item in items
        if item["platform"] is not None
    }
    translated = {
        (platform, key): value["name"]
        for platform, entries in strings["entity"].items()
        for key, value in entries.items()
        if key.startswith(product)
    }

    assert translated == expected


def test_config_and_options_flows_share_errors() -> None:
    """Both flows show the same form, so they need the same error texts."""
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))

    assert strings["config"]["error"] == strings["options"]["error"]
