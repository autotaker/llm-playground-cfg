# TODO — Issue-1: Responses API CFG/Regex Experiments

Scope: docs/tickets/issue-1/TASK.md に基づき、CFG/正規表現制約での生成実験を実装・検証する。

## Setup
- [x] Python 3.12 + uv 環境を同期（`uv sync`）
- [x] OpenAI API キー設定（`.env` に設定済み）
- [x] 依存追加：`lark`（CFG 検証用）、`pytest`（導入済み）

## Tooling / 基盤
- [x] `lib/openai_client.py` を作成（Responses API 呼び出しラッパ、timeout/retry）
- [x] `cli.py` を作成（サブコマンドで各実験を実行：`ping`, `cfg-math`）
- [ ] `[project.scripts]` にエントリ `llm-playground = "cli:main"` を追加（任意、`uv run python -m cli ...` で代替可）

## CFG 実験（Lark）

### 四則演算（算術式）
- [x] 文法定義（加減乗除、括弧、整数）
- [x] プロンプト・API 呼び出し（grammar= Lark）
- [x] 検証：Lark でパースし、評価の整合性チェック（安全な評価器）
- [x] サンプル出力・失敗例の記録（docs/experiments/cfg-math/*.md）

### SQL（最小サブセット）
- [ ] 文法定義（SELECT FROM WHERE LIMIT、識別子/リテラルの簡易化）
- [ ] プロンプト・API 呼び出し
- [ ] 検証：Lark でパース（実行は任意、行わない方針でも可）
- [ ] サンプル出力・失敗例の記録

### KQL（最小サブセット）
- [ ] 文法定義（`where`/`project`/`summarize` など）
- [ ] プロンプト・API 呼び出し
- [ ] 検証：Lark でパース
- [ ] サンプル出力・失敗例の記録

### OData（$filter サブセット）
- [ ] 文法定義（比較/論理演算、関数は最小限）
- [ ] プロンプト・API 呼び出し
- [ ] 検証：Lark でパース
- [ ] サンプル出力・失敗例の記録

### 独自 DSL（Mini Flow DSL）
- [ ] 文法定義（docs/tickets/issue-1/references/custom_dsl.md を Lark 化）
- [ ] プロンプト・API 呼び出し
- [ ] 検証：Lark でパース（サンプルフローの再現）
- [ ] サンプル出力・失敗例の記録

## 正規表現 実験

### 日本の住所
- [ ] 正規表現定義（都道府県/市区町村/番地 などを命名グループで抽出）
- [ ] プロンプト・API 呼び出し（syntax= regex）
- [ ] 検証：マッチ可否と抽出グループの妥当性
- [ ] サンプル出力・失敗例の記録

### アクセスログ（Common Log Format 等）
- [ ] 正規表現定義（`ip`/`ident`/`user`/`ts`/`method`/`path`/`proto`/`status`/`size`）
- [ ] プロンプト・API 呼び出し
- [ ] 検証：マッチ可否と抽出グループの妥当性
- [ ] サンプル出力・失敗例の記録

## ドキュメント/運用
- [ ] README 更新（実行方法、API キー設定、CLI 例）
- [ ] 実験ノート追加（`docs/experiments/` に観察結果・落とし穴を記録）（任意）

## 受け入れ基準（Definition of Done）
- [ ] 主要 5 つの CFG（算術/SQL/KQL/OData/DSL）それぞれで「生成→パース成功」の最小例を確認
- [ ] 正規表現 2 件（住所/アクセスログ）で「生成→正規表現マッチ成功」の最小例を確認
- [ ] CLI から各実験を一発実行できる（例：`uv run llm-playground cfg-sql`）
- [ ] README に手順が明記され、再現可能

## 参考
- docs/tickets/issue-1/TASK.md
- docs/tickets/issue-1/references/syntax.md
- docs/tickets/issue-1/references/custom_dsl.md
