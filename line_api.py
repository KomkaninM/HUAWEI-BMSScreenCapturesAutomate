import uuid
import requests
import config

def push_image(image_url: str, caption: str):
    """Pushes image to target user (used by scheduled loop)."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.CHANNEL_ACCESS_TOKEN}",
        "X-Line-Retry-Key": str(uuid.uuid4()),
    }
    payload = {
        "to": config.USER_ID,
        "messages": [
            {"type": "text", "text": caption},
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            },
        ],
    }
    requests.post(config.LINE_PUSH_URL, headers=headers, json=payload)


def reply_image(reply_token: str, image_url: str, caption: str):
    """Replies with an image message."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.CHANNEL_ACCESS_TOKEN}",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [
            {"type": "text", "text": caption},
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            },
        ],
    }
    requests.post(config.LINE_REPLY_URL, headers=headers, json=payload)


def reply_text(reply_token: str, message: str):
    """Replies with a simple status text message."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.CHANNEL_ACCESS_TOKEN}",
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}],
    }
    requests.post(config.LINE_REPLY_URL, headers=headers, json=payload)