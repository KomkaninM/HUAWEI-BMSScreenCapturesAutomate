import threading

auto_capture_enabled = False
capture_interval_seconds = 600  # Default: 10 minutes
state_lock = threading.Lock()
wake_event = threading.Event()  # Instantly wakes up scheduler when interval changes or stops