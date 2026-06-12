from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str

    @classmethod
    def from_dict(cls, value: dict) -> "TranscriptSegment":
        return cls(
            start=float(value["start"]),
            end=float(value["end"]),
            text=str(value.get("text", "")),
        )

    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }


@dataclass(frozen=True)
class FrameReference:
    time: float
    path: str | None = None

    def to_dict(self) -> dict:
        value = {"time": self.time}
        if self.path:
            value["path"] = self.path
        return value


@dataclass(frozen=True)
class ChunkInput:
    index: int
    start: float
    end: float
    transcript_segments: tuple[TranscriptSegment, ...]
    frames: tuple[FrameReference, ...]

    def to_dict(self) -> dict:
        return {
            "chunk_index": self.index,
            "chunk_start": self.start,
            "chunk_end": self.end,
            "transcript_segments": [
                segment.to_dict() for segment in self.transcript_segments
            ],
            "frames": [frame.to_dict() for frame in self.frames],
            "analysis_method": "frame_group",
        }


def generate_chunk_ranges(
    duration: float,
    chunk_seconds: float,
    overlap_seconds: float,
) -> list[tuple[float, float]]:
    if duration <= 0:
        raise ValueError("duration must be greater than 0")
    if chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be greater than 0")
    if overlap_seconds < 0:
        raise ValueError("overlap_seconds must not be negative")
    if overlap_seconds >= chunk_seconds:
        raise ValueError("overlap_seconds must be smaller than chunk_seconds")

    ranges: list[tuple[float, float]] = []
    start = 0.0
    step = chunk_seconds - overlap_seconds

    while start < duration:
        end = min(start + chunk_seconds, duration)
        ranges.append((_round_time(start), _round_time(end)))
        if end >= duration:
            break
        start += step

    return ranges


def attach_transcript_segments(
    transcript_segments: Iterable[TranscriptSegment],
    chunk_start: float,
    chunk_end: float,
) -> tuple[TranscriptSegment, ...]:
    return tuple(
        segment
        for segment in transcript_segments
        if segment.start < chunk_end and segment.end > chunk_start
    )


def generate_frame_references(
    chunk_start: float,
    chunk_end: float,
    frame_interval_seconds: float,
) -> tuple[FrameReference, ...]:
    if frame_interval_seconds <= 0:
        raise ValueError("frame_interval_seconds must be greater than 0")
    if chunk_end <= chunk_start:
        raise ValueError("chunk_end must be greater than chunk_start")

    frames: list[FrameReference] = []
    current = chunk_start

    while current < chunk_end:
        frames.append(FrameReference(time=_round_time(current)))
        current += frame_interval_seconds

    if not frames or frames[-1].time < chunk_end:
        frames.append(FrameReference(time=_round_time(chunk_end)))

    return tuple(frames)


def build_chunk_inputs(
    duration: float,
    transcript_segments: Iterable[TranscriptSegment],
    chunk_seconds: float = 60.0,
    overlap_seconds: float = 5.0,
    frame_interval_seconds: float = 5.0,
) -> list[ChunkInput]:
    transcript = tuple(transcript_segments)
    chunks: list[ChunkInput] = []

    for index, (chunk_start, chunk_end) in enumerate(
        generate_chunk_ranges(duration, chunk_seconds, overlap_seconds)
    ):
        chunks.append(
            ChunkInput(
                index=index,
                start=chunk_start,
                end=chunk_end,
                transcript_segments=attach_transcript_segments(
                    transcript,
                    chunk_start,
                    chunk_end,
                ),
                frames=generate_frame_references(
                    chunk_start,
                    chunk_end,
                    frame_interval_seconds,
                ),
            )
        )

    return chunks


def _round_time(value: float) -> float:
    return round(value, 3)
