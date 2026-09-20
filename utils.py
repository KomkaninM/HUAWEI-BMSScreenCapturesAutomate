import re

def parse_schedule_args(arg_string: str) -> tuple[int | None, str, str]:
    """
    Parses arguments for start-capture.
    Returns: (interval_seconds, interval_desc, note)
    """
    arg_string = arg_string.strip()
    if not arg_string:
        return None, "Empty argument", ""

    parts = arg_string.split(maxsplit=1)
    time_token = parts[0]
    note = parts[1].strip() if len(parts) > 1 else ""

    match = re.fullmatch(r"(\d+)([smh]?)", time_token.lower())
    if not match:
        return None, f"Invalid time interval '{time_token}'. Use e.g. 30s, 5m, 1h.", ""

    val = int(match.group(1))
    unit = match.group(2)

    if unit == "s" or unit == "":
        seconds = val
        desc = f"{val} second(s)"
    elif unit == "m":
        seconds = val * 60
        desc = f"{val} minute(s)"
    elif unit == "h":
        seconds = val * 3600
        desc = f"{val} hour(s)"

    return seconds, desc, note