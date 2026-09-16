import os
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("USER_ID")
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY")

if not CHANNEL_ACCESS_TOKEN or not USER_ID:
    raise ValueError("Missing CHANNEL_ACCESS_TOKEN or USER_ID in .env file.")

if not IMGBB_API_KEY:
    raise ValueError("Missing IMGBB_API_KEY in .env file.")

LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"
IMGBB_UPLOAD_URL = "https://api.imgbb.com/1/upload"