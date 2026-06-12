from __future__ import annotations

import argparse
from pathlib import Path

from video_vlm_experiment.integration import (
    integrate_chunk_results,
    load_chunk_analysis_results,
)
from video_vlm_experiment.io import write_json


def main() -> None:
    args = parse_args()
    chunk_results = load_chunk_analysis_results(args.input_dir)
    integrated = integrate_chunk_results(chunk_results)
    write_json(args.output, integrated)
    print(
        f"integrated {integrated['chunk_count']} chunks, "
        f"{integrated['stats']['event_count']} events, "
        f"{integrated['stats']['entity_count']} entities into {args.output}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Integrate per-chunk VLM analysis JSON files into a timeline.",
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        type=Path,
        help="Directory containing parsed chunk_*.json VLM results.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output integrated_analysis.json path.",
    )
    return parser.parse_args()
