"""Checks that the documentation matches the integration."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant.common import MockConfigEntry
import yaml

from .conftest import HITEMP_FIXTURE, setup_entry
from .fake_cloud import FakeDevice

ROOT = Path(__file__).parent.parent
DOCS = ROOT / "docs"
HITEMP = "1245226668902080512"


def _dashboard_entities(node: Any) -> set[str]:
    """Return every entity ID a dashboard configuration refers to."""
    found: set[str] = set()

    if isinstance(node, dict):
        for key, value in node.items():
            if key == "entity" and isinstance(value, str):
                found.add(value)
            elif key == "entities":
                for item in value:
                    found |= (
                        {item} if isinstance(item, str) else _dashboard_entities(item)
                    )
            else:
                found |= _dashboard_entities(value)

    elif isinstance(node, list):
        for item in node:
            found |= _dashboard_entities(item)

    return found


@pytest.mark.usefixtures("fake_cloud", "entity_registry_enabled_by_default")
async def test_dashboard_entities_exist(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Every entity of the example dashboard exists for a heat pump named Heat Pump."""
    device = add_device(HITEMP_FIXTURE)
    device.nickname = "Heat Pump"
    await setup_entry(hass, make_entry())

    dashboard = yaml.safe_load((DOCS / "hitemp-dashboard.yaml").read_text())
    entities = _dashboard_entities(dashboard)
    registry = er.async_get(hass)

    assert entities
    for entity in sorted(entities):
        assert registry.async_get(entity) is not None, entity


def _hitemp_items() -> list[dict[str, Any]]:
    return json.loads(
        (
            ROOT
            / "custom_components"
            / "aqua_temp"
            / "parameters"
            / f"entity_description.{HITEMP}.json"
        ).read_text(encoding="utf-8")
    )


def _guide_code_rows() -> list[dict[str, str]]:
    """Return the rows of the guide tables whose first column is the code."""
    rows = []
    header: list[str] | None = None

    for line in (
        (DOCS / "HITEMP_PARAMETERS.md").read_text(encoding="utf-8").splitlines()
    ):
        if not line.startswith("|"):
            header = None
            continue

        cells = [cell.strip() for cell in line.strip()[1:-1].split("|")]

        if header is None:
            header = cells
        elif header[0] == "Code" and not set("".join(cells)) <= set("-: "):
            rows.append(dict(zip(header, cells, strict=True)))

    return rows


def _home_assistant_column(item: dict[str, Any]) -> str:
    """Describe an entity the way the guide's Home Assistant column does."""
    platform = item["platform"]
    if platform is None:
        return "requested, no entity"

    controls = platform in ("number", "select")
    category = item.get("entity_category", None if controls else "diagnostic")
    section = {
        "diagnostic": "Diagnostic",
        "config": "Configuration",
        None: "Controls" if controls else "Sensors",
    }[category]
    disabled = ", disabled" if item.get("enabled_by_default", True) is False else ""

    return f"{platform}, {section}{disabled}"


def test_guide_tables_match_the_parameter_file() -> None:
    """Guide tables give each entity's name, platform, section, default and confidence."""
    items = {item["key"]: item for item in _hitemp_items()}
    checked = set()

    for row in _guide_code_rows():
        key = row["Code"].strip("`")
        item = items.get(key)
        if item is None:
            continue

        checked.add(key)
        name = row.get("Name in Home Assistant", row.get("Name"))
        if name is not None:
            assert name == item["name"], key
        if "Home Assistant" in row:
            assert row["Home Assistant"] == _home_assistant_column(item), key
        if "Confidence" in row:
            assert row["Confidence"] == (item.get("confidence") or ""), key

    exposed = {key for key, item in items.items() if item["platform"] is not None}
    assert exposed <= checked


def test_guide_covers_every_code() -> None:
    """The parameter guide documents every code of the parameter file."""
    guide = (DOCS / "HITEMP_PARAMETERS.md").read_text(encoding="utf-8")
    items = _hitemp_items()

    for item in items:
        assert f"| `{item['key']}` " in guide, item["key"]

    for item in items:
        for source in item.get("source", []):
            assert f"`{source}`" in guide, source
