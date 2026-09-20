import requests
import config

def push_text(message: str) -> bool:
    """Sends a proactive push text message directly to your personal LINE user ID."""
    headers = {
        "Authorization": f"Bearer {config.CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "to": config.USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        res = requests.post(config.LINE_PUSH_URL, headers=headers, json=payload, timeout=5)
        return res.status_code == 200
    except requests.RequestException as e:
        print(f"[-] Failed to push text message: {e}")
        return False

def push_image(image_url: str, caption: str = "") -> bool:
    """Sends proactive push messages to LINE with text displayed BEFORE the image."""
    headers = {
        "Authorization": f"Bearer {config.CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    messages = []
    # 1. Add the text message first (if present)
    if caption:
        messages.append({"type": "text", "text": caption})
        
    # 2. Add the image second
    messages.append({
        "type": "image",
        "originalContentUrl": image_url,
        "previewImageUrl": image_url
    })

    payload = {
        "to": config.USER_ID,
        "messages": messages
    }
    try:
        res = requests.post(config.LINE_PUSH_URL, headers=headers, json=payload, timeout=10)
        return res.status_code == 200
    except requests.RequestException as e:
        print(f"[-] Failed to push image message: {e}")
        return False

def reply_text(reply_token: str, message: str) -> bool:
    """Replies directly to an incoming webhook message event with text."""
    headers = {
        "Authorization": f"Bearer {config.CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        res = requests.post(config.LINE_REPLY_URL, headers=headers, json=payload, timeout=5)
        return res.status_code == 200
    except requests.RequestException as e:
        print(f"[-] Failed to send reply text: {e}")
        return False

def reply_image(reply_token: str, image_url: str, caption: str = "") -> bool:
    """Replies to a webhook event with text displayed BEFORE the image."""
    headers = {
        "Authorization": f"Bearer {config.CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    messages = []
    # 1. Add the text message first (if present)
    if caption:
        messages.append({"type": "text", "text": caption})
        
    # 2. Add the image second
    messages.append({
        "type": "image",
        "originalContentUrl": image_url,
        "previewImageUrl": image_url
    })

    payload = {
        "replyToken": reply_token,
        "messages": messages
    }
    try:
        res = requests.post(config.LINE_REPLY_URL, headers=headers, json=payload, timeout=10)
        return res.status_code == 200
    except requests.RequestException as e:
        print(f"[-] Failed to send reply image: {e}")
        return False