from __future__ import annotations

from pathlib import Path
from typing import Any

from video_vlm_experiment.io import load_json


def load_chunk_analysis_results(input_dir: Path) -> list[dict[str, Any]]:
    results = []
    for path in sorted(input_dir.glob("chunk_*.json")):
        value = load_json(path)
        if not isinstance(value, dict):
            raise ValueError(f"{path} must contain a JSON object")
        results.append(value)
    if not results:
        raise ValueError(f"no chunk_*.json files found in {input_dir}")
    return results


def integrate_chunk_results(chunk_results: list[dict[str, Any]]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    entities_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    memory_updates: list[dict[str, Any]] = []
    uncertainties: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []

    for fallback_index, chunk in enumerate(chunk_results):
        chunk_index = _int_value(chunk.get("chunk_index"), fallback_index)
        chunk_start = _float_value(chunk.get("chunk_start"))
        chunk_end = _float_value(chunk.get("chunk_end"))
        source = {
            "chunk_index": chunk_index,
            "chunk_start": chunk_start,
            "chunk_end": chunk_end,
        }
        chunks.append(source)

        entity_id_map = _merge_entities(
            entities_by_key,
            chunk.get("entities", []),
            source,
        )

        for event_index, event in enumerate(_list_value(chunk.get("events"))):
            if not isinstance(event, dict):
                continue
            normalized = dict(event)
            normalized["source_chunk_index"] = chunk_index
            normalized["source_event_index"] = event_index
            normalized["chunk_start"] = chunk_start
            normalized["chunk_end"] = chunk_end
            normalized["time_seconds"] = _event_time_seconds(
                event.get("time"),
                chunk_start,
            )
            _rewrite_entity_reference(normalized, "actor", entity_id_map)
            _rewrite_entity_reference(normalized, "target", entity_id_map)
            events.append(normalized)

        for memory_index, memory in enumerate(_list_value(chunk.get("memory_update"))):
            memory_updates.append(
                _with_source(
                    memory,
                    source,
                    "source_memory_index",
                    memory_index,
                )
            )

        for uncertainty_index, uncertainty in enumerate(_list_value(chunk.get("uncertainties"))):
            uncertainties.append(
                _with_source(
                    uncertainty,
                    source,
                    "source_uncertainty_index",
                    uncertainty_index,
                )
            )

    events.sort(key=lambda event: (_sort_time(event), event["source_chunk_index"]))
    entities = sorted(
        entities_by_key.values(),
        key=lambda entity: (entity.get("type", ""), entity.get("label", "")),
    )

    return {
        "analysis_method": "integrated_chunk_events",
        "chunk_count": len(chunk_results),
        "chunks": chunks,
        "events": events,
        "entities": entities,
        "memory": memory_updates,
        "uncertainties": uncertainties,
        "stats": {
            "event_count": len(events),
            "entity_count": len(entities),
            "memory_update_count": len(memory_updates),
            "uncertainty_count": len(uncertainties),
        },
    }


def _merge_entities(
    entities_by_key: dict[tuple[str, str], dict[str, Any]],
    raw_entities: Any,
    source: dict[str, Any],
) -> dict[str, str]:
    entity_id_map: dict[str, str] = {}
    for entity_index, entity in enumerate(_list_value(raw_entities)):
        if not isinstance(entity, dict):
            continue
        label = str(entity.get("label") or entity.get("id") or f"entity_{entity_index}")
        entity_type = str(entity.get("type") or "unknown")
        key = (entity_type.strip().lower(), label.strip().lower())
        stable_id = f"entity_{len(entities_by_key):04d}"
        existing = entities_by_key.get(key)
        if existing is None:
            existing = {
                "id": stable_id,
                "type": entity_type,
                "label": label,
                "confidence": _float_value(entity.get("confidence")),
                "evidence": entity.get("evidence", ""),
                "source_entities": [],
            }
            entities_by_key[key] = existing
        else:
            existing["confidence"] = _max_optional_float(
                existing.get("confidence"),
                entity.get("confidence"),
            )
            if not existing.get("evidence") and entity.get("evidence"):
                existing["evidence"] = entity.get("evidence")

        original_id = str(entity.get("id") or f"chunk_entity_{entity_index}")
        entity_id_map[original_id] = existing["id"]
        existing["source_entities"].append(
            {
                **_source_fields(source),
                "source_entity_index": entity_index,
                "source_entity_id": original_id,
            }
        )
    return entity_id_map


def _with_source(
    value: Any,
    source: dict[str, Any],
    index_key: str,
    index: int,
) -> dict[str, Any]:
    if isinstance(value, dict):
        return {**value, **_source_fields(source), index_key: index}
    return {"text": str(value), **_source_fields(source), index_key: index}


def _source_fields(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_chunk_index": source["chunk_index"],
        "chunk_start": source["chunk_start"],
        "chunk_end": source["chunk_end"],
    }


def _event_time_seconds(raw_time: Any, chunk_start: float | None) -> float | None:
    if isinstance(raw_time, int | float):
        return float(raw_time)
    if raw_time is None:
        return chunk_start

    text = str(raw_time).strip()
    try:
        return float(text)
    except ValueError:
        pass

    parts = text.split(":")
    if len(parts) in (2, 3):
        try:
            numbers = [float(part) for part in parts]
        except ValueError:
            return chunk_start
        if len(numbers) == 2:
            return numbers[0] * 60 + numbers[1]
        return numbers[0] * 3600 + numbers[1] * 60 + numbers[2]

    return chunk_start


def _rewrite_entity_reference(
    event: dict[str, Any],
    key: str,
    entity_id_map: dict[str, str],
) -> None:
    value = event.get(key)
    if value is None:
        return
    text = str(value)
    if text in entity_id_map:
        event[key] = entity_id_map[text]


def _sort_time(event: dict[str, Any]) -> float:
    value = event.get("time_seconds")
    if isinstance(value, int | float):
        return float(value)
    chunk_start = event.get("chunk_start")
    if isinstance(chunk_start, int | float):
        return float(chunk_start)
    return 0.0


def _int_value(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float_value(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _max_optional_float(left: Any, right: Any) -> float | None:
    left_float = _float_value(left)
    right_float = _float_value(right)
    if left_float is None:
        return right_float
    if right_float is None:
        return left_float
    return max(left_float, right_float)


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
