import re
from datetime import datetime, timedelta

def parse_starttime_token(arg_string: str) -> tuple[datetime | None, str]:
    """
    Finds and extracts --starttime or --start-time (supporting --, —, –).
    Returns (start_time_dt, cleaned_arg_string).
    """
    pattern = r'(?:--|—|–)\s*start-?time\s+(\d{1,2}:\d{2}(?::\d{2})?)'
    match = re.search(pattern, arg_string, re.IGNORECASE)
    
    if not match:
        return None, arg_string.strip()

    time_str = match.group(1)
    if time_str.count(':') == 1:
        parsed_time = datetime.strptime(time_str, "%H:%M").time()
    else:
        parsed_time = datetime.strptime(time_str, "%H:%M:%S").time()

    now = datetime.now()
    start_time_dt = datetime.combine(now.date(), parsed_time)

    if start_time_dt <= now:
        start_time_dt += timedelta(days=1)

    cleaned_str = arg_string[:match.start()] + arg_string[match.end():]
    return start_time_dt, cleaned_str.strip()


def parse_schedule_args(arg_string: str):
    """
    Parses arguments for start-capture.
    Returns: (interval_seconds, interval_desc, note, start_time_dt)
    """
    arg_string = arg_string.strip()
    if not arg_string:
        return None, "Empty argument", "", None

    try:
        start_time_dt, arg_string = parse_starttime_token(arg_string)
    except ValueError:
        return None, "Invalid time format. Use HH:MM or HH:MM:SS.", "", None

    # Extract Interval and Note
    parts = arg_string.split(maxsplit=1)
    if not parts:
        return None, "Missing interval argument", "", None

    time_token = parts[0]
    note = parts[1].strip() if len(parts) > 1 else ""

    match_interval = re.fullmatch(r"(\d+)([smh]?)", time_token.lower())
    if not match_interval:
        return None, f"Invalid time interval '{time_token}'. Use e.g. 15s, 5m, 1h.", "", None

    val = int(match_interval.group(1))
    unit = match_interval.group(2)

    if unit in ("s", ""):
        seconds = val
        desc = f"{val} second(s)"
    elif unit == "m":
        seconds = val * 60
        desc = f"{val} minute(s)"
    elif unit == "h":
        seconds = val * 3600
        desc = f"{val} hour(s)"

    return seconds, desc, note, start_time_dt


def parse_single_capture_args(arg_string: str) -> tuple[str, datetime | None]:
    """
    Parses arguments for single 'capture [note] [--starttime HH:MM:SS]'.
    Returns (note, start_time_dt).
    """
    arg_string = arg_string.strip()
    if not arg_string:
        return "", None

    try:
        start_time_dt, cleaned_note = parse_starttime_token(arg_string)
        return cleaned_note, start_time_dt
    except ValueError:
        return arg_string, None