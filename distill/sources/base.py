"""Common resume/skip/failure-marker logic, so adapters only implement fetching."""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
from .. import config
from ..transcribe import to_wav, transcribe
from ..keyframes import extract as extract_frames, prune as prune_frames

FAILURE_PREFIX = "[!]"


@dataclass
class Item:
    key: str            # stable id, used as the output filename
    title: str = ""
    extra: dict | None = None


class Source:
    name = "base"

    def fetch_media(self, item: Item, dest_dir: Path) -> Path | None:
        """Download and return a path to a media file, or None on failure."""
        raise NotImplementedError

    def fetch_title(self, item: Item) -> str:
        return item.title

    # ---- shared driver -------------------------------------------------

    def already_done(self, out: Path) -> bool:
        if not out.exists() or out.stat().st_size < config.MIN_VALID_CHARS:
            return False
        return FAILURE_PREFIX not in out.read_text(encoding="utf-8")[:200]

    def mark_failed(self, out: Path, reason: str, title: str = "") -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f"title: {title}\n{FAILURE_PREFIX} {reason}\n", encoding="utf-8")

    def run_one(self, item: Item, frames: int = 0) -> tuple[bool, str]:
        """frames > 0 also extracts that many key frames before deleting the media."""
        out = config.OUT / self.name / f"{item.key}.txt"
        if self.already_done(out):
            return True, "skip"

        media_dir = config.MEDIA / self.name / item.key
        media = self.fetch_media(item, media_dir)
        if media is None:
            self.mark_failed(out, "download failed", item.title)
            return False, "download"

        wav = config.MEDIA / self.name / f"{item.key}.wav"
        if not to_wav(media, wav):
            self.mark_failed(out, "ffmpeg failed", item.title)
            return False, "ffmpeg"

        try:
            text = transcribe(
                wav, language=config.LANGUAGE,
                size=config.WHISPER_SIZE, device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE,
            )
        except Exception as e:                      # noqa: BLE001 - report, don't crash the batch
            self.mark_failed(out, f"transcribe failed: {e}", item.title)
            wav.unlink(missing_ok=True)
            return False, "transcribe"

        n_frames = 0
        if frames > 0:
            fdir = config.OUT / self.name / "frames" / item.key
            got = extract_frames(media, fdir)
            n_frames = len(got)
            prune_frames(got, frames)

        title = self.fetch_title(item)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f"title: {title}\n\n{text}", encoding="utf-8")

        # Media files are large and we already have what we came for.
        wav.unlink(missing_ok=True)
        try:
            media.unlink(missing_ok=True)
        except OSError:
            pass
        return True, f"{len(text)} chars" + (f", {n_frames} frames" if frames else "")
