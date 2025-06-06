import os
import requests
import openai
import json
import base64
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# *** 1. Configure API keys and tokens ***
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# Cloudflare R2 credentials from environment
R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_PUBLIC_DOMAIN = os.getenv("R2_PUBLIC_DOMAIN")

# *** 2. Generate daily prompt and caption using GPT-4o ***
def generate_prompt_and_caption(client):
    """
    Calls GPT-4o to get a new scene, caption, and hashtags.
    """
    print("Generating scene, caption, and hashtags with GPT-4o...")
    system_msg = (
        "You are an AI assistant that generates creative ideas for 'Dreamy Monotone Worlds' illustrations. "
        "Your goal is to create a unique, whimsical, and peaceful scene description each day for a bedtime-themed post. "
        "The scenes should be minimalist and imaginative. Think about animals, magical objects, or serene landscapes. "
        "Avoid repeating subjects. Be creative and diverse. "
        "Alongside the scene, create a short, motivational caption with a calm, dreamy tone. "
        "Finally, provide a string of 5-7 relevant hashtags, starting with a # and separated by spaces (e.g., '#aiart #dreamy #illustration #animation #digitalart')."
        "You must respond ONLY in JSON format with three keys: 'description', 'caption', and 'hashtags'."
    )
    user_msg = "Please generate a new scene description, a caption, and hashtags for today's post."
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            response_format={"type": "json_object"},
            temperature=0.8
        )
        content = response.choices[0].message.content
        print("Successfully got response from GPT-4o.")
    except Exception as e:
        print(f"Error calling OpenAI API for text generation: {e}")
        return None, None, None

    try:
        result = json.loads(content)
        description = result.get("description", "").strip()
        caption = result.get("caption", "").strip()
        hashtags = result.get("hashtags", "").strip()
        if not description or not caption or not hashtags:
            raise ValueError("Missing 'description', 'caption', or 'hashtags' in GPT-4o response.")
        return description, caption, hashtags
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse GPT-4o output. Error: {e}\nRaw content: {content}")
        return None, None, None

# *** 3. Use gpt-image-1 to generate an image and save it to a file ***
def generate_image_file(client, description, output_path="pending_image.png"):
    """
    Calls gpt-image-1, decodes the base64 response, and saves it to a file.
    Returns the path to the saved image.
    """
    print("Generating image with gpt-image-1...")
    style_description = (
        f"A whimsical digital illustration of: {description}. "
        "Style: minimalist, clean, flat vector art. "
        "Palette: calming, monotone, shades of deep color and soft, glowing bright colors. "
        "Mood: cozy, serene, dreamlike, perfect for a bedtime story. Centered composition."
    )
    
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=style_description,
            n=1,
            size="1024x1024",
            quality="medium",
        )
        
        b64_data = response.data[0].b64_json
        image_bytes = base64.b64decode(b64_data)
        
        with open(output_path, "wb") as f:
            f.write(image_bytes)
            
        print(f"Image saved successfully to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error calling gpt-image-1 API for image generation. Details: {repr(e)}")
        return None

# *** 4. Upload image to Cloudflare R2 ***
def upload_image_to_r2(image_path):
    """
    Uploads the specified image file to a Cloudflare R2 bucket.
    Returns the public URL of the uploaded image.
    """
    print("Verifying Cloudflare R2 credentials...")
    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_PUBLIC_DOMAIN]):
        print("Error: Missing one or more Cloudflare R2 environment variables. Please check repository secrets.")
        return None

    try:
        # Construct the R2 endpoint URL
        r2_endpoint_url = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        
        print("Connecting to Cloudflare R2...")
        # Create a boto3 client for R2
        s3_client = boto3.client(
            service_name='s3',
            endpoint_url=r2_endpoint_url,
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name='auto', # Required by boto3, 'auto' is fine for R2
        )

        image_filename = os.path.basename(image_path)
        print(f"Uploading '{image_filename}' to R2 bucket '{R2_BUCKET_NAME}'...")

        # Upload the file
        with open(image_path, "rb") as f:
            s3_client.upload_fileobj(
                f,
                R2_BUCKET_NAME,
                image_filename,
                ExtraArgs={'ContentType': 'image/png'}
            )
        
        # Construct the final public URL
        public_url = f"https://{R2_PUBLIC_DOMAIN}/{image_filename}"
        print(f"✅ Successfully uploaded to R2. Public URL: {public_url}")
        return public_url

    except ClientError as e:
        # Catch specific boto3 client errors for better diagnostics
        error_code = e.response.get("Error", {}).get("Code")
        print(f"A client-side error occurred: {error_code}. Check your credentials and bucket settings.")
        print(f"Full error: {repr(e)}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during R2 upload: {repr(e)}")
        return None

# *** 5. Save content to a file for the publishing workflow ***
def save_content_for_approval(image_url, caption, hashtags):
    """
    Saves the generated content metadata to a JSON file.
    The key is now 'image_url' instead of 'image_path'.
    """
    print("Saving content metadata to pending_post.json...")
    content = {
        "image_url": image_url,
        "caption": caption,
        "hashtags": hashtags
    }
    with open("pending_post.json", "w") as f:
        json.dump(content, f, indent=4)
    print("Content metadata saved.")

# *** 6. Send a Slack notification asking for approval ***
def send_approval_request_to_slack(image_url, caption, hashtags):
    """
    Sends a notification to Slack with a direct link to the published image.
    """
    print("Sending Slack notification for approval...")

    if not image_url:
        image_url = "https://via.placeholder.com/512.png?text=Image+Upload+Failed"
        
    message_text = (
        f"✨ *New Post Ready for Approval* ✨\n\n"
        f"*Caption:*\n{caption}\n\n"
        f"*Hashtags:*\n`{hashtags}`\n\n"
        f"To view the image, visit this URL:\n{image_url}\n\n"
        f"To proceed, go to your repository's *Actions* tab, click on the *'Daily TikTok Post Workflow'*, and run it manually.\n"
        f"🔹 Choose `publish` to post this content to TikTok.\n"
        f"🔹 Choose `regenerate` to discard this version and create a new one."
    )

    slack_payload = { "text": message_text }
    
    try:
        resp = requests.post(SLACK_WEBHOOK_URL, json=slack_payload)
        resp.raise_for_status()
        print("Slack notification sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Slack message: {e}")

# *** Main execution flow ***
def main():
    """Main function to handle command-line arguments."""
    import sys

    # Simple argument parsing
    if '--slack-only' in sys.argv:
        print("Running in Slack notification-only mode.")
        try:
            with open("pending_post.json", "r") as f:
                content = json.load(f)
            # The key is now 'image_url'
            image_url = content["image_url"]
            caption = content["caption"]
            hashtags = content["hashtags"]
            if SLACK_WEBHOOK_URL:
                send_approval_request_to_slack(image_url, caption, hashtags)
            else:
                print("SLACK_WEBHOOK_URL not set, skipping notification.")
        except Exception as e:
            print(f"Failed to read pending files or send notification. Error: {repr(e)}")
            exit(1)
        return

    # Default behavior: generate files
    print("Starting content generation script...")
    
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    
    description, caption, hashtags = generate_prompt_and_caption(client)
    if not description or not caption:
        print("Failed to get description/caption. Exiting.")
        exit(1)
    
    image_path = generate_image_file(client, description)
    if not image_path:
        print("Image generation failed. Exiting.")
        exit(1)
        
    # New step: Upload the generated image to Cloudflare R2
    image_url = upload_image_to_r2(image_path)
    if not image_url:
        print("Cloudflare R2 upload failed. Exiting.")
        exit(1)
        
    # The image file is no longer needed after upload, so we remove it
    try:
        os.remove(image_path)
        print(f"Removed local image file: {image_path}")
    except OSError as e:
        print(f"Error removing local image file: {e}")

    save_content_for_approval(image_url, caption, hashtags)
    
    # Conditionally skip Slack notification if --no-slack is passed
    if '--no-slack' in sys.argv:
        print("Skipping Slack notification as requested.")
    elif SLACK_WEBHOOK_URL:
        # This path is for local runs where you want immediate notification
        send_approval_request_to_slack(image_url, caption, hashtags)
    
    print("Content generation script finished successfully!")

if __name__ == "__main__":
    main() 