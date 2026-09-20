import os
import re
import subprocess
import sys
import time
import requests
from dotenv import load_dotenv
from line_api import push_text

# ----------------------------------------------------
# 1. Environment & Pre-flight Checks
# ----------------------------------------------------
load_dotenv()

TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
if not TOKEN:
    print("[-] Error: CHANNEL_ACCESS_TOKEN is missing from your .env file.")
    sys.exit(1)

python_exe = sys.executable

# ----------------------------------------------------
# 2. Start Pinggy SSH Tunnel
# ----------------------------------------------------
print("[1/4] Establishing secure Pinggy SSH tunnel...")

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

print("[*] Waiting for tunnel assignment...")
pinggy_url = None
start_time = time.time()

# Extract the assigned URL safely (handles binary/ANSI sequences)
while time.time() - start_time < 15:
    if pinggy_process.poll() is not None:
        break

    line_bytes = pinggy_process.stdout.readline()
    if line_bytes:
        line = line_bytes.decode("utf-8", errors="ignore")
        match = re.search(r"https://[a-zA-Z0-9\-]+(?:\.free\.pinggy\.net|\.run\.pinggy-free\.link)", line)
        if match:
            pinggy_url = match.group(0)
            break

    # Fallback to local status REST endpoint if SSH stdout buffer delays
    try:
        res = requests.get("http://127.0.0.1:4300/bin/status", timeout=0.5)
        if res.status_code == 200:
            urls = res.json().get("urls", [])
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
    print("[-] Failed to retrieve Pinggy URL. Please check your internet connection or firewall.")
    pinggy_process.terminate()
    sys.exit(1)

if not pinggy_url.startswith("http"):
    pinggy_url = f"https://{pinggy_url}"

webhook_url = f"{pinggy_url}/callback"
print(f"[+] Tunnel Online: {pinggy_url}")

# ----------------------------------------------------
# 3. Start Webhook Server (server.py)
# ----------------------------------------------------
print("[2/4] Starting Flask server with local image hosting...")

# Pass the public tunnel base URL into server.py via environment variable
server_env = os.environ.copy()
server_env["PUBLIC_TUNNEL_URL"] = pinggy_url

server_process = subprocess.Popen(
    [python_exe, "server.py"],
    env=server_env
)

# Allow Flask server a moment to bind to 127.0.0.1:5000
time.sleep(1.5)

# ----------------------------------------------------
# 4. Synchronize LINE Webhook Configuration
# ----------------------------------------------------
print("[3/4] Registering Webhook with LINE Platform...")
line_headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

update_res = requests.put(
    "https://api.line.me/v2/bot/channel/webhook/endpoint",
    headers=line_headers,
    json={"endpoint": webhook_url}
)

if update_res.status_code == 200:
    print(f"[+] Successfully registered endpoint: {webhook_url}")
else:
    print(f"[-] Failed to update LINE webhook ({update_res.status_code}): {update_res.text}")

print("[4/4] Verifying Webhook connectivity...")
test_res = requests.post(
    "https://api.line.me/v2/bot/channel/webhook/test",
    headers=line_headers,
    json={"endpoint": webhook_url}
)

if test_res.status_code == 200:
    print(f"[+] Webhook Test Passed: {test_res.status_code}")
    
    # ADD THIS EXACT LINE:
    push_text("🟢 BMS Screen Capture Bot is ONLINE!\nPC connected and ready for commands.")
else:
    print(f"[!] Warning: Test verification returned status {test_res.status_code}")

print("\n" + "=" * 55)
print(" 🚀 BMS Screen Capture Service is LIVE and Ready!")
print(f" Local Storage:   ./screenshots/")
print(f" Public Endpoint: {webhook_url}")
print(" Press Ctrl+C in this console to stop all services.")
print("=" * 55 + "\n")

# ----------------------------------------------------
# 5. Process Lifecycle Management
# ----------------------------------------------------
try:
    server_process.wait()
except KeyboardInterrupt:
    print("\n[!] Received shutdown signal. Cleaning up processes...")
    server_process.terminate()
    pinggy_process.terminate()
    server_process.wait()
    pinggy_process.wait()
    print("[+] All services stopped safely.")