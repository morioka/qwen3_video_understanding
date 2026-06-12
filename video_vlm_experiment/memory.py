from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MemoryItem:
    text: str
    confidence: float | None
    source_chunk_index: int | None
    chunk_start: float | None
    chunk_end: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "source_chunk_index": self.source_chunk_index,
            "chunk_start": self.chunk_start,
            "chunk_end": self.chunk_end,
        }


class RollingMemory:
    def __init__(self) -> None:
        self._items: list[MemoryItem] = []
        self._seen: set[tuple[int | None, str]] = set()

    def add_chunk_result(self, chunk_result: dict[str, Any]) -> None:
        chunk_index = _optional_int(chunk_result.get("chunk_index"))
        chunk_start = _optional_float(chunk_result.get("chunk_start"))
        chunk_end = _optional_float(chunk_result.get("chunk_end"))

        for raw_item in _list_value(chunk_result.get("memory_update")):
            item = _memory_item_from_value(
                raw_item,
                chunk_index=chunk_index,
                chunk_start=chunk_start,
                chunk_end=chunk_end,
            )
            if item is None:
                continue
            key = (item.source_chunk_index, item.text)
            if key in self._seen:
                continue
            self._seen.add(key)
            self._items.append(item)

    def to_prompt_text(self, limit: int) -> str | None:
        items = self.latest(limit)
        if not items:
            return None

        lines = [
            "これまでのチャンクから引き継ぐ memory:",
            "- この memory は過去チャンクの解析結果であり、現在チャンクの映像証拠そのものではありません。",
            "- 現在チャンクの映像・発話と矛盾する場合は、現在チャンクの観察を優先し uncertainties に記録してください。",
        ]
        for item in items:
            confidence = (
                "unknown" if item.confidence is None else f"{item.confidence:.3f}"
            )
            source = _format_source(item)
            lines.append(f"- {source} confidence={confidence}: {item.text}")
        return "\n".join(lines)

    def latest(self, limit: int) -> list[MemoryItem]:
        if limit <= 0:
            return []
        return self._items[-limit:]

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self._items],
        }


def _memory_item_from_value(
    value: Any,
    *,
    chunk_index: int | None,
    chunk_start: float | None,
    chunk_end: float | None,
) -> MemoryItem | None:
    if isinstance(value, dict):
        text = str(value.get("text") or "").strip()
        confidence = _optional_float(value.get("confidence"))
    else:
        text = str(value).strip()
        confidence = None

    if not text:
        return None

    return MemoryItem(
        text=text,
        confidence=confidence,
        source_chunk_index=chunk_index,
        chunk_start=chunk_start,
        chunk_end=chunk_end,
    )


def _format_source(item: MemoryItem) -> str:
    if item.source_chunk_index is None:
        return "[chunk unknown]"
    if item.chunk_start is None or item.chunk_end is None:
        return f"[chunk {item.source_chunk_index}]"
    return f"[chunk {item.source_chunk_index} {item.chunk_start:.3f}-{item.chunk_end:.3f}s]"


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
