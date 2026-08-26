"""CLI: read a list of items, transcribe each, write one .txt per item."""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
from . import config
from .sources import REGISTRY


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="distill",
        description="Download media from a list, transcribe it, write plain-text files.",
    )
    ap.add_argument("source", choices=sorted(REGISTRY), help="which platform")
    ap.add_argument("list_file", type=Path, help="one item per line; '#' comments ignored")
    ap.add_argument("--sleep", type=float, default=0.0,
                    help="seconds between items; use this to stay polite to the host")
    ap.add_argument("--limit", type=int, default=0, help="stop after N items (0 = all)")
    args = ap.parse_args(argv)

    src = REGISTRY[args.source]()
    lines = [l for l in args.list_file.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.lstrip().startswith("#")]
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

        success, note = src.run_one(item)
        if note == "skip":
            skipped += 1
        elif success:
            ok += 1
        else:
            failed += 1
        print(f"[{i}/{len(lines)}] {'ok ' if success else 'FAIL'} {item.key}  {note}")

        if args.sleep and i < len(lines):
            time.sleep(args.sleep)

    print(f"\ndone: {ok} transcribed, {skipped} already had transcripts, {failed} failed")
    print(f"output: {config.OUT / src.name}")
    return 1 if failed and not ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
