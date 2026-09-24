from pynput.mouse import Listener
import sys

def on_click(x, y, button, pressed):
    # We only care when the mouse button is pressed down, not released
    if pressed:
        print(f"pyautogui.click(x={int(x)}, y={int(y)})  # Clicked with {button}")

print("Listening for mouse clicks... (Press Ctrl+C in this terminal to stop)")

try:
    # Start listening to mouse events
    with Listener(on_click=on_click) as listener:
        listener.join()
except KeyboardInterrupt:
    print("\nExiting script.")
    sys.exit()