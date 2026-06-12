from __future__ import annotations

import subprocess
from pathlib import Path

from video_vlm_experiment.chunking import ChunkInput, FrameReference


def extract_frames(
    video_path: Path,
    output_dir: Path,
    chunks: list[ChunkInput],
    image_extension: str = "jpg",
) -> list[ChunkInput]:
    output_dir.mkdir(parents=True, exist_ok=True)
    updated_chunks: list[ChunkInput] = []

    for chunk in chunks:
        frame_dir = output_dir / f"chunk_{chunk.index:04d}"
        frame_dir.mkdir(parents=True, exist_ok=True)
        updated_frames: list[FrameReference] = []

        for frame_index, frame in enumerate(chunk.frames):
            frame_path = frame_dir / f"frame_{frame_index:04d}_{frame.time:.3f}s.{image_extension}"
            _extract_frame(video_path, frame.time, frame_path)
            updated_frames.append(FrameReference(time=frame.time, path=str(frame_path)))

        updated_chunks.append(
            ChunkInput(
                index=chunk.index,
                start=chunk.start,
                end=chunk.end,
                transcript_segments=chunk.transcript_segments,
                frames=tuple(updated_frames),
            )
        )

    return updated_chunks


def _extract_frame(video_path: Path, timestamp: float, frame_path: Path) -> None:
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{timestamp:.3f}",
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-y",
        str(frame_path),
    ]
    subprocess.run(command, check=True)
