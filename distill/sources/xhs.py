"""Xiaohongshu / RedNote adapter.

Delegates the actual download to XHS-Downloader (JoeanAmier, GPL-3.0), which is
NOT bundled with this project — point XHS_DOWNLOADER_PATH at your own clone.
We only orchestrate it.
"""
from __future__ import annotations
import subprocess, sqlite3, glob
from pathlib import Path
from .base import Source, Item
from .. import config

MEDIA_EXTS = ("mp4", "m4v", "mov", "mkv", "webm")


class XhsSource(Source):
    name = "xhs"

    @staticmethod
    def parse_line(line: str) -> Item:
        """`note_id|xsec_token` or `note_id|xsec_token|title`."""
        parts = [p.strip() for p in line.strip().split("|")]
        if len(parts) < 2:
            raise ValueError(f"expected 'note_id|xsec_token[|title]', got: {line!r}")
        return Item(key=parts[0], title=parts[2] if len(parts) > 2 else "",
                    extra={"token": parts[1]})

    def _clear_dedup_record(self, note_id: str) -> None:
        """XHS-Downloader keeps a seen-ids table and silently skips repeats.
        On a retry that is exactly wrong, so we drop the row first."""
        db = config.XHS_DOWNLOADER / "Volume" / "ExploreID.db"
        if not db.exists():
            return
        try:
            con = sqlite3.connect(db)
            con.execute("DELETE FROM explore_id WHERE ID=?", (note_id,))
            con.commit()
            con.close()
        except sqlite3.Error:
            pass   # a stale record is not worth aborting the batch over

    def fetch_media(self, item: Item, dest_dir: Path) -> Path | None:
        if not config.XHS_DOWNLOADER or not config.XHS_DOWNLOADER.exists():
            raise RuntimeError(
                "XHS_DOWNLOADER_PATH is not set. Clone "
                "https://github.com/JoeanAmier/XHS-Downloader and point the env var at it."
            )
        self._clear_dedup_record(item.key)
        token = (item.extra or {}).get("token", "")
        url = f"https://www.xiaohongshu.com/explore/{item.key}?xsec_token={token}&xsec_source=pc_user"
        try:
            subprocess.run(
                ["python3", "main.py", "--url", url,
                 "--work_path", str(dest_dir.parent), "--folder_name", item.key],
                cwd=str(config.XHS_DOWNLOADER), capture_output=True, timeout=300,
            )
        except subprocess.TimeoutExpired:
            return None
        for ext in MEDIA_EXTS:
            hits = glob.glob(str(dest_dir / f"*.{ext}"))
            if hits:
                return Path(hits[0])
        return None
