import json
from datetime import datetime
# Assume external functions/modules for logging and timestamp handling exist
# e.g., log_message(), set_last_send_timestamp()

def load_dedupe_timestamps(filename="logs/deduplicate_tracker.json"):
    """Loads the file tracking article IDs or unique hashes to prevent duplication."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # If file doesn't exist yet, start fresh
        return {}

def save_dedupe_timestamps(timestamps, filename="logs/deduplicate_tracker.json"):
    """Saves the current set of processed articles."""
    with open(filename, 'w') as f:
        json.dump(timestamps, f, indent=2)

def compile_telegram_messages(articles):
    """
    Processes raw article data, checks for duplication, formats messages, 
    and returns a list of finalized Telegram message strings.
    """
    processed_articles = {} # Stores articles already processed (using a unique ID/hash)
    final_messages = []

    # Load existing tracker from the logs directory
    timestamps = load_dedupe_timestamps()

    for article in articles:
        # In a real system, we would generate a stable hash based on URL + Title. 
        # For this simulation, we use the link as the unique ID.
        unique_id = article.get('link')
        if not unique_id:
            continue # Skip if no unique identifier

        if unique_id in timestamps:
            # print(f"⏭️ Skipping duplicate article: {article['title']}") # Logged for debugging
            continue 
        
        # Mark as processed immediately to prevent duplicates within the same run
        processed_articles[unique_id] = True
        
        source_name = article.get('source_name', 'Unknown Source')
        title = article['title']
        description = article['description']
        link = article['link']

        # --- MESSAGE FORMATTING LOGIC (Telegram friendly) ---
        current_time_str = datetime.now().strftime("%H:%M")
        
        message_template = f"""*📰 {source_name} Quick News Update ({current_time_str})*
-------------------------------------
*Title:* {title}
🔗 *Link:* [Read Article]({link})
• Summary: {description[:150]}... (truncated)

(This message is ready to be sent via the resilient Telegram function.)
"""
        final_messages.append(message_template)

    # Save all newly processed IDs to maintain history across runs
    timestamps.update(processed_articles)
    save_dedupe_timestamps(timestamps) 
    
    print(f"\n✨ Successfully compiled {len(final_messages)} unique messages.")
    return final_messages

if __name__ == "__main__":
    # This block is for isolated testing only. It assumes raw article data is available.
    
    # Simulate the output from rss_fetcher.py 
    mock_articles = [
        {"title": "Test Article A", "link": "http://example.com/a", "description": "Description of A.", "source_name": "Mock Source"},
        {"title": "Duplicate Test B", "link": "http://example.com/b", "description": "Original description.", "source_name": "Mock Source"},
        {"title": "Test Article C", "link": "http://example.com/c", "description": "Description of C.", "source_name": "Another Source"}
    ]

    # Simulate processing the mock data and then simulating a second run with a duplicate 
    print("--- FIRST RUN SIMULATION ---")
    messages1 = compile_telegram_messages(mock_articles)
    for msg in messages1:
        print("-" * 20 + "\n" + msg)

    # Simulate running it again, which should skip Article A and C if the tracker worked.
    print("\n\n--- SECOND RUN SIMULATION (Testing Deduplication) ---")
    messages2 = compile_telegram_messages(mock_articles) # Uses the same mock data
    if not messages2:
        print("✅ Deduction successful! No new unique articles were found.")