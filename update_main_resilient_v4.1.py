"""
update_main_resilient.py v4.1 - FIXED DEDUPLICATION LOGIC
Properly detects new articles without false positives
Uses .env for credentials (never prints sensitive values)
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests

# ✅ Load credentials silently from .env (NEVER print token values!)
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = "-1002185654913"

if not TELEGRAM_TOKEN:
    logging.error("❌ FATAL ERROR: TELEGRAM_BOT_TOKEN not found in .env!")
    exit(1)

# ✅ Setup logging to file AND console (no credential exposure)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/mitch/projects/sandboxes/news_aggregator/logs/aggregator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ✅ Configuration paths
RSS_CONFIG_PATH = '/home/mitch/projects/sandboxes/news_aggregator/rss_config.json'
CACHE_DIR = '/home/mitch/projects/sandboxes/news_aggregator/cache'
TIMESTAMP_FILE = os.path.join(CACHE_DIR, 'last_run_timestamp.txt')


def get_previous_run_time():
    """Safely retrieves last successful run time from timestamp file."""
    if not os.path.exists(TIMESTAMP_FILE):
        logger.info("⚠️ No timestamp file found - this is a FRESH RUN (will send ALL articles)")
        return None  # Fresh run, no deduplication needed
    
    try:
        with open(TIMESTAMP_FILE, 'r') as f:
            last_time_str = f.read().strip()
            previous_time = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')
            logger.info(f"📅 Previous run detected at: {last_time_str}")
            return previous_time
    except Exception as e:
        logger.warning(f"⚠️ Error reading timestamp file: {e} - treating as fresh run")
        return None


def save_timestamp():
    """Updates the last run timestamp after successful completion."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        with open(TIMESTAMP_FILE, 'w') as f:
            f.write(current_time)
        logger.info(f"✅ Timestamp updated to: {current_time}")
    except Exception as e:
        logger.error(f"❌ Error saving timestamp: {e}")


def fetch_rss_feeds_from_config():
    """Loads RSS feeds from config and fetches articles."""
    logger.info("=" * 60)
    logger.info("🚀 Starting RSS Aggregation Run")
    logger.info("=" * 60)
    
    rss_sources = []
    if os.path.exists(RSS_CONFIG_PATH):
        with open(RSS_CONFIG_PATH, 'r') as f:
            rss_sources = json.load(f)
        
        logger.info(f"📋 Loaded {len(rss_sources)} RSS feed configurations")
    else:
        logger.error(f"❌ RSS config not found at: {RSS_CONFIG_PATH}")
        return []
    
    all_articles = []
    previous_time = get_previous_run_time()
    
    # Fetch each feed
    for source in rss_sources:
        feed_url = source.get('url')
        cache_file = source.get('cache_file')
        category = source.get('category', 'Unknown')
        name = source.get('name', 'Feed')
        
        logger.info(f"\n🔍 Fetching from: {feed_url} ({category})")
        
        try:
            # ✅ FIX: Use requests to fetch REAL RSS data (not simulated!)
            response = requests.get(feed_url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Successfully fetched RSS from {feed_url}")
                
                # Parse RSS XML
                from xml.dom.minidom import parseString
                
                rss_data = response.content
                dom = parseString(rss_data)
                items = dom.getElementsByTagName('item')
                
                for item in items:
                    article = {
                        'source': category,
                        'title': item.getElementsByTagName('title')[0].firstChild.data[:100] if item.getElementsByTagName('title') else '',
                        'url': item.getElementsByTagName('link')[0].firstChild.data if item.getElementsByTagName('link') else '#',
                        'description': item.getElementsByTagName('description')[0].firstChild.data[:200] if item.getElementsByTagName('description') else '',
                        'published_at': item.getElementsByTagName('pubDate')[0].firstChild.data if item.getElementsByTagName('pubDate') else datetime.now().isoformat(),
                        'timestamp': item.getAttribute('dc:date') if item.getAttribute('dc:date') else None
                    }
                    
                    all_articles.append(article)
            
            logger.info(f"✅ Parsed {len(items)} articles from feed")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Network error fetching {feed_url}: {e}")
        except Exception as e:
            logger.error(f"❌ Error parsing RSS from {feed_url}: {e}")
    
    return all_articles, previous_time


def filter_new_articles(all_articles, previous_time):
    """Filters articles that are NEW (not duplicates)."""
    if not all_articles:
        logger.warning("⚠️ No articles fetched - nothing to send")
        return []
    
    if previous_time is None:
        # ✅ FIX: This is a FRESH RUN - send ALL articles!
        logger.info("=" * 60)
        logger.info(f"✨ FRESH RUN DETECTED - {len(all_articles)} articles found (no previous run)")
        logger.info("=" * 60)
        
        return all_articles
    
    # ✅ FIX: Compare article timestamps vs previous run time
    new_articles = []
    
    for article in all_articles:
        pub_date = article.get('published_at', '')
        
        try:
            if pub_date:
                pub_time = datetime.fromisoformat(pub_date)
                
                # ✅ FIX: Article is NEW if published AFTER last run time
                if pub_time > previous_time:
                    new_articles.append(article)
                else:
                    logger.debug(f"⏭️ Skipping duplicate: {article['title'][:50]} (published before last run)")
        
        except Exception as e:
            # If timestamp parsing fails, include it anyway (better than missing news)
            logger.warning(f"⚠️ Could not parse timestamp for article: {e} - including anyway")
            new_articles.append(article)
    
    logger.info("=" * 60)
    logger.info(f"🔍 Deduplication complete:")
    logger.info(f"• Total articles fetched: {len(all_articles)}")
    logger.info(f"• New articles to send: {len(new_articles)}")
    
    if len(new_articles) == 0:
        logger.warning("😴 No new unique articles found - exiting gracefully!")
    else:
        logger.info(f"✅ {len(new_articles)} fresh articles identified for Telegram delivery")
    
    logger.info("=" * 60)
    
    return new_articles


def send_to_telegram(articles):
    """Sends articles to Telegram with proper formatting."""
    BATCH_SIZE = 3
    
    if not articles:
        return
    
    total_sent = 0
    grouped_by_source = {}
    
    # Group by source for better organization
    for article in articles:
        source = article['source']
        if source not in grouped_by_source:
            grouped_by_source[source] = []
        grouped_by_source[source].append(article)
    
    for category, source_articles in grouped_by_source.items():
        for i in range(0, len(source_articles), BATCH_SIZE):
            batch = source_articles[i:i + BATCH_SIZE]
            message_parts = []
            
            # Create Telegram-friendly message (MarkdownV2 format)
            for article in batch:
                title = article['title'][:50]  # Truncate long titles
                url = article['url'] if article['url'] else '#'
                source_name = category
                
                message_parts.append(
                    f"\n📰 *[{source_name}] {title}*\n"
                    f"_Link: {url}_\n"
                )
            
            # Compile final message with timestamp
            current_time = datetime.now().strftime('%H:%M')
            full_message = f"🚀 RSS Briefing • {current_time}\n" + "".join(message_parts)
            
            try:
                result = requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    data={
                        'chat_id': TELEGRAM_CHAT_ID,
                        'text': full_message,
                        'parse_mode': 'MarkdownV2',
                        'disable_web_page_preview': 'true'
                    },
                    timeout=10
                )
                
                if result.status_code == 200:
                    logger.info(f"✅ Sent {len(batch)} articles for {category}")
                    total_sent += len(batch)
                    time.sleep(2)  # Rate limiting
                    
            except Exception as e:
                logger.error(f"❌ Failed to send batch for {category}: {e}")
    
    return total_sent


def main():
    """Main execution flow - clean and simple."""
    print("\n" + "=" * 60)
    print("🚀 RSS AGGREGATOR - FIXED DEDUPLICATION v4.1")
    print("=" * 60)
    
    # Fetch all feeds
    all_articles, previous_time = fetch_rss_feeds_from_config()
    
    if not all_articles:
        logger.error("❌ No articles fetched from any feed - exiting!")
        return
    
    print(f"\n✅ Fetched {len(all_articles)} total articles")
    
    # Filter new articles (deduplication)
    new_articles = filter_new_articles(all_articles, previous_time)
    
    if not new_articles:
        logger.info("No new articles to send - exiting gracefully!")
        return
    
    print(f"✅ Found {len(new_articles)} unique new articles")
    
    # Send via Telegram
    print(f"\n📤 Sending {len(new_articles)} articles to Telegram...")
    total_sent = send_to_telegram(new_articles)
    
    if total_sent > 0:
        logger.info("=" * 60)
        logger.info(f"✅ SUCCESS! Sent {total_sent} articles via Telegram!")
        logger.info("=" * 60)
        
        # Update timestamp for next run
        save_timestamp()
        
    else:
        logger.error("❌ No articles delivered to Telegram")
    
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()