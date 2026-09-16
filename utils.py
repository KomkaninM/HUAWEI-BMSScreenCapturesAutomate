import re

def parse_interval(time_str: str) -> tuple[int, str] | tuple[None, str]:
    """
    Parses '3s', '10m', '1h', or plain numbers like '3600'.
    Returns (seconds, human_readable_string) or (None, error_string).
    """
    time_str = time_str.strip().lower()
    match = re.match(r"^(\d+)([smh]?)$", time_str)
    if not match:
        return None, f"Invalid format '{time_str}'. Use e.g., 30s, 10m, 1h, or 600."

    value, unit = match.groups()
    num = int(value)

    if num <= 0:
        return None, "Interval must be greater than 0."

    if unit == "s" or unit == "":
        return num, f"{num} second(s)"
    elif unit == "m":
        return num * 60, f"{num} minute(s)"
    elif unit == "h":
        return num * 3600, f"{num} hour(s)"

    return None, "Unknown time unit."