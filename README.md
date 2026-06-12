# Qwen3 video understanding 実験

Qwen3で動画を解析する実験。音声を直接扱えない場合は、Whisperで書き起こした結果を
別途プロンプトに与えるか、フレーム群と書き起こしを組み合わせて入力する。

https://chatgpt.com/share/6a2b73d5-fcb0-83ee-8202-b4e9ef7f551f

## 初期実装

`docs/design_video_vlm_experiment.md` に基づき、まずは方式B（フレーム群方式）で実験を回すための入力生成を実装している。

## セットアップ

このリポジトリは `uv` で管理する。

```bash
uv sync
```

処理内容:

1. 動画全体の書き起こし `transcript_segments.json` を読み込む
2. 動画を時間ベースで chunk 分割する
3. 隣接 chunk に overlap を持たせる
4. 各 chunk に重なる発話セグメントを添付する
5. 各 chunk 内のフレーム時刻を生成する
6. 必要に応じて `ffmpeg` でフレーム画像を抽出する
7. chunk 解析用プロンプトを出力する
8. OpenAI 互換 VLM に chunk 入力を送信する
9. chunk ごとの解析結果を時系列に統合する

Whisper で `transcript_segments.json` を作る手順は `docs/transcription_with_whisper.md` を参照する。

### 使い方

```bash
uv run prepare-video-chunks \
  --video video.mp4 \
  --transcript transcript_segments.json \
  --output-dir runs/example \
  --chunk-seconds 60 \
  --overlap-seconds 5 \
  --frame-interval-seconds 5
```

フレーム画像も抽出する場合:

```bash
uv run prepare-video-chunks \
  --video video.mp4 \
  --transcript transcript_segments.json \
  --output-dir runs/example \
  --extract-frames
```

`--video-duration` を指定しない場合は `ffprobe` を使って動画長を取得する。`--extract-frames` を使う場合は `ffmpeg` が必要。

VLM に送信する場合:

```bash
uv run run-vlm-chunks \
  --chunk-input-dir runs/example/chunk_inputs \
  --output-dir runs/example/chunk_results \
  --base-url http://localhost:8000/v1 \
  --model Qwen3-VL \
  --response-format-json
```

`run-vlm-chunks` は OpenAI 互換の `/chat/completions` エンドポイントを使う。API key が必要な場合は `VLM_API_KEY` に設定するか、`--api-key-env` / `--api-key` を指定する。

実リクエスト前に payload を確認する場合:

```bash
uv run run-vlm-chunks \
  --chunk-input-dir runs/example/chunk_inputs \
  --output-dir runs/example/chunk_results \
  --model Qwen3-VL \
  --dry-run
```

chunk 解析結果を統合する場合:

```bash
uv run integrate-chunk-results \
  --input-dir runs/example/chunk_results \
  --output runs/example/integrated_analysis.json
```

### 入力

`transcript_segments.json`:

```json
[
  {
    "start": 0.0,
    "end": 3.2,
    "text": "..."
  }
]
```

### 出力

- `runs/example/chunks.json`: 全 chunk の一覧
- `runs/example/chunk_inputs/chunk_0000.json`: chunk ごとの VLM 入力
- `runs/example/chunk_analysis_prompt.md`: イベント抽出用プロンプト
- `runs/example/frames/`: `--extract-frames` 指定時の抽出画像
- `runs/example/chunk_results/chunk_0000.json`: chunk ごとの VLM 解析結果
- `runs/example/chunk_results/raw/`: VLM の生レスポンスと message text
- `runs/example/integrated_analysis.json`: 統合済みイベント・エンティティ・memory・不確実事項
