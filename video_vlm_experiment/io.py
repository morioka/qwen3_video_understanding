from __future__ import annotations

import json
import subprocess
from pathlib import Path

from video_vlm_experiment.chunking import TranscriptSegment


def load_transcript(path: Path) -> list[TranscriptSegment]:
    raw_segments = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_segments, list):
        raise ValueError("transcript must be a JSON array")
    return [TranscriptSegment.from_dict(segment) for segment in raw_segments]


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def probe_video_duration(video_path: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return float(result.stdout.strip())
