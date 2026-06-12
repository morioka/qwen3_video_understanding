from __future__ import annotations

import unittest

from video_vlm_experiment.integration import integrate_chunk_results


class IntegrationTest(unittest.TestCase):
    def test_integrates_events_and_deduplicates_entities_by_type_and_label(self) -> None:
        integrated = integrate_chunk_results(
            [
                {
                    "chunk_index": 0,
                    "chunk_start": 0.0,
                    "chunk_end": 10.0,
                    "events": [
                        {
                            "time": "00:00:01",
                            "target": "panel_a",
                            "category": "observation",
                        }
                    ],
                    "entities": [
                        {
                            "id": "panel_a",
                            "type": "object",
                            "label": "Control Panel",
                            "confidence": 0.6,
                        }
                    ],
                    "memory_update": ["panel is visible"],
                    "uncertainties": [],
                },
                {
                    "chunk_index": 1,
                    "chunk_start": 8.0,
                    "chunk_end": 18.0,
                    "events": [
                        {
                            "time": 12.0,
                            "target": "panel_b",
                            "category": "action",
                        }
                    ],
                    "entities": [
                        {
                            "id": "panel_b",
                            "type": "object",
                            "label": "control panel",
                            "confidence": 0.9,
                        }
                    ],
                    "memory_update": [],
                    "uncertainties": ["button label is unclear"],
                },
            ]
        )

        self.assertEqual(integrated["stats"]["event_count"], 2)
        self.assertEqual(integrated["stats"]["entity_count"], 1)
        self.assertEqual(integrated["entities"][0]["confidence"], 0.9)
        self.assertEqual(integrated["events"][0]["time_seconds"], 1.0)
        self.assertEqual(integrated["events"][0]["target"], "entity_0000")
        self.assertEqual(integrated["events"][1]["target"], "entity_0000")
        self.assertEqual(integrated["memory"][0]["source_chunk_index"], 0)
        self.assertEqual(integrated["uncertainties"][0]["source_chunk_index"], 1)


if __name__ == "__main__":
    unittest.main()
