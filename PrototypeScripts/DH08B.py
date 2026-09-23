import pyautogui
import time

# Safety features:
# Move mouse to any corner of the screen to abort the script immediately
pyautogui.FAILSAFE = True
# Small default pause after each PyAutoGUI call
pyautogui.PAUSE = 0.2


def click_and_type(x: int, y: int, text: str, interval: float = 0.05, delay_after: float = 0.3):
    """
    Clicks on the specified (x, y) coordinates and types the given text.
    
    :param x: Target X coordinate
    :param y: Target Y coordinate
    :param text: Text string to type
    :param interval: Delay in seconds between each keystroke
    :param delay_after: Delay in seconds after typing completes
    """
    pyautogui.click(x=x, y=y)
    pyautogui.typewrite(text, interval=interval)
    time.sleep(delay_after)


def main():
    # Grace period before the automation starts so you can switch windows if needed
    print("Starting automation in 3 seconds... (Move mouse to screen corner to abort)")
    time.sleep(3)

    # 1. Login credentials
    click_and_type(1769, 1104, "Huawei")
    click_and_type(1769, 1251, "Huawei@1234")

    # 2. Press Enter to submit & wait 1 second
    pyautogui.press('enter')
    time.sleep(1.0)

    # 3. Action sequence
    pyautogui.click(x=715, y=708)
    pyautogui.click(x=702, y=624)
    pyautogui.click(x=702, y=624)
    pyautogui.click(x=713, y=684)
    pyautogui.click(x=2982, y=1371)
    time.sleep(0.5)
    pyautogui.click(x=2982, y=1371)
    time.sleep(0.5)
    pyautogui.click(x=856, y=574)
    # time.sleep(2)
    # pyautogui.click(x=77, y=273)

    print("Sequence completed successfully.")


if __name__ == "__main__":
    main()