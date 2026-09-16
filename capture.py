import base64
import os
import subprocess
from datetime import datetime
import requests
import config

def take_native_screenshot(filepath: str) -> str:
    """Captures primary screen using built-in Windows System.Drawing & User32 DPI awareness."""
    abs_path = os.path.abspath(filepath)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    ps_command = f"""
    Add-Type -AssemblyName System.Windows.Forms,System.Drawing;

    $SetDpiDefinition = @'
    [System.Runtime.InteropServices.DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
'@
    $User32 = Add-Type -MemberDefinition $SetDpiDefinition -Name "User32" -Namespace "Win32" -PassThru;
    [Win32.User32]::SetProcessDPIAware() | Out-Null;

    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds;
    $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height;
    $graphics = [System.Drawing.Graphics]::FromImage($bmp);
    $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size);
    $bmp.Save('{abs_path}', [System.Drawing.Imaging.ImageFormat]::Png);
    $graphics.Dispose();
    $bmp.Dispose();
    """

    res = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_command],
        capture_output=True,
        text=True,
    )

    if res.returncode != 0:
        raise RuntimeError(f"PowerShell capture failed: {res.stderr.strip()}")

    return abs_path


def upload_to_imgbb(filepath: str) -> str:
    """Uploads local image and returns a direct HTTPS image URL."""
    with open(filepath, "rb") as f:
        payload = {
            "key": config.IMGBB_API_KEY,
            "image": base64.b64encode(f.read()).decode("utf-8"),
        }
        res = requests.post(config.IMGBB_UPLOAD_URL, data=payload)

    if res.status_code != 200:
        raise RuntimeError(f"ImgBB upload failed: {res.text}")

    return res.json()["data"]["url"]


def capture_and_upload() -> tuple[str, str]:
    """Helper: takes screenshot and uploads. Returns (image_url, timestamp_str)."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join("screenshots", f"shot_{timestamp}.png")

    take_native_screenshot(filepath)
    image_url = upload_to_imgbb(filepath)
    return image_url, now_str