import os
import threading
import time
import re 
from flask import Flask, request, send_from_directory

import state
from utils import parse_schedule_args
from capture import capture_screen_local
from line_api import push_image, reply_image, reply_text
from scheduler import start_automated_captures, stop_automated_captures, is_scheduler_running

app = Flask(__name__)
SCREENSHOT_DIR = os.path.abspath("screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

@app.route("/internal/update-tunnel", methods=["POST"])
def update_tunnel():
    """Internal endpoint for launcher.py to sync new URLs on reconnect."""
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

def get_latest_screenshots(limit=1):
    """Finds the most recently created images in the screenshots folder."""
    files = [os.path.join(SCREENSHOT_DIR, f) for f in os.listdir(SCREENSHOT_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    if not files:
        return []
    
    files.sort(key=os.path.getmtime, reverse=True)
    return [os.path.basename(f) for f in files[:limit]]

def process_manual_trigger(reply_token: str, comment: str):
    try:
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        note = f"{comment} ({now_str})" if comment else f"Manual capture\nTimestamp: {now_str}"
        reply_image(reply_token, img_url, f"Note: {note}")
        print(f"[Manual] Served image: {img_url}")
    except Exception as e:
        print(f"[Manual Error] {e}")

def process_recall_trigger(reply_token: str, limit: int):
    try:
        filenames = get_latest_screenshots(limit)
        if not filenames:
            reply_text(reply_token, "❌ No screenshots found on the server.")
            return

        if len(filenames) == 1:
            img_url = get_public_image_url(filenames[0])
            reply_image(reply_token, img_url, f"🔄 Recalled: {filenames[0]}")
            print(f"[Recall] Served latest image: {img_url}")
        else:
            reply_text(reply_token, f"🔄 Recalling the latest {len(filenames)} images...")
            
            for filename in reversed(filenames):
                time.sleep(0.5) 
                img_url = get_public_image_url(filename)
                push_image(img_url, f"🔄 Recalled: {filename}")
                print(f"[Recall] Pushed image: {img_url}")
    except Exception as e:
        print(f"[Recall Error] {e}")

def perform_scheduled_capture(note_text):
    """The background task executed by APScheduler every X minutes."""
    try:
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        
        with state.state_lock:
            state.schedule_count += 1
            count = state.schedule_count

        if note_text:
            caption = f"Scheduled Capture\n{note_text} #{count}\nTimestamp: {now_str}"
        else:
            caption = f"Scheduled Capture #{count}\nTimestamp: {now_str}"

        push_image(img_url, caption)
        print(f"[Auto] Served scheduled #{count} image: {img_url}")
    except Exception as e:
        print(f"[Auto Capture Error] {e}")

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

            # --- START AUTOMATED CAPTURE ---
            if lower_text.startswith("start-capture"):
                parts = raw_text.split()
                
                # Default fallback values
                total_seconds = 30 * 60
                human_readable = "30 minutes"
                
                if len(parts) > 1:
                    # Parse the time string (e.g., "10", "25s", "30m", "5h")
                    match = re.match(r"^(\d+)([smh]?)$", parts[1].lower())
                    if match:
                        val = int(match.group(1))
                        unit = match.group(2)
                        
                        if unit == 'h':
                            total_seconds = val * 3600
                            human_readable = f"{val} hours"
                        elif unit == 'm':
                            total_seconds = val * 60
                            human_readable = f"{val} minutes"
                        else:
                            # Default to seconds if 's' or no unit is provided
                            total_seconds = val
                            human_readable = f"{val} seconds"

                note = " ".join(parts[2:]) if len(parts) > 2 else ""
                
                with state.state_lock:
                    state.schedule_count = 0  # Reset the image counter
                
                # Pass the calculated seconds to the scheduler
                start_automated_captures(total_seconds, note, perform_scheduled_capture)
                reply_text(reply_token, f"⏱️ Scheduled: Auto-capturing every {human_readable}.")
                
            # --- STOP AUTOMATED CAPTURE ---
            elif lower_text == "stop-capture":
                if stop_automated_captures():
                    reply_text(reply_token, "🛑 Stopped all automated captures.")
                else:
                    reply_text(reply_token, "⚠️ No active captures to stop.")
                    
            # --- MANUAL CAPTURE COMMAND ---
            elif lower_text.startswith("capture"):
                parts = raw_text.split(maxsplit=1)
                comment = parts[1].strip() if len(parts) > 1 else ""
                threading.Thread(target=process_manual_trigger, args=(reply_token, comment), daemon=True).start()

            # --- RECALL LATEST IMAGE COMMAND ---
            elif lower_text.startswith("recall") or lower_text.startswith("latest"):
                parts = lower_text.split()
                limit = 1
                
                if len(parts) > 1 and parts[1].isdigit():
                    limit = int(parts[1])
                    limit = min(limit, 5) # Safety cap
                    
                threading.Thread(target=process_recall_trigger, args=(reply_token, limit), daemon=True).start()

            else:
                # Group Chat Spam Prevention Toggle
                show_errors = os.getenv("REPLY_UNKNOWN_COMMANDS", "False").lower() in ["true", "1", "yes"]
                if show_errors:
                    reply_text(reply_token, "❌ Available commands:\n• start-capture [time] [note]\n• stop-capture\n• capture [note]\n• recall [number]")

    return "OK", 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)