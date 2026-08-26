"""Build the distillation prompt. Deliberately model-agnostic.

The tool does the deterministic work — fetch, transcribe, pick frames, render.
Summarising is the one step that needs a language model, and hard-wiring one
would force an API key on every user and lock the pipeline to a vendor. So we
emit a prompt instead, and read back a JSON object.
"""
from __future__ import annotations
from pathlib import Path
import json

TEMPLATE = """You are turning a video transcript into a working reference note.

TITLE: {title}
SOURCE: {source}

READER PROFILE (write `for_you` for this specific person):
{profile}

TRANSCRIPT:
\"\"\"
{transcript}
\"\"\"

Return ONLY a JSON object with these keys:

  "body"      — what was actually said. Markdown. Lead with a one-line thesis,
                then short sections. Keep the speaker's own phrasing for any
                claim that carries their reasoning; do not smooth it into
                generic advice.
  "takeaways" — array of 3-6 strings. Each must be something the reader could
                act on or check, not a restatement of the topic.
  "for_you"   — what this means for the reader in the profile above. Say plainly
                where it does NOT apply to them; a note that flatters everything
                is useless.

Rules:
- If the transcript is too garbled or too short to support a section, say so in
  that field rather than inventing content.
- Do not add facts that are not in the transcript. Speech-to-text makes errors;
  if a number or name looks wrong, flag it instead of repeating it confidently.
- Quote sparingly and mark quotes as quotes.
"""


def build(transcript: str, title: str = "", source: str = "",
          profile: str = "(no profile given — write `for_you` for a general reader)",
          max_chars: int = 24000) -> str:
    """Assemble the prompt. Long transcripts are truncated from the middle,
    because the opening and the conclusion carry the most signal."""
    t = transcript.strip()
    if len(t) > max_chars:
        head = t[: max_chars // 2]
        tail = t[-max_chars // 2:]
        t = f"{head}\n\n[... {len(transcript) - max_chars} characters omitted from the middle ...]\n\n{tail}"
    return TEMPLATE.format(title=title or "(untitled)", source=source or "(unknown)",
                           profile=profile.strip(), transcript=t)


def parse_response(raw: str) -> dict:
    """Tolerate a model wrapping its JSON in prose or a code fence."""
    s = raw.strip()
    if "```" in s:
        parts = s.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                s = p
                break
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found in the model response")
    return json.loads(s[start : end + 1])
