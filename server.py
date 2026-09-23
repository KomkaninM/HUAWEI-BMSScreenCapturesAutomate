import os
import threading
import time
import re 
import subprocess
import sys
from flask import Flask, request, send_from_directory

import state
from utils import parse_schedule_args
from capture import capture_screen_local
from line_api import push_image, reply_image, reply_text
from scheduler import start_automated_captures, stop_automated_captures, is_scheduler_running
import pyautogui
from detector import is_logged_out

app = Flask(__name__)
SCREENSHOT_DIR = os.path.abspath("screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def execute_login_macro() -> bool:
    """Executes the login macro subprocess and waits for UI settle."""
    macro_filename = os.getenv("LOGIN_MACRO_SCRIPT", "DH08C.py")
    script_path = os.path.abspath(os.path.join("PrototypeScripts", macro_filename))
    
    if not os.path.exists(script_path):
        print(f"[Login Macro] Script not found: {script_path}")
        return False
        
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print("[Login Macro] Executed successfully.")
            time.sleep(1)  # Let BMS finish loading the dashboard
            return True
        else:
            print(f"[Login Macro Error] Exit code {result.returncode}:\n{result.stderr}")
            return False
    except Exception as e:
        print(f"[Login Macro Exception] {e}")
        return False

def ensure_logged_in() -> bool:
    """
    Silent guard: checks if logged out, relogs if necessary.
    Returns True if a relogin was performed.
    """
    if is_logged_out():
        print("[Guard] Logout detected. Relogging in background...")
        execute_login_macro()
        return True
    return False

def process_close_menu(reply_token: str):
    """Clicks the menu toggle button to close the BMS navigation drawer."""
    try:
        reply_text(reply_token, "🔄 Closing BMS menu...")
        
        # Click the menu button
        pyautogui.click(x=77, y=273)
        time.sleep(0.2)
        pyautogui.click(x=1394, y=263) 
        print("[Close Menu] Clicked at (77, 273)")
        
        # Wait 1 second for the slide/fade animation to finish
        time.sleep(1)
        
        # Capture and push confirmation
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        push_image(img_url, f"✅ Menu closed.\nTimestamp: {now_str}")
        print(f"[Close Menu] Confirmation image sent: {img_url}")
        
    except Exception as e:
        print(f"[Close Menu Error] {e}")
        push_image(None, f"⚠️ Failed to close menu: {e}")

def process_login_command(reply_token: str):
    """Handles manual 'login' command from LINE with progress feedback."""
    try:
        if not is_logged_out():
            reply_text(reply_token, "ℹ️ BMS is already logged in. Capturing current screen...")
        else:
            reply_text(reply_token, "🔄 Logout detected. Running login macro...")
            success = execute_login_macro()
            if not success:
                push_image(None, "❌ BMS login macro failed. Please check host console.")
                return

        # Verification screenshot push
        time.sleep(1)
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        push_image(img_url, f"✅ BMS Status Checked\nTimestamp: {now_str}")
        
    except Exception as e:
        print(f"[Login Command Error] {e}")
        push_image(None, f"⚠️ Error executing login: {e}")

def process_manual_trigger(reply_token: str, note_text: str = ""):
    """Handles manual 'capture [note]' command."""
    try:
        # Silently relog first so the user doesn't get a login page image
        relogged = ensure_logged_in()
        
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        
        relog_tag = " (Auto-relogged)" if relogged else ""
        caption = f"Manual Capture\n{note_text}{relog_tag}\nTimestamp: {now_str}".strip()
        
        reply_image(reply_token, img_url, caption)
        print(f"[Manual] Served image: {img_url}")
    except Exception as e:
        print(f"[Manual Capture Error] {e}")

def perform_scheduled_capture(note_text):
    """The recurring background capture task."""
    try:
        # Check and relog quietly if needed
        ensure_logged_in()

        # Capture the active screen
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        
        with state.state_lock:
            state.schedule_count += 1
            count = state.schedule_count

        base_note = f"{note_text} " if note_text else ""
        caption = f"Scheduled Capture\n{base_note}#{count}\nTimestamp: {now_str}"

        # Sends exactly one image push
        push_image(img_url, caption)
        print(f"[Auto] Pushed scheduled capture #{count}: {img_url}")
        
    except Exception as e:
        print(f"[Scheduled Capture Error] {e}")

def get_latest_screenshots(limit=1):
    """Finds the most recently created images in the screenshots folder."""
    files = [os.path.join(SCREENSHOT_DIR, f) for f in os.listdir(SCREENSHOT_DIR) if f.endswith(('.png', '.jpg', '.jpeg'))]
    if not files:
        return []
    
    files.sort(key=os.path.getmtime, reverse=True)
    return [os.path.basename(f) for f in files[:limit]]

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
                
                total_seconds = 30 * 60
                human_readable = "30 minutes"
                
                if len(parts) > 1:
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
                            total_seconds = val
                            human_readable = f"{val} seconds"

                note = " ".join(parts[2:]) if len(parts) > 2 else ""
                
                with state.state_lock:
                    state.schedule_count = 0 
                
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
                    limit = min(limit, 5)
                    
                threading.Thread(target=process_recall_trigger, args=(reply_token, limit), daemon=True).start()

            # --- MANUAL LOGIN COMMAND ---
            elif lower_text == "login":
                threading.Thread(
                    target=process_login_command,
                    args=(reply_token,),
                    daemon=True
                ).start()

            # --- CLOSE BMS MENU COMMAND ---
            elif lower_text == "close-menu":
                threading.Thread(
                    target=process_close_menu,
                    args=(reply_token,),
                    daemon=True
                ).start()

            # --- GET ROOM ID COMMAND ---
            elif lower_text == "check-id":
                source = event.get("source", {})
                g_id = source.get("groupId", "None (Not in a group)")
                u_id = source.get("userId", "None")
                reply_text(reply_token, f"Group ID: {g_id}\nUser ID: {u_id}")

            else:
                show_errors = os.getenv("REPLY_UNKNOWN_COMMANDS", "False").lower() in ["true", "1", "yes"]
                if show_errors:
                    reply_text(reply_token, "❌ Available commands:\n• start-capture [time] [note]\n• stop-capture\n• capture [note]\n• recall [number]\n• login\n• close-menu")

    return "OK", 200

if __name__ == "__main__":
    # Dynamically select port for concurrent bot testing (defaults to 5000)
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)