import os
import state
from capture import capture_screen_local
from line_api import push_image

def scheduled_worker():
    print("[*] Scheduler initialized (Standby mode).")
    while True:
        with state.state_lock:
            is_active = state.auto_capture_enabled
            interval = state.capture_interval_seconds

        if not is_active:
            state.wake_event.wait(timeout=1)
            state.wake_event.clear()
            continue

        interrupted = state.wake_event.wait(timeout=interval)
        state.wake_event.clear()
        if interrupted:
            continue

        with state.state_lock:
            if not state.auto_capture_enabled:
                continue

        try:
            filename, now_str = capture_screen_local()
            base_url = os.getenv("PUBLIC_TUNNEL_URL", "http://127.0.0.1:5000").rstrip("/")
            img_url = f"{base_url}/images/{filename}"
            push_image(img_url, f"⏱️ Scheduled Capture ({now_str})")
            print(f"[Auto] Pushed private image: {img_url}")
        except Exception as e:
            print(f"[Auto Error] {e}")