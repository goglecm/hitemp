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


def test_guide_covers_every_code() -> None:
    """The parameter guide documents every code of the parameter file."""
    guide = (DOCS / "HITEMP_PARAMETERS.md").read_text(encoding="utf-8")
    items = json.loads(
        (
            ROOT
            / "custom_components"
            / "aqua_temp"
            / "parameters"
            / f"entity_description.{HITEMP}.json"
        ).read_text(encoding="utf-8")
    )

    for item in items:
        assert f"| `{item['key']}` " in guide, item["key"]
