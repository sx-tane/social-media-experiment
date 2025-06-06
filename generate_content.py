import os
import requests
import openai
import json
import base64
from dotenv import load_dotenv
from PIL import Image
import io

# Load environment variables from .env file
load_dotenv()

# *** 1. Configure API keys and tokens ***
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
# GitHub context for generating image preview URLs in Slack
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY") # E.g., 'user/repo'
GITHUB_REF_NAME = os.getenv("GITHUB_REF_NAME") # E.g., 'main'

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
def generate_image_file(client, description, output_path="pending_image.jpg"):
    """
    Calls gpt-image-1, decodes the base64 response, converts to JPEG, 
    and saves it to a file. Returns the path to the saved image.
    """
    print("Generating image with gpt-image-1...")
    style_description = (
        f"A whimsical digital illustration of: {description}. "
        "The style is minimalist, clean, flat vector art. "
        "Use a calming, monotone color palette, primarily in shades of deep blue and soft, glowing whites, inspired by the artist lulu._.sketch. "
        "The mood is cozy, serene, and dreamlike, perfect for a bedtime story. Centered composition."
    )
    
    try:
        response = client.images.generate(
            model="gpt-image-1",
            prompt=style_description,
            n=1,
            size="1024x1024",
            response_format="b64_json" # Ask for base64 data
        )
        
        b64_data = response.data[0].b64_json
        image_bytes = base64.b64decode(b64_data)
        
        # Convert from PNG bytes to JPEG bytes
        img = Image.open(io.BytesIO(image_bytes))
        # Ensure image is in RGB mode for JPEG saving
        if img.mode != 'RGB':
            img = img.convert('RGB')

        with open(output_path, "wb") as f:
            img.save(f, "JPEG", quality=95)
            
        print(f"Image saved successfully to {output_path}")
        return output_path
    except Exception as e:
        print(f"Error calling gpt-image-1 API for image generation. Details: {repr(e)}")
        return None

# *** 4. Save content to a file for the publishing workflow ***
def save_content_for_approval(image_path, caption, hashtags):
    """
    Saves the generated content metadata to a JSON file.
    """
    print("Saving content metadata to pending_post.json...")
    content = {
        "image_path": image_path,
        "caption": caption,
        "hashtags": hashtags
    }
    with open("pending_post.json", "w") as f:
        json.dump(content, f, indent=4)
    print("Content metadata saved.")

# *** 5. Send a Slack notification asking for approval ***
def send_approval_request_to_slack(image_path, caption, hashtags):
    """
    Sends a notification to Slack with a preview and instructions to approve.
    Constructs a public URL to the image based on GitHub context.
    """
    print("Sending Slack notification for approval...")

    image_url = "https://via.placeholder.com/512.png?text=Image+Preview+Unavailable"
    if GITHUB_REPOSITORY and GITHUB_REF_NAME and os.path.exists(image_path):
        image_url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/{GITHUB_REF_NAME}/{image_path}"
        print(f"Constructed Slack image preview URL: {image_url}")
    else:
        print("Could not construct GitHub URL for image preview. Using placeholder.")
        
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
            image_path = content["image_path"]
            caption = content["caption"]
            hashtags = content["hashtags"]
            if SLACK_WEBHOOK_URL:
                send_approval_request_to_slack(image_path, caption, hashtags)
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
        
    save_content_for_approval(image_path, caption, hashtags)
    
    # Conditionally skip Slack notification if --no-slack is passed
    if '--no-slack' in sys.argv:
        print("Skipping Slack notification as requested.")
    elif SLACK_WEBHOOK_URL:
        # This path is for local runs where you want immediate notification
        send_approval_request_to_slack(image_path, caption, hashtags)
    
    print("Content generation script finished successfully!")

if __name__ == "__main__":
    main() 