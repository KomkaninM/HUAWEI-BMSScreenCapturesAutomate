import os
import pyautogui

# Anchor image cropped from the Schneider login screen (e.g., "Log in" button)
ANCHOR_PATH = os.path.abspath(os.path.join("assets", "login_anchor.png"))

def is_logged_out() -> bool:
    """
    Returns True if the Schneider login anchor image is visible on the screen.
    """
    if not os.path.exists(ANCHOR_PATH):
        print(f"[Detector Warning] Anchor file missing at {ANCHOR_PATH}")
        return False
        
    try:
        # confidence=0.8 requires opencv-python installed
        location = pyautogui.locateOnScreen(ANCHOR_PATH, confidence=0.8)
        return location is not None
    except Exception as e:
        # Fallback if opencv-python is not installed
        try:
            location = pyautogui.locateOnScreen(ANCHOR_PATH)
            return location is not None
        except Exception as inner_e:
            print(f"[Detector Error] {inner_e}")
            return False