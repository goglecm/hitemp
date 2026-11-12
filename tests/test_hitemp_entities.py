"""Tests for how the HiTemp parameters are exposed."""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.components.climate import ATTR_FAN_MODE
from homeassistant.components.select import (
    ATTR_OPTION,
    ATTR_OPTIONS,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.sensor import (
    ATTR_STATE_CLASS,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant.common import MockConfigEntry

from custom_components.aqua_temp.common.consts import CONF_LIVE_DATA
from custom_components.aqua_temp.common.utils import parse_bitword
from custom_components.aqua_temp.number import AquaTempNumberEntity
from custom_components.aqua_temp.select import AquaTempParameterSelectEntity
from custom_components.aqua_temp.sensor import AquaTempSensorEntity

from .conftest import HITEMP_FIXTURE, entity_id, setup_entry
from .fake_cloud import FakeCloud, FakeDevice

STATIC_ATTRIBUTES = {
    "code",
    "app_name",
    "level",
    "range",
    "app_value",
    "confidence",
    "description",
    "guidance",
}


async def _setup(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
    **data: str | None,
) -> FakeDevice:
    device = add_device(HITEMP_FIXTURE)
    device.data.update(data)
    await setup_entry(hass, make_entry())
    return device


async def _select(hass: HomeAssistant, entity: str, option: str) -> None:
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: entity, ATTR_OPTION: option},
        blocking=True,
    )


@pytest.mark.usefixtures("fake_cloud")
async def test_names_start_with_the_code(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Entity names lead with the code, followed by a short description."""
    device = await _setup(hass, add_device, make_entry)

    assert hass.states.get(entity_id(hass, "number", "R01", device.code)).name == (
        "Hot Water R01 Target water temperature"
    )
    assert hass.states.get(entity_id(hass, "sensor", "O07", device.code)).name == (
        "Hot Water O07 EEV position"
    )


@pytest.mark.usefixtures("fake_cloud")
async def test_parameters_explain_themselves(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Each parameter carries its app name, level, range and guidance."""
    device = await _setup(hass, add_device, make_entry)

    attributes = hass.states.get(
        entity_id(hass, "number", "R01", device.code)
    ).attributes

    assert attributes["code"] == "R01"
    assert attributes["app_name"] == "Target temp"
    assert attributes["level"] == "002 (user)"
    assert attributes["range"] == "38.0C to 60.0C, steps of 0.5C"
    assert attributes["confidence"] == "documented"
    assert "R03" in attributes["guidance"]

    superheat = hass.states.get(entity_id(hass, "sensor", "superheat", device.code))
    assert superheat.attributes["calculated_from"] == "T05 - T04"
    assert "code" not in superheat.attributes


def test_explanations_are_not_recorded() -> None:
    """The static explanation is kept out of the recorder database."""
    for entity_class in (
        AquaTempSensorEntity,
        AquaTempNumberEntity,
        AquaTempParameterSelectEntity,
    ):
        unrecorded = entity_class._Entity__combined_unrecorded_attributes
        assert STATIC_ATTRIBUTES | {"calculated_from"} <= unrecorded
        assert "raw_value" not in unrecorded


@pytest.mark.usefixtures("fake_cloud")
async def test_enum_sensor_shows_label_and_raw_value(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Codes with app labels read 'label (raw)', with every label as an option."""
    device = await _setup(hass, add_device, make_entry, H31="1")

    state = hass.states.get(entity_id(hass, "sensor", "H31", device.code))

    assert state.state == "DTU&WIFI (1)"
    assert state.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.ENUM
    assert state.attributes[ATTR_OPTIONS] == [
        "Centralized control (0)",
        "DTU&WIFI (1)",
    ]
    assert state.attributes["raw_value"] == "1"


@pytest.mark.usefixtures("fake_cloud")
async def test_values_the_app_does_not_list_are_shown_raw(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A raw value without a label is shown as such instead of being guessed."""
    device = await _setup(hass, add_device, make_entry, **{"/01": "1", "H98": "2"})

    out05 = hass.states.get(entity_id(hass, "sensor", "/01", device.code))
    assert out05.state == "1 (not listed in the app)"
    assert out05.attributes[ATTR_OPTIONS] == ["1 (not listed in the app)"]
    assert out05.attributes["app_options"] == ["Low speed", "Solar water pump"]

    assert hass.states.get(entity_id(hass, "sensor", "H98", device.code)).state == (
        "0X08 (2)"
    )


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_select_sends_the_raw_value(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Choosing an option writes the raw value the app uses for it."""
    device = await _setup(hass, add_device, make_entry, E01="0")
    select = entity_id(hass, "select", "E01", device.code)

    state = hass.states.get(select)
    assert state.state == "Manual (0)"
    assert state.attributes[ATTR_OPTIONS] == ["Manual (0)", "Automatic (1)"]

    await _select(hass, select, "Automatic (1)")

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": "E01", "value": "1"}]
    ]
    assert hass.states.get(select).state == "Automatic (1)"


@pytest.mark.usefixtures("fake_cloud", "entity_registry_enabled_by_default")
async def test_select_with_an_unlisted_value_is_unavailable(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """A select can't show a value outside its options, so it goes unavailable."""
    device = await _setup(hass, add_device, make_entry, D06="7", H01="")

    assert hass.states.get(entity_id(hass, "select", "D06", device.code)).state == (
        STATE_UNAVAILABLE
    )
    assert hass.states.get(entity_id(hass, "select", "H01", device.code)).state == (
        STATE_UNAVAILABLE
    )


async def test_fan_speed_select_matches_the_climate_fan_mode(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """M17 is written the same way as the climate entity's fan mode."""
    device = await _setup(hass, add_device, make_entry, M17="1")
    select = entity_id(hass, "select", "M17", device.code)

    assert hass.states.get(select).state == "Low (1)"

    await _select(hass, select, "High (2)")

    assert fake_cloud.control_requests() == [
        [{"deviceCode": device.code, "protocolCode": "M17", "value": "2"}]
    ]
    climate = hass.states.get(entity_id(hass, "climate", "Mode", device.code))
    assert climate.attributes[ATTR_FAN_MODE] == "high"


@pytest.mark.usefixtures("fake_cloud")
async def test_calculated_differences(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Superheat and water ΔT are differences of the reported temperatures."""
    device = await _setup(
        hass, add_device, make_entry, T02="29.0", T03="32.5", T04="0.5", T05="-4.0"
    )

    superheat = hass.states.get(entity_id(hass, "sensor", "superheat", device.code))
    assert float(superheat.state) == -4.5
    assert superheat.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT
    assert superheat.attributes[ATTR_DEVICE_CLASS] == (
        SensorDeviceClass.TEMPERATURE_DELTA
    )

    delta = hass.states.get(entity_id(hass, "sensor", "water_delta_t", device.code))
    assert float(delta.state) == 3.5


@pytest.mark.usefixtures("fake_cloud")
async def test_calculated_difference_needs_both_values(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Without one of the temperatures the difference is unavailable."""
    device = await _setup(hass, add_device, make_entry, T04="")

    assert hass.states.get(
        entity_id(hass, "sensor", "superheat", device.code)
    ).state == (STATE_UNAVAILABLE)


@pytest.mark.usefixtures("fake_cloud")
async def test_eev_position_and_running_hours_can_be_graphed(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """O07 is a measurement in steps; O08 is an increasing duration in hours."""
    device = await _setup(hass, add_device, make_entry, O07="240", O08="210")

    eev = hass.states.get(entity_id(hass, "sensor", "O07", device.code))
    assert eev.state == "240.0"
    assert eev.attributes[ATTR_UNIT_OF_MEASUREMENT] == "steps"
    assert eev.attributes[ATTR_STATE_CLASS] == SensorStateClass.MEASUREMENT

    hours = hass.states.get(entity_id(hass, "sensor", "O08", device.code))
    assert float(hours.state) == 210
    assert hours.attributes[ATTR_UNIT_OF_MEASUREMENT] == UnitOfTime.HOURS
    assert hours.attributes[ATTR_DEVICE_CLASS] == SensorDeviceClass.DURATION
    assert hours.attributes[ATTR_STATE_CLASS] == SensorStateClass.TOTAL_INCREASING


@pytest.mark.usefixtures("fake_cloud")
async def test_live_switches_are_labelled(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Switch inputs and outputs read like the app's CL/OP and ON/OFF."""
    device = await _setup(hass, add_device, make_entry)

    assert hass.states.get(entity_id(hass, "sensor", "S01", device.code)).state == (
        "Closed (1)"
    )
    assert hass.states.get(entity_id(hass, "sensor", "S03", device.code)).state == (
        "Open (0)"
    )
    assert hass.states.get(entity_id(hass, "sensor", "O01", device.code)).state == (
        "On (1)"
    )


@pytest.mark.usefixtures("fake_cloud")
async def test_empty_live_switches_are_unavailable(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Without live data the cloud returns nothing, which is not shown as unknown."""
    device = add_device(HITEMP_FIXTURE)
    entry = make_entry()
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_LIVE_DATA: False}
    )
    await setup_entry(hass, entry)

    for key in ("S01", "O01"):
        assert hass.states.get(entity_id(hass, "sensor", key, device.code)).state == (
            STATE_UNAVAILABLE
        )


@pytest.mark.usefixtures("fake_cloud")
async def test_unconfirmed_and_unused_codes_are_disabled(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Codes the app does not show, and the solar circuit, start disabled."""
    device = await _setup(hass, add_device, make_entry)
    registry = er.async_get(hass)

    for key in ("T06", "T11", "T12", "S02", "O10", "O15", "N01", "N11"):
        entry = registry.async_get(entity_id(hass, "sensor", key, device.code))
        assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION, key


async def test_each_code_is_requested_once(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """The climate's mode code is not requested a second time."""
    await _setup(hass, add_device, make_entry)

    codes = fake_cloud.data_requests()[0]

    assert codes.count("Mode") == 1
    assert len(codes) == len(set(codes))
    assert "superheat" not in codes


@pytest.mark.parametrize(
    ("value", "word"),
    [
        ("0000000100100100", 0b100100100),
        ("292", 292),
        (292, 292),
        ("", None),
        (None, None),
        ("-1", None),
        ("on", None),
        ("0101", 101),
    ],
)
def test_status_words_are_parsed(value: object, word: int | None) -> None:
    """Status words arrive as 16 binary digits or as a number."""
    assert parse_bitword(value) == word


@pytest.mark.usefixtures("fake_cloud", "entity_registry_enabled_by_default")
async def test_operating_status_bits(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """2050 is shown as its bits, and bits 8 and 9 drive the running sensors."""
    device = await _setup(hass, add_device, make_entry, **{"2050": "0000000100100100"})

    status = hass.states.get(entity_id(hass, "sensor", "2050", device.code))
    assert status.state == "0000000100100100"
    assert status.attributes["hex"] == "0x0124"
    assert status.attributes["bits_set"] == [2, 5, 8]

    compressor = hass.states.get(
        entity_id(hass, "binary_sensor", "compressor_running", device.code)
    )
    assert compressor.state == STATE_ON
    assert compressor.attributes["calculated_from"] == "2050 bit 8"
    assert hass.states.get(
        entity_id(hass, "binary_sensor", "electric_heater_on", device.code)
    ).state == (STATE_OFF)


@pytest.mark.usefixtures("fake_cloud")
async def test_operating_status_bits_without_a_value(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """Without the status word, the bit sensors are unavailable."""
    device = await _setup(hass, add_device, make_entry, **{"2050": ""})

    assert hass.states.get(entity_id(hass, "sensor", "2050", device.code)).state == (
        STATE_UNAVAILABLE
    )
    assert hass.states.get(
        entity_id(hass, "binary_sensor", "compressor_running", device.code)
    ).state == (STATE_UNAVAILABLE)


async def test_status_word_is_not_requested_twice(
    hass: HomeAssistant,
    fake_cloud: FakeCloud,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """The bit sensors read 2050 from the main request instead of their own code."""
    await _setup(hass, add_device, make_entry)

    codes = fake_cloud.data_requests()[0]

    assert codes.count("2050") == 1
    assert "compressor_running" not in codes


@pytest.mark.usefixtures("fake_cloud")
async def test_operating_mode_and_related_readings(
    hass: HomeAssistant,
    add_device: Callable[..., FakeDevice],
    make_entry: Callable[..., MockConfigEntry],
) -> None:
    """The operating mode, electric heating switch and fan speed are labelled."""
    device = await _setup(
        hass, add_device, make_entry, mode_real="3", M06="1", O29="830"
    )

    assert hass.states.get(
        entity_id(hass, "sensor", "mode_real", device.code)
    ).state == ("Standard (3)")
    assert hass.states.get(entity_id(hass, "sensor", "M06", device.code)).state == (
        "On (1)"
    )
    fan = hass.states.get(entity_id(hass, "sensor", "O29", device.code))
    assert float(fan.state) == 830
    assert fan.attributes[ATTR_UNIT_OF_MEASUREMENT] == "rpm"
