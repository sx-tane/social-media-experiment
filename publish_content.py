import os
import requests
import json
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
# The script now requires a long-lived refresh token.
TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN")

# --- Helper Functions ---
def get_access_token():
    """
    Refreshes the access token using the refresh token.
    Returns the new access token, or None on failure.
    """
    print("Refreshing TikTok access token...")
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    payload = {
        'client_key': TIKTOK_CLIENT_KEY,
        'client_secret': TIKTOK_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': TIKTOK_REFRESH_TOKEN,
    }
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        token_data = response.json()
        
        if "access_token" in token_data:
            print("Successfully refreshed access token.")
            return token_data["access_token"]
        else:
            print(f"Error refreshing token. Response: {token_data}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error refreshing access token: {e}")
        if e.response:
            print(f"API Response: {e.response.text}")
        return None

def query_creator_info(access_token):
    """
    Queries the Creator Info endpoint to get available privacy options.
    """
    print("Querying creator info as required by TikTok API...")
    url = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data.get("error", {}).get("code", "ok").lower() == "ok":
            creator_info = data.get("data", {})
            print(f"Successfully queried creator info: {creator_info}")
            return creator_info
        else:
            print(f"Error querying creator info: {data.get('error')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling creator info endpoint: {e}")
        if e.response:
            print(f"API Response: {e.response.text}")
        return None

def post_to_tiktok(access_token, image_url, caption, hashtags, privacy_level):
    """
    Posts the generated image to TikTok using the PULL_FROM_URL method.
    The image is now referenced by a public URL from Cloudflare R2.
    """
    print("Initiating post to TikTok via PULL_FROM_URL...")
    print(f"--> Using public image URL: {image_url}")

    endpoint = "https://open.tiktokapis.com/v2/post/publish/content/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    # Per TikTok docs, title is short, description is long.
    title = (caption[:85] + '...') if len(caption) > 88 else caption
    full_description = f"{caption}\n\n{hashtags}"

    payload = {
        "post_info": {
            "title": title,
            "description": full_description,
            "disable_comment": False,
            "privacy_level": privacy_level,
            "auto_add_music": True
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": 0,
            "photo_images": [image_url]
        },
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO"
    }

    print("Sending TikTok API payload:")
    print(json.dumps(payload, indent=2))

    try:
        resp = requests.post(endpoint, headers=headers, json=payload)
        resp.raise_for_status()
        result = resp.json()

        if result.get("error", {}).get("code", "ok").lower() == "ok":
            publish_id = result.get("data", {}).get("publish_id")
            print(f"✅ TikTok post initiated successfully. Publish ID: {publish_id}")
            return True, publish_id
        else:
            err_msg = result.get("error", {}).get("message", "Unknown TikTok API error")
            print(f"TikTok API returned an error: {err_msg}")
            print(f"Full error object: {result.get('error')}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"Error posting to TikTok: {e}")
        if e.response:
            print(f"TikTok API raw error response: {e.response.text}")
        return False, None

def send_slack_message(status, publish_id, caption, image_url):
    """
    Sends a final status notification to a Slack channel.
    """
    print("Sending final Slack notification...")
    status_text = "Successfully posted to TikTok ✔️" if status else "Failed to post to TikTok ❌"
    if status and publish_id:
        status_text += f" (Publish ID: {publish_id})"
        
    message_text = (
        f"**Publishing Result** ✨\n\n"
        f"*Caption:*\n{caption}\n\n"
        f"*Status:* {status_text}\n\n"
        f"<{image_url}|View the post source image here>"
    )

    slack_payload = { "text": message_text }
    
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=slack_payload)
        resp.raise_for_status()
        print("Slack notification sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Slack message: {e}")

# *** Main execution flow ***
if __name__ == "__main__":
    print("Starting publishing script...")

    # 1. Load content from the pending file
    try:
        with open("pending_post.json", "r") as f:
            content = json.load(f)
        # The key is now 'image_url' and contains a full public URL
        image_url = content["image_url"]
        caption = content["caption"]
        hashtags = content["hashtags"]
    except (FileNotFoundError, KeyError) as e:
        print(f"Error: Could not read 'pending_post.json' or file is invalid. {e}")
        # Notify Slack about the failure if possible
        send_slack_message(False, None, "Could not find pending post file.", "https://via.placeholder.com/512.png?text=Error")
        exit(1)

    # 2. Get a fresh access token
    access_token = get_access_token()
    if not access_token:
        print("Failed to get access token, cannot publish. Exiting.")
        send_slack_message(False, None, caption, "https://via.placeholder.com/512.png?text=Auth+Error")
        exit(1)
        
    # 3. Query creator info to verify permissions
    creator_info = query_creator_info(access_token)
    if not creator_info:
        send_slack_message(False, None, caption, "https://via.placeholder.com/512.png?text=Creator+Info+Error")
        exit(1)

    # For an unaudited app, we must use one of the allowed levels, SELF_ONLY is the safest.
    allowed_privacy_levels = creator_info.get("privacy_level_options", [])
    print(f"Available privacy options: {allowed_privacy_levels}")
    
    privacy_level_to_use = "SELF_ONLY"
    if privacy_level_to_use not in allowed_privacy_levels:
        print(f"Error: '{privacy_level_to_use}' is not in the allowed list from TikTok: {allowed_privacy_levels}")
        send_slack_message(False, None, "Publishing failed: Privacy level mismatch.", "https://via.placeholder.com/512.png?text=Privacy+Error")
        exit(1)

    # 4. Post to TikTok
    success, publish_id = post_to_tiktok(access_token, image_url, caption, hashtags, privacy_level_to_use)

    # 5. Notify via Slack
    # We now use the image_url directly from the pending file for the notification
    if SLACK_WEBHOOK_URL:
        send_slack_message(success, publish_id, caption, image_url)
    else:
        print("SLACK_WEBHOOK_URL not set, skipping final notification.")

    if success:
        print("Script finished successfully!")
    else:
        print("Script finished with errors.")
        exit(1) 