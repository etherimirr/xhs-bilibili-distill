# media-distill-pipeline

**Turn a list of video links into illustrated, structured reports you actually re-read.**

Built for a real problem: I follow a few hundred creators whose useful content is locked inside video. Watching does not scale and does not search. Existing tools stop at a transcript — which is just a longer thing to read.

So this goes three stages further: **transcript + key frames + a report that says what it means for a specific reader.**

<br>

## What it does

```
   list of items
        │
   ┌────┴─────────────────────────┐
   │  Xiaohongshu → XHS-Downloader│
   │  Bilibili    → yt-dlp        │
   └────┬─────────────────────────┘
        │
   ┌────┴────────────────┬──────────────────────────┐
   │ audio               │ video                    │
   │ ffmpeg → 16kHz mono │ ffmpeg scene-detect      │
   │ faster-whisper      │ + periodic sampling      │
   ↓                     ↓                          │
transcript            key frames                    │
   └──────────┬──────────┘                          │
              ↓                                     │
     prompt (your LLM, any vendor)                   │
              ↓                                     │
   { body, takeaways, for_you }  ←──────────────────┘
              ↓
   one self-contained HTML report
```

```bash
pip install -r requirements.txt          # plus ffmpeg and yt-dlp on PATH

# 1. fetch + transcribe + keep 8 key frames each
python -m distill.cli fetch bilibili my_videos.txt --frames 8 --sleep 2

# 2. get the distillation prompt, feed it to whatever model you use
python -m distill.cli prompt transcripts/bilibili/BV1xx.txt --profile me.txt > p.txt

# 3. paste the model's JSON back, get an illustrated report
python -m distill.cli report transcripts/bilibili/BV1xx.txt model_out.json \
       --frames-dir transcripts/bilibili/frames/BV1xx
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

## The report schema is the whole point

A summariser that emits one blob of prose gives you a shorter transcript. Three fields make it something you act on:

| field | question it answers |
|---|---|
| `body` | what was actually said |
| `takeaways` | what to remember |
| **`for_you`** | **what it means for *this* reader, given a profile you supply** |

`for_you` is the field that makes a note worth keeping — and the one a model is most likely to fabricate, so the prompt explicitly instructs it to say where the content does *not* apply. A note that flatters everything is useless.

Reports are single self-contained HTML files with frames inlined as data URIs. The header states how many frames were detected versus shown, so you can see the sampling rather than trust it.

<br>

## The parts that took actual thinking

**Frame selection is a union, not an interval.**
Fixed-interval sampling misses cuts and wastes frames on static shots. Scene-cut detection alone returns a single frame for a ten-minute unbroken monologue. So: `select='gt(scene,0.3)+not(mod(n,240))'` — every scene change above threshold **plus** a periodic sample. Then prune evenly across the timeline rather than taking the first N, so a heavily-cut opening does not eat the whole quota.

**The LLM step is deliberately not built in.**
Hard-wiring a model would force an API key on every user and lock the pipeline to one vendor. Instead the tool emits a prompt and reads back JSON. `parse_response` tolerates a model wrapping its answer in prose or a code fence, because they all do.

**Long transcripts truncate from the middle.**
The opening states the thesis and the ending states the conclusion; the middle is where repetition lives. Cutting the middle and labelling the gap preserves more signal per token than a head-only cut.

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
