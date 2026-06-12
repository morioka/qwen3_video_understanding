# Whisper Transcription

## 目的

動画全体を一度だけ Whisper 系で書き起こし、後続のチャンク解析に渡す `transcript_segments.json` を作る。

チャンクごとに書き起こしは行わない。発話途中で切れることを避け、後段で任意のチャンク時間帯に重なる発話を添付できるようにする。

## 前提

- `uv sync` が完了している
- `ffmpeg` がインストールされている
- Whisper 実行時にモデルをダウンロードできるネットワーク環境がある

OpenAI Whisper の CLI は `openai-whisper` パッケージで提供される。プロジェクト本体の依存には固定せず、必要時に `uvx` で実行する。

## 手順

### 1. Whisper JSON を生成する

```bash
mkdir -p runs/transcripts

uvx --from openai-whisper whisper video.mp4 \
  --model small \
  --language Japanese \
  --task transcribe \
  --output_format json \
  --output_dir runs/transcripts
```

出力例:

```text
runs/transcripts/video.json
```

モデル選択の目安:

- `tiny`, `base`: 軽いが精度は低め
- `small`: 初期実験向けの現実的な候補
- `medium`, `large`: 重いが精度重視
- `turbo`: 高速な通常書き起こし向け

### 2. transcript_segments.json に変換する

```bash
uv run convert-whisper-json \
  runs/transcripts/video.json \
  transcript_segments.json
```

出力形式:

```json
[
  {
    "start": 0.0,
    "end": 3.2,
    "text": "..."
  }
]
```

### 3. チャンク入力を生成する

```bash
uv run prepare-video-chunks \
  --video video.mp4 \
  --transcript transcript_segments.json \
  --output-dir runs/example \
  --chunk-seconds 60 \
  --overlap-seconds 5 \
  --frame-interval-seconds 5
```

## 注意

- `transcript_segments.json` は生成物なので git 管理しない
- 実動画、抽出音声、Whisper の中間出力も git 管理しない
- 発話境界はチャンク境界としては扱わず、解析時の補助情報として使う
