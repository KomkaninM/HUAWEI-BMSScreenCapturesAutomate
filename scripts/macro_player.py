import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("❌ Error: 'pyautogui' is not installed. Run: pip install pyautogui")
    sys.exit(1)

# Enable failsafe: slamming the cursor into any screen corner halts execution
pyautogui.FAILSAFE = True


def execute_step(step: dict, fallback_delay: float = 0.2):
    action = step.get("action")

    if action == "click_image":
        target = step.get("target")
        conf = float(step.get("confidence", 0.8))
        if not os.path.exists(target):
            raise FileNotFoundError(f"Anchor image not found: {target}")

        loc = pyautogui.locateCenterOnScreen(target, confidence=conf)
        if loc:
            pyautogui.click(loc)
        else:
            raise RuntimeError(f"Anchor image was not matched on screen: {target}")

    elif action == "click_coord":
        x = int(step["x"])
        y = int(step["y"])
        btn = step.get("button", "left")
        pyautogui.click(x=x, y=y, button=btn)

    elif action == "type_text":
        text = step.get("text", "")
        pyautogui.write(text, interval=0.02)
        if step.get("press_enter", False):
            pyautogui.press("enter")

    elif action == "press_key":
        key = step.get("key", "enter")
        pyautogui.press(key)

    elif action == "hotkey":
        keys = step.get("keys", [])
        if keys:
            pyautogui.hotkey(*keys)

    elif action == "sleep":
        sleep_duration = float(step.get("seconds", 1.0))
        time.sleep(sleep_duration)

    else:
        print(f"⚠️ Warning: Unrecognized action '{action}', skipping.")

    # Apply per-step post-delay (or default fallback)
    post_delay = float(step.get("post_delay", fallback_delay))
    if post_delay > 0:
        time.sleep(post_delay)


def run_macro(json_path: str | Path) -> bool:
    target_path = Path(json_path)

    if not target_path.is_file():
        print(f"❌ Error: Macro file does not exist: {target_path}")
        return False

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return False

    name = data.get("name", "Unnamed Macro")
    steps = data.get("steps", [])
    default_delay = float(data.get("default_post_delay", 0.2))

    print(f"▶️ Executing Macro: '{name}' ({len(steps)} steps)")

    for idx, step in enumerate(steps, 1):
        action_name = step.get("action")
        try:
            execute_step(step, fallback_delay=default_delay)
            print(f"  [{idx}/{len(steps)}] Step '{action_name}' executed.")
        except pyautogui.FailSafeException:
            print("\n🚨 Fail-safe triggered by mouse movement! Halting execution.")
            return False
        except Exception as e:
            print(f"\n❌ Step {idx} failed ({action_name}): {e}")
            return False

    print("✅ Macro executed successfully.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Standalone Pure JSON Macro Player")
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default="scripts/macros/login_bms.json",
        help="Path to JSON macro file (default: macros/login_bms.json)",
    )
    parser.add_argument(
        "-c",
        "--countdown",
        type=int,
        default=3,
        help="Seconds countdown before execution starts (default: 3)",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🕹️ PURE MACRO PLAYER")
    print(f"Target: {args.file}")
    print("=" * 60)

    if args.countdown > 0:
        print("Switch to the target BMS window now.")
        for s in range(args.countdown, 0, -1):
            print(f"Starting in {s}...", flush=True)
            time.sleep(1)
        print("🚀 Running...\n")

    success = run_macro(args.file)
    sys.exit(0 if success else 1)