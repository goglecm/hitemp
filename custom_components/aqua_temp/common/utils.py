def safe_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return None
