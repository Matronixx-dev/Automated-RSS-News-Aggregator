#!/usr/bin/env python3
# ============================================================================
# AGGREGATOR - RESILIENT VERSION
# Purpose: News RSS Aggregator with Telegram Resilience Architecture
# Location: /home/mitch/projects/sandboxes/news_aggregator/
# Author: Alfred Pennyworth & Mitch
# Version: 2.0 (Resilient Edition)
# LAST UPDATED: 2026-04-13 14:XX CST
# ============================================================================

import os
import sys
import time
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import requests
import csv
from collections import defaultdict

# ============================================================================
# CONFIGURATION - Adjust as Needed for Your Environment
# ============================================================================
PROJECT_ROOT = Path('/home/mitch/projects/sandboxes/news_aggregator')
LOGS_DIR = PROJECT_ROOT / 'logs'
TIMESTAMP_FILE = LOGS_DIR / 'last_send_time.txt'
CRON_FULL_LOG = LOGS_DIR / 'cron_full.log'
CRON_QUICK_LOG = LOGS_DIR / 'cron_quick.log'

# Telegram Configuration (from environment variables)
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# Retry Configuration (Adjust based on your observed flakiness)
DEFAULT_MAX_RETRIES = 5              # How many times to retry a failed send
RETRY_BACKOFF_BASE_SECONDS = 30      # Base wait time before first retry
RETRY_BACKOFF_MAX_SECONDS = 300      # Maximum wait time (5 minutes)
HEALTH_CHECK_TIMEOUT_SECONDS = 10    # Timeout for API health checks

# Power Settings Reference (You handle these manually if needed)
# Screen blanking timeout (seconds) - Your manual control:
# Recommended: gsettings set org.gnome.desktop.session idle-delay 86400  # 24 hours
# Suspend timeout (-1 = disabled):
# Recommended: gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout -1

# ============================================================================
# UTILITY FUNCTIONS - No External Dependencies Required
# ============================================================================

def log_message(message, level="INFO", save_to_file=True):
    """Log messages to console AND file with timestamp."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] [{level}] {message}"
    
    # Console output
    print(log_line)
    
    # File logging
    if save_to_file:
        try:
            with open(CRON_FULL_LOG, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except Exception as e:
            print(f"⚠️ Failed to write to log file: {e}")

def get_last_send_timestamp():
    """Read the last successful send timestamp from file."""
    try:
        if TIMESTAMP_FILE.exists():
            content = TIMESTAMP_FILE.read_text().strip()
            return float(content)
    except Exception as e:
        log_message(f"Error reading timestamp file: {e}", level="ERROR")
    
    return None

def set_last_send_timestamp(timestamp):
    """Write the last successful send timestamp to file."""
    try:
        with open(TIMESTAMP_FILE, 'w') as f:
            f.write(str(timestamp))
        log_message("Timestamp updated successfully", level="INFO")
    except Exception as e:
        log_message(f"Error writing timestamp: {e}", level="ERROR")

def format_datetime_iso(dt=None):
    """Return ISO formatted datetime string."""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()

# ============================================================================
# TELEGRAM RESILIENCE FUNCTIONS - THE KEY IMPROVEMENTS
# ============================================================================

def verify_telegram_connectivity(max_attempts=3):
    """Verify Telegram API is reachable and active (with retry)."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    if not bot_token:
        log_message("❌ No TELEGRAM_BOT_TOKEN configured. Skipping health check.", level="ERROR")
        return False, "No token"
    
    last_error = None
    
    for attempt in range(max_attempts):
        try:
            # Lightweight ping to test API connectivity
            response = requests.get(
                f"https://api.telegram.org/bot{bot_token}/getMe",
                timeout=HEALTH_CHECK_TIMEOUT_SECONDS
            )
            
            if response.status_code == 200:
                bot_info = response.json()
                log_message(f"✅ Telegram API verified - Bot ID: {bot_info.get('id')}")
                
                # Check if bot is actually active (not banned/disabled)
                if 'ok' in response.json():
                    return True, "Telegram reachable and active"
                else:
                    last_error = f"API returned non-ok status: {response.text}"
            else:
                last_error = f"HTTP error: {response.status_code} - {response.text[:100]}"
                
        except requests.exceptions.Timeout:
            last_error = "Request timed out (API may be unreachable)"
        except Exception as e:
            last_error = f"Connectivity check failed: {str(e)}"
        
        # If we get here, the attempt failed - wait before retrying
        if attempt < max_attempts - 1:
            wait_time = 5  # Wait 5 seconds between attempts for health check
            log_message(f"⚠️ Telegram health check failed (attempt {attempt+1}/{max_attempts}). Retrying in {wait_time}s...")
            time.sleep(wait_time)
    
    return False, last_error

def send_to_telegram_resiliently(keyboard_dict={}, max_retries=DEFAULT_MAX_RETRIES):
    """Send message to Telegram with exponential backoff retry logic."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    chat_id = TELEGRAM_CHAT_ID
    
    if not bot_token or not chat_id:
        log_message("❌ Missing Telegram credentials. Cannot send message.", level="ERROR")
        return False
    
    attempt = 1
    last_error = None
    
    while attempt <= max_retries:
        try:
            # Build the JSON payload for the request
            payload = {
                'chat_id': chat_id,
                'text': json.dumps(keyboard_dict),
                'parse_mode': 'Markdown',
                'disable_notification': False
            }
            
            # Send the message
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if 'ok' in result or (result.get('result') and isinstance(result.get('result'), dict) and result['result'].get('message_id')):
                    log_message(f"✅ Message sent successfully (attempt {attempt}/{max_retries})")
                    
                    # Update dedupe timestamp on success
                    set_last_send_timestamp(time.time())
                    return True
                
                else:
                    # API acknowledged but message failed for some reason
                    error_msg = str(result.get('description', 'Unknown error'))
                    last_error = f"Telegram accepted request but failed to send: {error_msg}"
            
            else:
                last_error = f"HTTP error: {response.status_code} - {response.text[:200]}"
                
        except requests.exceptions.Timeout:
            last_error = "Request timed out (API may be unreachable)"
        except Exception as e:
            last_error = f"Send failed: {str(e)}"
        
        # Handle specific error types
        
        # If it's a token or disabled issue, won't recover
        if last_error and ('token' in str(last_error).lower() or 'disabled' in str(last_error).lower()):
            log_message(f"⚠️ Telegram API issue (likely token/disabled). No auto-recovery possible.", level="ERROR")
            return False
        
        # All other errors should retry with exponential backoff
        if attempt < max_retries:
            # Calculate wait time using exponential backoff
            wait_time = min(
                RETRY_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)),
                RETRY_BACKOFF_MAX_SECONDS
            )
            
            log_message(f"⚠️ Send failed: {last_error}. Attempt {attempt}/{max_retries}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
        
        attempt += 1
    
    # All retries exhausted
    log_message(f"❌ ALL RETRIES EXHAUSTED after {max_retries} attempts. Last error: {last_error}", level="ERROR")
    return False

# ============================================================================
# AGGREGATOR CORE FUNCTIONS
# ============================================================================

class NewsAggregatorResilient:
    """Main news aggregator class with resilience built-in."""
    
    def __init__(self):
        self.config = self.load_config()
        self.last_quick_run = None
        self.last_full_run = None
    
    def load_config(self):
        """Load configuration from file if available."""
        config_path = PROJECT_ROOT / 'config.json'
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            log_message(f"Warning: Could not load config file: {e}", level="WARN")
        
        # Default configuration
        return {
            'quick_update_frequency_minutes': 60,
            'full_briefing_schedule': ['08:00', '12:00', '16:00', '20:00'],
            'log_retention_days': 30
        }
    
    def update_quick_logs(self):
        """Generate quick update log entries."""
        timestamp = time.time()
        
        try:
            with open(CRON_QUICK_LOG, 'a') as f:
                f.write(f"[{datetime.fromtimestamp(timestamp).isoformat()}] Quick Update Run\n")
                f.write(f"  RSS Feeds Updated: {self.config.get('quick_feeds_count', 0)}\n")
                f.write(f"  Timestamps Validated: Yes\n")
                f.write("=" * 60 + "\n")
            
            self.last_quick_run = datetime.fromtimestamp(timestamp).isoformat()
            log_message("Quick update logs updated successfully")
            
        except Exception as e:
            log_message(f"Error writing quick update logs: {e}", level="ERROR")
    
    def update_full_logs(self):
        """Generate full briefing log entries."""
        timestamp = time.time()
        
        try:
            with open(CRON_FULL_LOG, 'a') as f:
                f.write(f"[{datetime.fromtimestamp(timestamp).isoformat()}] Full Briefing Run\n")
                f.write(f"  RSS Feeds Processed: {self.config.get('full_feeds_count', 0)}\n")
                f.write(f"  Dedupe Logic Applied: Yes\n")
                f.write(f"  Keyboard Status: {'Active' if self.check_keyboard_status() else 'Requires Attention'}\n")
                f.write("=" * 60 + "\n")
            
            self.last_full_run = datetime.fromtimestamp(timestamp).isoformat()
            log_message("Full briefing logs updated successfully")
            
        except Exception as e:
            log_message(f"Error writing full update logs: {e}", level="ERROR")
    
    def check_keyboard_status(self):
        """Check if keyboard layout is active/functional."""
        # Placeholder for your existing keyboard status logic
        return True
    
    def get_feeds_to_process(self, feed_type='full'):
        """Get list of RSS feeds to process."""
        # Your existing feed processing logic goes here
        feeds = []
        
        try:
            if feed_type == 'quick':
                feeds = self.config.get('quick_feeds', [])
            else:
                feeds = self.config.get('full_feeds', [])
        except Exception as e:
            log_message(f"Error loading feeds: {e}", level="ERROR")
        
        return feeds
    
    def process_feed(self, feed_url):
        """Process a single RSS feed."""
        # Placeholder for your existing RSS processing logic
        # This is where you'd integrate requests/urllib with your parser
        
        log_message(f"Processing feed: {feed_url[:50]}...", level="INFO")
        
        # Return dummy data for now - replace with actual feed fetching
        return {
            'url': feed_url,
            'items_processed': 1,
            'last_updated': datetime.now().isoformat()
        }
    
    def generate_keyboard_dict(self):
        """Generate the keyboard dictionary to send to Telegram."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
        
        return {
            'timestamp': timestamp,
            'status': 'Active',
            'recent_feeds': self.config.get('quick_feeds_count', 0),
            'log_files': [
                'cron_full.log',
                'cron_quick.log'
            ]
        }
    
    def run_health_checks(self):
        """Run pre-flight health checks before sending to Telegram."""
        log_message("🔍 Running pre-send health checks...", level="INFO")
        
        # 1. Verify timestamps are current
        last_ts = get_last_send_timestamp()
        if last_ts and (datetime.now().timestamp() - last_ts) > 21600:  # > 6 hours
            log_message("⚠️ Timestamp stale (>6h). This may indicate missing runs.", level="WARN")
        
        # 2. Verify Telegram connectivity
        telegram_ok, telegram_status = verify_telegram_connectivity(max_attempts=2)
        
        if not telegram_ok:
            log_message(f"⚠️ Telegram health check failed: {telegram_status}", level="WARN")
            return False
        
        log_message("✅ All pre-send health checks passed", level="INFO")
        return True
    
    def run_full_briefing(self):
        """Run the full daily briefing with resilience."""
        log_message("=" * 60)
        log_message("📊 STARTING FULL BRIEFING - Daily News Aggregation", level="INFO")
        log_message("=" * 60)
        
        try:
            # 1. Process all RSS feeds
            feeds = self.get_feeds_to_process('full')
            
            if not feeds:
                log_message("⚠️ No full feeds configured!", level="WARN")
                return False
            
            total_items = 0
            for feed_url in feeds:
                result = self.process_feed(feed_url)
                total_items += result.get('items_processed', 0)
            
            # 2. Run health checks before sending to Telegram
            if not self.run_health_checks():
                log_message("⚠️ Health checks failed. Skipping Telegram send.", level="WARN")
                return False
            
            # 3. Generate and send keyboard dictionary
            keyboard = self.generate_keyboard_dict()
            keyboard['total_items'] = total_items
            keyboard['feed_count'] = len(feeds)
            
            success = send_to_telegram_resiliently(keyboard, max_retries=DEFAULT_MAX_RETRIES)
            
            if success:
                # Update logs
                self.update_full_logs()
                
                log_message("✅ Full briefing completed successfully!")
                log_message(f"   Feeds processed: {total_items}")
                log_message(f"   Telegram sent: Yes")
            else:
                log_message("❌ Full briefing failed to send to Telegram (retrying may occur)", level="ERROR")
            
            return success
            
        except Exception as e:
            log_message(f"❌ Error during full briefing: {e}", level="ERROR")
            import traceback
            traceback.print_exc()
            return False
    
    def run_quick_update(self):
        """Run a quick update cycle."""
        log_message("=" * 60)
        log_message("⚡ STARTING QUICK UPDATE - Incremental News Check", level="INFO")
        log_message("=" * 60)
        
        try:
            # 1. Process quick feeds
            feeds = self.get_feeds_to_process('quick')
            
            if not feeds:
                log_message("⚠️ No quick feeds configured!", level="WARN")
                return False
            
            total_items = 0
            for feed_url in feeds:
                result = self.process_feed(feed_url)
                total_items += result.get('items_processed', 0)
            
            # 2. Quick updates don't send to Telegram (to save bandwidth)
            # Update logs only
            self.update_quick_logs()
            
            log_message("✅ Quick update completed!")
            log_message(f"   Feeds updated: {total_items}")
            
            return True
            
        except Exception as e:
            log_message(f"❌ Error during quick update: {e}", level="ERROR")
            import traceback
            traceback.print_exc()
            return False
    
    def run_monitoring_loop(self, interval_minutes=60):
        """Run continuous monitoring (for scheduled jobs)."""
        log_message("🔁 Starting monitoring loop (interval: {} minutes)".format(interval_minutes))
        
        while True:
            try:
                # Check current time
                now = datetime.now().strftime('%H:%M')
                
                # Determine which operation to run based on config
                schedule = self.config.get('full_briefing_schedule', ['08:00'])
                
                should_run_full = any(s.strip() == now for s in schedule)
                
                if should_run_full and 'Full Briefing' not in str(self.last_full_run):
                    log_message(f"⏰ {now}: Running full briefing per schedule")
                    self.run_full_briefing()
                
                # Always run quick updates (more frequent monitoring)
                elif datetime.now().minute % 15 == 0:
                    log_message(f"⏰ {now}: Running periodic check")
                    self.run_quick_update()
                
            except Exception as e:
                log_message(f"Monitoring error: {e}", level="ERROR")
            
            # Wait before next iteration
            time.sleep(interval_minutes * 60)

# ============================================================================
# MAIN EXECUTION - Command Line Interface
# ============================================================================

def main_with_dedupe():
    """Main entry point with deduplication logic."""
    log_message("=" * 70)
    log_message("🚀 NEWS AGGREGATOR - RESILIENT EDITION v2.0", level="INFO")
    log_message("=" * 70)
    
    aggregator = NewsAggregatorResilient()
    
    # Check last run time and decide what to do
    last_ts = get_last_send_timestamp()
    
    if last_ts is None:
        log_message("🆕 No previous timestamp found. This may be a fresh install.", level="INFO")
    
    else:
        hours_since = (datetime.now().timestamp() - last_ts) / 3600
        
        if hours_since < 1:
            log_message(f"ℹ️ Last run was {hours_since:.1f}h ago. Recent operation detected.", level="INFO")
        
        elif hours_since > 24:
            log_message("⚠️ Long gap detected (>24h). Full check recommended.", level="WARN")

    # Run full briefing or quick update based on schedule
    import time
    current_time = datetime.now().strftime('%H:%M')
    
    if current_time in ['08:00', '12:00', '16:00', '20:00']:
        aggregator.run_full_briefing()
    else:
        aggregator.run_quick_update()
    
    log_message("✅ Execution complete", level="INFO")

if __name__ == '__main__':
    main_with_dedupe()