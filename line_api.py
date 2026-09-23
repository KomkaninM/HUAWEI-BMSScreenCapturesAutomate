import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)

CHANNEL_ACCESS_TOKEN = os.getenv("CHANNEL_ACCESS_TOKEN")
# Reads GROUP_ID first; if empty, falls back to USER_ID
TARGET_ID = os.getenv("GROUP_ID") or os.getenv("USER_ID") 

LINE_PUSH_ENDPOINT = "https://api.line.me/v2/bot/message/push"
LINE_REPLY_ENDPOINT = "https://api.line.me/v2/bot/message/reply"

headers = {
    "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

def push_image(image_url: str, caption: str = "Screen Capture"):
    if not image_url:
        push_text(caption)
        return

    if not TARGET_ID:
        print("❌ [LINE API Error] Cannot push! GROUP_ID or USER_ID is missing in .env")
        return

    payload = {
        "to": TARGET_ID,
        "messages": [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url
            },
            {
                "type": "text",
                "text": caption
            }
        ]
    }
    try:
        response = requests.post(LINE_PUSH_ENDPOINT, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"❌ [LINE Push Error] Failed to push to {TARGET_ID}")
            print(f"❌ [LINE Push Error] Code: {response.status_code} | Details: {response.text}")
    except Exception as e:
        print(f"[Line API Exception] {e}")

def push_text(text: str):
    if not TARGET_ID:
        print("❌ [LINE API Error] Cannot push text! TARGET_ID is missing in .env")
        return
    payload = {
        "to": TARGET_ID,
        "messages": [{"type": "text", "text": text}]
    }
    try:
        response = requests.post(LINE_PUSH_ENDPOINT, headers=headers, json=payload)
        if response.status_code != 200:
            print(f"❌ [LINE Push Error] Code: {response.status_code} | Details: {response.text}")
    except Exception as e:
        print(f"[Line API Exception] {e}")

def reply_image(reply_token: str, image_url: str, caption: str = "Screen Capture"):
    payload = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url
            },
            {
                "type": "text",
                "text": caption
            }
        ]
    }
    requests.post(LINE_REPLY_ENDPOINT, headers=headers, json=payload)

def reply_text(reply_token: str, text: str):
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(LINE_REPLY_ENDPOINT, headers=headers, json=payload)