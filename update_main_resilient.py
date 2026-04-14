import os
from dotenv import load_dotenv
load_dotenv('/home/mitch/projects/sandboxes/news_aggregator/.env')
import time
from datetime import datetime
# Assuming these modules are accessible in the path
from rss_fetcher import fetch_all_feeds 
from message_compiler import compile_telegram_messages 
from aggregator_resilient import send_to_telegram_resiliently
from health_check_resilient import verify_telegram_api

# Use absolute paths to avoid directory context issues
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'rss_config.json')
LOGS_DIR = os.path.join(SCRIPT_DIR, 'logs')

# --- Test Mode Function ---
def run_test_mode():
    """Force Telegram send for verification/test purposes"""
    print("\n=========================================")
    print("🧪 TEST MODE ENABLED")
    print("⚡ Forcing message generation and Telegram send for verification...")
    print("=========================================\n")
    
    # Generate test articles regardless of actual feed data
    test_articles = [
        {
            "title": "🚀 TEST: Script automation verified!",
            "source": "Alfred Test Feed",
            "time": datetime.now(),
            "url": "https://test.alfred.co.uk/verification"
        },
        {
            "title": "✅ Cron job successfully deployed!",
            "source": "System Monitor",
            "time": datetime.now(),
            "url": "https://test.alfred.co.uk/deploy"
        }
    ]
    
    print(f"📝 Generating {len(test_articles)} test articles...\n")
    
    try:
        # Create keyboard dictionary for TG message - CONVERT ALL DATES TO STRINGS FIRST!
        formatted_articles = []
        for article in test_articles:
            formatted_article = {
                "title": article["title"],
                "source": article["source"],
                "time": article["time"].strftime("%Y-%m-%d %H:%M:%S"),
                "url": article["url"]
            }
            formatted_articles.append(formatted_article)
        
        keyboard_data = {
            "message_type": "test",
            "article_count": len(test_articles),
            "articles": formatted_articles,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        print("💬 Preparing Telegram notification...")
        
        # Call the correct function signature - CHECK AGGREGATOR_RESILIENT.PY FOR EXACT PARAMETER NAME
        result = send_to_telegram_resiliently(keyboard_dict=keyboard_data)
        
        if result:
            print("🔔 TEST NOTIFICATION SENT SUCCESSFULLY!")
            print(f"✅ TG verification complete at {datetime.now()}\n")
        else:
            print("❌ Failed to send test notification. Check API credentials.\n")
    except Exception as e:
        print(f"❌ ERROR in test mode: {e}\n")

# --- Main Execution Function ---
def run_full_aggregation():
    """Orchestrates the entire news aggregation pipeline."""
    print("=========================================")
    print(f"🚀 Starting Aggregation Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=========================================\n")

    # 1. VERIFY TELEGRAM HEALTH (Pre-flight check)
    print("\n[STEP 1/4] Checking Telegram API connectivity...")
    is_telegram_ok, telegram_status, bot_name = verify_telegram_api()
    
    if not is_telegram_ok:
        print(f"🔴 CRITICAL FAILURE: Cannot proceed. Telegram connection failed or token invalid. Reason: {telegram_status}")
        return False
    
    print(f"✅ Telegram API is healthy - Connected as: @{bot_name}")

    # 2. FETCH RSS FEEDS
    print("\n[STEP 2/4] Fetching and parsing all configured news feeds...")
    all_articles = fetch_all_feeds(CONFIG_PATH)
    
    if not all_articles:
        print("🛑 WARNING: No articles were successfully fetched from any feed. Skipping message compilation.")
        return True # Success, but no content found

    # 3. COMPILE MESSAGES
    print("\n[STEP 3/4] Compiling unique messages and checking for duplicates...")
    final_messages = compile_telegram_messages(all_articles)
    
    if not final_messages:
        print("😴 INFO: No new, unique articles were found since the last run. Exiting gracefully.")
        return True

    # 4. SEND MESSAGES (Using Resilient Logic with config_dict)
    print(f"\n[STEP 4/4] Sending {len(final_messages)} messages to Telegram...")
    success_count = 0
    failure_count = 0
    config_dict = {
        "bot_name": bot_name,
        "run_mode": "production",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    for message_content in final_messages:
        # This function contains the retry loop, backoff, and logging
        success = send_to_telegram_resiliently(keyboard_dict=message_content)
        if success:
            success_count += 1
        else:
            failure_count += 1

    print("\n=========================================")
    print("✅ Aggregation Run Complete.")
    print(f"  Successful Sends: {success_count}")
    print(f"  Failed/Skipped Sends: {failure_count}")
    print("=========================================\n")
    return True

# Fixed the comparison bug - ensure articles is a list and count properly
def safe_count_list(items):
    """Safely count items, handling various data types"""
    try:
        return len(items) if isinstance(items, list) else 0
    except:
        return 0

import sys

if __name__ == "__main__":
    # Ensure logs directory exists for tracking and deduplication
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Check for test mode flag
    if '--test' in sys.argv or '-t' in sys.argv:
        run_test_mode()
    else:
        run_full_aggregation()