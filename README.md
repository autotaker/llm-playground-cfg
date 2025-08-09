# LLM Playground

このリポジトリでは、LLM や OpenAI の API を使用して、さまざまな実験やプロジェクトを行うためのコードを提供しています。

## セットアップ

```bash
uv sync
```

## 使い方（CLI 実行）

- 環境変数（.env 対応）
  - `OPENAI_API_KEY` を環境に設定してください（`.env` に定義すれば自動で読み込まれます）。
  - 既定モデルは `gpt-5` です。上書きする場合は `--model` か `OPENAI_MODEL` を使用します。

### 通信確認（ping）

```bash
uv run python -m cli ping
```

### Grammar（Lark）制約ツールのサンプル（四則演算）

```bash
uv run python -m cli cfg-math
```

- 備考: Grammar 制約ツールは `gpt-5` が必要です。
- 実行結果は数式（例: `4 + 4`）として出力されます。

### モデルの明示指定

```bash
uv run python -m cli ping --model gpt-5
# もしくは環境変数
export OPENAI_MODEL=gpt-5
uv run python -m cli ping
```

### エントリポイント（任意）

`pyproject.toml` に `project.scripts` を追加済みですが、uv でのローカル実行では未パッケージのため
`python -m cli` での実行を推奨します。
