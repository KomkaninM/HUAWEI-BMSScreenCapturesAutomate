import pyautogui
import time
import os

ANCHOR = os.path.abspath(os.path.join("assets", "login_anchor.png"))

print("Switch to the Schneider BMS login screen now...")
time.sleep(3) # Gives you 3 seconds to bring up the login screen

if not os.path.exists(ANCHOR):
    print(f"❌ ERROR: Anchor image not found at {ANCHOR}")
    exit()

print("🔍 Searching for login anchor...")

try:
    # Test 1: Fuzzy matching (Recommended)
    location = pyautogui.locateOnScreen(ANCHOR, confidence=0.8)
    if location:
        print(f"✅ FOUND (Fuzzy Match)! Coordinates: {location}")
    else:
        print("❌ NOT FOUND with confidence=0.8")
except Exception as e:
    print(f"⚠️ OpenCV Error: {e}")
    print("Trying exact pixel match instead...")

    # Test 2: Exact matching (Fallback)
    try:
        exact = pyautogui.locateOnScreen(ANCHOR)
        if exact:
            print(f"✅ FOUND (Exact Match)! Coordinates: {exact}")
        else:
            print("❌ NOT FOUND with exact match.")
    except Exception as e2:
        print(f"❌ Exact match failed completely: {e2}")