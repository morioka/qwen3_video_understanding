# Implementation Notes

## 現在の方針

本リポジトリでは、動画から直接説明文を生成するのではなく、まず再利用可能な構造化知識を抽出する。

初期実装では、実験を安定して回すことを優先し、動画解析はフレーム群方式で行う。

初期実装とこのメモの作成には Codex CLI を使用した。

## 入力の扱い

### 音声

音声は動画全体に対して一度だけ Whisper 系で書き起こす。

出力形式は `transcript_segments.json`:

```json
[
  {
    "start": 0.0,
    "end": 3.2,
    "text": "..."
  }
]
```

書き起こしはチャンク境界の主根拠ではなく、各チャンク解析時の補助情報として扱う。

### 動画

動画は時間ベースでチャンク分割する。

初期値:

- チャンク長: 60秒
- オーバーラップ: 5秒
- フレーム抽出間隔: 5秒

これらは CLI オプションで変更できる。

例:

```bash
uv run prepare-video-chunks \
  --video video.mp4 \
  --transcript transcript_segments.json \
  --output-dir runs/example \
  --chunk-seconds 60 \
  --overlap-seconds 5 \
  --frame-interval-seconds 5
```

## チャンクの扱い

各チャンクは、動画チャンクそのものではなく、まずは以下の形で VLM に渡す。

- チャンク開始時刻
- チャンク終了時刻
- チャンク内のフレーム群
- 各フレームの時刻
- チャンク時間帯に重なる書き起こしセグメント

`--extract-frames` を付けた場合のみ、`ffmpeg` でフレーム画像を抽出する。

```bash
uv run prepare-video-chunks \
  --video video.mp4 \
  --transcript transcript_segments.json \
  --output-dir runs/example \
  --extract-frames
```

## uv 管理

このプロジェクトは `uv` で管理する。

```bash
uv sync
```

CLI は `pyproject.toml` の entry point として登録している。

```bash
uv run prepare-video-chunks --help
```

`uv.lock` は再現性のため git 管理する。

`.venv/` は git 管理しない。

## git 管理方針

git 管理するもの:

- ソースコード
- `README.md`
- `docs/`
- `pyproject.toml`
- `uv.lock`
- 小さいサンプルや設定ファイル

git 管理しないもの:

- `.venv/`
- 実動画
- 音声ファイル
- 抽出フレーム
- Whisper 書き起こし出力
- chunk 生成結果
- `runs/`, `data/`, `videos/`, `frames/` などの実験入出力

## 未実装の改善候補

- Whisper 書き起こし実行部分
- OpenAI 互換 VLM / Qwen VLM への送信処理
- PySceneDetect 等によるシーン変化ベースの境界候補
- CLIP 等による画像特徴量変化点の検出
- イベント抽出結果の全体整合化
- 不確実区間の backward refinement
