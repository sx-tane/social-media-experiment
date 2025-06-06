import os
import requests
import openai
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# *** 1. Configure API keys and tokens ***
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# Configure the OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# *** 2. Generate daily prompt and caption using GPT-4o ***
def generate_prompt_and_caption():
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

# *** 3. Use gpt-image-1 to generate an image based on the description ***
def generate_image(description):
    """
    Calls gpt-image-1 to generate an image from the provided description.
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
            quality="hd",
        )
        image_url = response.data[0].url
        print(f"Image generated successfully: {image_url}")
        return image_url
    except Exception as e:
        print(f"Error calling gpt-image-1 API for image generation: {e}")
        return None

# *** 4. Save content to a file for the publishing workflow ***
def save_content_for_approval(image_url, caption, hashtags):
    """
    Saves the generated content to a JSON file.
    """
    print("Saving content to pending_post.json...")
    content = {
        "image_url": image_url,
        "caption": caption,
        "hashtags": hashtags
    }
    with open("pending_post.json", "w") as f:
        json.dump(content, f, indent=4)
    print("Content saved.")

# *** 5. Send a Slack notification asking for approval ***
def send_approval_request_to_slack(image_url, caption, hashtags):
    """
    Sends a notification to Slack with a preview and instructions to approve.
    """
    print("Sending Slack notification for approval...")
    
    slack_payload = {
        "text": f"New Post for Approval: {caption}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✨ *New Post Ready for Approval* ✨\n\n*Caption:*\n{caption}\n\n*Hashtags:*\n`{hashtags}`"
                }
            },
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Generated Image"
                },
                "image_url": image_url,
                "alt_text": "Daily dream illustration"
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "To proceed, go to your repository's **Actions** tab, click on the **'Daily TikTok Post Workflow'**, and run it manually.\n\n"
                            "🔹 Choose **`publish`** to post this content to TikTok.\n"
                            "🔹 Choose **`regenerate`** to discard this version and create a new one."
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
    print("Starting content generation script...")
    
    description, caption, hashtags = generate_prompt_and_caption()
    if not description or not caption:
        print("Failed to get description/caption. Exiting.")
        exit(1)
    
    image_url = generate_image(description)
    if not image_url:
        print("Image generation failed. Exiting.")
        exit(1)
        
    save_content_for_approval(image_url, caption, hashtags)
    send_approval_request_to_slack(image_url, caption, hashtags)
    
    print("Content generation script finished successfully!") 