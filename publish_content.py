import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# *** 1. Configure API keys and tokens ***
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN")

# *** 2. Refresh the TikTok Access Token ***
def refresh_tiktok_token():
    """
    Uses the refresh token to get a new access token.
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
        
        new_access_token = token_data.get('access_token')
        new_open_id = token_data.get('open_id')

        if not new_access_token or not new_open_id:
            print("❌ Failed to get new access token or open_id from response.")
            return None, None
            
        print("✅ New access token obtained successfully.")
        return new_access_token, new_open_id
        
    except requests.exceptions.RequestException as e:
        print("❌ An error occurred while refreshing the access token.")
        print(f"Status Code: {e.response.status_code}")
        print(f"Response: {e.response.text}")
        return None, None

# *** 3. Load content from the approval file ***
def load_pending_content():
    """
    Loads the image URL, caption, and hashtags from the pending_post.json file.
    """
    print("Loading content from pending_post.json...")
    try:
        with open("pending_post.json", "r") as f:
            content = json.load(f)
            image_url = content.get("image_url")
            caption = content.get("caption")
            hashtags = content.get("hashtags")
            if not image_url or not caption or not hashtags:
                print("Error: pending_post.json is missing 'image_url', 'caption', or 'hashtags'.")
                return None, None, None
            print("Content loaded successfully.")
            return image_url, caption, hashtags
    except FileNotFoundError:
        print("Error: pending_post.json not found. Was content generated first?")
        return None, None, None
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from pending_post.json.")
        return None, None, None

# *** 4. Post the image and caption to TikTok ***
def post_to_tiktok(access_token, open_id, image_url, caption, hashtags):
    """
    Posts the generated image and caption to TikTok using the Content Posting API.
    """
    print("Initiating post to TikTok...")
    
    full_caption = f"{caption}\n\n{hashtags}"

    endpoint = "https://open.tiktokapis.com/v2/post/publish/content/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    payload = {
        "post_info": {
            "title": caption[:2200],
            "description": full_caption,
            "disable_comment": False,
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "auto_add_music": True
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": 1,
            "photo_images": [image_url]
        },
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO"
    }
    
    try:
        resp = requests.post(endpoint, headers=headers, json=payload)
        resp.raise_for_status()
        result = resp.json()

        if result.get("error", {}).get("code", "ok").lower() == "ok":
            publish_id = result.get("data", {}).get("publish_id")
            print(f"TikTok post initiated successfully. Publish ID: {publish_id}")
            return True, publish_id
        else:
            err_msg = result.get("error", {}).get("message", "Unknown TikTok API error")
            print(f"TikTok API returned an error: {err_msg}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"Error posting to TikTok: {e}")
        if e.response:
            print(f"TikTok API response: {e.response.text}")
        return False, None

# *** 5. Send a final Slack notification ***
def send_final_slack_message(image_url, caption, hashtags, tiktok_status, publish_id):
    """
    Sends a final notification to Slack confirming the post status.
    """
    print("Sending final Slack notification...")
    status_text = "Successfully posted to TikTok ✔️" if tiktok_status else "Failed to post to TikTok ❌"
    if tiktok_status and publish_id:
        status_text += f" (Publish ID: {publish_id})"
        
    slack_payload = {
        "text": f"Post Published: {caption}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚀 *Post Published!* 🚀\n\n*Caption:*\n{caption}\n\n*Hashtags:*\n`{hashtags}`"
                }
            },
            {
                "type": "image",
                "image_url": image_url,
                "alt_text": "Published dream illustration"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Final Status:* {status_text}"
                }
            }
        ]
    }
    
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=slack_payload)
        resp.raise_for_status()
        print("Slack notification sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Slack message: {e}")

# *** Main execution flow ***
if __name__ == "__main__":
    print("Starting publishing script...")
    
    # First, get a fresh access token
    new_access_token, new_open_id = refresh_tiktok_token()
    if not new_access_token:
        print("Could not refresh TikTok token. Exiting.")
        exit(1)

    image_url, caption, hashtags = load_pending_content()
    
    if not image_url or not caption:
        print("Could not load content to publish. Exiting.")
        exit(1)
        
    success, publish_id = post_to_tiktok(new_access_token, new_open_id, image_url, caption, hashtags)
    
    send_final_slack_message(image_url, caption, hashtags, success, publish_id)
    
    if success:
        print("Publishing script finished successfully!")
    else:
        print("Publishing script finished with errors.") 