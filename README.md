# 📰 Automated RSS News Aggregator

<div align="center">

**Python-Based News Feed Processor with Telegram Notifications**

[![Python](https://img.shields.io/badge/Python-3.8+-blue)](https://www.python.org/downloads/)  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[![Telegram Notifications](https://img.shields.io/badge/Telegram-Auto--Notif-green)](https://telegram.org)

*A production-grade news aggregation system that fetches RSS feeds, processes articles intelligently, and delivers daily summaries via Telegram.*

---

## 📋 Table of Contents

- [About](#about)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Cron Setup Guide](#cron-setup-guide)
- [Troubleshooting](#troubleshooting)
- [Version History](#version-history)
- [Contributing](#contributing)
- [Security Notice](#security-notice)

---

## About

This Python-based news aggregator fetches articles from multiple RSS feeds, deduplicates content intelligently, and sends daily summaries via Telegram notifications. Perfect for staying informed across your preferred news sources with automated delivery.

### What It Does:

- ✅ Fetches articles from 10+ configured RSS feeds
- ✅ Removes duplicates using smart hash-based tracking
- ✅ Compiles daily digests into organized categories (Technology, Politics, Business, etc.)
- ✅ Delivers Telegram notifications at scheduled times (8:00 AM default)
- ✅ Debug mode for testing without hitting live feeds

---

## Features

- 🎯 **Smart Deduplication** — Prevents same articles from appearing multiple times
- 📊 **Category-Based Organization** — News sorted into logical topics
- 🔔 **Telegram API Integration** — Reliable notification delivery with retry logic
- ⚙️ **Pure Python Standard Lib** — No external pip dependencies needed!
- 🧪 **Debug Mode Support** — Test runs without affecting production data
- 🛡️ **Error Handling & Logging** — Comprehensive logs for troubleshooting

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/Matronixx-dev/Automated-RSS-News-Aggregator.git
cd Automated-RSS-News-Aggregator
```

### 2. Check Python Version

Ensure you have Python 3.8 or higher:

```bash
python3 --version
# Should output: Python 3.8.x or higher
```

### 3. Verify Core Files Present

```bash
ls -la update_main_resilient.py message_compiler.py aggregator_resilient.py rss_config.json
```

All files should exist in the project root directory.

### 4. (Optional) Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

---

## Configuration

### Main Config File: `rss_config.json`

Located at: `/home/mitch/projects/sandboxes/news_aggregator/rss_config.json`

#### Quick Structure Overview:

```json
{
  "quick_feeds": [
    {
      "name": "Technology Briefs",
      "url": "https://example-tech-rss.com/feed.xml"
    }
  ],
  "full_feeds": [
    {
      "name": "Full News Source A",
      "url": "https://example-news.com/rss.xml"
    }
  ]
}
```

#### Feed Types:

- **quick_feeds** — Lighter-weight RSS sources, processed faster
- **full_feeds** — Heavier news sources with more articles per run

#### Customizing Your Feeds:

1. Open `rss_config.json` in any text editor
2. Add new feed URLs following the structure above
3. Save and test your configuration

---

## Usage

### Running with Debug Mode (Testing)

```bash
DEBUG_MODE=TRUE python3 update_main_resilient.py
```

**What it does:**
- Clears dedup tracker after each run
- Forces fresh compilation without checking previous articles
- Perfect for testing message length and delivery
- Shows all RSS processing without dedup filtering

### Normal Production Run (Recommended)

```bash
python3 update_main_resilient.py
```

**What it does:**
- Uses existing dedup tracker (`dedup_tracker.json`)
- Only processes NEW articles since last run
- Efficient and avoids duplicate Telegram messages
- Standard production behavior

### Forcing Full Rescan (Rare Cases)

Use `aggregator_resilient.py` when you need to clear the dedup cache:

```bash
python3 aggregator_resilient.py --force
```

**When to use:**
- After changing RSS feed URLs significantly
- To fix stuck/missing articles
- To reset dedup tracking database manually

---

## Cron Setup Guide

### Linux/macOS

#### 1. Add Your User's Cron Entry

```bash
crontab -e
```

#### 2. Add This Line (Daily at 8:00 AM)

```cron
0 8 * * * cd /home/mitch/projects/sandboxes/news_aggregator && PYTHONPATH=/home/mitch/projects/sandboxes/news_aggregator python3 update_main_resilient.py >> logs/aggregator.log 2>&1
```

#### 3. Verify Cron Setup

```bash
crontab -l | grep "news"
```

### Windows (Task Scheduler)

#### 1. Open Task Scheduler → Create Basic Task

Name: `RSS News Aggregator`

#### 2. Trigger Settings

- **Start:** Daily
- **Time:** 08:00 AM

#### 3. Action Settings

- **Program/script:** `python.exe`
- **Add arguments:** `-c "import os; os.chdir(r'\\path\\to\\news_aggregator'); import sys; sys.path.append(os.getcwd()); exec(open('update_main_resilient.py').read())"`
- **Start in:** `C:\Path\To\News_Aggregator`

#### 4. Finish & Test

Open Command Prompt, navigate to folder, run:
```bash
python3 update_main_resilient.py
```

### Testing Cron Jobs (Before Production)

**Linux/macOS:**
```bash
sudo -u mitch /bin/bash -c "cd /home/mitch/projects/sandboxes/news_aggregator && python3 update_main_resilient.py"
```

**Windows Command Prompt:**
```cmd
cd C:\Path\To\News_Aggregator && python3 update_main_resilient.py
```

---

## Troubleshooting

### Telegram "Bad Request: message is too long" Error

**Cause:** Article descriptions exceed Telegram's 4,096 character limit per message.

**Fix:** The `message_compiler.py` truncates descriptions to 150 characters automatically. If still failing, check for oversized titles or hyperlinks in article URLs.

### Dedup Tracker Not Updating

**Symptoms:** Old articles keep appearing daily despite being sent previously.

**Solution:**
1. Locate `dedup_tracker.json` in project folder
2. Clear/backup the file (it will regenerate on next run)
3. Run production mode: `python3 update_main_resilient.py`

### RSS Feed Not Processing Any Articles

**Possible Causes:**
- Feed URL is invalid or unreachable
- Network/firewall blocking external requests
- Feed changed structure (e.g., moved to HTTPS only)

**Fix:**
1. Test URL in browser or curl: `curl https://your-feed-url.com/rss.xml`
2. Update `rss_config.json` with working URLs
3. Check logs for specific feed failure messages

### Script Crashes During Debug Mode

**Recent Fix:** The `force_refresh=True` parameter causing TypeError was removed in v2.1.0. If you're still seeing crashes:
1. Update from latest version (v2.1.0+)
2. Run: `DEBUG_MODE=TRUE python3 update_main_resilient.py`

### Telegram Login Failed / API Connection Issues

**Cause:** Telegram Bot Token not set or expired.

**Fix:**
1. Verify token exists in `.env` file or hardcoded location
2. Ensure bot is active via @BotFather on Telegram
3. Restart cron job after making changes

---

## Version History

### v2.1.0 — Bug Fix Release (April 20, 2026)

**What Changed:**
- ✅ Removed `force_refresh=True` parameter causing TypeError in debug mode
- ✅ Fixed crash when running `DEBUG_MODE=TRUE` environment variable
- ✅ Telegram notifications now work reliably in both debug and production modes

**Files Modified:**
- `update_main_resilient.py` — Core script logic fix

---

### v2.1 — RSS Processing Enhancements (April 17, 2026)

**What Changed:**
- ✅ Enhanced deduplication logic using hash-based tracking
- ✅ Category-based article organization (Technology, Politics, Business, Sports)
- ✅ Improved Telegram message compilation and delivery system
- ✅ Reduced false positives in duplicate detection

**Files Modified:**
- `update_main_resilient.py` — Core aggregation improvements
- `aggregator_resilient.py` — New helper for dedup tracking management
- `message_compiler.py` — Better message formatting

---

### v2.0 — Initial Public Release (April 13, 2026)

**What Changed:**
- ✅ Initial production-ready release with RSS feed processing
- ✅ Telegram bot integration and notification system
- ✅ Basic deduplication logic implemented
- ✅ Cron job scheduling for daily 8 AM deliveries

**Files Created:**
- `update_main_resilient.py` — Main aggregation script
- `aggregator_resilient.py` — Helper utilities
- `rss_config.json` — Feed configuration
- `CHANGELOG.md` — Version history tracking
- `.gitignore` — Repository security and clean-up rules

---

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## Security Notice

> ⚠️ **GitHub Actions Currently Paused**  
> We're pausing GitHub Actions workflows until we research and address known CI/CD security vulnerabilities mentioned in recent industry advisories. No automated testing is running at this time; manual verification required for all changes.

> 🔐 **Environment Variables & API Keys**  
> If you use environment variables (e.g., `.env` files), ensure they're not committed to the repository. The `.gitignore` includes common patterns, but verify your setup excludes sensitive data.

---

## Support & Contact

If you encounter issues or have suggestions, please open an issue on GitHub. For production deployments requiring support, contact the project maintainer directly.

---

<div align="center">
  
**Made with ❤️ and ☕ by Matronixx-dev** Code written by Alfred Pennyworth (Powered by Qwen 3.5) 
*April 2026 — Production News Aggregation Pipeline*

</div>
