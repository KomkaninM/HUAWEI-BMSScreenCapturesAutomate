import os
import threading
from flask import Flask, request, send_from_directory

import state
from utils import parse_interval
from capture import capture_screen_local
from line_api import push_image, reply_image, reply_text
from scheduler import scheduled_worker

app = Flask(__name__)
SCREENSHOT_DIR = os.path.abspath("screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ----------------------------------------------------
# Self-Hosted Static Image Endpoint
# ----------------------------------------------------

@app.route("/images/<filename>", methods=["GET"])
def serve_image(filename):
    """Serves captured screenshots directly to LINE from local storage."""
    # Omitting mimetype lets Flask auto-detect image/jpeg vs image/png from filename
    return send_from_directory(SCREENSHOT_DIR, filename)

def get_public_image_url(filename: str) -> str:
    base_url = os.getenv("PUBLIC_TUNNEL_URL", "http://127.0.0.1:5000").rstrip("/")
    return f"{base_url}/images/{filename}"

def process_manual_trigger(reply_token: str, comment: str):
    try:
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        
        note = f"{comment} ({now_str})" if comment else f"Manual capture ({now_str})"
        reply_image(reply_token, img_url, f"Note: {note}")
        print(f"[Manual] Served private image: {img_url}")
    except Exception as e:
        print(f"[Manual Error] {e}")

def process_immediate_first_capture():
    try:
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        push_image(img_url, f"⏱️ Scheduled Capture Started ({now_str})")
        print(f"[Auto] Served private initial image: {img_url}")
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

            if lower_text.startswith("start-capture") or lower_text.startswith("start capture"):
                parts = raw_text.split(maxsplit=1)
                if len(parts) > 1:
                    parsed_seconds, text_desc = parse_interval(parts[1].strip())
                    if parsed_seconds is None:
                        reply_text(reply_token, f"❌ Command Error: {text_desc}")
                        continue
                    with state.state_lock:
                        state.capture_interval_seconds = parsed_seconds
                else:
                    with state.state_lock:
                        text_desc = f"{state.capture_interval_seconds} second(s)"

                with state.state_lock:
                    state.auto_capture_enabled = True
                state.wake_event.set()
                
                reply_text(reply_token, f"▶️ Automated capture started! Capturing initial picture now, then every {text_desc}.")
                threading.Thread(target=process_immediate_first_capture, daemon=True).start()

            elif lower_text in ["stop-capture", "stop capture"]:
                with state.state_lock:
                    state.auto_capture_enabled = False
                state.wake_event.set()
                reply_text(reply_token, "⏹️ Automated capture stopped.")

            elif lower_text.startswith("capture"):
                parts = raw_text.split(maxsplit=1)
                comment = parts[1].strip() if len(parts) > 1 else ""
                threading.Thread(target=process_manual_trigger, args=(reply_token, comment), daemon=True).start()

            else:
                reply_text(reply_token, "❌ Available commands:\n• start-capture [time]\n• stop-capture\n• capture [note]")

    return "OK", 200

if __name__ == "__main__":
    threading.Thread(target=scheduled_worker, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)