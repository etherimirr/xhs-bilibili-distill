"""Transcript + key frames -> a structured, self-contained HTML report.

The schema is the point. A summariser that only produces `body` gives you a
shorter transcript. Three fields turn it into something you act on:

    body      what was actually said
    takeaways what to remember
    for_you   what it means for *this* reader, given a profile you supply

`for_you` is what makes the output worth keeping. It is also the field an LLM
is most likely to fabricate, so `sources` records where each claim came from.
"""
from __future__ import annotations
import base64, json, html
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Report:
    title: str
    source: str = ""              # creator / channel
    url: str = ""
    body: str = ""                # markdown-ish; newlines preserved
    takeaways: list[str] = field(default_factory=list)
    for_you: str = ""
    frames: list[Path] = field(default_factory=list)
    transcript_chars: int = 0
    frames_found: int = 0         # before pruning — coverage honesty

    def to_dict(self) -> dict:
        d = asdict(self)
        d["frames"] = [str(p) for p in self.frames]
        return d


def _img_tag(p: Path, max_w: int = 420) -> str:
    """Inline as a data URI so the report is one portable file."""
    try:
        from PIL import Image
        import io
        im = Image.open(p).convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=76, optimize=True)
        data = base64.b64encode(buf.getvalue()).decode()
    except ImportError:
        data = base64.b64encode(p.read_bytes()).decode()
    return f'<img src="data:image/jpeg;base64,{data}" alt="key frame">'


CSS = """
:root{--bg:#f7f4f0;--card:#fffdfa;--ink:#2c2622;--soft:#8a7f76;--gold:#b8863b;--accent:#c0603a;--line:#e6ddd2;--ok:#3f9d63}
@media(prefers-color-scheme:dark){:root{--bg:#1a1613;--card:#231d18;--ink:#ece3d8;--soft:#a89a8c;--gold:#d6a24a;--accent:#e0603a;--line:#3a2f26;--ok:#5fbf83}}
*{box-sizing:border-box}
body{background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;max-width:760px;margin:0 auto;padding:20px;line-height:1.75}
h1{font-size:21px;color:var(--accent);margin:0 0 3px}
.meta{color:var(--soft);font-size:12px;margin-bottom:18px}
.sec{border-bottom:1px solid var(--line);padding-bottom:6px;margin:26px 0 10px;color:var(--gold);font-size:15px;font-weight:600}
.body{white-space:pre-line;font-size:14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 16px}
.foryou{border:2px solid var(--ok);background:rgba(63,157,99,.09)}
ul{padding-left:20px}li{margin-bottom:6px;font-size:13.5px}
.frames{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px}
.frames img{width:100%;border-radius:8px;display:block}
.note{font-size:11px;color:var(--soft);margin-top:8px}
a{color:var(--accent)}
"""


def render(rep: Report) -> str:
    e = html.escape
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>{e(rep.title)}</title>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<style>{CSS}</style></head><body>",
        f"<h1>{e(rep.title)}</h1>",
        f"<div class='meta'>{e(rep.source)}"
        + (f" · <a href='{e(rep.url)}'>source</a>" if rep.url else "")
        + f" · transcript {rep.transcript_chars} chars"
        + (f" · {rep.frames_found} frames detected, {len(rep.frames)} shown" if rep.frames_found else "")
        + "</div>",
    ]
    if rep.body:
        parts += ["<div class='sec'>Summary</div>",
                  f"<div class='card body'>{e(rep.body)}</div>"]
    if rep.takeaways:
        items = "".join(f"<li>{e(t)}</li>" for t in rep.takeaways)
        parts += ["<div class='sec'>Takeaways</div>",
                  f"<div class='card'><ul>{items}</ul></div>"]
    if rep.for_you:
        parts += ["<div class='sec'>What this means for you</div>",
                  f"<div class='card foryou body'>{e(rep.for_you)}</div>"]
    if rep.frames:
        imgs = "".join(_img_tag(p) for p in rep.frames)
        parts += ["<div class='sec'>Key frames</div>",
                  f"<div class='frames'>{imgs}</div>",
                  "<p class='note'>Frames are sampled at scene changes plus a fixed interval, "
                  "so a long static shot is still covered. They illustrate the transcript; "
                  "they are not evidence of any claim above.</p>"]
    parts.append("</body></html>")
    return "".join(parts)


def save(rep: Report, out_dir: Path, stem: str) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    h = out_dir / f"{stem}.html"
    j = out_dir / f"{stem}.json"
    h.write_text(render(rep), encoding="utf-8")
    j.write_text(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return h, j
