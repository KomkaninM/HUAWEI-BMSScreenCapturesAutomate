import json
import os
import sys
import time
from pathlib import Path
from pynput import mouse, keyboard

# Ensure root imports resolve properly
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import config
from macro_player import run_macro

DEFAULT_POST_DELAY = 0.3
MACROS_DIR = Path(config.MACROS_DIR)
BASE_MACRO_FILE = MACROS_DIR / "_base.json"

events = []
char_buffer = []
recording = False
stop_requested = False


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
        print(f"  📝 Word captured: \"{word}\"")
        char_buffer = []


def on_click(x, y, button, pressed):
    if not recording:
        return
    if pressed:
        flush_buffer()
        btn_str = "left" if button == mouse.Button.left else "right"
        events.append({
            "action": "click_coord",
            "x": int(x),
            "y": int(y),
            "button": btn_str,
            "post_delay": DEFAULT_POST_DELAY
        })
        print(f"  🖱️ Click at ({int(x)}, {int(y)}) [{btn_str}]")


def on_press(key):
    global recording, stop_requested

    # Press F8 to begin recording generator steps
    if key == keyboard.Key.f8 and not recording:
        recording = True
        print("\n🔴 [RECORDING STARTED] Perform the generator steps on screen...")
        print("🔴 Press [F9] or [ESC] when finished.\n")
        return

    # Press F9 or ESC to stop recording
    if (key == keyboard.Key.f9 or key == keyboard.Key.esc) and recording:
        flush_buffer()
        recording = False
        stop_requested = True
        print("\n⏹️ Recording finished.")
        return False

    if not recording:
        return

    # Handle Backspace buffer edits
    if key == keyboard.Key.backspace:
        if char_buffer:
            removed = char_buffer.pop()
            print(f"  ⌫ Backspace: removed '{removed}'")
        else:
            events.append({
                "action": "press_key",
                "key": "backspace",
                "post_delay": DEFAULT_POST_DELAY
            })
        return

    # Handle alphanumeric / typing characters
    if hasattr(key, "char") and key.char is not None:
        char_buffer.append(key.char)
        return

    # Handle spacebar
    if key == keyboard.Key.space:
        char_buffer.append(" ")
        return

    # Navigation / Functional keys (Enter, Tab, Up, Down, etc.)
    flush_buffer()

    # Ignore lone modifiers
    if key in (keyboard.Key.shift, keyboard.Key.shift_r,
               keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
               keyboard.Key.alt_l, keyboard.Key.alt_r):
        return

    events.append({
        "action": "press_key",
        "key": key.name,
        "post_delay": DEFAULT_POST_DELAY
    })
    print(f"  ⌨️ Key: [{key.name}]")


def load_base_macro():
    """Loads steps from _base.json."""
    if not BASE_MACRO_FILE.exists():
        raise FileNotFoundError(f"Missing base macro file: {BASE_MACRO_FILE}")

    with open(BASE_MACRO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("steps", [])


def adjust_click_delays(steps: list):
    """
    Finds the last two click_coord steps in the newly recorded sequence:
    - 2nd to last click -> post_delay = 0.7
    - Last click -> post_delay = 1.0
    """
    click_indices = [i for i, step in enumerate(steps) if step.get("action") == "click_coord"]
    
    if len(click_indices) >= 1:
        last_idx = click_indices[-1]
        steps[last_idx]["post_delay"] = 1.0
        print(f"  ⏱️ Set last click (step #{last_idx + 1}) post_delay to 1.0s")

    if len(click_indices) >= 2:
        second_last_idx = click_indices[-2]
        steps[second_last_idx]["post_delay"] = 0.7
        print(f"  ⏱️ Set 2nd last click (step #{second_last_idx + 1}) post_delay to 0.7s")


def record_subsequent_steps():
    """Starts mouse and keyboard listeners to capture generator steps."""
    global recording, events, char_buffer
    events = []
    char_buffer = []

    mouse_listener = mouse.Listener(on_click=on_click)
    keyboard_listener = keyboard.Listener(on_press=on_press)

    mouse_listener.start()
    keyboard_listener.start()

    print("\n---------------------------------------------------------")
    print("👉 Switch to the BMS window.")
    print("👉 Press [F8] when you are ready to record the generator steps.")
    print("👉 Press [F9] or [ESC] when finished.")
    print("---------------------------------------------------------")

    keyboard_listener.join()
    mouse_listener.stop()
    flush_buffer()

    # Apply the custom delay timing on the recorded clicks
    adjust_click_delays(events)

    return events


def main():
    print("=" * 60)
    print("🛠️  BMS GENERATOR MACRO BUILDER")
    print("=" * 60)

    gen_name = input("Enter new generator macro name (e.g., DH09D or Gen03): ").strip()
    if not gen_name:
        print("❌ Macro name cannot be empty.")
        return

    if not gen_name.endswith(".json"):
        gen_name += ".json"

    output_path = MACROS_DIR / gen_name

    # 1. Load base steps
    print(f"\n[*] Step 1: Loading baseline steps from '{BASE_MACRO_FILE.name}'...")
    try:
        base_steps = load_base_macro()
        print(f"    Loaded {len(base_steps)} steps from _base.json.")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 2. Run the base macro to set up the screen
    print(f"[*] Step 2: Executing '{BASE_MACRO_FILE.name}' to reset BMS view...")
    success = run_macro(BASE_MACRO_FILE)
    if not success:
        print("❌ Base macro execution failed. Aborting.")
        return

    time.sleep(1.0)

    # 3. Record new generator steps
    print("\n[*] Step 3: Recording new generator navigation...")
    new_steps = record_subsequent_steps()

    if not new_steps:
        print("⚠️ No new steps were recorded. Aborted without saving.")
        return

    # 4. Combine and save as a new JSON macro
    combined_steps = base_steps + new_steps

    macro_payload = {
        "name": f"Generator Macro - {Path(gen_name).stem}",
        "description": f"Generated from _base.json + custom steps on {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "default_post_delay": DEFAULT_POST_DELAY,
        "steps": combined_steps
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(macro_payload, f, indent=2)

    print("\n" + "=" * 60)
    print(f"🎉 Macro created successfully: {output_path.name}")
    print(f"📁 Saved to: {output_path}")
    print(f"📊 Total steps: {len(combined_steps)} ({len(base_steps)} base + {len(new_steps)} new)")
    print(f"💬 You can now run it from LINE via: macro {Path(gen_name).stem}")
    print("=" * 60)


if __name__ == "__main__":
    main()