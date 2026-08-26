"""Paths and knobs. Override any of these with environment variables."""
import os
from pathlib import Path

WORK = Path(os.environ.get("DISTILL_WORK", Path.home() / ".cache" / "media-distill"))
OUT = Path(os.environ.get("DISTILL_OUT", WORK / "transcripts"))
MEDIA = WORK / "media"

# Path to a local clone of JoeanAmier/XHS-Downloader (GPL-3.0, NOT bundled here).
# Careful: Path("") is Path("."), which exists — so an unset variable has to stay
# None, or the "not configured" guard silently passes and we shell out to the cwd.
_xhs = os.environ.get("XHS_DOWNLOADER_PATH", "").strip()
XHS_DOWNLOADER = Path(_xhs).expanduser() if _xhs else None

WHISPER_SIZE = os.environ.get("DISTILL_WHISPER", "small")
WHISPER_DEVICE = os.environ.get("DISTILL_DEVICE", "cpu")
WHISPER_COMPUTE = os.environ.get("DISTILL_COMPUTE", "int8")
LANGUAGE = os.environ.get("DISTILL_LANG", "zh")

# Treat an existing transcript as done only if it is longer than this and not a
# failure marker. Prevents a truncated run from being mistaken for a good one.
MIN_VALID_CHARS = 150
