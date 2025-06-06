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

def post_to_tiktok(access_token, image_path, caption, hashtags):
    """
    Posts the generated image and caption to TikTok using direct file upload.
    """
    print("Initiating post to TikTok with file upload...")
    # 1. Initialize the post to get an upload URL
    init_url = "https://open.tiktokapis.com/v2/post/publish/content/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    # Get the size of the image to include in the payload
    try:
        image_size = os.path.getsize(image_path)
    except OSError as e:
        print(f"Could not get size of image file: {e}")
        return False, None

    payload = {
        "post_info": {
            "title": (caption + " " + hashtags)[:2200],
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_comment": False,
            "auto_add_music": True
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "photo_size": image_size
        },
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO"
    }

    print(f"Sending initialization payload: {json.dumps(payload, indent=2)}")

    try:
        init_resp = requests.post(init_url, headers=headers, json=payload)
        init_resp.raise_for_status()
        init_result = init_resp.json()

        if init_result.get("error", {}).get("code", "ok").lower() != "ok":
            err_msg = init_result.get("error", {}).get("message", "Unknown TikTok API error during init")
            print(f"TikTok API returned an error: {err_msg}")
            return False, None
        
        upload_url = init_result.get("data", {}).get("upload_url")
        publish_id = init_result.get("data", {}).get("publish_id")
        print(f"Successfully initiated post. Publish ID: {publish_id}")
        
        # 2. Upload the image file to the provided URL
        print(f"Uploading image file to: {upload_url}")
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        upload_headers = {'Content-Type': 'image/png'}
        upload_resp = requests.put(upload_url, headers=upload_headers, data=image_data)
        upload_resp.raise_for_status()
        
        print("Image file uploaded successfully.")
        # NOTE: With direct post, the upload is sufficient. No need to check status.
        return True, publish_id

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
        image_path = content["image_path"]
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

    # 3. Post to TikTok
    success, publish_id = post_to_tiktok(access_token, image_path, caption, hashtags)

    # 4. Notify via Slack
    # Construct the GitHub URL for the final notification
    github_repo = os.getenv("GITHUB_REPOSITORY")
    github_ref = os.getenv("GITHUB_REF_NAME")
    final_image_url = f"https://raw.githubusercontent.com/{github_repo}/{github_ref}/{image_path}" if github_repo and github_ref else "https://via.placeholder.com/512.png?text=Image"
    
    if SLACK_WEBHOOK_URL:
        send_slack_message(success, publish_id, caption, final_image_url)
    else:
        print("SLACK_WEBHOOK_URL not set, skipping final notification.")

    if success:
        print("Script finished successfully!")
    else:
        print("Script finished with errors.")
        exit(1) 