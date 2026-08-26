"""CLI. Three commands mirroring the three stages of the pipeline."""
from __future__ import annotations
import argparse, sys, time, json
from pathlib import Path
from . import config
from .sources import REGISTRY
from .prompt import build as build_prompt, parse_response
from .report import Report, save as save_report


def _read_list(p: Path) -> list[str]:
    return [l for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#")]


def cmd_fetch(args) -> int:
    src = REGISTRY[args.source]()
    lines = _read_list(args.list_file)
    if args.limit:
        lines = lines[: args.limit]

    ok = skipped = failed = 0
    for i, line in enumerate(lines, 1):
        try:
            item = src.parse_line(line)
        except ValueError as e:
            print(f"[{i}/{len(lines)}] BAD LINE  {e}", file=sys.stderr)
            failed += 1
            continue
        success, note = src.run_one(item, frames=args.frames)
        if note == "skip":
            skipped += 1
        elif success:
            ok += 1
        else:
            failed += 1
        print(f"[{i}/{len(lines)}] {'ok  ' if success else 'FAIL'} {item.key}  {note}")
        if args.sleep and i < len(lines):
            time.sleep(args.sleep)

    print(f"\ndone: {ok} transcribed, {skipped} already done, {failed} failed")
    print(f"output: {config.OUT / src.name}")
    return 1 if failed and not ok else 0


def cmd_prompt(args) -> int:
    """Print the distillation prompt for one transcript. Pipe it to any model."""
    text = args.transcript.read_text(encoding="utf-8")
    title = ""
    if text.startswith("title:"):
        title, _, text = text.partition("\n")
        title = title[len("title:"):].strip()
    profile = args.profile.read_text(encoding="utf-8") if args.profile else None
    print(build_prompt(text, title=title, source=args.source or "",
                       **({"profile": profile} if profile else {})))
    return 0


def cmd_report(args) -> int:
    """Combine a transcript, the model's JSON, and key frames into one HTML file."""
    text = args.transcript.read_text(encoding="utf-8")
    title = args.title or ""
    if text.startswith("title:"):
        line, _, text = text.partition("\n")
        title = title or line[len("title:"):].strip()

    data = parse_response(args.distilled.read_text(encoding="utf-8"))

    frames: list[Path] = []
    found = 0
    if args.frames_dir and args.frames_dir.exists():
        all_frames = sorted(args.frames_dir.glob("f_*.jpg"))
        found = len(all_frames)
        frames = all_frames[: args.max_frames] if args.max_frames else all_frames

    rep = Report(
        title=title or args.transcript.stem, source=args.source or "", url=args.url or "",
        body=data.get("body", ""), takeaways=data.get("takeaways", []) or [],
        for_you=data.get("for_you", ""), frames=frames,
        transcript_chars=len(text), frames_found=found,
    )
    h, j = save_report(rep, args.out, args.transcript.stem)
    print(f"wrote {h}\nwrote {j}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="distill",
        description="Video links -> transcripts + key frames -> illustrated reports.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="download, transcribe, optionally extract key frames")
    f.add_argument("source", choices=sorted(REGISTRY))
    f.add_argument("list_file", type=Path)
    f.add_argument("--frames", type=int, default=0,
                   metavar="N", help="also keep N key frames per item (0 = none)")
    f.add_argument("--sleep", type=float, default=0.0, help="seconds between items")
    f.add_argument("--limit", type=int, default=0)
    f.set_defaults(func=cmd_fetch)

    p = sub.add_parser("prompt", help="print the distillation prompt for a transcript")
    p.add_argument("transcript", type=Path)
    p.add_argument("--profile", type=Path, help="text file describing the reader")
    p.add_argument("--source", default="")
    p.set_defaults(func=cmd_prompt)

    r = sub.add_parser("report", help="transcript + model JSON + frames -> HTML")
    r.add_argument("transcript", type=Path)
    r.add_argument("distilled", type=Path, help="the model's JSON response")
    r.add_argument("--frames-dir", type=Path)
    r.add_argument("--max-frames", type=int, default=8)
    r.add_argument("--out", type=Path, default=Path("reports"))
    r.add_argument("--title", default="")
    r.add_argument("--source", default="")
    r.add_argument("--url", default="")
    r.set_defaults(func=cmd_report)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
