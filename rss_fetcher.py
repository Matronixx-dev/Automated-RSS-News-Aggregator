import requests
import json
from datetime import datetime
import xml.etree.ElementTree as ET

def fetch_feed(url):
    """Fetches and parses a single RSS feed URL."""
    try:
        # Add realistic User-Agent header to avoid 420 errors from some sites
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching feed {url}: {e}")
        return None

def parse_rss(xml_data):
    """
    Properly parses RSS/Atom XML data and extracts article information.
    Uses xml.etree.ElementTree for robust XML parsing.
    """
    if not xml_data:
        print("⚠️  No XML data to parse")
        return []

    try:
        root = ET.fromstring(xml_data)
        
        articles = []
        namespaces = {
            'rss': 'http://www.w3.org/2006/12/rss',
            'atom': 'http://www.w3.org/2005/Atom'
        }
        
        # Standard RSS 2.0: root is <rss>, entries are in <channel> -> <item>
        if root.tag == 'rss' or root.tag.endswith('rss'):
            channel = root.find('.//channel')
            if channel is not None:
                items = channel.findall('.//item', namespaces=namespaces)
                if not items:
                    # Try without namespace (some feeds don't declare it)
                    items = channel.findall('.//item')
                
                for entry in items:
                    title = entry.findtext('title', '', namespaces=namespaces)
                    link = entry.findtext('link', '', namespaces=namespaces)
                    description = entry.findtext('description', '', namespaces=namespaces)
                    
                    # Try multiple date fields
                    pub_date = (entry.findtext('published', 
                                entry.findtext('pubDate', ''), 
                                namespaces=namespaces) or
                              entry.findtext('updated', '', namespaces=namespaces))
                    
                    if title and link:
                        articles.append({
                            "title": title,
                            "link": link,
                            "description": description or "",
                            "pub_date": pub_date
                        })
        
        # Atom feeds (root is <feed>)
        elif root.tag == 'feed' or root.tag.endswith('feed'):
            entries = root.findall('.//entry', namespaces=namespaces)
            
            for entry in entries:
                title = entry.findtext('title')
                link_elem = entry.find('link')
                link = link_elem.attrib.get('href') if link_elem is not None else ""
                description = entry.findtext('content') or entry.findtext('summary')
                pub_date = entry.findtext('published', entry.findtext('updated'))
                
                if title and link:
                    articles.append({
                        "title": title,
                        "link": link,
                        "description": description or "",
                        "pub_date": pub_date
                    })
        
        if articles:
            print(f"✅ Successfully parsed {len(articles)} real feed entries.")
        else:
            print("⚠️  No valid articles extracted from feed.")
            
        return articles
        
    except ET.ParseError as e:
        print(f"❌ ERROR parsing XML: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error during parsing: {e}")
        return []

def fetch_all_feeds(config_path):
    """Loads config and fetches all specified feeds."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ ERROR: rss_config.json not found!")
        return []
    except json.JSONDecodeError:
        print("❌ ERROR: Invalid JSON in rss_config.json!")
        return []

    all_articles = []
    
    # Get optional max_articles limit from config (optional, default None means no limit)
    max_articles = config.get('max_articles', None)
    
    # Support both quick_feeds and full_feeds config structure
    for feed_type in ["quick_feeds", "full_feeds"]:
        feeds = config.get(feed_type, [])
        if not feeds:
            print(f"\n--- No {feed_type} feeds to fetch ---")
            continue
            
        print(f"\n--- Fetching {len(feeds)} {feed_type} feeds ---")
        
        for feed in feeds:
            url = feed['url']
            name = feed.get('name', 'Unknown Source')
            
            xml_data = fetch_feed(url)
            if xml_data:
                articles = parse_rss(xml_data)
                # Append the articles with source metadata, respecting max_articles limit
                for article in articles:
                    # Only check limit if max_articles is set (not None)
                    if max_articles is not None and len(all_articles) >= max_articles:
                        print(f"⚠️  Max article limit ({max_articles}) reached. Skipping additional feeds.")
                        break
                    article['source_name'] = name
                    all_articles.append(article)

    if all_articles:
        print(f"\n🎉 RSS Fetching Complete. Total articles fetched: {len(all_articles)}")
    else:
        print("\n⚠️  No articles were fetched from any feeds.")
        
    return all_articles

if __name__ == "__main__":
    # Assuming rss_config.json is in the same directory
    articles = fetch_all_feeds('rss_config.json')
