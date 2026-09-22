import os
import subprocess
import sys
import time
import requests
from dotenv import load_dotenv
from line_api import push_text

load_dotenv(override=True)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN")
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN") # <-- Added this

LINE_WEBHOOK_ENDPOINT_URL = "https://api.line.me/v2/bot/channel/webhook/endpoint"
LINE_WEBHOOK_TEST_URL = "https://api.line.me/v2/bot/channel/webhook/test"

line_headers = {
    "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def start_flask_server():
    print("[*] Starting local Flask server...")
    return subprocess.Popen([sys.executable, "server.py"])

def configure_ngrok_authtoken():
    # Automatically apply the token if it is provided in the .env file
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
        "5000"
    ]
    
    proc = subprocess.Popen(cmd)
    time.sleep(3) 
    
    public_url = f"https://{NGROK_DOMAIN}"
    return proc, public_url

def sync_line_webhook(public_url):
    webhook_url = f"{public_url}/callback"
    print(f"[*] Updating LINE webhook: {webhook_url}")

    requests.put(LINE_WEBHOOK_ENDPOINT_URL, headers=line_headers, json={"endpoint": webhook_url}, timeout=10)
    time.sleep(1)
    test_res = requests.post(LINE_WEBHOOK_TEST_URL, headers=line_headers, json={"endpoint": webhook_url}, timeout=10)
    return test_res.status_code == 200

def notify_flask_of_new_url(public_url):
    try:
        requests.post("http://127.0.0.1:5000/internal/update-tunnel", json={"url": public_url}, timeout=5)
    except Exception as e:
        print(f"[!] Could not notify local Flask server: {e}")

def main():
    # 1. Apply Authtoken first
    configure_ngrok_authtoken()
    
    flask_proc = start_flask_server()
    time.sleep(2)

    tunnel_proc = None
    try:
        tunnel_proc, public_url = open_ngrok_tunnel()
        
        if tunnel_proc.poll() is not None:
            print("[!] Ngrok failed to start. Check the error messages above.")
            return

        print(f"[+] Tunnel Online: {public_url}")

        notify_flask_of_new_url(public_url)
        if sync_line_webhook(public_url):
            print("[+] LINE Webhook synced successfully.")
            push_text("🟢 BMS Screen Capture Bot is ONLINE (Ngrok 24/7)!\nReady for commands.")
        else:
            print("[!] Warning: Webhook registration check failed.")

        print("\n=======================================================")
        print(f" 🚀 Monitor active on Ngrok. PID: {tunnel_proc.pid}")
        print(f" URL: {public_url}")
        print(" Press CTRL+C to stop.")
        print("=======================================================\n")

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