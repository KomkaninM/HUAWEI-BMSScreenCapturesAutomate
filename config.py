import os
from pathlib import Path
from dotenv import load_dotenv

# --- Directory Setup ---
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from the .env file in the root directory
load_dotenv(BASE_DIR / ".env")

# --- LINE API Credentials ---
CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN", "")
USER_ID = os.getenv("USER_ID", "")
GROUP_ID = os.getenv("GROUP_ID", "")

# --- ngrok Settings ---
NGROK_AUTHTOKEN = os.getenv("NGROK_AUTHTOKEN", "")
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN", "")

# --- Server & Webhook Settings ---
PORT = int(os.getenv("PORT", 5000))
REPLY_UNKNOWN_COMMANDS = os.getenv("REPLY_UNKNOWN_COMMANDS", "False").strip().lower() in [
    "true",
    "1",
    "yes",
]

# --- Macro Configuration ---
DEFAULT_LOGIN_MACRO = os.getenv(
    "LOGIN_MACRO_SCRIPT", os.getenv("DEFAULT_LOGIN_MACRO", "login_bms.json")
)
MACROS_DIR = BASE_DIR / "scripts" / "macros"
DEFAULT_LOGIN_MACRO_PATH = MACROS_DIR / DEFAULT_LOGIN_MACRO

# --- Auto Logout Configuration ---
ENABLE_AUTO_LOGOUT = os.getenv("ENABLE_AUTO_LOGOUT", "False").strip().lower() in [
    "true",
    "1",
    "yes",
]
LOGOUT_MACRO_SCRIPT = os.getenv("LOGOUT_MACRO_SCRIPT", "logout.json")

# --- Detector Configuration ---
LOGOUT_ANCHOR_PATH = BASE_DIR / "assets" / "logout_anchor.png"
DETECTOR_INTERVAL_SEC = int(os.getenv("DETECTOR_INTERVAL_SEC", 10))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 0.8))