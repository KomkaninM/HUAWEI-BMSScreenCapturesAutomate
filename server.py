import os
import time
import re 
import sys
import threading
from pathlib import Path
from flask import Flask, request, send_from_directory
import pyautogui

capture_lock = threading.RLock()

import config
import state
from utils import parse_schedule_args, parse_single_capture_args
from capture import capture_screen_local
from line_api import push_image, reply_image, reply_text, push_text
from scheduler import (
    start_automated_captures, 
    stop_automated_captures, 
    schedule_single_capture, 
    is_scheduler_running
)
from detector import is_logged_out
from macro_player import execute_macro

app = Flask(__name__)
SCREENSHOT_DIR = os.path.abspath("screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def perform_auto_logout():
    """Triggers the logout macro if ENABLE_AUTO_LOGOUT is True in .env."""
    if not config.ENABLE_AUTO_LOGOUT:
        return
        
    print("[Auto Logout] Triggering post-capture logout sequence...")
    # Small pause so the screen capture pipeline is completely settled
    time.sleep(2)
    success, msg = execute_macro(config.LOGOUT_MACRO_SCRIPT)
    if success:
        print("[Auto Logout] Logged out successfully.")
    else:
        print(f"[Auto Logout Error] Failed: {msg}")

def ensure_logged_in() -> bool:
    """
    Silent guard: checks if logged out, relogs via JSON macro in background.
    Returns True if a relogin was performed.
    """
    if is_logged_out():
        print("[Guard] Logout detected. Relogging in background...")
        # Automatically uses config.DEFAULT_LOGIN_MACRO 
        success, msg = execute_macro()
        if success:
            time.sleep(1) # Let BMS finish loading the dashboard
        return True
    return False

def perform_precheck_task():
    """Runs 10 seconds before a scheduled capture to ensure BMS is logged in without shifting the target time."""
    with capture_lock:
        try:
            if ensure_logged_in():
                print("[Pre-Check] 🔄 Auto-relogged 10s before schedule.")
            else:
                print("[Pre-Check] ✅ Session verified 10s before schedule.")
        except Exception as e:
            print(f"[Pre-Check Error] {e}")

def process_close_menu(reply_token: str):
    """Clicks the menu toggle button to close the BMS navigation drawer."""
    try:
        reply_text(reply_token, "🔄 Closing BMS menu...")
        
        pyautogui.click(x=77, y=273)
        time.sleep(0.2)
        pyautogui.click(x=1394, y=263) 
        print("[Close Menu] Clicked at (77, 273)")
        
        time.sleep(1)
        
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        push_image(img_url, f"✅ Menu closed.\nTimestamp: {now_str}")
        print(f"[Close Menu] Confirmation image sent: {img_url}")
        
    except Exception as e:
        print(f"[Close Menu Error] {e}")
        push_image(None, f"⚠️ Failed to close menu: {e}")

def process_login_command(reply_token: str):
    """Handles manual 'login' command from LINE."""
    try:
        if not is_logged_out():
            reply_text(reply_token, "ℹ️ BMS is already logged in. Capturing current screen...")
        else:
            reply_text(reply_token, "🔄 Logout detected. Running JSON login macro...")
            success, msg = execute_macro()
            if not success:
                push_image(None, f"❌ BMS login macro failed: {msg}")
                return

        time.sleep(1)
        filename, now_str = capture_screen_local()
        img_url = get_public_image_url(filename)
        push_image(img_url, f"✅ BMS Status Checked\nTimestamp: {now_str}")
        
    except Exception as e:
        print(f"[Login Command Error] {e}")
        push_image(None, f"⚠️ Error executing login: {e}")

def process_manual_trigger(reply_token: str, note_text: str = ""):
    with capture_lock:
        try:
            relogged = ensure_logged_in()

            filename, now_str = capture_screen_local()
            img_url = get_public_image_url(filename)

            relog_tag = " (Auto-relogged)" if relogged else ""
            caption = f"Manual Capture\n{note_text}{relog_tag}\nTimestamp: {now_str}".strip()

            reply_image(reply_token, img_url, caption)
            print(f"[Manual] Served image: {img_url}")

            perform_auto_logout()

        except Exception as e:
            print(f"[Manual Capture Error] {e}")

def perform_scheduled_capture(note_text):
    """The recurring background capture task."""
    with capture_lock:
        try:
            ensure_logged_in()

            filename, now_str = capture_screen_local()
            img_url = get_public_image_url(filename)

            with state.state_lock:
                state.schedule_count += 1
                count = state.schedule_count

            base_note = f"{note_text} " if note_text else ""
            caption = f"Scheduled Capture\n{base_note}#{count}\nTimestamp: {now_str}"

            push_image(img_url, caption)
            print(f"[Auto] Pushed scheduled capture #{count}: {img_url}")

            # Run auto-logout inside the lock so another capture doesn't interrupt it
            perform_auto_logout()

        except Exception as e:
            print(f"[Scheduled Capture Error] {e}")

def perform_one_time_capture(note_text: str):
    """Executes a scheduled single capture and pushes it via LINE."""
    with capture_lock:
        try:
            ensure_logged_in()

            filename, now_str = capture_screen_local()
            img_url = get_public_image_url(filename)

            base_note = f"{note_text}\n" if note_text else ""
            caption = f"Scheduled 1-Time Capture\n{base_note}Timestamp: {now_str}"

            push_image(img_url, caption)
            print(f"[Auto 1-Time] Pushed capture: {img_url}")

            perform_auto_logout()

        except Exception as e:
            print(f"[One-Time Capture Error] {e}")

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
    base_url = os.getenv("PUBLIC_TUNNEL_URL", f"http://127.0.0.1:{config.PORT}").rstrip("/")
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
            if lower_text.startswith("start-capture") or lower_text.startswith("start capture"):
                prefix = "start-capture" if lower_text.startswith("start-capture") else "start capture"
                arg_string = raw_text[len(prefix):].strip()

                def _start_capture_worker(token, raw_args):
                    total_seconds = 30 * 60
                    human_readable = "30 minute(s)"
                    note = ""
                    start_time = None

                    if raw_args:
                        parsed = parse_schedule_args(raw_args)
                        if parsed[0] is None:
                            reply_text(token, f"❌ Command Error: {parsed[1]}\nExample: start-capture 10m GenTest --starttime 15:00:00")
                            return
                        total_seconds, human_readable, note, start_time = parsed

                    with state.state_lock:
                        state.schedule_count = 0 

                    start_automated_captures(
                        interval_seconds=total_seconds, 
                        note=note, 
                        capture_task_function=perform_scheduled_capture, 
                        start_time=start_time,
                        precheck_function=perform_precheck_task
                    )

                    msg = f"⏱️ Scheduled: Auto-capturing every {human_readable}."
                    if note:
                        msg += f"\n📝 Note: {note}"
                    if start_time:
                        msg += f"\n⏳ Starts at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    else:
                        msg += "\n▶️ Capturing initial picture (#1) now."

                    reply_text(token, msg)

                # Fire off in background thread so HTTP response is instant
                threading.Thread(target=_start_capture_worker, args=(reply_token, arg_string), daemon=True).start()
                
            # --- STOP AUTOMATED CAPTURE ---
            elif lower_text == "stop-capture":
                if stop_automated_captures():
                    reply_text(reply_token, "🛑 Stopped all automated captures.")
                else:
                    reply_text(reply_token, "⚠️ No active captures to stop.")
                    
            # --- AUTO LOGOUT TOGGLES ---
            elif lower_text == "enable-autologout":
                config.ENABLE_AUTO_LOGOUT = True
                reply_text(reply_token, "✅ Auto-logout after capture is now ENABLED.")
                
            elif lower_text == "disable-autologout":
                config.ENABLE_AUTO_LOGOUT = False
                reply_text(reply_token, "🚫 Auto-logout after capture is now DISABLED.")
                    
            # --- MANUAL / ONE-TIME CAPTURE COMMAND ---
            elif lower_text.startswith("capture"):
                arg_string = raw_text[len("capture"):].strip()
                note, start_time = parse_single_capture_args(arg_string)

                if start_time:
                    # Scheduled 1-time capture
                    schedule_single_capture(
                        run_date=start_time, 
                        note=note, 
                        capture_task_function=perform_one_time_capture,
                        precheck_function=perform_precheck_task
                    )
                    
                    msg = f"⏱️ Scheduled 1-Time Capture\n⏳ Time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    if note:
                        msg += f"\n📝 Note: {note}"
                    reply_text(reply_token, msg)
                else:
                    # Immediate capture
                    threading.Thread(target=process_manual_trigger, args=(reply_token, note), daemon=True).start()

            # --- RECALL LATEST IMAGE COMMAND ---
            elif lower_text.startswith("recall") or lower_text.startswith("latest"):
                parts = lower_text.split()
                limit = 1
                
                if len(parts) > 1 and parts[1].isdigit():
                    limit = int(parts[1])
                    limit = min(limit, 5)
                    
                threading.Thread(target=process_recall_trigger, args=(reply_token, limit), daemon=True).start()

            # --- CHANGE DEFAULT LOGIN MACRO ---
            elif lower_text.startswith("set-login "):
                new_macro = lower_text.split(" ", 1)[1].strip()
                if not new_macro.endswith(".json"):
                    new_macro += ".json"
                    
                macro_path = Path(config.MACROS_DIR) / new_macro
                if not macro_path.exists():
                    reply_text(reply_token, f"❌ Error: Macro '{new_macro}' not found in macros folder.")
                else:
                    # 1. Update active variables in memory
                    config.DEFAULT_LOGIN_MACRO = new_macro
                    config.DEFAULT_LOGIN_MACRO_PATH = macro_path
                    
                    # 2. Update physical .env file so the setting persists
                    env_file = Path(config.BASE_DIR) / ".env"
                    try:
                        if env_file.exists():
                            with open(env_file, "r") as f:
                                lines = f.readlines()
                            with open(env_file, "w") as f:
                                found = False
                                for line in lines:
                                    if line.startswith("DEFAULT_LOGIN_MACRO="):
                                        f.write(f"DEFAULT_LOGIN_MACRO={new_macro}\n")
                                        found = True
                                    else:
                                        f.write(line)
                                if not found:
                                    f.write(f"DEFAULT_LOGIN_MACRO={new_macro}\n")
                        reply_text(reply_token, f"✅ Default login macro successfully changed to:\n{new_macro}")
                    except Exception as e:
                        reply_text(reply_token, f"⚠️ Config updated in memory, but failed to save to .env:\n{e}")

            # --- MANUAL LOGIN COMMAND ---
            elif lower_text == "login":
                threading.Thread(
                    target=process_login_command,
                    args=(reply_token,),
                    daemon=True
                ).start()

            # --- DYNAMIC MACRO COMMAND ---
            elif lower_text.startswith("macro "):
                target_name = lower_text.split(" ", 1)[1].strip()
                
                # Check file existence before executing
                check_name = target_name if target_name.endswith(".json") else f"{target_name}.json"
                macro_path = Path(config.MACROS_DIR) / check_name
                
                if not macro_path.exists():
                    reply_text(reply_token, f"❌ Error: Macro file '{check_name}' does not exist.")
                    continue

                reply_text(reply_token, f"⏳ Running macro: {target_name}...")

                def _run_dynamic(name_to_run, file_name):
                    success, msg = execute_macro(name_to_run)
                    print(f"[Macro Execution] {'✅' if success else '❌'} {msg}")
                    # Push error to LINE if macro fails mid-execution
                    if not success:
                        push_text(f"❌ Macro '{file_name}' failed to complete:\n{msg}")

                threading.Thread(target=_run_dynamic, args=(target_name, check_name), daemon=True).start()

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

            # --- HELP COMMAND ---
            elif lower_text == "help":
                cmds = (
                    "ℹ️ Available commands:\n"
                    "• start-capture [time] [note] [--starttime HH:MM]\n"
                    "• stop-capture\n"
                    "• capture [note]\n"
                    "• recall [number]\n"
                    "• login\n"
                    "• set-login [macro_name]\n"
                    "• macro [name]\n"
                    "• close-menu\n"
                    "• enable-autologout\n"
                    "• disable-autologout"
                )
                reply_text(reply_token, cmds)
            else:
                show_errors = os.getenv("REPLY_UNKNOWN_COMMANDS", "False").lower() in ["true", "1", "yes"]
                if show_errors:
                    cmds = (
                        "❌ Available commands:\n"
                        "• start-capture [time] [note] [--starttime HH:MM]\n"
                        "• stop-capture\n"
                        "• capture [note]\n"
                        "• recall [number]\n"
                        "• login\n"
                        "• set-login [macro_name]\n"
                        "• macro [name]\n"
                        "• close-menu\n"
                        "• enable-autologout\n"
                        "• disable-autologout"
                    )
                    reply_text(reply_token, cmds)

    return "OK", 200

if __name__ == "__main__":
    print(f"Starting server on port {config.PORT}...")
    app.run(host="0.0.0.0", port=config.PORT, debug=False, use_reloader=False)