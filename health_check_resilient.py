import os
import requests

def verify_telegram_api():
    """
    Verifies that the Telegram API is reachable and the bot token is valid.
    Returns:
        bool: True if successful, False otherwise.
    Raises:
        ValueError: If required environment variables are missing.
    """
    # Retrieve credentials from .env file using os.getenv()
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        raise ValueError("Telegram BOT token is missing. Please check your .env file.")
    
    # Construct the URL to verify connectivity
    url = f"https://api.telegram.org/bot{bot_token}/getMe"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "ok" in data and data["ok"]:
                bot_info = data.get("result", {})
                return True, bot_info.get("id", "Unknown"), bot_info.get("first_name", "Unknown")
            else:
                print(f"Telegram API responded with non-OK status: {data}")
                return False, None, None
        else:
            print(f"Failed to reach Telegram API. Status code: {response.status_code}")
            return False, None, None
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return False, None, None

def health_check_resilient():
    """
    Resilient health check that retries failed connections.
    
    Returns:
        bool: True if all checks pass, False otherwise.
    """
    max_retries = 3
    for attempt in range(max_retries):
        success, bot_id, first_name = verify_telegram_api()
        if success:
            print(f"✅ Telegram API reachable - Bot ID: {bot_id}, Name: {first_name}")
            return True
        else:
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # Exponential backoff
                print(f"⚠️  Telegram API check failed. Retrying in {2**attempt}s... (Attempt {attempt+1}/{max_retries})")
            else:
                print(f"❌ Failed to reach Telegram API after {max_retries} attempts.")
    
    return False
