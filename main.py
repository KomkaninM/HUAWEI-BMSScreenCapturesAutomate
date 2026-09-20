import threading
from flask import Flask, request

# Import our custom modules
import state
from utils import parse_schedule_args
from capture import capture_and_upload
from line_api import push_image, reply_image, reply_text
from scheduler import scheduled_worker

app = Flask(__name__)

def process_manual_trigger(reply_token: str, comment: str):
    """Takes a screenshot and replies with the custom note and timestamp."""
    try:
        img_url, now_str = capture_and_upload()
        
        # Include timestamp in both cases
        if comment:
            note = f"{comment} ({now_str})"
        else:
            note = f"Manual capture ({now_str})"
            
        reply_image(reply_token, img_url, f"Note: {note}")
        print(f"[Manual] Sent screenshot with note: {note}")
    except Exception as e:
        print(f"[Manual Error] {e}")


def process_immediate_first_capture():
    """Takes and pushes the first screenshot immediately after start-capture."""
    try:
        img_url, now_str = capture_and_upload()
        push_image(img_url, f"⏱️ Scheduled Capture Started ({now_str})")
        print("[Auto] Initial screenshot pushed successfully.")
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

            # ------------------------------------------------
            # Command 1: start-capture [interval]
            # ------------------------------------------------
            if lower_text.startswith("start-capture") or lower_text.startswith("start capture"):
                parts = raw_text.split(maxsplit=1)
                
                parsed_seconds = 600
                text_desc = "10 minute(s)"
                note = ""

                # If user passed arguments: e.g. "start-capture 5m Chiller Check"
                if len(parts) > 1:
                    parsed_seconds, text_desc, note = parse_schedule_args(parts[1])
                    if parsed_seconds is None:
                        reply_text(reply_token, f"❌ Command Error: {text_desc}\nExample: start-capture 5m Generator Load")
                        continue

                with state.state_lock:
                    state.capture_interval_seconds = parsed_seconds
                    state.schedule_note = note
                    state.schedule_count = 1  # Reset count to 1 for new session
                    state.auto_capture_enabled = True

                state.wake_event.set()
                
                confirm_msg = f"▶️ Scheduled capture started!\n• Interval: Every {text_desc}"
                if note:
                    confirm_msg += f"\n• Note: {note}"
                confirm_msg += f"\n• Capturing initial picture (#1) now."

                reply_text(reply_token, confirm_msg)
                threading.Thread(target=process_immediate_first_capture, daemon=True).start()

            elif lower_text in ["stop-capture", "stop capture"]:
                with state.state_lock:
                    state.auto_capture_enabled = False
                    count_summary = state.schedule_count
                    state.schedule_count = 0
                    state.schedule_note = ""
                state.wake_event.set()
                reply_text(reply_token, f"⏹️ Automated capture stopped. Completed {count_summary} capture(s).")

            # ------------------------------------------------
            # Command 2: stop-capture
            # ------------------------------------------------
            elif lower_text in ["stop-capture", "stop capture"]:
                with state.state_lock:
                    state.auto_capture_enabled = False
                state.wake_event.set()

                print("[State] Auto-capture STOPPED.")
                reply_text(reply_token, "⏹️ Automated capture stopped. Scheduled captures are paused.")

            # ------------------------------------------------
            # Command 3: capture [optional note]
            # ------------------------------------------------
            elif lower_text.startswith("capture"):
                parts = raw_text.split(maxsplit=1)
                comment = parts[1].strip() if len(parts) > 1 else ""

                print(f"[Webhook] Capture triggered with comment: '{comment}'")
                threading.Thread(
                    target=process_manual_trigger,
                    args=(reply_token, comment),
                    daemon=True,
                ).start()

            # ------------------------------------------------
            # Invalid Command Fallback
            # ------------------------------------------------
            else:
                error_msg = (
                    f"Command Error: '{raw_text}' is not a valid command.\n\n"
                    "Available commands:\n"
                    "• start-capture [time] (e.g. start-capture 30s, 10m, 1h, or 3600)\n"
                    "• stop-capture\n"
                    "• capture [optional note]"
                )
                reply_text(reply_token, error_msg)

    return "OK", 200


if __name__ == "__main__":
    scheduler_thread = threading.Thread(target=scheduled_worker, daemon=True)
    scheduler_thread.start()

    print("[*] Starting Webhook server on 127.0.0.1:5000...")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)