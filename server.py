import os
import threading
from flask import Flask, request, send_from_directory

import state
from utils import parse_schedule_args
from capture import capture_screen_local
from line_api import push_image, reply_image, reply_text
from scheduler import scheduled_worker

app = Flask(__name__)
SCREENSHOT_DIR = os.path.abspath("screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

@app.route("/internal/update-tunnel", methods=["POST"])
def update_tunnel():
    """Internal endpoint for launcher.py to sync new Pinggy URLs on reconnect."""
    data = request.get_json(silent=True) or {}
    new_url = data.get("url")
    if new_url:
        os.environ["PUBLIC_TUNNEL_URL"] = new_url
        print(f"[Dynamic Update] Server image base URL updated to: {new_url}")
        return {"status": "success", "url": new_url}, 200
    return {"status": "error", "message": "Missing url"}, 400


@app.route("/images/<filename>", methods=["GET"])
def serve_image(filename):
    """Serves captured screenshots directly to LINE from local storage."""
    return send_from_directory(SCREENSHOT_DIR, filename)

def get_public_image_url(filename: str) -> str:
    base_url = os.getenv("PUBLIC_TUNNEL_URL", "http://127.0.0.1:5000").rstrip("/")
    return f"{base_url}/images/{filename}"

def get_latest_screenshot():
    """Finds the most recently created image in the screenshots folder."""
    files = [os.path.join(SCREENSHOT_DIR, f) for f in os.listdir(SCREENSHOT_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    if not files:
        return None
    # Return the filename of the most recently modified file
    latest_file = max(files, key=os.path.getmtime)
    return os.path.basename(latest_file)

def process_manual_trigger(reply_token: str, comment: str):
    try:
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        note = f"{comment} ({now_str})" if comment else f"Manual capture\nTimestamp: {now_str}"
        reply_image(reply_token, img_url, f"Note: {note}")
        print(f"[Manual] Served image: {img_url}")
    except Exception as e:
        print(f"[Manual Error] {e}")

def process_immediate_first_capture():
    try:
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        
        with state.state_lock:
            note = state.schedule_note
            count = state.schedule_count

        if note:
            caption = f"Scheduled Capture\n{note} #{count}\nTimestamp: {now_str}"
        else:
            caption = f"Scheduled Capture #{count}\nTimestamp: {now_str}"

        push_image(img_url, caption)
        print(f"[Auto] Served initial #{count} image: {img_url}")
    except Exception as e:
        print(f"[Auto First Capture Error] {e}")

@app.route("/callback", methods=["POST"])
def callback():
    body = request.get_json(silent=True)
    if not body:
        return "OK", 200

    events = body.get("events", [])
    for event in events:
        if event.get("type") == "message" and event["message"].get("type") == "text":
            raw_text = event["message"]["text"].strip()
            lower_text = raw_text.lower()
            reply_token = event.get("replyToken")
            if not reply_token:
                continue

            # --- START CAPTURE COMMAND ---
            if lower_text.startswith("start-capture") or lower_text.startswith("start capture"):
                parts = raw_text.split(maxsplit=1)
                
                parsed_seconds = 600
                text_desc = "10 minute(s)"
                note = ""

                if len(parts) > 1:
                    parsed_seconds, text_desc, note = parse_schedule_args(parts[1])
                    if parsed_seconds is None:
                        reply_text(reply_token, f"❌ Command Error: {text_desc}\nExample: start-capture 5m Generator Load")
                        continue

                with state.state_lock:
                    state.capture_interval_seconds = parsed_seconds
                    state.schedule_note = note
                    state.schedule_count = 1  # Start at #1
                    state.auto_capture_enabled = True

                state.wake_event.set()
                
                confirm_msg = f"▶️ Scheduled capture started!\n• Interval: Every {text_desc}"
                if note:
                    confirm_msg += f"\n• Note: {note}"
                confirm_msg += f"\n• Capturing initial picture (#1) now."

                reply_text(reply_token, confirm_msg)
                threading.Thread(target=process_immediate_first_capture, daemon=True).start()

            # --- STOP CAPTURE COMMAND ---
            elif lower_text in ["stop-capture", "stop capture"]:
                with state.state_lock:
                    state.auto_capture_enabled = False
                    count_summary = state.schedule_count
                    state.schedule_count = 0
                    state.schedule_note = ""
                state.wake_event.set()
                reply_text(reply_token, f"⏹️ Automated capture stopped. Completed {count_summary} capture(s).")

            # --- MANUAL CAPTURE COMMAND ---
            elif lower_text.startswith("capture"):
                parts = raw_text.split(maxsplit=1)
                comment = parts[1].strip() if len(parts) > 1 else ""
                threading.Thread(target=process_manual_trigger, args=(reply_token, comment), daemon=True).start()

            elif lower_text in ["recall", "latest"]:
                latest_filename = get_latest_screenshot()
                if not latest_filename:
                    reply_text(reply_token, "❌ No screenshots found on the server.")
                else:
                    img_url = get_public_image_url(latest_filename)
                    reply_image(reply_token, img_url, f"🔄 Recalled: {latest_filename}")
                    print(f"[Recall] Served latest image: {img_url}")

                    
            else:
                # Group Chat Spam Prevention Toggle
                show_errors = os.getenv("REPLY_UNKNOWN_COMMANDS", "False").lower() in ["true", "1", "yes"]
                if show_errors:
                    reply_text(reply_token, "❌ Available commands:\n• start-capture [time] [note]\n• stop-capture\n• capture [note]\n• get-id")

    return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=scheduled_worker, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)