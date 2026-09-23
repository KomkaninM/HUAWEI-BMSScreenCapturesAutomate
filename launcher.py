import os
import subprocess
import sys
import time
import requests
from dotenv import load_dotenv

# Fallback in case line_api imports fail from the root directory
try:
    from line_api import push_text
except ImportError:
    def push_text(msg):
        print(f"[Fallback Push] {msg}")

load_dotenv(override=True)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN")
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN")

# Dynamically read PORT (defaults to 5000)
PORT = int(os.getenv("PORT", 5000))
LOCAL_BASE_URL = f"http://127.0.0.1:{PORT}"

LINE_WEBHOOK_ENDPOINT_URL = "https://api.line.me/v2/bot/channel/webhook/endpoint"
LINE_WEBHOOK_TEST_URL = "https://api.line.me/v2/bot/channel/webhook/test"

line_headers = {
    "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def start_flask_server():
    print(f"[*] Starting local Flask server on port {PORT}...")
    # Locate server.py (handles if it's in src/ or current directory)
    server_path = "server.py"
    if not os.path.exists(server_path) and os.path.exists(os.path.join("src", "server.py")):
        server_path = os.path.join("src", "server.py")
        
    return subprocess.Popen([sys.executable, server_path])

def configure_ngrok_authtoken():
    if NGROK_AUTHTOKEN:
        print("[*] Applying Ngrok Authtoken from .env...")
        subprocess.run(
            [os.path.abspath("ngrok.exe"), "config", "add-authtoken", NGROK_AUTHTOKEN], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )

def open_ngrok_tunnel():
    if not NGROK_DOMAIN:
        raise ValueError("NGROK_DOMAIN is missing from your .env file!")
        
    print(f"[*] Establishing Ngrok Tunnel on {NGROK_DOMAIN}...")
    cmd = [
        os.path.abspath("ngrok.exe"),
        "http",
        f"--domain={NGROK_DOMAIN}",
        "--log=stderr",      
        "--log-level=error", 
        str(PORT)
    ]
    
    proc = subprocess.Popen(cmd)
    return proc, f"https://{NGROK_DOMAIN}"

def wait_for_flask(timeout=25):
    """Waits up to 'timeout' seconds for Flask to respond."""
    print(f"[*] Waiting for Flask server to finish booting...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # We just need any response from the server to know it's alive
            requests.get(f"{LOCAL_BASE_URL}/images/dummy", timeout=1)
            print("[+] Flask server is up and listening!")
            return True
        except requests.exceptions.ConnectionError:
            # Server isn't ready yet, wait 1 second and try again
            time.sleep(1)
        except Exception:
            # If we get a 404 or other HTTP error, the server is up!
            print("[+] Flask server is up and listening!")
            return True
    return False

def sync_line_webhook(public_url):
    webhook_url = f"{public_url}/callback"
    print(f"[*] Updating LINE webhook: {webhook_url}")

    try:
        requests.put(LINE_WEBHOOK_ENDPOINT_URL, headers=line_headers, json={"endpoint": webhook_url}, timeout=10)
        time.sleep(1)
        test_res = requests.post(LINE_WEBHOOK_TEST_URL, headers=line_headers, json={"endpoint": webhook_url}, timeout=10)
        return test_res.status_code == 200
    except Exception as e:
        print(f"[!] Webhook sync error: {e}")
        return False

def notify_flask_of_new_url(public_url):
    try:
        res = requests.post(f"{LOCAL_BASE_URL}/internal/update-tunnel", json={"url": public_url}, timeout=5)
        if res.status_code == 200:
            print("[+] Flask synced with current Ngrok tunnel URL.")
        else:
            print(f"[!] Flask tunnel sync failed with HTTP {res.status_code}")
    except Exception as e:
        print(f"[!] Could not notify local Flask server: {e}")

def main():
    configure_ngrok_authtoken()
    
    flask_proc = start_flask_server()
    
    # 1. Wait patiently for Flask to load PyAutoGUI/OpenCV before proceeding
    if not wait_for_flask(timeout=25):
        print("[!] Flask server did not start in time. Check for syntax or import errors in server.py.")
        flask_proc.terminate()
        return

    # 2. Start Ngrok only after Flask is fully up
    tunnel_proc, public_url = open_ngrok_tunnel()
    time.sleep(3) # Give Ngrok a few seconds to establish the network connection
    
    if tunnel_proc.poll() is not None:
        print("[!] Ngrok failed to start. Check error messages above.")
        flask_proc.terminate()
        return

    print(f"[+] Tunnel Online: {public_url}")

    notify_flask_of_new_url(public_url)
    
    if sync_line_webhook(public_url):
        print("[+] LINE Webhook synced successfully.")
        push_text("🟢 BMS Screen Capture Bot is ONLINE!\nReady for commands.")
    else:
        print("[!] Warning: Webhook registration check failed.")

    print("\n=======================================================")
    print(f" 🚀 Monitor active on Ngrok. PID: {tunnel_proc.pid}")
    print(f" URL: {public_url}")
    print(" Press CTRL+C to stop.")
    print("=======================================================\n")

    try:
        while True:
            if tunnel_proc.poll() is not None:
                print("\n[!] Ngrok process crashed or stopped unexpectedly.")
                break
            if flask_proc.poll() is not None:
                print("\n[!] Flask server process crashed or stopped unexpectedly.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Stopping services...")
    finally:
        if tunnel_proc and tunnel_proc.poll() is None:
            tunnel_proc.terminate()
        if flask_proc and flask_proc.poll() is None:
            flask_proc.terminate()
        print("[+] Stopped cleanly.")

if __name__ == "__main__":
    main()