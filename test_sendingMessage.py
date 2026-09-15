import os
import uuid
import requests

from dotenv import load_dotenv

load_dotenv()

token_id = os.getenv("TOKEN_ID")

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
USER_ID = os.getenv("USER_ID")

url = "https://api.line.me/v2/bot/message/push"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    "X-Line-Retry-Key": str(uuid.uuid4()),
}

payload = {
    "to": USER_ID,
    "messages": [
        {"type": "text", "text": "Hello, world1"},
        {"type": "text", "text": "Hello, world2"},
    ],
}

res = requests.post(url, headers=headers, json=payload)
print(res.status_code, res.text)