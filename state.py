import threading

# Thread lock for state safety
state_lock = threading.Lock()

# Auto-capture flags and settings
auto_capture_enabled = False
capture_interval_seconds = 600  # Default 10 minutes
wake_event = threading.Event()

# New: Scheduling metadata
schedule_note = ""      # Stores the custom note (e.g., "AHU-01 Testing")
schedule_count = 0      # Tracks the increment counter (#1, #2, ...)