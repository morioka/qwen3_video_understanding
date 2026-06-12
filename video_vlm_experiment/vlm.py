from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_RESPONSE_TIMEOUT_SECONDS = 300.0


@dataclass(frozen=True)
class VlmClient:
    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = DEFAULT_RESPONSE_TIMEOUT_SECONDS

    def create_chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        response_format_json: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        request = urllib.request.Request(
            _chat_completions_url(self.base_url),
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"VLM request failed with HTTP {error.code}: {detail}"
            ) from error

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def build_chunk_messages(
    *,
    chunk_input: dict[str, Any],
    prompt: str,
    include_images: bool = True,
    max_images: int | None = None,
) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": prompt.strip(),
        },
        {
            "type": "text",
            "text": "Analyze this chunk input JSON:\n"
            + json.dumps(_metadata_only_chunk(chunk_input), ensure_ascii=False, indent=2),
        },
    ]

    if include_images:
        image_count = 0
        for frame in chunk_input.get("frames", []):
            if max_images is not None and image_count >= max_images:
                break
            path = frame.get("path") if isinstance(frame, dict) else None
            if not path:
                continue
            content.append(
                {
                    "type": "text",
                    "text": f"Frame time: {frame.get('time')} seconds",
                }
            )
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_path_to_data_url(Path(path)),
                    },
                }
            )
            image_count += 1

    return [{"role": "user", "content": content}]


def extract_message_text(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("VLM response does not contain choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("VLM response choice does not contain a message")
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        return "\n".join(parts)
    raise ValueError("VLM response message content is not text")


def parse_json_from_text(text: str) -> Any:
    stripped = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, re.DOTALL)
    if fenced:
        stripped = fenced.group(1).strip()

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    candidate = _first_balanced_json_value(stripped)
    if candidate is None:
        raise ValueError("No JSON object or array found in VLM response text")
    return json.loads(candidate)


def image_path_to_data_url(path: Path) -> str:
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{encoded}"


def api_key_from_args(value: str | None, env_name: str | None) -> str | None:
    if value:
        return value
    if env_name:
        return os.environ.get(env_name)
    return None


def _metadata_only_chunk(chunk_input: dict[str, Any]) -> dict[str, Any]:
    copied = dict(chunk_input)
    frames = []
    for frame in copied.get("frames", []):
        if not isinstance(frame, dict):
            continue
        frames.append(
            {
                "time": frame.get("time"),
                "path": frame.get("path"),
            }
        )
    copied["frames"] = frames
    return copied


def _chat_completions_url(base_url: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def _first_balanced_json_value(text: str) -> str | None:
    for start, character in enumerate(text):
        if character not in "{[":
            continue
        end = _find_balanced_end(text, start)
        if end is not None:
            return text[start : end + 1]
    return None


def _find_balanced_end(text: str, start: int) -> int | None:
    opening = text[start]
    closing = "}" if opening == "{" else "]"
    stack = [closing]
    in_string = False
    escaped = False

    for index in range(start + 1, len(text)):
        character = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
            continue
        if character in "{[":
            stack.append("}" if character == "{" else "]")
            continue
        if character in "}]":
            if not stack or character != stack[-1]:
                return None
            stack.pop()
            if not stack:
                return index

    return None
