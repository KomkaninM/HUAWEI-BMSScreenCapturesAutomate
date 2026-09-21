import os
import re
import subprocess
import sys
import time
import requests
from dotenv import load_dotenv
from line_api import push_text

load_dotenv(override=True)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
TARGET_ID = os.getenv("USER_ID")

LINE_WEBHOOK_ENDPOINT_URL = "https://api.line.me/v2/bot/channel/webhook/endpoint"
LINE_WEBHOOK_TEST_URL = "https://api.line.me/v2/bot/channel/webhook/test"

line_headers = {
    "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def start_flask_server():
    """Starts the Flask server as a persistent subprocess."""
    print("[*] Starting local Flask server...")
    return subprocess.Popen([sys.executable, "server.py"])

def open_pinggy_tunnel():
    """Spawns a Pinggy SSH tunnel quickly using character-by-character reading."""
    print("[*] Establishing Pinggy SSH tunnel...")
    ssh_cmd = [
        "ssh",
        "-4",                               # Force IPv4 immediately
        "-T",                               # Disable pseudo-terminal allocation
        "-p", "443",
        "-R0:127.0.0.1:5000",
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        "a.pinggy.io"
    ]
    
    proc = subprocess.Popen(
        ssh_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=0
    )

    public_url = None
    start_time = time.time()
    accumulated_output = ""

    # Read exactly 1 character at a time so Python never blocks waiting for a large chunk
    while time.time() - start_time < 20:
        char = proc.stdout.read(1)
        if char:
            accumulated_output += char
            
            # Only run the regex once we start seeing URL-like text
            if "pinggy" in accumulated_output:
                match = re.search(r"https://[a-zA-Z0-9\-]+\.(free\.pinggy\.net|a\.pinggy\.link)", accumulated_output)
                if match:
                    public_url = match.group(0)
                    break
        elif proc.poll() is not None:
            break

    if not public_url:
        proc.terminate()
        raise RuntimeError("Failed to parse public Pinggy URL.")

    return proc, public_url

def sync_line_webhook(public_url):
    """Registers the new URL with the LINE API and verifies connectivity."""
    webhook_url = f"{public_url}/callback"
    print(f"[*] Updating LINE webhook: {webhook_url}")

    # 1. Update endpoint
    res = requests.put(
        LINE_WEBHOOK_ENDPOINT_URL,
        headers=line_headers,
        json={"endpoint": webhook_url},
        timeout=10
    )
    if res.status_code != 200:
        print(f"[!] Warning: Failed to set endpoint: {res.text}")
        return False

    # 2. Test endpoint connectivity
    time.sleep(1)
    test_res = requests.post(
        LINE_WEBHOOK_TEST_URL,
        headers=line_headers,
        json={"endpoint": webhook_url},
        timeout=10
    )
    return test_res.status_code == 200

def notify_flask_of_new_url(public_url):
    """Notifies the running Flask server of the updated Pinggy domain."""
    try:
        requests.post(
            "http://127.0.0.1:5000/internal/update-tunnel",
            json={"url": public_url},
            timeout=5
        )
    except Exception as e:
        print(f"[!] Could not notify local Flask server of new URL: {e}")

def main():
    flask_proc = start_flask_server()
    time.sleep(2)  # Give Flask time to bind port 5000

    tunnel_proc = None
    is_initial_start = True

    try:
        while True:
            try:
                # 1. Start or restart SSH tunnel
                tunnel_proc, public_url = open_pinggy_tunnel()
                print(f"[+] Tunnel Online: {public_url}")

                # 2. Notify Flask and LINE API
                notify_flask_of_new_url(public_url)
                webhook_ok = sync_line_webhook(public_url)

                if webhook_ok:
                    print("[+] LINE Webhook synced successfully.")
                    if is_initial_start:
                        push_text("🟢 BMS Screen Capture Bot is ONLINE!\nPC connected and ready for commands.")
                        is_initial_start = False
                    else:
                        push_text("🔄 Pinggy session renewed.\nBot remains active and ready for commands.")
                else:
                    print("[!] Webhook test failed to return status 200.")

                print("\n=======================================================")
                print(f" 🚀 Monitor active. Tunnel PID: {tunnel_proc.pid}")
                print(" Auto-reconnect supervisor will restart tunnel on exit.")
                print("=======================================================\n")

                # 3. Wait for the tunnel process to drop (e.g. 60 min timeout)
                tunnel_proc.wait()
                print("\n[!] Pinggy tunnel dropped. Initiating automatic reconnection in 5s...")
                time.sleep(5)

            except Exception as loop_err:
                print(f"[!] Error in tunnel connection loop: {loop_err}")
                print("[*] Retrying connection in 10 seconds...")
                time.sleep(10)

    except KeyboardInterrupt:
        print("\n[*] Stopping all services...")
    finally:
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if flask_proc and flask_proc.poll() is None:
            flask_proc.terminate()
        print("[+] Bot stopped cleanly.")

if __name__ == "__main__":
    main()