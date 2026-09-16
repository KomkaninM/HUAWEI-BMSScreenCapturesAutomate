import os
import uuid
from datetime import datetime
from mss import mss
from PIL import Image

def capture_screen_local() -> tuple[str, str]:
    """
    Captures primary screen using mss + Pillow.
    Saves as optimized JPEG in ~15-20ms.
    Returns (filename, formatted_timestamp).
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rand_token = uuid.uuid4().hex[:8]
    filename = f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{rand_token}.jpg"
    
    os.makedirs("screenshots", exist_ok=True)
    filepath = os.path.abspath(os.path.join("screenshots", filename))

    with mss() as sct:
        # sct.monitors[1] is the primary display (sct.monitors[0] is all monitors combined)
        primary_monitor = sct.monitors[1]
        sct_img = sct.grab(primary_monitor)

        # Convert BGRA raw buffer directly to PIL RGB Image
        img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        
        # Save as compressed JPEG (quality=80 reduces 4-6MB PNGs down to ~350KB)
        img.save(filepath, format="JPEG", quality=80, optimize=True)

    return filename, now_str