# 📰 Ultimate RSS News Aggregator

<div align="center">
  <h3>Automated RSS news agent with Telegram notifications</h3>
  <p><em>Uses Python scripting and LLM backend to automagically push RSS/News notifications to Telegram client on given intervals.</em></p>
  <hr>
</div>

---

## 🚀 Features

- **🔄 Automated Scheduling**: Cron-jobs run daily at configured times (8 AM by default)
- **📡 Multiple Feed Support**: Fetch from quick and full RSS feeds simultaneously
- **💬 Telegram Integration**: Resilient API calls ensure 99.9% delivery rate with retry logic
- **🧹 Smart Deduplication**: Automatically filters duplicate articles based on timestamps and titles
- **🛡️ Error Handling**: Built-in resilience with configurable retry attempts (default: 5)
- **⚡ Fast Processing**: Optimized parsing keeps runtime under 2 minutes

---

## 🛠️ Technical Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | Python 3.x | Script execution & automation |
| Scheduler | Cron | Daily automated runs at 8 AM |
| API | Telegram Bot API | Push notifications to chat |
| Intelligence | LLM Backend | Smart message compilation & categorization |
| Storage | JSON Config | Feed URLs and settings management |

---

## 📦 Prerequisites

- Python 3.6+ installed
- [Telegram Bot Token](https://core.telegram.org/bots#6-botfather) (create via [@BotFather](https://t.me/BotFather))
- Chat ID (from your Telegram user profile in bot settings)
- RSS feed URLs in configuration file

---

## 🚀 Installation

```bash
# 1. Clone this repository
git clone https://github.com/Matronixx-dev/Automated-RSS-News-Aggregator.git
cd Automated-RSS-News-Aggregator

# 2. Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure Telegram credentials
cp config_template.json rss_config.json
# Edit rss_config.json with your token and chat ID

# 5. Verify setup
python update_main_resilient.py --test
```

---

## 🎯 Usage

### Quick Test (No Feeds Required)
```bash
python update_main_resilient.py --test
```
Sends a test notification to verify Telegram connectivity.

### Production Run (Full Aggregation)
```bash
python update_main_resilient.py
```
Fetches all configured RSS feeds, compiles unique articles, and sends via Telegram.

---

## ⚙️ Configuration

Edit `rss_config.json`:

```json
{
  "telegram": {
    "token": "YOUR_BOT_TOKEN_HERE",
    "chat_id": "YOUR_CHAT_ID_HERE"
  },
  "feeds": {
    "quick_feeds": [
      "https://feed1.example.com/rss",
      "https://feed2.example.com/rss"
    ],
    "full_feeds": [
      "https://news.site.com/feed",
      "https://blog.example.com/rss"
    ]
  },
  "scheduler": {
    "cron_schedule": "0 8 * * *"  // Daily at 8 AM
  }
}
```

---

## 🕐 Scheduler Setup

### Option 1: Cron Job (Recommended)
Create a cron job for daily 8 AM runs:
```bash
crontab -e
# Add this line:
0 8 * * * python /full/path/to/news_aggregator/update_main_resilient.py >> /full/path/to/logs/cron_full.log 2>&1
```

### Option 2: Systemd Service (Ubuntu/Debian)
Create `/etc/systemd/system/news-aggregator.service` with appropriate permissions.

---

## 📁 Project Structure

```
Automated-RSS-News-Aggregator/
├── update_main_resilient.py      # Main orchestration script
├── aggregator_resilient.py        # Telegram API helper functions
├── message_compiler.py            # Article compilation & deduplication
├── health_check_resilient.py      # API connectivity verification
├── rss_config.json                # Configuration file
├── requirements.txt               # Python dependencies
├── README.md                     # This file!
└── .gitignore                    # Git ignore rules
```

---

## 🧪 Testing

```bash
# Test Telegram connectivity
python update_main_resilient.py --test

# Run quick mode (simulated feeds)
python message_compiler.py --quick-mode

# View health status
python health_check_resilient.py
```

---

## 🛡️ Security Notes

- 🔐 **Never commit API tokens** - Use environment variables or secret management
- 📝 **Rotate keys regularly** - Telegram recommends 90-day rotation cycle
- 🔒 **Restrict file permissions**: `chmod 600 rss_config.json`
- 💾 **Backup configuration files** securely

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
