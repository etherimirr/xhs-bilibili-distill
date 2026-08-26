# Third-party dependencies

## XHS-Downloader — GPL-3.0

The `xhs` source adapter invokes **[XHS-Downloader](https://github.com/JoeanAmier/XHS-Downloader)** by JoeanAmier, licensed **GPL-3.0**.

**It is not bundled, vendored, or redistributed by this repository.** You install it yourself and point `XHS_DOWNLOADER_PATH` at your own clone. This project interacts with it only by launching it as a separate process (`subprocess.run`), passing arguments, and reading the files it leaves on disk.

That separation is deliberate: it keeps this repository an aggregate rather than a derivative work, so the MIT licence here does not conflict with GPL-3.0 there. If you fork this and *do* vendor XHS-Downloader into your tree, GPL-3.0 obligations attach to the result — relicense accordingly.

## Others

- **yt-dlp** — Unlicense
- **faster-whisper** — MIT
- **ffmpeg** — LGPL/GPL depending on build; invoked as an external binary, not linked
