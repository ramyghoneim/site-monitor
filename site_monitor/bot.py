"""Main bot runner for site monitoring."""

import logging
import signal
import sys
import time
from datetime import datetime
from typing import Optional

import schedule

from .monitor import SiteMonitor, SiteConfig
from .config import Config, load_config
from .notifier import (
    NotificationManager,
    ConsoleNotifier,
    WebhookNotifier,
    EmailNotifier
)

logger = logging.getLogger(__name__)


class SiteMonitorBot:
    """Main bot that orchestrates site monitoring."""

    def __init__(self, config: Config):
        self.config = config
        self.monitor = SiteMonitor(data_dir=config.settings.data_dir)
        self.notification_manager = NotificationManager()
        self.running = False
        self._setup_notifiers()
        self._setup_logging()

    def _setup_logging(self):
        """Configure logging based on settings."""
        log_level = getattr(logging, self.config.settings.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _setup_notifiers(self):
        """Set up notification channels based on config."""
        # Always add console notifier
        self.notification_manager.add_notifier(ConsoleNotifier(show_diff=True))

        # Add webhook notifier if configured
        if self.config.settings.webhook_url:
            self.notification_manager.add_notifier(
                WebhookNotifier(self.config.settings.webhook_url)
            )
            logger.info("Webhook notifications enabled")

        # Add email notifier if configured
        if self.config.settings.email:
            self.notification_manager.add_notifier(
                EmailNotifier(self.config.settings.email)
            )
            logger.info("Email notifications enabled")

    def check_site(self, site: SiteConfig):
        """Check a single site for changes."""
        try:
            logger.debug(f"Checking {site.name}...")
            change = self.monitor.check_site(site)

            if change:
                logger.info(f"Change detected on {site.name}")
                self.notification_manager.notify_all(change)
            else:
                logger.debug(f"No changes on {site.name}")

        except Exception as e:
            logger.error(f"Error checking {site.name}: {e}")

    def check_all_sites(self):
        """Check all configured sites."""
        logger.info(f"Running check on {len(self.config.sites)} site(s)...")
        for site in self.config.sites:
            self.check_site(site)

    def run_once(self):
        """Run a single check of all sites."""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting site check...")
        self.check_all_sites()
        print("Check complete.\n")

    def run(self):
        """Run the bot continuously."""
        self.running = True

        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            print("\nShutting down gracefully...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        print(f"""
╔════════════════════════════════════════════════════════════╗
║                    SITE MONITOR BOT                        ║
╠════════════════════════════════════════════════════════════╣
║  Monitoring {len(self.config.sites):2d} site(s)                                  ║
║  Check interval: {self.config.settings.check_interval:4d} seconds                          ║
║  Data directory: {self.config.settings.data_dir:<38} ║
╚════════════════════════════════════════════════════════════╝
        """)

        print("Sites being monitored:")
        for i, site in enumerate(self.config.sites, 1):
            interval = site.interval or self.config.settings.check_interval
            print(f"  {i}. {site.name} ({site.url}) - every {interval}s")
        print()

        # Schedule checks for each site
        for site in self.config.sites:
            interval = site.interval or self.config.settings.check_interval
            schedule.every(interval).seconds.do(self.check_site, site)

        # Run initial check
        print("Running initial check...")
        self.check_all_sites()
        print("\nMonitoring started. Press Ctrl+C to stop.\n")

        # Main loop
        while self.running:
            schedule.run_pending()
            time.sleep(1)

        print("Bot stopped.")

    def list_sites(self):
        """List all monitored sites and their status."""
        print("\nMonitored Sites:")
        print("-" * 60)

        for i, site in enumerate(self.config.sites, 1):
            status = self.monitor.get_site_status(site.name)
            interval = site.interval or self.config.settings.check_interval

            print(f"\n{i}. {site.name}")
            print(f"   URL: {site.url}")
            print(f"   Mode: {site.mode}")
            print(f"   Interval: {interval}s")
            print(f"   Has snapshot: {status['has_snapshot']}")
            print(f"   Total changes: {status['total_changes']}")
            if status['last_check']:
                print(f"   Last check: {status['last_check']}")

        print("\n" + "-" * 60)

    def show_history(self, site_name: str, limit: int = 20):
        """Show change history for a site."""
        # Find site by name
        site = None
        for s in self.config.sites:
            if s.name.lower() == site_name.lower():
                site = s
                break

        if not site:
            print(f"Site '{site_name}' not found.")
            return

        history = self.monitor.load_history(site.name)

        print(f"\nChange History for {site.name}:")
        print("-" * 60)

        if not history:
            print("No history available.")
            return

        for event in history[-limit:]:
            timestamp = event.get('timestamp', 'Unknown')
            event_type = event.get('event', 'unknown')

            if event_type == 'initial_snapshot':
                print(f"  [{timestamp}] Initial snapshot created")
            elif event_type == 'change_detected':
                diff_lines = event.get('diff_lines', 0)
                print(f"  [{timestamp}] CHANGE - {diff_lines} lines modified")

        print("-" * 60)


def create_bot(config_path: str = "config.yaml") -> SiteMonitorBot:
    """Create a bot instance from config file."""
    config = load_config(config_path)
    return SiteMonitorBot(config)
