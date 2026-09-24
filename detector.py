import time
import threading
import pyautogui

from config import (
    LOGOUT_ANCHOR_PATH, 
    DETECTOR_INTERVAL_SEC, 
    CONFIDENCE_THRESHOLD
)
from macro_player import execute_macro


def is_logged_out():
    """Scans the screen once for the logout anchor."""
    if not LOGOUT_ANCHOR_PATH.exists():
        print(f"[Detector] ⚠️ Missing anchor image: {LOGOUT_ANCHOR_PATH}")
        return False

    try:
        loc = pyautogui.locateOnScreen(
            str(LOGOUT_ANCHOR_PATH), 
            confidence=CONFIDENCE_THRESHOLD
        )
        return loc is not None
    except Exception as e:
        print(f"[Detector] OpenCV matching error: {e}")
        return False


def detector_loop():
    """Continuous background loop for monitoring the screen."""
    print(f"[Detector] Started. Scanning every {DETECTOR_INTERVAL_SEC}s...")
    
    while True:
        try:
            if is_logged_out():
                print("[Detector] 🚨 Logout screen detected! Triggering auto-login...")
                
                # Execute the default macro from .env (no arguments needed)
                success, msg = execute_macro()
                
                if success:
                    print(f"[Detector] ✅ Re-login successful: {msg}")
                    # Sleep extra time to let the dashboard fully load before scanning again
                    time.sleep(15) 
                else:
                    print(f"[Detector] ❌ Re-login failed: {msg}")
                    # Sleep briefly before retrying so we don't spam the macro
                    time.sleep(10)
            else:
                pass # Still logged in, do nothing
                
        except Exception as e:
            print(f"[Detector] Unexpected loop error: {e}")
            
        time.sleep(DETECTOR_INTERVAL_SEC)


def start_detector_thread():
    """Spawns the detector loop in a daemon thread so it runs in the background."""
    thread = threading.Thread(target=detector_loop, daemon=True, name="LogoutDetector")
    thread.start()
    return thread