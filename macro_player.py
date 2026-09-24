import json
import os
import time
from pathlib import Path
import pyautogui
from config import BASE_DIR, DEFAULT_LOGIN_MACRO, MACROS_DIR

pyautogui.FAILSAFE = True

def execute_step(step: dict, fallback_delay: float = 0.2):
    action = step.get("action")

    if action == "click_image":
        target = step.get("target")
        conf = float(step.get("confidence", 0.8))
        target_path = BASE_DIR / target if not os.path.isabs(target) else Path(target)
        if not target_path.exists():
            raise FileNotFoundError(f"Anchor image not found: {target_path}")

        loc = pyautogui.locateCenterOnScreen(str(target_path), confidence=conf)
        if loc:
            pyautogui.click(loc)
        else:
            raise RuntimeError(f"Anchor image not found on screen: {target}")

    elif action == "click_coord":
        pyautogui.click(x=int(step["x"]), y=int(step["y"]), button=step.get("button", "left"))

    elif action == "type_text":
        pyautogui.write(step.get("text", ""), interval=0.02)
        if step.get("press_enter", False):
            pyautogui.press("enter")

    elif action == "press_key":
        pyautogui.press(step.get("key", "enter"))

    elif action == "hotkey":
        keys = step.get("keys", [])
        if keys:
            pyautogui.hotkey(*keys)

    elif action == "sleep":
        time.sleep(float(step.get("seconds", 1.0)))

    delay = float(step.get("post_delay", fallback_delay))
    if delay > 0:
        time.sleep(delay)


def execute_macro(macro_name: str | None = None) -> tuple[bool, str]:
    """
    Executes a JSON macro from scripts/macros/.
    If macro_name is None, falls back to DEFAULT_LOGIN_MACRO from .env.
    """
    selected_name = macro_name or DEFAULT_LOGIN_MACRO
    if not selected_name.endswith(".json"):
        selected_name += ".json"

    macro_path = MACROS_DIR / selected_name

    if not macro_path.is_file():
        return False, f"Macro file not found: {macro_path}"

    try:
        with open(macro_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        return False, f"Failed to parse JSON '{selected_name}': {e}"

    steps = data.get("steps", [])
    default_delay = float(data.get("default_post_delay", 0.2))
    name = data.get("name", selected_name)

    print(f"▶️ [Macro] Executing '{name}' ({len(steps)} steps) from {macro_path.name}...")

    for idx, step in enumerate(steps, 1):
        try:
            execute_step(step, fallback_delay=default_delay)
        except pyautogui.FailSafeException:
            return False, "Aborted by PyAutoGUI fail-safe."
        except Exception as e:
            return False, f"Step {idx} ({step.get('action')}) failed: {e}"

    return True, f"Macro '{name}' completed successfully."