import os
from datetime import datetime
import state
from capture import capture_screen_local
from line_api import push_image, push_text

def scheduled_worker():
    """Background worker thread that handles automated periodic screen captures."""
    print("[*] Scheduler initialized (Standby mode).")
    while True:
        with state.state_lock:
            is_active = state.auto_capture_enabled
            interval = state.capture_interval_seconds

        if not is_active:
            state.wake_event.wait(timeout=1)
            state.wake_event.clear()
            continue

        # Wait for the specified interval or until woken up/stopped
        interrupted = state.wake_event.wait(timeout=interval)
        state.wake_event.clear()
        if interrupted:
            continue

        with state.state_lock:
            if not state.auto_capture_enabled:
                continue
            state.schedule_count += 1
            current_count = state.schedule_count
            current_note = state.schedule_note

        try:
            filename, now_str = capture_screen_local()
            base_url = os.getenv("PUBLIC_TUNNEL_URL", "http://127.0.0.1:5000").rstrip("/")
            img_url = f"{base_url}/images/{filename}"

            # --- NEW CAPTION FORMAT ---
            if current_note:
                caption = f"Scheduled Capture\n{current_note} #{current_count}\nTimestamp: {now_str}"
            else:
                caption = f"Scheduled Capture #{current_count}\nTimestamp: {now_str}"

            push_image(img_url, caption)
            print(f"[Auto] Pushed image #{current_count}: {img_url}")

        except Exception as e:
            print(f"[Auto Error] Failed to send scheduled screenshot: {e}")
            try:
                push_text(f"⚠️ Scheduled capture #{current_count} failed at {datetime.now().strftime('%H:%M:%S')}.\nError: {e}")
            except Exception as net_err:
                print(f"[Critical] Network disconnection: {net_err}")