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


def test_config_and_options_flows_share_errors() -> None:
    """Both flows show the same form, so they need the same error texts."""
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))

    assert strings["config"]["error"] == strings["options"]["error"]
