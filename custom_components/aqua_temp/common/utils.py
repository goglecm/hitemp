import math

from homeassistant.const import UnitOfTemperature
from homeassistant.util.unit_conversion import (
    TemperatureConverter,
    TemperatureDeltaConverter,
)

DEVICE_CLASS_TEMPERATURE = "temperature"
DEVICE_CLASS_TEMPERATURE_DELTA = "temperature_delta"
TEMPERATURE_DEVICE_CLASSES = (DEVICE_CLASS_TEMPERATURE, DEVICE_CLASS_TEMPERATURE_DELTA)

UNLISTED_VALUE = "not listed in the app"


def raw_value_key(value) -> str | None:
    """Return a cloud value in the form value labels use, '1.0' and 1 become '1'."""
    if value is None or value == "":
        return None

    number = safe_float(value)

    if number is not None and number.is_integer():
        return str(int(number))

    return str(value).strip()


def format_option(raw: str, label: str) -> str:
    """Show a value as the app's label with the raw value, for example 'NO (0)'."""
    return f"{label} ({raw})"


def label_value(value, labels: dict[str, str]) -> str | None:
    """Return the labelled form of a cloud value, also for values the app lacks."""
    raw = raw_value_key(value)

    if raw is None:
        return None

    if raw in labels:
        return format_option(raw, labels[raw])

    return f"{raw} ({UNLISTED_VALUE})"


def labelled_options(labels: dict[str, str]) -> list[str]:
    return [format_option(raw, label) for raw, label in labels.items()]


def safe_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except ValueError, TypeError:
        return None


def normalize_state(value) -> str | None:
    """Return a comparable form of a cloud value, mapping on/off spellings to 1/0."""
    if value is None:
        return None

    if isinstance(value, bool):
        return "1" if value else "0"

    text = str(value).strip().lower()

    if text in ("true", "1", "1.0"):
        return "1"

    if text in ("false", "0", "0.0"):
        return "0"

    return text


def convert_temperature(
    value: float | None,
    device_class: str | None,
    from_unit: str | None,
    to_unit: str,
) -> float | None:
    """Convert a temperature or temperature difference between units."""
    from_unit = from_unit or UnitOfTemperature.CELSIUS

    if value is None or from_unit == to_unit:
        return value

    if device_class == DEVICE_CLASS_TEMPERATURE:
        return TemperatureConverter.convert(value, from_unit, to_unit)

    if device_class == DEVICE_CLASS_TEMPERATURE_DELTA:
        return TemperatureDeltaConverter.convert(value, from_unit, to_unit)

    return value


def convert_range(
    minimum: float,
    maximum: float,
    device_class: str | None,
    from_unit: str | None,
    to_unit: str,
) -> tuple[float, float]:
    """Convert a range, narrowing it to whole numbers so it never grows."""
    converted_minimum = convert_temperature(minimum, device_class, from_unit, to_unit)
    converted_maximum = convert_temperature(maximum, device_class, from_unit, to_unit)

    if converted_minimum == minimum and converted_maximum == maximum:
        return minimum, maximum

    return float(math.ceil(converted_minimum)), float(math.floor(converted_maximum))


def round_to_step(value: float, step: float | None, offset: float = 0.0) -> float:
    """Round a value to the closest multiple of step counted from offset."""
    if not step:
        return value

    return round(offset + round((value - offset) / step) * step, 6)
