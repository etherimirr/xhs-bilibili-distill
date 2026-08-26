"""Bilibili adapter. Uses yt-dlp, which handles the extraction and rate limiting."""
from __future__ import annotations
import subprocess
from pathlib import Path
from .base import Source, Item


class BilibiliSource(Source):
    name = "bilibili"

    @staticmethod
    def parse_line(line: str) -> Item:
        """Accepts a bare BV id or a full bilibili URL."""
        line = line.strip()
        if "bilibili.com" in line:
            bv = line.rstrip("/").split("/")[-1].split("?")[0]
        else:
            bv = line
        return Item(key=bv)

    def url(self, item: Item) -> str:
        return f"https://www.bilibili.com/video/{item.key}"

    def fetch_media(self, item: Item, dest_dir: Path) -> Path | None:
        dest_dir.mkdir(parents=True, exist_ok=True)
        audio = dest_dir / f"{item.key}.m4a"
        if audio.exists():
            return audio
        try:
            # -f ba = bestaudio. We never need the video stream for a transcript,
            # which cuts download size by roughly an order of magnitude.
            subprocess.run(
                ["yt-dlp", "-f", "ba", "-o", str(audio), self.url(item)],
                capture_output=True, timeout=300,
            )
        except subprocess.TimeoutExpired:
            return None
        return audio if audio.exists() else None

    def fetch_title(self, item: Item) -> str:
        if item.title:
            return item.title
        try:
            r = subprocess.run(
                ["yt-dlp", "--print", "%(title)s", "--skip-download", self.url(item)],
                capture_output=True, text=True, timeout=60,
            )
            return r.stdout.strip()[:120]
        except Exception:      # noqa: BLE001
            return ""
