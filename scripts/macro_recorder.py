import json
import time
from pathlib import Path
from pynput import mouse, keyboard

DEFAULT_POST_DELAY = 0.3

# Resolves to the 'scripts' folder, then looks for 'macros/recorder.json'
SCRIPTS_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = SCRIPTS_DIR / "macros" / "recorder.json"

events = []
char_buffer = []
recording = True

def flush_buffer():
    """Flushes accumulated keystrokes into a single word string step."""
    global char_buffer
    if char_buffer:
        word = "".join(char_buffer)
        events.append({
            "action": "type_text",
            "text": word,
            "post_delay": DEFAULT_POST_DELAY
        })
        print(f"📝 Word captured: \"{word}\"")
        char_buffer = []

# --- Mouse Callbacks ---
def on_click(x, y, button, pressed):
    if not recording:
        return False
    if pressed:
        # A click terminates word typing and commits the buffer
        flush_buffer()
        
        btn_str = "left" if button == mouse.Button.left else "right"
        events.append({
            "action": "click_coord",
            "x": int(x),
            "y": int(y),
            "button": btn_str,
            "post_delay": DEFAULT_POST_DELAY
        })
        print(f"🖱️ Click at ({int(x)}, {int(y)}) [{btn_str}]")

# --- Keyboard Callbacks ---
def on_press(key):
    global recording
    if key == keyboard.Key.esc:
        print("\n⏹️ Recording stopped via [ESC].")
        flush_buffer()
        recording = False
        return False

    # Backspace handles character buffer edits while typing
    if key == keyboard.Key.backspace:
        if char_buffer:
            removed = char_buffer.pop()
            print(f"⌫ Backspace: removed '{removed}'")
        else:
            events.append({
                "action": "press_key",
                "key": "backspace",
                "post_delay": DEFAULT_POST_DELAY
            })
        return

    # Printable alphanumeric / symbol characters
    if hasattr(key, "char") and key.char is not None:
        char_buffer.append(key.char)
        return

    # Spacebar handling (part of natural text or separate token)
    if key == keyboard.Key.space:
        char_buffer.append(" ")
        return

    # Navigation / Control keys (Enter, Tab, Up, Down, etc.)
    flush_buffer()
    
    # Ignore modifier-only keypresses (shift, ctrl, alt) so they don't produce empty steps
    if key in (keyboard.Key.shift, keyboard.Key.shift_r,
               keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
               keyboard.Key.alt_l, keyboard.Key.alt_r):
        return

    events.append({
        "action": "press_key",
        "key": key.name,
        "post_delay": DEFAULT_POST_DELAY
    })
    print(f"⌨️ Key: [{key.name}]")

def main():
    print("=" * 60)
    print("🎥 BMS MACRO RECORDER")
    print("=" * 60)
    print("1. Switch to your BMS login target.")
    print("2. Type words normally (e.g. 'HUA', 'Admin', passwords).")
    print("3. Tab, Enter, or Mouse Clicks flush the word automatically.")
    print("4. Press [ESC] when finished to save.")
    print("=" * 60)

    for i in range(3, 0, -1):
        print(f"Starting in {i}...")
        time.sleep(1)

    print("🔴 RECORDING... (Press ESC to stop)")

    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)

    mouse_listener.start()
    keyboard_listener.start()

    keyboard_listener.join()
    mouse_listener.stop()

    flush_buffer()

    macro_payload = {
        "name": "Recorded BMS Login",
        "description": f"Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "default_post_delay": DEFAULT_POST_DELAY,
        "steps": events
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(macro_payload, f, indent=2)

    print(f"\n✅ Saved {len(events)} steps to: {OUTPUT_FILE.resolve()}")

if __name__ == "__main__":
    main()