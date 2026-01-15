"""Core site monitoring functionality."""

import hashlib
import json
import os
import re
import difflib
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup


@dataclass
class ChangeRecord:
    """Represents a detected change."""
    site_name: str
    url: str
    timestamp: str
    old_hash: str
    new_hash: str
    diff: list[str]
    old_content: str = ""
    new_content: str = ""


@dataclass
class SiteConfig:
    """Configuration for a monitored site."""
    name: str
    url: str
    mode: str = "text"  # "full", "text", "selector"
    selector: Optional[str] = None
    interval: Optional[int] = None
    ignore: list[str] = field(default_factory=list)
    headers: dict = field(default_factory=dict)


class SiteMonitor:
    """Monitors websites for changes."""

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = data_dir
        self.snapshots_dir = os.path.join(data_dir, "snapshots")
        self.history_dir = os.path.join(data_dir, "history")
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create necessary directories."""
        os.makedirs(self.snapshots_dir, exist_ok=True)
        os.makedirs(self.history_dir, exist_ok=True)

    def _get_safe_filename(self, name: str) -> str:
        """Convert site name to safe filename."""
        return re.sub(r'[^\w\-]', '_', name.lower())

    def _get_snapshot_path(self, site_name: str) -> str:
        """Get path to snapshot file for a site."""
        filename = self._get_safe_filename(site_name)
        return os.path.join(self.snapshots_dir, f"{filename}.txt")

    def _get_history_path(self, site_name: str) -> str:
        """Get path to history file for a site."""
        filename = self._get_safe_filename(site_name)
        return os.path.join(self.history_dir, f"{filename}.json")

    def fetch_content(self, site: SiteConfig) -> Optional[str]:
        """Fetch and process content from a URL."""
        try:
            headers = {**self.DEFAULT_HEADERS, **site.headers}
            response = requests.get(
                site.url,
                headers=headers,
                timeout=30,
                allow_redirects=True
            )
            response.raise_for_status()

            content = response.text

            if site.mode == "full":
                return content

            soup = BeautifulSoup(content, 'lxml')

            # Remove ignored elements
            for selector in site.ignore:
                for element in soup.select(selector):
                    element.decompose()

            if site.mode == "selector" and site.selector:
                elements = soup.select(site.selector)
                if elements:
                    return "\n".join(el.get_text(strip=True, separator=" ") for el in elements)
                return None

            # mode == "text"
            # Remove script and style elements
            for tag in soup(['script', 'style', 'noscript', 'iframe']):
                tag.decompose()

            text = soup.get_text(separator='\n', strip=True)
            # Normalize whitespace
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines)

        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch {site.url}: {e}")

    def get_content_hash(self, content: str) -> str:
        """Generate hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def load_snapshot(self, site_name: str) -> Optional[str]:
        """Load previous snapshot for a site."""
        path = self._get_snapshot_path(site_name)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def save_snapshot(self, site_name: str, content: str):
        """Save current content as snapshot."""
        path = self._get_snapshot_path(site_name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def load_history(self, site_name: str) -> list[dict]:
        """Load change history for a site."""
        path = self._get_history_path(site_name)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def save_history(self, site_name: str, history: list[dict]):
        """Save change history for a site."""
        path = self._get_history_path(site_name)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)

    def get_diff(self, old_content: str, new_content: str) -> list[str]:
        """Generate unified diff between old and new content."""
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)

        diff = list(difflib.unified_diff(
            old_lines, new_lines,
            fromfile='previous',
            tofile='current',
            lineterm=''
        ))
        return diff

    def check_site(self, site: SiteConfig) -> Optional[ChangeRecord]:
        """
        Check a site for changes.
        Returns ChangeRecord if changes detected, None otherwise.
        """
        current_content = self.fetch_content(site)
        if current_content is None:
            return None

        current_hash = self.get_content_hash(current_content)
        previous_content = self.load_snapshot(site.name)

        if previous_content is None:
            # First time checking this site
            self.save_snapshot(site.name, current_content)
            history = self.load_history(site.name)
            history.append({
                "timestamp": datetime.now().isoformat(),
                "event": "initial_snapshot",
                "hash": current_hash
            })
            self.save_history(site.name, history)
            return None

        previous_hash = self.get_content_hash(previous_content)

        if current_hash != previous_hash:
            # Change detected!
            diff = self.get_diff(previous_content, current_content)
            timestamp = datetime.now().isoformat()

            # Save new snapshot
            self.save_snapshot(site.name, current_content)

            # Update history
            history = self.load_history(site.name)
            history.append({
                "timestamp": timestamp,
                "event": "change_detected",
                "old_hash": previous_hash,
                "new_hash": current_hash,
                "diff_lines": len([l for l in diff if l.startswith('+') or l.startswith('-')])
            })
            self.save_history(site.name, history)

            return ChangeRecord(
                site_name=site.name,
                url=site.url,
                timestamp=timestamp,
                old_hash=previous_hash,
                new_hash=current_hash,
                diff=diff,
                old_content=previous_content,
                new_content=current_content
            )

        return None

    def get_site_status(self, site_name: str) -> dict:
        """Get current monitoring status for a site."""
        snapshot_path = self._get_snapshot_path(site_name)
        history = self.load_history(site_name)

        return {
            "has_snapshot": os.path.exists(snapshot_path),
            "total_changes": len([h for h in history if h.get("event") == "change_detected"]),
            "last_check": history[-1]["timestamp"] if history else None,
            "history": history[-10:]  # Last 10 events
        }
