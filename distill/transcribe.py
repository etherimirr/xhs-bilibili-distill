"""Audio extraction + speech-to-text. Shared by every source adapter."""
from __future__ import annotations
import subprocess, os
from pathlib import Path

_MODEL = None


def get_model(size: str = "small", device: str = "cpu", compute_type: str = "int8"):
    """Lazy-load faster-whisper. Loading costs ~10s, so we do it once per process."""
    global _MODEL
    if _MODEL is None:
        from faster_whisper import WhisperModel
        _MODEL = WhisperModel(size, device=device, compute_type=compute_type)
    return _MODEL


def to_wav(src: Path, dst: Path, timeout: int = 120) -> bool:
    """Extract mono 16 kHz WAV — the format Whisper wants. Returns success."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000", str(dst)],
            capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return False
    return r.returncode == 0 and dst.exists()


def transcribe(wav: Path, language: str = "zh", vad: bool = True, **model_kw) -> str:
    """WAV -> plain text. VAD filtering drops silence, which matters a lot for vlogs."""
    model = get_model(**model_kw)
    segments, _info = model.transcribe(str(wav), language=language, vad_filter=vad)
    return "".join(s.text for s in segments)
