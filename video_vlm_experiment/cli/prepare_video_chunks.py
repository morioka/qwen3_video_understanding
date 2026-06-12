from __future__ import annotations

import argparse
from pathlib import Path

from video_vlm_experiment.chunking import build_chunk_inputs
from video_vlm_experiment.frame_extract import extract_frames
from video_vlm_experiment.io import load_transcript, probe_video_duration, write_json
from video_vlm_experiment.prompts import CHUNK_ANALYSIS_PROMPT


def main() -> None:
    args = parse_args()
    video_path = args.video
    output_dir = args.output_dir

    duration = args.video_duration
    if duration is None:
        duration = probe_video_duration(video_path)

    transcript_segments = load_transcript(args.transcript)
    chunks = build_chunk_inputs(
        duration=duration,
        transcript_segments=transcript_segments,
        chunk_seconds=args.chunk_seconds,
        overlap_seconds=args.overlap_seconds,
        frame_interval_seconds=args.frame_interval_seconds,
    )

    if args.extract_frames:
        chunks = extract_frames(
            video_path=video_path,
            output_dir=output_dir / "frames",
            chunks=chunks,
            image_extension=args.image_extension,
        )

    chunk_dicts = [chunk.to_dict() for chunk in chunks]
    write_json(
        output_dir / "chunks.json",
        {
            "video": str(video_path),
            "duration": duration,
            "chunk_seconds": args.chunk_seconds,
            "overlap_seconds": args.overlap_seconds,
            "frame_interval_seconds": args.frame_interval_seconds,
            "chunks": chunk_dicts,
        },
    )

    chunk_input_dir = output_dir / "chunk_inputs"
    for chunk in chunk_dicts:
        write_json(
            chunk_input_dir / f"chunk_{chunk['chunk_index']:04d}.json",
            chunk,
        )

    (output_dir / "chunk_analysis_prompt.md").write_text(
        CHUNK_ANALYSIS_PROMPT,
        encoding="utf-8",
    )

    print(f"wrote {len(chunks)} chunks to {output_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare frame-group inputs for initial video VLM experiments.",
    )
    parser.add_argument("--video", required=True, type=Path, help="Input video path.")
    parser.add_argument(
        "--transcript",
        required=True,
        type=Path,
        help="transcript_segments.json path.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Directory for chunks, prompts, and optional frames.",
    )
    parser.add_argument(
        "--video-duration",
        type=float,
        default=None,
        help="Video duration in seconds. If omitted, ffprobe is used.",
    )
    parser.add_argument(
        "--chunk-seconds",
        type=float,
        default=60.0,
        help="Time-based chunk length in seconds.",
    )
    parser.add_argument(
        "--overlap-seconds",
        type=float,
        default=5.0,
        help="Overlap between adjacent chunks in seconds.",
    )
    parser.add_argument(
        "--frame-interval-seconds",
        type=float,
        default=5.0,
        help="Frame sampling interval in seconds.",
    )
    parser.add_argument(
        "--extract-frames",
        action="store_true",
        help="Extract frame images with ffmpeg.",
    )
    parser.add_argument(
        "--image-extension",
        default="jpg",
        choices=("jpg", "png"),
        help="Extracted frame image format.",
    )
    return parser.parse_args()
