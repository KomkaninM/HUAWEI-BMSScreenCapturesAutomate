import os
import re
import subprocess
import time
import sys
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")

if not TOKEN:
    raise ValueError("CHANNEL_ACCESS_TOKEN missing in .env")

# Ensure Python runs the virtual environment's executable
python_exe = sys.executable

print("[1/4] Starting main bot server...")
bot_process = subprocess.Popen([python_exe, "main.py"])

print("[2/4] Starting Pinggy tunnel...")
# x:debug:4300 instructs Pinggy to launch its local REST dashboard on port 4300
pinggy_cmd = [
    "ssh",
    "-p", "443",
    "-R0:127.0.0.1:5000",
    "-o", "StrictHostKeyChecking=no",
    "-o", "ServerAliveInterval=30",
    "a.pinggy.io",
    "x:debug:4300"
]

pinggy_process = subprocess.Popen(
    pinggy_cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT
)

print("[*] Waiting for Pinggy URL...")
pinggy_url = None

# Attempt 1: Read direct console output using safe raw bytes
start_time = time.time()
while time.time() - start_time < 12:
    # Check if process died
    if pinggy_process.poll() is not None:
        break

    line_bytes = pinggy_process.stdout.readline()
    if line_bytes:
        line = line_bytes.decode("utf-8", errors="ignore")
        match = re.search(r"https://[a-zA-Z0-9\-]+(?:\.free\.pinggy\.net|\.run\.pinggy-free\.link)", line)
        if match:
            pinggy_url = match.group(0)
            break

    # Attempt 2: Poll the local status API if port 4300 answered
    try:
        res = requests.get("http://127.0.0.1:4300/bin/status", timeout=0.5)
        if res.status_code == 200:
            data = res.json()
            urls = data.get("urls", [])
            for u in urls:
                if "pinggy" in u:
                    pinggy_url = u
                    break
            if pinggy_url:
                break
    except requests.RequestException:
        pass

    time.sleep(0.5)

if not pinggy_url:
    print("[-] Failed to capture Pinggy URL.")
    bot_process.terminate()
    pinggy_process.terminate()
    sys.exit(1)

if not pinggy_url.startswith("http"):
    pinggy_url = f"https://{pinggy_url}"

webhook_url = f"{pinggy_url}/callback"
print(f"[+] Tunnel online: {webhook_url}")

print("[3/4] Updating LINE Webhook endpoint automatically...")
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

update_res = requests.put(
    "https://api.line.me/v2/bot/channel/webhook/endpoint",
    headers=headers,
    json={"endpoint": webhook_url}
)

if update_res.status_code == 200:
    print("[+] LINE Webhook URL successfully updated!")
else:
    print(f"[-] Failed to update LINE webhook ({update_res.status_code}): {update_res.text}")

print("[4/4] Verifying Webhook connection...")
test_res = requests.post(
    "https://api.line.me/v2/bot/channel/webhook/test",
    headers=headers,
    json={"endpoint": webhook_url}
)

if test_res.status_code == 200:
    print(f"[+] Verification: {test_res.json()}")
else:
    print(f"[!] Test status {test_res.status_code}: {test_res.text}")

print("\nBot is online and ready for commands.")

try:
    bot_process.wait()
except KeyboardInterrupt:
    print("\nShutting down bot and tunnel...")
    bot_process.terminate()
    pinggy_process.terminate()