from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from video_vlm_experiment.vlm import VlmClient, extract_message_text, parse_json_from_text


class VlmJsonParsingTest(unittest.TestCase):
    def test_parses_plain_json(self) -> None:
        self.assertEqual(parse_json_from_text('{"a": 1}'), {"a": 1})

    def test_parses_fenced_json(self) -> None:
        self.assertEqual(parse_json_from_text('```json\n{"a": 1}\n```'), {"a": 1})

    def test_extracts_first_balanced_json_object(self) -> None:
        self.assertEqual(
            parse_json_from_text('before {"b": [1, {"c": "}"}]} after'),
            {"b": [1, {"c": "}"}]},
        )


class VlmClientTest(unittest.TestCase):
    def test_posts_chat_completion_request(self) -> None:
        captured: dict[str, object] = {}

        class Response:
            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "choices": [
                            {
                                "message": {
                                    "content": '{"events": []}',
                                }
                            }
                        ]
                    }
                ).encode("utf-8")

        def fake_urlopen(request: object, timeout: float) -> Response:
            captured["url"] = request.full_url
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return Response()

        with patch("urllib.request.urlopen", fake_urlopen):
            client = VlmClient(
                base_url="http://127.0.0.1:8000/v1",
                model="test-model",
                api_key="secret",
                timeout_seconds=5.0,
            )
            response = client.create_chat_completion(
                [{"role": "user", "content": [{"type": "text", "text": "hello"}]}],
                response_format_json=True,
            )

        self.assertEqual(captured["url"], "http://127.0.0.1:8000/v1/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(captured["body"]["model"], "test-model")
        self.assertEqual(
            captured["body"]["response_format"],
            {"type": "json_object"},
        )
        self.assertEqual(captured["timeout"], 5.0)
        self.assertEqual(extract_message_text(response), '{"events": []}')


if __name__ == "__main__":
    unittest.main()
