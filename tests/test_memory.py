from __future__ import annotations

import unittest

from video_vlm_experiment.memory import RollingMemory


class RollingMemoryTest(unittest.TestCase):
    def test_accumulates_memory_updates_with_source_metadata(self) -> None:
        memory = RollingMemory()
        memory.add_chunk_result(
            {
                "chunk_index": 0,
                "chunk_start": 0.0,
                "chunk_end": 10.0,
                "memory_update": [
                    {
                        "text": "operator_A is checking the control panel",
                        "confidence": 0.8,
                    },
                    "panel label is unclear",
                ],
            }
        )

        value = memory.to_dict()
        self.assertEqual(len(value["items"]), 2)
        self.assertEqual(value["items"][0]["source_chunk_index"], 0)
        self.assertEqual(value["items"][0]["confidence"], 0.8)
        self.assertEqual(value["items"][1]["confidence"], None)

    def test_prompt_text_uses_latest_limited_items(self) -> None:
        memory = RollingMemory()
        memory.add_chunk_result(
            {
                "chunk_index": 0,
                "memory_update": ["old memory"],
            }
        )
        memory.add_chunk_result(
            {
                "chunk_index": 1,
                "memory_update": ["new memory"],
            }
        )

        text = memory.to_prompt_text(limit=1)

        self.assertIsNotNone(text)
        assert text is not None
        self.assertNotIn("old memory", text)
        self.assertIn("new memory", text)
        self.assertIn("現在チャンクの観察を優先", text)


if __name__ == "__main__":
    unittest.main()
