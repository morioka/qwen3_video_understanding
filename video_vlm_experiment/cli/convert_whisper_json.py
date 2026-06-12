from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from video_vlm_experiment.io import write_json


def main() -> None:
    args = parse_args()
    whisper_json = json.loads(args.input.read_text(encoding="utf-8"))
    segments = extract_transcript_segments(whisper_json)
    write_json(args.output, segments)
    print(f"wrote {len(segments)} transcript segments to {args.output}")


def extract_transcript_segments(whisper_json: Any) -> list[dict]:
    raw_segments = whisper_json.get("segments") if isinstance(whisper_json, dict) else whisper_json
    if not isinstance(raw_segments, list):
        raise ValueError("Whisper JSON must contain a segments array")

    transcript_segments: list[dict] = []
    for raw_segment in raw_segments:
        if not isinstance(raw_segment, dict):
            raise ValueError("Each Whisper segment must be an object")
        transcript_segments.append(
            {
                "start": float(raw_segment["start"]),
                "end": float(raw_segment["end"]),
                "text": str(raw_segment.get("text", "")).strip(),
            }
        )

    return transcript_segments


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert OpenAI Whisper JSON output to transcript_segments.json.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Whisper JSON output path.",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Output transcript_segments.json path.",
    )
    return parser.parse_args()
