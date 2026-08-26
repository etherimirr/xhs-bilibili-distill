"""Pull representative still frames out of a video.

Naive approaches both fail on talking-head content:
  - fixed interval  -> misses cuts, and wastes frames on a static shot
  - scene-cut only  -> a ten-minute unbroken monologue yields one frame

So we take the union: every scene change above a threshold, PLUS a periodic
sample. Cuts get caught, and long static segments still get covered.
"""
from __future__ import annotations
import subprocess, glob
from pathlib import Path

# ffmpeg's `scene` value is the fraction of the frame that changed. 0.3 is a
# reasonable cut threshold for edited short-form video; lower it for slow fades.
DEFAULT_SCENE_THRESHOLD = 0.3
# ~8s at 30fps. Coarse on purpose: these are illustrations, not a storyboard.
DEFAULT_PERIOD_FRAMES = 240


def extract(video: Path, out_dir: Path, *, scene: float = DEFAULT_SCENE_THRESHOLD,
            period: int = DEFAULT_PERIOD_FRAMES, quality: int = 3,
            timeout: int = 300) -> list[Path]:
    """Write f_001.jpg, f_002.jpg ... into out_dir. Returns the frames written."""
    out_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(out_dir.glob("f_*.jpg"))
    if existing:
        return existing

    vf = f"select='gt(scene,{scene})+not(mod(n,{period}))',showinfo"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(video), "-vf", vf,
             "-vsync", "vfr", "-q:v", str(quality), str(out_dir / "f_%03d.jpg")],
            capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return sorted(out_dir.glob("f_*.jpg"))
    return sorted(out_dir.glob("f_*.jpg"))


def prune(frames: list[Path], keep: int) -> list[Path]:
    """Keep at most `keep` frames, evenly spread across the timeline.

    Scene detection on a heavily-cut video can return 80 frames; a report wants
    maybe 8. Sampling evenly preserves coverage better than taking the first N.
    """
    if keep <= 0 or len(frames) <= keep:
        return frames
    step = len(frames) / keep
    picked = [frames[min(int(i * step), len(frames) - 1)] for i in range(keep)]
    for f in frames:
        if f not in picked:
            f.unlink(missing_ok=True)
    return picked
