"""Notification system for site monitor."""

import json
import logging
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

from .monitor import ChangeRecord
from .config import EmailConfig

logger = logging.getLogger(__name__)


class Notifier(ABC):
    """Base class for notifiers."""

    @abstractmethod
    def notify(self, change: ChangeRecord) -> bool:
        """Send notification about a change. Returns True if successful."""
        pass


class ConsoleNotifier(Notifier):
    """Outputs change notifications to console."""

    def __init__(self, show_diff: bool = True, colorize: bool = True):
        self.show_diff = show_diff
        self.colorize = colorize
        try:
            from colorama import init, Fore, Style
            init()
            self.Fore = Fore
            self.Style = Style
        except ImportError:
            self.colorize = False

    def notify(self, change: ChangeRecord) -> bool:
        """Print change notification to console."""
        if self.colorize:
            print(f"\n{self.Fore.YELLOW}{'='*60}{self.Style.RESET_ALL}")
            print(f"{self.Fore.RED}CHANGE DETECTED!{self.Style.RESET_ALL}")
            print(f"{self.Fore.CYAN}Site:{self.Style.RESET_ALL} {change.site_name}")
            print(f"{self.Fore.CYAN}URL:{self.Style.RESET_ALL} {change.url}")
            print(f"{self.Fore.CYAN}Time:{self.Style.RESET_ALL} {change.timestamp}")
            print(f"{self.Fore.YELLOW}{'='*60}{self.Style.RESET_ALL}")
        else:
            print(f"\n{'='*60}")
            print("CHANGE DETECTED!")
            print(f"Site: {change.site_name}")
            print(f"URL: {change.url}")
            print(f"Time: {change.timestamp}")
            print(f"{'='*60}")

        if self.show_diff and change.diff:
            print("\nDiff:")
            for line in change.diff[:50]:  # Limit diff output
                if self.colorize:
                    if line.startswith('+') and not line.startswith('+++'):
                        print(f"{self.Fore.GREEN}{line.rstrip()}{self.Style.RESET_ALL}")
                    elif line.startswith('-') and not line.startswith('---'):
                        print(f"{self.Fore.RED}{line.rstrip()}{self.Style.RESET_ALL}")
                    else:
                        print(line.rstrip())
                else:
                    print(line.rstrip())

            if len(change.diff) > 50:
                print(f"\n... and {len(change.diff) - 50} more lines")

        print()
        return True


class WebhookNotifier(Notifier):
    """Sends notifications via webhook (Discord, Slack, etc.)."""

    def __init__(self, webhook_url: str, webhook_type: str = "auto"):
        self.webhook_url = webhook_url
        self.webhook_type = webhook_type

        # Auto-detect webhook type
        if webhook_type == "auto":
            if "discord.com" in webhook_url:
                self.webhook_type = "discord"
            elif "slack.com" in webhook_url:
                self.webhook_type = "slack"
            else:
                self.webhook_type = "generic"

    def notify(self, change: ChangeRecord) -> bool:
        """Send webhook notification."""
        try:
            if self.webhook_type == "discord":
                return self._send_discord(change)
            elif self.webhook_type == "slack":
                return self._send_slack(change)
            else:
                return self._send_generic(change)
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False

    def _send_discord(self, change: ChangeRecord) -> bool:
        """Send Discord webhook notification."""
        diff_preview = ""
        if change.diff:
            diff_lines = [l for l in change.diff if l.startswith('+') or l.startswith('-')]
            diff_preview = '\n'.join(diff_lines[:20])
            if len(diff_lines) > 20:
                diff_preview += f"\n... and {len(diff_lines) - 20} more changes"

        payload = {
            "embeds": [{
                "title": "Website Change Detected!",
                "color": 0xFF6B6B,
                "fields": [
                    {"name": "Site", "value": change.site_name, "inline": True},
                    {"name": "URL", "value": change.url, "inline": True},
                    {"name": "Detected At", "value": change.timestamp, "inline": False},
                ],
                "footer": {"text": "Site Monitor Bot"}
            }]
        }

        if diff_preview:
            payload["embeds"][0]["fields"].append({
                "name": "Changes Preview",
                "value": f"```diff\n{diff_preview[:1000]}\n```",
                "inline": False
            })

        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True

    def _send_slack(self, change: ChangeRecord) -> bool:
        """Send Slack webhook notification."""
        diff_preview = ""
        if change.diff:
            diff_lines = [l for l in change.diff if l.startswith('+') or l.startswith('-')]
            diff_preview = '\n'.join(diff_lines[:20])

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Website Change Detected!"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Site:*\n{change.site_name}"},
                    {"type": "mrkdwn", "text": f"*URL:*\n{change.url}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{change.timestamp}"}
                ]
            }
        ]

        if diff_preview:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Changes:*\n```{diff_preview[:2000]}```"}
            })

        payload = {"blocks": blocks}

        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True

    def _send_generic(self, change: ChangeRecord) -> bool:
        """Send generic JSON webhook notification."""
        payload = {
            "event": "site_change",
            "site_name": change.site_name,
            "url": change.url,
            "timestamp": change.timestamp,
            "old_hash": change.old_hash,
            "new_hash": change.new_hash,
            "diff_lines": len(change.diff) if change.diff else 0
        }

        response = requests.post(
            self.webhook_url,
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return True


class EmailNotifier(Notifier):
    """Sends notifications via email."""

    def __init__(self, config: EmailConfig):
        self.config = config

    def notify(self, change: ChangeRecord) -> bool:
        """Send email notification."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[Site Monitor] Change detected on {change.site_name}"
            msg['From'] = self.config.from_addr
            msg['To'] = self.config.to_addr

            # Plain text version
            text_content = f"""
Website Change Detected!

Site: {change.site_name}
URL: {change.url}
Time: {change.timestamp}

Old Hash: {change.old_hash}
New Hash: {change.new_hash}

Diff:
{''.join(change.diff[:100]) if change.diff else 'No diff available'}
"""

            # HTML version
            diff_html = ""
            if change.diff:
                diff_lines = []
                for line in change.diff[:100]:
                    if line.startswith('+') and not line.startswith('+++'):
                        diff_lines.append(f'<span style="color: green;">{line}</span>')
                    elif line.startswith('-') and not line.startswith('---'):
                        diff_lines.append(f'<span style="color: red;">{line}</span>')
                    else:
                        diff_lines.append(line)
                diff_html = '<br>'.join(diff_lines)

            html_content = f"""
<html>
<body>
<h2 style="color: #FF6B6B;">Website Change Detected!</h2>
<table>
<tr><td><strong>Site:</strong></td><td>{change.site_name}</td></tr>
<tr><td><strong>URL:</strong></td><td><a href="{change.url}">{change.url}</a></td></tr>
<tr><td><strong>Time:</strong></td><td>{change.timestamp}</td></tr>
</table>
<h3>Changes:</h3>
<pre style="background: #f4f4f4; padding: 10px; font-family: monospace;">
{diff_html}
</pre>
<p><small>Sent by Site Monitor Bot</small></p>
</body>
</html>
"""

            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.username, self.config.password)
                server.sendmail(
                    self.config.from_addr,
                    self.config.to_addr,
                    msg.as_string()
                )

            logger.info(f"Email notification sent to {self.config.to_addr}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False


class NotificationManager:
    """Manages multiple notifiers."""

    def __init__(self):
        self.notifiers: list[Notifier] = []

    def add_notifier(self, notifier: Notifier):
        """Add a notifier."""
        self.notifiers.append(notifier)

    def notify_all(self, change: ChangeRecord):
        """Send notification to all registered notifiers."""
        for notifier in self.notifiers:
            try:
                notifier.notify(change)
            except Exception as e:
                logger.error(f"Notifier {notifier.__class__.__name__} failed: {e}")
