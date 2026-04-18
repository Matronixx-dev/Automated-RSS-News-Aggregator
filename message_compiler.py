import os
import json
from datetime import datetime, timedelta

# Feed-to-Category Mapping (Production)
FEED_TO_CATEGORY = {
    "BBC World News": "Geopolitics",
    "Al Jazeera English": "Geopolitics",
    "TechCrunch": "Technology & Science",
    "The Verge": "Technology & Science",
    "Hacker News": "Technology & Science",
    "Ars Technica": "Technology & Science",
    "NPR News": "General News"  # Fallback for mixed content
}

# Category priority order in final message
CATEGORY_ORDER = ["Geopolitics", "Technology & Science", "General News"]
MAX_STORIES_PER_CATEGORY = 5

def load_dedupe_timestamps(force_refresh=False):
    """
    Load the deduplication timestamp tracker from logs.
    If force_refresh=True, returns empty dict (useful for testing).
    """
    try:
        import json
        log_dir = "/home/mitch/projects/sandboxes/news_aggregator/logs"
        tracker_file = f"{log_dir}/dedup_tracker.json"
        
        if not force_refresh:
            if not os.path.exists(tracker_file):
                print("🔍 Debug: Tracker file not found, creating fresh one...")
                return {}
            
            with open(tracker_file, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    print("⚠️ Tracker file corrupted, resetting...")
                    return {}
        else:
            print("🧪 DEBUG: Force refresh enabled - tracker will be cleared after run")
            return {}
    except Exception as e:
        print(f"⚠️ Error loading tracker: {e}")
        return {}

def save_dedupe_timestamps(timestamps):
    """
    Save the deduplication timestamp tracker to logs.
    """
    try:
        import json
        os.makedirs("/home/mitch/projects/sandboxes/news_aggregator/logs", exist_ok=True)
        log_dir = "/home/mitch/projects/sandboxes/news_aggregator/logs"
        tracker_file = f"{log_dir}/dedup_tracker.json"
        
        with open(tracker_file, 'w') as f:
            json.dump(timestamps, f, indent=2)
        
        print(f"✅ Tracker saved with {len(timestamps)} entries")
    except Exception as e:
        print(f"⚠️ Error saving tracker: {e}")

def categorize_article(article):
    """
    Determine category based on source/feed.
    """
    source = article.get('source_name') or article.get('source') or ''
    for feed, category in FEED_TO_CATEGORY.items():
        if feed.lower() in source.lower():
            return category
    return "General News"  # Default fallback

def compile_telegram_messages(articles):
    """
    Processes raw article data, checks for duplication, and compiles articles
    into categorized buckets (max 5 per category), then sends ONE consolidated message.
    
    Returns: List containing ONE unified message string (empty if no new articles)
    """
    processed_ids = set()  # Track seen URLs/titles to prevent duplicates
    final_messages = []

    # Load existing tracker from the logs directory
    timestamps = load_dedupe_timestamps(force_refresh=False)
    
    # DEBUG: Log how many entries exist in tracker
    print(f"\n🔍 Debug: Tracker contains {len(timestamps)} existing dedup keys")

    # Collect ALL unique articles first with their categories
    categorized_articles = {}  # {category: [articles]}
    
    for article in articles:
        # Handle different possible key names across feeds
        link = article.get('link') or article.get('url') or article.get('article_url')
        title = article.get('title', 'No Title')
        
        if not link:
            print(f"⚠️ Skipping article without link: {title}")
            continue  # Skip articles without a link
            
        dedup_key = f"{link}:{title}"
        
        is_new = dedup_key not in timestamps and dedup_key not in processed_ids
        
        if not is_new:
            print(f"⚠️ Duplicate detected (skipping): {title[:50]}...")
            continue  # Skip duplicates
            
        source_name = article.get('source_name') or article.get('source') or 'Unknown Source'
        description = article.get('description', '') or article.get('summary', '') or 'No description available.'
        
        unique_article = {
            "title": title,
            "source": source_name,
            "description": description[:200],  # Pre-truncate for Telegram limits
            "link": link
        }
        
        # Get category and add to bucket
        category = categorize_article(article)
        if category not in categorized_articles:
            categorized_articles[category] = []
        categorized_articles[category].append(unique_article)
        
        # Mark as processed in both local and global trackers
        processed_ids.add(dedup_key)
        timestamps[dedup_key] = True
        
        print(f"✅ New article added to {category}: {title[:40]}...")

    # Save updated tracker
    save_dedupe_timestamps(timestamps)
    
    if not categorized_articles:
        print(f"\n😴 INFO: No new, unique articles were found since the last run.")
        return []

    # Build the SINGLE consolidated message with categorized sections
    current_time = datetime.now().strftime("%H:%M")
    message_parts = [
        f"*📰 Daily News Digest - {current_time}*",
        "=" * 60,
        ""
    ]

    stories_total = 0
    has_overflow = False

    # Add sections in priority order
    for i, category in enumerate(CATEGORY_ORDER, 1):
        if category not in categorized_articles:
            continue
            
        articles_in_cat = categorized_articles[category]
        
        # Limit to MAX_STORIES_PER_CATEGORY
        display_articles = articles_in_cat[:MAX_STORIES_PER_CATEGORY]
        overflow_count = len(articles_in_cat) - MAX_STORIES_PER_CATEGORY
        
        if display_articles:
            message_parts.append(f"*🌍 {category} ({len(display_articles)} story{'' if len(display_articles)==1 else 'ies'})*")
            message_parts.append("-" * 50)
            
            for j, article in enumerate(display_articles, 1):
                title = article['title']
                desc = article['description']
                link = article['link']
                
                message_parts.append(f"   *{j}. {title}*")
                message_parts.append(f"   📝 {desc}")
                message_parts.append(f"   🔗 [Read Article]({link})")
                message_parts.append("")
            
            stories_total += len(display_articles)
        else:
            message_parts.append(f"*🌍 {category} - No new stories*")
            message_parts.append("")

    # Add overflow note if any category had >5 stories
    for category, articles in categorized_articles.items():
        if len(articles) > MAX_STORIES_PER_CATEGORY:
            has_overflow = True
            break
    
    if has_overflow:
        message_parts.append(f"*⚠️ NOTE: Some recent stories were omitted to keep messages concise. Check sources directly for more.*")
        message_parts.append("")

    # Final summary footer
    message_parts.append("=" * 60)
    message_parts.append(f"✅ **Total Stories Sent:** {stories_total}")
    message_parts.append(f"🕐 **Compiled at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Join all parts into ONE final message string
    final_message = "\n".join(message_parts)

    print(f"\n✨ Successfully compiled 1 unified message with {stories_total} categorized stories.")
    
    # GUARANTEE: Always return exactly one message in a list
    return [final_message]

if __name__ == "__main__":
    # Test mode with mock data
    mock_articles = [
        {"title": "Global Summit Results", "link": "http://example.com/g1", "description": "World leaders agree on new climate pact.", "source_name": "BBC World News"},
        {"title": "Tech Startup Funding", "link": "http://example.com/t1", "description": "AI company raises $50M in Series B round.", "source_name": "TechCrunch"},
        {"title": "Market Rally Continues", "link": "http://example.com/f1", "description": "Dow Jones hits record high as tech stocks surge.", "source_name": "NPR News"}
    ]
    
    print("--- CATEGORIZED MESSAGE TEST ---")
    messages = compile_telegram_messages(mock_articles)
    for msg in messages:
        print(msg)
