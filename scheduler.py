import state
from capture import capture_and_upload
from line_api import push_image

def scheduled_worker():
    print("[*] Scheduler initialized (Standby mode). Awaiting 'start-capture' command...")

    while True:
        with state.state_lock:
            is_active = state.auto_capture_enabled
            interval = state.capture_interval_seconds

        if not is_active:
            # Standby mode: Wait until wake_event is set by start-capture
            state.wake_event.wait(timeout=1)
            state.wake_event.clear()
            continue

        # Wait for the interval (can be woken immediately by stop-capture or start-capture update)
        interrupted = state.wake_event.wait(timeout=interval)
        state.wake_event.clear()

        # If interrupted by stop-capture or interval reconfiguration, restart evaluation
        if interrupted:
            continue

        # Verify state is still active before capturing
        with state.state_lock:
            if not state.auto_capture_enabled:
                continue

        try:
            print(f"[Auto] Running scheduled capture (every {interval}s)...")
            img_url, now_str = capture_and_upload()
            push_image(img_url, f"⏱️ Scheduled Capture ({now_str})")
            print("[Auto] Screenshot pushed successfully.")
        except Exception as e:
            print(f"[Auto Error] {e}")