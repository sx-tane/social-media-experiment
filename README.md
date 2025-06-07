# **Automating Daily Dreamy TikTok Posts: A Beginner's Step-by-Step Guide**

Do you want to automatically create a calming bedtime illustration every day and share it on TikTok with a motivational caption? This tutorial will walk you through setting up a simple system – using AI for image and text, and automating posting to TikTok – all for little to no cost. We'll also set up Slack notifications so you get a daily preview and status update. No coding experience is required; we'll provide all code and detailed instructions. Just follow along step by step!

## Step to auth a tiktok account:
https://blog.csdn.net/youbl/article/details/143779929

## **Overview and Tools**

**What We'll Build:** A script that every day will use **GPT-4o** to generate a creative scene description and a motivational caption. It will then feed that description to OpenAI's **gpt-image-1** image generator to create a unique, whimsical illustration in a **flat, minimalist, monotone blue style** with a "cozy bedtime" vibe. The script will then automatically post the image and caption to TikTok with a **randomly selected soundtrack** and send you a Slack notification with the result.

**Tools & Services Needed (all free or <\$10/month):**

*   **OpenAI API (GPT-4o & gpt-image-1)** – for both text and image generation. *(Cost: Pay-per-use. GPT-4o is very efficient, and one image generation is a few cents. Total monthly cost should be low.)*
*   **TikTok Developer Account** – to use TikTok's Content Posting API for uploading posts.
*   **Slack** – a Slack workspace (free) where you can receive notifications. We'll use a Slack *Incoming Webhook* to post messages.
*   **Somewhere to Run the Script Daily** – We'll show how to use **GitHub Actions** (free) to schedule the script to run automatically every day. *(No server needed!)*

Each step below will guide you through setting up these components, with links and instructions. **By the end, you'll have a fully automated system** that creates a unique dreamy illustration every day and posts it to TikTok for you. Let's get started!

## **Step 1: Set Up OpenAI API (for Text and Image)**

First, we need the AI that will generate our daily scene descriptions, captions, and the illustration itself. The great news is that OpenAI provides all of this with a single API key.

1.  **Create an OpenAI Account and API Key:** If you haven't already, sign up at **OpenAI's platform** ([Platform OPENAPI](https://platform.openai.com/usage)). Once logged in, navigate to the **API Keys** section (usually under your account settings). Click "Create new secret key" and copy your API key. It will look something like `sk-XXXXXXXXXXXXXXXXXXXX`. *Keep this key secret!* We'll use it in our code to call both GPT-4o and gpt-image-1.

2.  **Add a Payment Method:** To use the API for generating images with gpt-image-1 and text with GPT-4o, you'll need to add a payment method to your OpenAI account. Go to the **Billing** section in your OpenAI account settings and add a credit card. Usage is pay-as-you-go, and for our daily task, the costs will be very low (likely under \$5/month).

3.  **Test Your API Key (Optional):** If you want to ensure your key works, you can do a quick test using `curl` or a tool like Postman. For example, in a terminal you could run:

    ```bash
    curl https://api.openai.com/v1/models -H "Authorization: Bearer YOUR_API_KEY"
    ```

    If set up correctly, this should return a list of models. This step isn't required, but it's a good sanity check.

**Keep your OpenAI API key handy** – it's the only key you'll need for the AI part of this project.

## **Step 2: Get Your TikTok API Credentials**

To post content automatically, you first need to get permission from your TikTok account. Because TikTok uses a secure authorization process (OAuth 2.0 with PKCE), the easiest way to do this is to use a special script we've provided.

### **2.1 Set Up Your TikTok Developer App**

1.  **Create a TikTok Developer Account:** Visit the [TikTok Developers Portal](https://developers.tiktok.com/app/7512675493315725318/sandbox/7512746189046155270) and log in with your TikTok account.
2.  **Create an App:** Go to **My Apps** and click **"Create App"**. Give it a name (e.g., "DailyDreamPosts") and select **Personal** as the app type.
3.  **Add Content Posting API:** In your new app's dashboard, find the **"Products"** section. Click **"Add Product"** and select **Content Posting API**.
4.  **Get Your Client Key & Secret:** In your app's "App details" page, you will find your `Client key` and `Client secret`. You will need these for the next step.
5.  **Set Your Redirect URI:** In your app's settings, you must add a valid **Redirect URI**. For our script to work, add `https://www.tourii.xyz/auth/callback` to this list and save your changes.

### **2.2 Run the Token Generator Script**

Now you can use the provided script to get your `Access Token`, `Open ID`, and, most importantly, your `Refresh Token`.

1.  **Add Credentials to your `.env` file:** Before running the script, you must have a `.env` file in your project directory. Open it and make sure it contains your `TIKTOK_CLIENT_KEY` and `TIKTOK_CLIENT_SECRET` from the developer portal. It should look something like this:
    ```
    TIKTOK_CLIENT_KEY="your_client_key_here"
    TIKTOK_CLIENT_SECRET="your_client_secret_here"
    ```
2.  **Run the Script:** Open your terminal and run the command: `python get_tiktok_token.py`.
3.  **Authorize in Browser:** Your web browser will open. Log in to TikTok and click "Authorize". After authorizing, you will be redirected to a page at `tourii.xyz`.
4.  **Copy the Redirect URL:** Copy the **full URL** from your browser's address bar. It will be long and contain an authorization `code`.
5.  **Paste the URL into the Terminal:** The script will be waiting for your input. Paste the full URL you just copied into the terminal and press Enter.
6.  **Get Your Tokens:** The script will then exchange the code for your tokens and print them out.
7.  **Save Your Credentials:** The script worked! Now, copy the `TIKTOK_REFRESH_TOKEN` value it printed out and add it to your `.env` file. You will need this for the automated workflow.

> **Troubleshooting:** If the script gives an error, the most common reason is an incorrect Redirect URI. Please double-check that `https://www.tourii.xyz/auth/callback` is saved in your app's settings in the TikTok Developer Portal.

At this point, you have all the necessary keys and tokens from TikTok to proceed.

## **Step 3: Set Up Slack Incoming Webhook (for Notifications)**

Now let's configure Slack so the system can send you a message each day with the new image and caption (and whether it posted successfully). We'll use Slack's **Incoming Webhooks**, which allow external apps (our script) to post messages into a Slack channel.

1.  **Create a Slack App for Webhook:** Go to Slack's API page [api.slack.com/apps](https://api.slack.com/apps) and click **"Create an App"**. Choose "From scratch". Give the app a name (e.g., "DailyDreamBot") and pick your Slack workspace. Click **Create**.

2.  **Activate Incoming Webhooks:** In your Slack app settings, on the left sidebar, click **"Incoming Webhooks"** (under "Features"). Turn on the **Activate Incoming Webhooks** switch.

    &#x20;*Screenshot: Activating Incoming Webhooks in Slack app settings.*
    *In your Slack app's settings, enable "Incoming Webhooks" by toggling it On. This allows the app to receive webhook POST requests and forward messages to Slack.*

3.  **Create a Webhook URL:** Still on the Incoming Webhooks page, click **"Add New Webhook to Workspace"**. Slack will prompt you to select a channel – choose the Slack channel where you want to get the daily updates (maybe a private channel just for you, or anywhere you prefer). Then click **Allow**. Slack will generate a **Webhook URL**. It will look like `https://hooks.slack.com/services/XXXXX/YYYYY/ZZZZZZ`. Copy this URL – it's essentially a secret endpoint that allows posting to that channel.

    &#x20;*Screenshot: Adding a new webhook URL for Slack.*
    *After enabling webhooks, click "Add New Webhook to Workspace" and authorize the app to post in your chosen channel. Slack will then show you the webhook URL to use.*

4.  **Security Note:** Keep this Slack webhook URL private (don't share it), because anyone who has it can post messages to your Slack. We'll treat it like a secret in our code.

That's it for Slack setup. Now, whenever we send a properly formatted HTTP POST to that URL with a message, it will appear in your Slack channel.

## **Step 4: Build the Automation Script (Python)**

With all keys and tokens gathered, we can now create the script that ties everything together: calling GPT-4o for a prompt and caption, generating the image via gpt-image-1, posting to TikTok, and sending the Slack message. We'll write this in Python for clarity. You can literally copy-paste this code – just insert your keys where indicated.

### **4.1 Prepare Your Secrets**

Before editing the code, make sure you have the following from previous steps:

*   `OPENAI_API_KEY` – your OpenAI secret key.
*   `SLACK_WEBHOOK_URL` – the full Slack webhook URL you obtained.
*   `TIKTOK_CLIENT_KEY` – the Client Key from your TikTok Developer App.
*   `TIKTOK_CLIENT_SECRET` – the Client Secret from your TikTok Developer App.
*   `TIKTOK_REFRESH_TOKEN` – the long-lived refresh token you got from running the `get_tiktok_token.py` script.

We will include these as configurable variables in the script. For personal use, it's fine to embed them for now – just **don't publish your keys publicly**.

### **4.2 Install Python and Required Libraries**

Ensure you have Python installed (3.x). We will use a couple of libraries: `requests` (for making HTTP calls) and `openai` (OpenAI's official library).

Install the libraries by running this in your terminal:

```bash
pip install openai requests
```

### **4.3 The Code:**

Now copy the following code into a file named `daily_tiktok_post.py`. After copying, **replace the placeholder values** (`<YOUR_...>`) with your actual keys and tokens from earlier steps.

```python
import os
import requests
import openai
import json

# *** 1. Configure API keys and tokens ***
# It's better to use environment variables, but for simplicity, we'll define them here.
# Remember to replace these with your actual keys and not to share them publicly.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "<YOUR_OPENAI_API_KEY>")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "<YOUR_SLACK_WEBHOOK_URL>")
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "<YOUR_TIKTOK_CLIENT_KEY>")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "<YOUR_TIKTOK_CLIENT_SECRET>")
TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN", "<YOUR_TIKTOK_REFRESH_TOKEN>")

# Configure the OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# *** 2. Generate daily prompt and caption using GPT-4o ***
def generate_prompt_and_caption():
    """
    Calls GPT-4o to get a new scene description and a motivational caption.
    """
    print("Generating scene description and caption with GPT-4o...")
    system_msg = (
        "You are an AI assistant that generates creative ideas for 'Dreamy Monotone Worlds' illustrations. "
        "Your goal is to create a unique, whimsical, and peaceful scene description each day for a bedtime-themed post. "
        "The scenes should be minimalist and imaginative. Think about animals (like foxes, whales, sleeping dragons), "
        "magical objects (like floating teacups or umbrella boats), or serene landscapes (like starlit gardens or cloud concerts). "
        "Avoid repeating the same subjects. Be creative and diverse in your daily suggestions. "
        "Alongside the scene description, create a short, motivational, or comforting caption with a calm, dreamy tone. "
        "You must respond ONLY in JSON format with two keys: 'description' and 'caption'."
    )
    user_msg = "Please generate a new scene description and a caption for today's post."
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
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
        return None, None

    try:
        result = json.loads(content)
        description = result.get("description", "").strip()
        caption = result.get("caption", "").strip()
        if not description or not caption:
            raise ValueError("Missing 'description' or 'caption' in GPT-4o response.")
        return description, caption
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Failed to parse GPT-4o output. Error: {e}\nRaw content: {content}")
        return None, None

# *** 3. Use gpt-image-1 to generate an image based on the description ***
def generate_image(description):
    """
    Calls gpt-image-1 to generate an image from the provided description.
    """
    print("Generating image with gpt-image-1...")
    # Add detailed style cues to the description for gpt-image-1
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
            size="1024x1024",  # gpt-image-1 supports 1024x1024, 1792x1024, or 1024x1792
            quality="hd", # use "hd" for higher quality and detail, at a higher cost
        )
        image_url = response.data[0].url
        print(f"Image generated successfully: {image_url}")
        return image_url
    except Exception as e:
        print(f"Error calling gpt-image-1 API for image generation: {e}")
        return None

# *** 4. Post the image and caption to TikTok ***
def post_to_tiktok(image_url, caption):
    """
    Posts the generated image and caption to TikTok using the Content Posting API.
    """
    print("Initiating post to TikTok...")
    endpoint = "https://open.tiktokapis.com/v2/post/publish/content/init/"
    headers = {
        "Authorization": f"Bearer {TIKTOK_REFRESH_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    payload = {
        "post_info": {
            "title": caption[:2200],
            "description": caption,
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
            # Note: For a robust solution, you might want to periodically check the post status.
            # For this simple script, we'll assume initiation is sufficient.
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

# *** 5. Send a Slack notification ***
def send_slack_message(image_url, caption, tiktok_status, publish_id):
    """
    Sends a notification to a Slack channel with the post details.
    """
    print("Sending Slack notification...")
    status_text = "Successfully posted to TikTok ✔️" if tiktok_status else "Failed to post to TikTok ❌"
    if tiktok_status and publish_id:
        # Note: A publish_id doesn't guarantee immediate public visibility due to audits.
        status_text += f" (Publish ID: {publish_id})"
        
    slack_payload = {
        "text": f"**Daily Dream Post**\n\n**Caption:** {caption}\n\n**Status:** {status_text}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"**Daily Dream Post** ✨\n\n*{caption}*"
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
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Status:* {status_text}"
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
    print("Starting daily post script...")
    
    # 1. Get prompt and caption from GPT-4o
    description, caption = generate_prompt_and_caption()
    if not description or not caption:
        print("Failed to get description/caption from GPT-4o. Exiting.")
        # Also notify Slack about the failure if possible
        send_slack_message(
            "https://via.placeholder.com/512.png?text=Error",
            "Could not generate text.",
            False,
            None
        )
        exit(1)
    
    print(f"GPT-4o Description: {description}")
    print(f"GPT-4o Caption: {caption}")
    
    # 2. Generate image via gpt-image-1
    image_url = generate_image(description)
    if not image_url:
        print("Image generation failed. Exiting.")
        send_slack_message(
            "https://via.placeholder.com/512.png?text=Error",
            caption,
            False,
            None
        )
        exit(1)
        
    # 3. Post to TikTok
    success, publish_id = post_to_tiktok(image_url, caption)
    
    # 4. Notify via Slack
    send_slack_message(image_url, caption, success, publish_id)
    
    if success:
        print("Script finished successfully!")
    else:
        print("Script finished with errors.")
```

**🔧 A few things to check in this code before running:**

*   **API Keys**: Make sure you've replaced `<YOUR_...>` placeholders with your actual keys. For better security (especially when using GitHub Actions), we'll use repository secrets later, and the script is already set up to read them from environment variables.
*   **Image Prompting**: In the `generate_image` function, we've added a detailed `style_description`. This is key to getting the consistent look you want. Feel free to tweak the wording ("*flat vector art*", "*monotone color palette*", etc.) to refine the artistic style.
*   **TikTok Posting**: The `post_to_tiktok` function uses the `PULL_FROM_URL` method. This requires the `image_url` (from OpenAI) to be publicly accessible. OpenAI image URLs work for this, but they expire after about an hour, which is plenty of time for our script to use it. Remember the sandbox note: posts from new, unaudited developer apps will likely be private on TikTok until your app is reviewed.

### **4.4 Run the Script Manually (Test)**

Before automating, let's test the script to make sure everything works. Open a terminal in the same folder as your `daily_tiktok_post.py` file and run:

```bash
python daily_tiktok_post.py
```

Watch the output. The script will print its progress.

*   If the GPT or image generation call fails, check your `OPENAI_API_KEY` and make sure you have a valid payment method on your OpenAI account.
*   If the TikTok post fails, the error message from the API will be printed. This is often due to an incorrect or expired `TIKTOK_REFRESH_TOKEN`. You might need to go back to the TikTok Developer Portal and generate a new one.
*   If all goes well, the script will print success messages, and you should see a new post on your TikTok account (it might be private!) and a notification in your Slack channel. 🎉

Once you've confirmed it works, you're ready to schedule it to run automatically every day!

## **Step 5: Schedule and Run Your Workflow**

We'll use **GitHub Actions** to run our scripts. With the addition of a "regenerate" option, the workflow is now even more powerful.

### **5.1 How the New Workflow Works**

1.  **Automatic Generation**: Every day at your scheduled time, a workflow runs the `generate_content.py` script. It creates the image, caption, and hashtags, saves them to a `pending_post.json` file in your repository, and sends you a Slack message for approval.
2.  **Manual Action from Slack**: The Slack message will present you with the generated content. You then decide what to do next.
3.  **Manual Trigger in GitHub**: Go to your repository's **Actions** tab and click on the **"Daily TikTok Post Workflow"**. You will see a **"Run workflow"** button. When you click it, a dropdown menu will appear where you can:
    *   Choose **`publish`**: This runs the `publish_content.py` script. It will post the content from `pending_post.json` to TikTok, send a confirmation to Slack, and delete the pending file.
    *   Choose **`regenerate`**: This runs the `generate_content.py` script again. It will create a brand new post, overwrite the `pending_post.json` file, and send you a new Slack message to review, starting the approval process over.

This gives you full control to keep regenerating content until you get a result you love.

### **5.2 Setting Up the Workflow**

1.  **Create a GitHub Repository:** If you don't have one, create a free GitHub account and then create a **new private repository**.

2.  **Add Your Files to the Repo:**
    *   Add `generate_content.py`.
    *   Add `publish_content.py`.
    *   Add `requirements.txt`.
    *   **Important:** Create a `.gitignore` file and add `.env` to it to ensure you never accidentally commit your local secrets file.

3.  **Add Secrets to GitHub:** In your repository, go to **Settings > Secrets and variables > Actions**. Create the following secrets and paste in the corresponding values.
    *   `OPENAI_API_KEY`: Your key from OpenAI.
    *   `SLACK_WEBHOOK_URL`: Your incoming webhook URL from Slack.
    *   `TIKTOK_CLIENT_KEY`: The Client Key from your TikTok Developer App.
    *   `TIKTOK_CLIENT_SECRET`: The Client Secret from your TikTok Developer App.
    *   `TIKTOK_REFRESH_TOKEN`: The long-lived refresh token you got from running the `get_tiktok_token.py` script.

4.  **Add the GitHub Actions Workflow File:** Add the `daily_post.yml` file to the `.github/workflows` directory. The file is now configured to automatically refresh your access token before every post.

5.  **Give Workflow Permissions:** For the workflow to be able to save and delete the `pending_post.json` file, you need to give it write permissions. Go to your repository **Settings > Actions > General**. Scroll to **"Workflow permissions"** and select **"Read and write permissions"**. Click **Save**.

6.  **Commit and Push Your Files:** Save all your files and push them to your GitHub repository.

### **5.3 Running the Workflow**

*   **Wait for the Schedule:** The `generate_content` job will run automatically at the time you specified in the cron schedule.
*   **Manual Trigger:** To publish or regenerate, go to the **Actions** tab, select the workflow, click **"Run workflow"**, choose your desired action from the dropdown, and click the final **"Run workflow"** button.

**Congrats!** You have now built a sophisticated, fully automated content pipeline with a crucial manual approval and regeneration loop. You have complete creative control before anything goes public. Enjoy your endless supply of dreamlike worlds!

## **Wrapping Up and Tips**

*   **Adjusting Prompts or Style:** The magic is in the prompts! If you want to change the art style, modify the `style_description` in the `generate_image` function. If you want different kinds of captions or scene ideas, tweak the `system_msg` in the `generate_prompt_and_caption` function. The current setup is designed to give you a wide variety of "Dreamy Monotone Worlds," but feel free to customize it further.

*   **Costs:** Keep an eye on your OpenAI API usage in the first few days, but it should be very affordable. A single `gpt-4o` call and one HD-quality `gpt-image-1` image per day will likely cost only a few dollars per month.

*   **TikTok App Audit:** For your posts to be public automatically, you'll need to submit your TikTok app for review. In the TikTok Developer Portal, there's usually a process for an "App Audit". You'll need to explain what your app does. Until then, you may need to manually switch your posts from "private" to "public" in the TikTok app.

*   **Troubleshooting:** The logs in the GitHub Actions tab are your best friend. If a run fails, the logs will almost always tell you why. Common issues are expired tokens or incorrect secrets.

You now have a complete, hands-free system delivering delightful bedtime artwork to TikTok every day. Enjoy your creation, and sweet dreams 🌙✨.
