"""Configuration management for site monitor."""

import os
from dataclasses import dataclass, field
from typing import Optional

import yaml

from .monitor import SiteConfig


@dataclass
class EmailConfig:
    """Email notification configuration."""
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    from_addr: str
    to_addr: str


@dataclass
class Settings:
    """Global settings."""
    check_interval: int = 60
    data_dir: str = "./data"
    log_level: str = "INFO"
    webhook_url: Optional[str] = None
    email: Optional[EmailConfig] = None


@dataclass
class Config:
    """Complete configuration."""
    settings: Settings
    sites: list[SiteConfig]


def load_config(config_path: str = "config.yaml") -> Config:
    """Load configuration from YAML file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # Parse settings
    settings_data = data.get('settings', {})
    email_config = None
    if 'email' in settings_data and settings_data['email']:
        email_data = settings_data['email']
        email_config = EmailConfig(
            smtp_server=email_data.get('smtp_server', 'smtp.gmail.com'),
            smtp_port=email_data.get('smtp_port', 587),
            username=email_data.get('username', ''),
            password=email_data.get('password', ''),
            from_addr=email_data.get('from_addr', ''),
            to_addr=email_data.get('to_addr', '')
        )

    settings = Settings(
        check_interval=settings_data.get('check_interval', 60),
        data_dir=settings_data.get('data_dir', './data'),
        log_level=settings_data.get('log_level', 'INFO'),
        webhook_url=settings_data.get('webhook_url'),
        email=email_config
    )

    # Parse sites
    sites = []
    for site_data in data.get('sites', []):
        site = SiteConfig(
            name=site_data['name'],
            url=site_data['url'],
            mode=site_data.get('mode', 'text'),
            selector=site_data.get('selector'),
            interval=site_data.get('interval'),
            ignore=site_data.get('ignore', []),
            headers=site_data.get('headers', {})
        )
        sites.append(site)

    return Config(settings=settings, sites=sites)


def create_sample_config(path: str = "config.yaml"):
    """Create a sample configuration file."""
    sample = """# Site Monitor Configuration
# Add sites you want to monitor below

settings:
  # How often to check sites (in seconds)
  check_interval: 60

  # Where to store snapshots and change history
  data_dir: "./data"

  # Log level: DEBUG, INFO, WARNING, ERROR
  log_level: "INFO"

  # Optional: webhook URL for notifications (Discord, Slack, etc.)
  # webhook_url: "https://discord.com/api/webhooks/..."

# Sites to monitor
sites:
  - name: "Example Site"
    url: "https://example.com"
    mode: "text"
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(sample)
