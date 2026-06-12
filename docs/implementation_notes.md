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

## 書き起こしとフレームの対応づけ

現状では、書き起こしはタイムスタンプに基づいて「重なる chunk」に添付する。

`run-vlm-chunks` の user message では、chunk 全体の `transcript_segments` と `frames` を同じ JSON に入れ、画像を送る場合は各画像の直前に `Frame time: ... seconds` を付ける。したがって VLM は発話の `start` / `end` とフレームの `time` から対応関係を推論できる。

ただし、現状では「各フレームに対応する発話」を事前に明示的には紐づけていない。

将来の実現形態としては複数ある。

- chunk 単位: 現状の方式。chunk 内の全発話と全フレームをまとめて渡す。単純で情報落ちが少ない。
- frame 単位: 各 frame に `nearby_transcript_segments` を付ける。画像ごとの音声文脈が明確になる。
- message 単位: 各画像の直前に、その frame 時刻近辺の発話だけを text として挿入する。OpenAI 互換 VLM の入力構造と相性がよい。
- window 単位: frame 時刻の前後 N 秒の発話を対応づける。発話と作業のタイミングが少しずれる動画に強い。
- event 候補単位: 発話境界・無音・視覚変化点を合わせてイベント候補を作り、各候補に複数 frame と発話を紐づける。実装は重いが後段のイベント抽出に近い。

初期実験では、まず chunk 単位で十分に回し、VLM が発話と画像を取り違える、または画像ごとの根拠が曖昧になる場合に frame 単位または message 単位へ進める。

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

- Whisper 書き起こし実行部分の自動化
- PySceneDetect 等によるシーン変化ベースの境界候補
- CLIP 等による画像特徴量変化点の検出
- 不確実区間の backward refinement

## VLM 送信

`run-vlm-chunks` は `chunk_inputs/chunk_*.json` を読み込み、OpenAI 互換の `/chat/completions` に送信する。

```bash
uv run run-vlm-chunks \
  --chunk-input-dir runs/example/chunk_inputs \
  --output-dir runs/example/chunk_results \
  --base-url http://localhost:8000/v1 \
  --model Qwen3-VL \
  --response-format-json
```

API key は `VLM_API_KEY` を既定値として読む。ローカル vLLM 等で不要な場合は未設定のままでよい。

既定では各 chunk を独立に送る。前 chunk までの `memory_update` を次 chunk の入力に含める場合は `--memory-mode rolling` を使う。

```bash
uv run run-vlm-chunks \
  --chunk-input-dir runs/example/chunk_inputs \
  --output-dir runs/example/chunk_results \
  --base-url http://localhost:8000/v1 \
  --model Qwen3-VL \
  --response-format-json \
  --memory-mode rolling \
  --memory-limit 20
```

rolling memory は `chunk_results/memory.json` にも保存する。memory は過去 chunk の解析結果であり、現在 chunk の映像証拠ではないため、prompt 内で現在 chunk の観察を優先するよう明示している。

`--dry-run` を指定すると、実際の HTTP 送信はせず、画像 data URL を伏せた request preview を `chunk_results/requests/` に出力する。

## VLM 入出力ログ

最低限の追跡用に、VLM の output は実行時に保存する。

- parsed output: `chunk_results/chunk_0000.json`
- raw output: `chunk_results/raw/chunk_0000.response.json`
- model message text: `chunk_results/raw/chunk_0000.message.txt`

VLM input は現状、実リクエスト前の確認用として `--dry-run` 時のみ保存する。

- input preview: `chunk_results/requests/chunk_0000.json`

input preview では画像 data URL は `<data-url-redacted>` に置換する。画像そのものは `prepare-video-chunks --extract-frames` が出力する `frames/` を参照する。現状では、実 VLM 送信時の request payload は保存しない。

実行時の request payload も監査用に残したくなった場合は、`run-vlm-chunks` に `--save-requests` を追加し、dry-run と同じ redacted 形式で保存するのが自然な拡張になる。

## 解析結果の統合

`integrate-chunk-results` は chunk ごとの JSON 結果を読み込み、時系列イベント、エンティティ、memory、不確実事項を 1 つの JSON にまとめる。

```bash
uv run integrate-chunk-results \
  --input-dir runs/example/chunk_results \
  --output runs/example/integrated_analysis.json
```

初期版の統合は決定的なルールベースで行う。

- イベントに `source_chunk_index` と `time_seconds` を付ける
- entity は `type` と `label` の小文字一致で同一視する
- memory と uncertainties は source chunk 情報付きで集約する

意味的に似た entity の統合、後続チャンクで判明した名称による過去イベント修正、矛盾解消は今後の backward refinement 側で扱う。
