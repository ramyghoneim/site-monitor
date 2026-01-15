# Site Monitor Bot

A Python bot that monitors websites for changes and notifies you in real-time. Track any website and get instant alerts when content changes.

## Features

- **Real-time monitoring** - Continuously checks websites at configurable intervals
- **Smart change detection** - Uses content hashing and diffing to detect changes
- **Multiple monitoring modes**:
  - `full` - Monitor entire HTML page
  - `text` - Monitor text content only (ignores HTML structure changes)
  - `selector` - Monitor specific CSS selectors
- **Flexible notifications**:
  - Console output with colored diff
  - Discord webhooks
  - Slack webhooks
  - Email notifications
  - Generic JSON webhooks
- **Change history** - Stores snapshots and tracks all changes over time
- **Ignore patterns** - Exclude dynamic elements like timestamps or ads

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd site-monitor

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

1. **Edit the configuration file** (`config.yaml`):

```yaml
settings:
  check_interval: 60  # Check every 60 seconds
  data_dir: "./data"

sites:
  - name: "My Website"
    url: "https://example.com"
    mode: "text"
```

2. **Run the bot**:

```bash
python main.py
```

## Usage

```bash
# Start continuous monitoring
python main.py

# Run a single check
python main.py --once

# List all monitored sites and their status
python main.py --list

# Show change history for a site
python main.py --history "My Website"

# Use a custom config file
python main.py --config /path/to/config.yaml

# Create a sample config file
python main.py --init

# Enable verbose logging
python main.py --verbose
```

## Configuration

### Settings

| Option | Description | Default |
|--------|-------------|---------|
| `check_interval` | How often to check sites (seconds) | 60 |
| `data_dir` | Directory for snapshots and history | ./data |
| `log_level` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `webhook_url` | URL for webhook notifications | None |

### Site Configuration

| Option | Description | Required |
|--------|-------------|----------|
| `name` | Unique name for the site | Yes |
| `url` | URL to monitor | Yes |
| `mode` | Monitoring mode: `full`, `text`, or `selector` | No (default: text) |
| `selector` | CSS selector (only for `selector` mode) | No |
| `interval` | Override check interval for this site | No |
| `ignore` | List of CSS selectors to ignore | No |
| `headers` | Custom HTTP headers | No |

### Example Configuration

```yaml
settings:
  check_interval: 60
  data_dir: "./data"
  log_level: "INFO"

  # Discord webhook (optional)
  webhook_url: "https://discord.com/api/webhooks/..."

sites:
  # Monitor entire page text
  - name: "News Site"
    url: "https://news.ycombinator.com"
    mode: "text"
    interval: 120

  # Monitor specific element
  - name: "Product Price"
    url: "https://example.com/product"
    mode: "selector"
    selector: ".price"

  # Monitor with ignored elements
  - name: "Blog"
    url: "https://example.com/blog"
    mode: "text"
    ignore:
      - ".timestamp"
      - ".visitor-count"
      - ".advertisement"

  # Custom headers
  - name: "Protected Page"
    url: "https://example.com/protected"
    headers:
      Authorization: "Bearer token123"
      User-Agent: "CustomBot/1.0"
```

## Notifications

### Discord Webhooks

1. Go to your Discord server settings
2. Navigate to Integrations > Webhooks
3. Create a new webhook and copy the URL
4. Add to config:

```yaml
settings:
  webhook_url: "https://discord.com/api/webhooks/..."
```

### Slack Webhooks

1. Create a Slack app at https://api.slack.com/apps
2. Enable Incoming Webhooks
3. Add to config:

```yaml
settings:
  webhook_url: "https://hooks.slack.com/services/..."
```

### Email Notifications

```yaml
settings:
  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "your-email@gmail.com"
    password: "your-app-password"
    from_addr: "your-email@gmail.com"
    to_addr: "recipient@example.com"
```

**Note**: For Gmail, you'll need to use an [App Password](https://support.google.com/accounts/answer/185833).

## Data Storage

The bot stores data in the configured `data_dir`:

```
data/
├── snapshots/          # Latest content snapshot for each site
│   ├── my_website.txt
│   └── news_site.txt
└── history/            # Change history JSON for each site
    ├── my_website.json
    └── news_site.json
```

## Programmatic Usage

```python
from site_monitor.bot import create_bot
from site_monitor.monitor import SiteMonitor, SiteConfig

# Using the bot
bot = create_bot("config.yaml")
bot.run()  # Continuous monitoring
bot.run_once()  # Single check

# Direct monitor usage
monitor = SiteMonitor(data_dir="./data")
site = SiteConfig(name="Test", url="https://example.com", mode="text")
change = monitor.check_site(site)
if change:
    print(f"Change detected: {change.diff}")
```

## License

MIT License
