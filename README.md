# media-distill-pipeline

**Turn a list of video links into a folder of plain-text transcripts.** Resumable, idempotent, and honest about what failed.

Built for a real problem: I follow a few hundred creators whose useful content is locked inside video. Reading is 10× faster than watching, and text is searchable. So: download → extract audio → transcribe → text file. Then any LLM can work on it.

<br>

## What it does

```
list of items
   ├── Xiaohongshu  →  XHS-Downloader  →  video
   └── Bilibili     →  yt-dlp -f ba    →  audio only
                            ↓
                  ffmpeg → 16 kHz mono WAV
                            ↓
              faster-whisper (int8, CPU, VAD)
                            ↓
              transcripts/<source>/<id>.txt
```

```bash
pip install -r requirements.txt          # plus ffmpeg and yt-dlp on PATH

python -m distill.cli bilibili my_videos.txt --sleep 2
python -m distill.cli xhs      my_notes.txt  --sleep 4
```

Input is one item per line, `#` for comments:

```
# bilibili.txt — bare BV id or full URL
BV1xx411c7mD
https://www.bilibili.com/video/BV1xx411c7mD

# xhs.txt — note_id|xsec_token[|title]
6790f9b9000000001800da16|ABSSNxfeuYQ...|optional title
```

<br>

## The parts that took actual thinking

This started as eight near-identical scripts — one per creator I was following. Collapsing them into one parameterised tool surfaced the decisions that were implicit before:

**Resume has to distinguish "done" from "failed".**
A naive `if output exists: skip` is wrong, because failures also write output. Every failure writes a marker line (`[!] download failed`), and `already_done()` checks for it — so a rerun retries exactly the broken items and leaves the good ones alone. It also enforces a minimum length, so a truncated write doesn't get mistaken for success.

**XHS-Downloader's dedup table fights retries.**
It keeps a `Volume/ExploreID.db` of seen note IDs and silently skips repeats. That is correct for its own use case and exactly wrong for ours — a retry after a network failure would no-op forever. The adapter deletes the row before each attempt.

**Download audio, not video.**
Bilibili's `-f ba` fetches the audio stream alone. A transcript never needs pixels, and this cuts download size by roughly an order of magnitude. XHS doesn't expose an audio-only path, so there we download video and delete it immediately after extraction — media files are the thing that fills a disk, not transcripts.

**One model load per process.**
`faster-whisper` costs ~10s to initialise. The model is a module-level singleton behind a lazy getter, so a 200-item batch pays it once rather than 200 times.

**Every subprocess has a timeout.**
A hung `yt-dlp` on one bad link used to stall an overnight batch. Now it fails that item and moves on.

<br>

## Layout

```
distill/
├── config.py            env-var configuration
├── transcribe.py        ffmpeg + whisper (shared by all sources)
├── cli.py               argparse entry point
└── sources/
    ├── base.py          resume / failure-marker / cleanup driver
    ├── bilibili.py      yt-dlp adapter
    └── xhs.py           XHS-Downloader adapter
```

Adding a platform means implementing `fetch_media()` and optionally `fetch_title()`. Everything else is inherited.

<br>

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `DISTILL_WORK` | `~/.cache/media-distill` | working directory |
| `DISTILL_OUT` | `$DISTILL_WORK/transcripts` | where transcripts land |
| `XHS_DOWNLOADER_PATH` | *(unset)* | path to your XHS-Downloader clone — **required for the `xhs` source** |
| `DISTILL_WHISPER` | `small` | whisper model size |
| `DISTILL_DEVICE` / `DISTILL_COMPUTE` | `cpu` / `int8` | inference backend |
| `DISTILL_LANG` | `zh` | transcription language |

<br>

## Dependencies you install yourself

- **ffmpeg** — audio extraction
- **yt-dlp** — Bilibili
- **[XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader)** by JoeanAmier — Xiaohongshu. **GPL-3.0, and deliberately not vendored here.** Clone it separately and point `XHS_DOWNLOADER_PATH` at it. This project only shells out to it; see [NOTICE.md](NOTICE.md).

<br>

## Responsible use

This is a personal archival tool for content you can already access. Two things are built in on purpose:

- **`--sleep`** exists so you can rate-limit yourself. Use it. Hammering a platform gets your own account throttled, and the throttled responses are indistinguishable from missing content — which quietly corrupts whatever you build downstream.
- **Nothing is republished.** The output is transcripts on your own disk for your own reading. Respect the platform's terms and the creators' rights; a transcript is not a licence to repost.

<br>

## License

MIT for the code in this repository. XHS-Downloader is GPL-3.0 and is *not* included — see [NOTICE.md](NOTICE.md).
