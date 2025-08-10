---
title: "GPT-5のCFG function callingを試してみた Part 2: SQL"
---

# はじめに

本記事は、Responses API の CFG（文法制約）機能を用いて「SQL の最小サブセット」を安全に生成・検証した記録です。前編（Part 1）では四則演算の式生成と検証を行いましたが、本稿では SQL（SELECT/JOIN/WHERE/LIMIT）に範囲を広げ、日本語の自然文から文法的に正しいクエリを強制生成し、SQLite で実行・評価するまでを一気通貫で行います。

# 既存の JSON ベースの SQL 生成との違い

従来の Function Calling による SQL 生成では JSON の文字列として生成させることが一般的でしたが、CFG を使用することで以下の課題がありました。

- **文法方言**: SQL の文法は多様であり、データベースによって微妙に異なるため、生成した SQL が文法エラーとなることがありました。
- **構文の厳密性**: JSON では SQL の構文を厳密に表現することが難しく、生成されたクエリが意図した通りに解釈されないことがありました。
- **SQL インジェクション対策**: 生成された SQL が危険な操作を含む可能性があり、セキュリティ上のリスクがありました。

CFG を使用することで、これらの課題を解決し、より安全で正確な SQL 生成が可能になります。

- **文法制約**: CFG を使用することで、SQL の文法を厳密に定義し、生成されるクエリが常に正しい構文を持つことを保証します。
- **構文の明確化**: CFG により、SQL の構文を明確に定義できるため、生成されたクエリが意図した通りに解釈されます。
- **セキュリティの向上**: CFG を使用することで、生成される SQL が安全な操作のみを含むように制約を設けることができ、SQL インジェクションのリスクを低減します。

# 実験セットアップ

- Python 3.12 / パッケージ管理: uv
- 主要依存: openai, lark, rich, tqdm, pytest
- 実行環境: `OPENAI_API_KEY` を `.env` で設定（値は出力しない）

実行例（以降のコマンドは uv を使用）:

```bash
uv sync
uv run --env-file .env -- python -m cli ping
```

# 検証シナリオ

## SQL の文法

フルセットの SQL は定義が非常に大きくなるため、今回は以下の最小サブセットに絞ります。

- SELECT 句（列名 or `*`）のみ（DELETE/INSERT/UPDATE は除外）
  - 列名は実際に存在するカラムに限定
- FROM 句（単一テーブルのみ、JOIN は可能）
- WHERE はブール式（AND/OR/NOT、括弧対応・優先順位: NOT > AND > OR）
- LIMIT 句（行数制限）

実際の文法定義は以下のとおりです。

```lark
start: select_stmt

select_stmt: "SELECT" select_list "FROM" table (join_clause)* ("WHERE" condition)? ("LIMIT" INT)?

select_list: "*" | sel_item ("," sel_item)*
sel_item: colref

join_clause: "JOIN" table "ON" colref "=" colref

table: "users" | "orders"

// Allow either qualified or unqualified column references
colref: (table ".")? column

column: "id" | "name" | "age" | "city" | "user_id" | "amount" | "status"

?condition: or_expr
?or_expr: and_expr ("OR" and_expr)*
?and_expr: not_expr ("AND" not_expr)*
?not_expr: ("NOT" not_expr) | cond_atom
?cond_atom: "(" condition ")" | predicate

predicate: colref op value
op: "=" | "!=" | "<" | "<=" | ">" | ">="
value: INT | SQSTRING

SQSTRING: "'" /[^']*/ "'"

%import common.INT
%import common.WS_INLINE
%ignore WS_INLINE
```

## 検証用データベース

今回は二つのテーブル `users` と `orders` を SQLite メモリ DB に作成し、以下のようなダミーデータを投入します。

```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  age INTEGER NOT NULL,
  city TEXT NOT NULL
);
CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
```

users は 6 件、orders は 8 件のダミーデータを投入しています（Tokyo/Osaka/Nagoya/Kyoto/Sapporo、status: paid/pending/cancelled 等）。

```sql
INSERT INTO users (id, name, age, city) VALUES
(1, 'Alice', 30, 'Tokyo'),
(2, 'Bob', 25, 'Osaka'),
(3, 'Charlie', 35, 'Tokyo'),
(4, 'Diana', 28, 'Nagoya'),
(5, 'Evan', 42, 'Kyoto'),
(6, 'Fiona', 33, 'Sapporo');

INSERT INTO orders (id, user_id, amount, status) VALUES
(1, 1, 120, 'paid'),
(2, 1, 60, 'pending'),
(3, 2, 200, 'paid'),
(4, 3, 80, 'cancelled'),
(5, 3, 300, 'paid'),
(6, 4, 150, 'paid'),
(7, 5, 40, 'pending'),
(8, 6, 220, 'paid');
```

## システムプロンプト

以下のようなシステムプロンプトを設定し、SQL の文法と制約を明示します。

```txt
Use the sql_query tool to output only one SQL statement.
Use uppercase keywords.

Available tables and schema:
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  age INTEGER NOT NULL,
  city TEXT NOT NULL
);
city: Tokyo, Osaka, Nagoya, Kyoto, Sapporo

CREATE TABLE orders (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL,
  amount INTEGER NOT NULL,
  status TEXT NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id)
);
status: paid, pending, cancelled

Boolean operators supported: AND, OR, NOT.
Use parentheses to group conditions when needed.
Prefer qualified column names (table.column).
```

# 実験

以下のコマンドで自然文から SQL を生成し、SQLite で実行・検証することができ。す。

```bash
uv run --env-file .env -- python -m cli cfg-sql --prompt "{自然文のクエリ}" --expect-rows {期待行数}
```

## 基本的なクエリ

```bash
uv run --env-file .env -- python -m cli cfg-sql --prompt "東京のユーザからの支払い済みの注文一覧を取得。" --expect-rows 2
```

結果

```console
╭────────────────────────────────────────────────────────────────── CFG SQL Validation ──────────────────────────────────────────────────────────────────╮
│  Prompt         東京のユーザからの支払い済みの注文一覧を取得。                                                                                         │
│  Query          SELECT orders.id, orders.user_id, orders.amount, orders.status FROM orders JOIN users ON orders.user_id = users.id WHERE users.city =  │
│                 'Tokyo' AND orders.status = 'paid'                                                                                                     │
│  Parsed         yes                                                                                                                                    │
│  Executed       yes                                                                                                                                    │
│  Columns        id, user_id, amount, status                                                                                                            │
│  Rows           2                                                                                                                                      │
│  Expected rows  2                                                                                                                                      │
│  Check          pass                                                                                                                                   │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────── Run Stats ──────────╮
│  Model     gpt-5-2025-08-07  │
│  Time (s)  13.90             │
│  Tokens    in=506, out=1013  │
╰──────────────────────────────╯
```

期待通りに SQL を生成することができました。文法制約も満たし、自然文から正しい SQL クエリを生成することができました。

## 制約違反の場合

今回は SELECT 文のみが生成可能です。ここで INSERT 文の生成を指示するとどうなるのか試してみます。

```bash
uv run --env-file .env -- python -m cli cfg-sql --prompt "新しいユーザを追加するSQLを生成してください。"
```

```console
$ uv run --env-file .env -- python -m cli cfg-sql --prompt "新しいユーザを追加するSQLを生 成してください。"
╭────────────────────────────────────────────────────────────────── CFG SQL Validation ──────────────────────────────────────────────────────────────────╮
│  Prompt    新しいユーザを追加するSQLを生成してください。                                                                                               │
│  Query     申し訳ありません。このツールはSELECT文のみ対応しており、INSERT文を生成できません。新規ユーザ追加のSQLは次をご利用ください。                 │
│                                                                                                                                                        │
│            INSERT INTO users (name, age, city) VALUES ('Taro Yamada', 28, 'Tokyo');                                                                    │
│  Parsed    no                                                                                                                                          │
│  Executed  no                                                                                                                                          │
│  Rows      0                                                                                                                                           │
│  Error     near "申し訳ありません。このツールはSELECT文のみ対応しており、INSERT文を生成できません。新規ユーザ追加のSQLは次をご利用ください。": synta…  │
│            error                                                                                                                                       │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────── Run Stats ──────────╮
│  Model     gpt-5-2025-08-07  │
│  Time (s)  23.33             │
│  Tokens    in=502, out=1600  │
╰──────────────────────────────╯
```

ツール呼び出しは行われず、代わりにエラーメッセージが返されました。これは CFG による制約が正しく機能していることを示しています。

では今度は、文法上存在しない集計関数を使用した場合を見てみましょう。

```bash
uv run --env-file .env -- python -m cli cfg-sql --prompt "ユーザごとの注文数をカウントするSQLを生成してください。"
```

```console
╭────────────────────────────────────────── CFG SQL Validation ──────────────────────────────────────────╮
│  Prompt    ユーザごとの注文数をカウントするSQLを生成してください。                                     │
│  Query     SELECT users.id, users.name, orders.id FROM users JOIN orders ON users.id = orders.user_id  │
│  Parsed    yes                                                                                         │
│  Executed  yes                                                                                         │
│  Columns   id, name, id                                                                                │
│  Rows      8                                                                                           │
╰────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭───────── Run Stats ──────────╮
│  Model     gpt-5-2025-08-07  │
│  Time (s)  17.89             │
│  Tokens    in=508, out=1315  │
╰──────────────────────────────╯
```

今回の場合は、SQL は生成されましたが、集計関数は使用されていません。これは、文法制約により集計関数が許可されていないためです。おそらく、モデルは集計関数を使用せずに、JOIN と WHERE 句を組み合わせて結果を取得し、その結果を自身で解釈して集計しようとしたのでしょう。

## パフォーマンス比較

以下のコマンドで、複数のモデル（gpt-5, gpt-5-mini, gpt-5-nano）を比較し、５つのケースで SQL の生成と実行時間を測定します。

```bash
uv run --env-file .env -- python -m cli \
  cfg-sql-suite --out-dir docs/experiments/cfg-sql --models gpt-5,gpt-5-mini,gpt-5-nano
```

使用したテストケースは以下のとおりです。

```python
def default_sql_cases() -> List[Tuple[str, Optional[int]]]:
    return [
        # 1) 単純条件 + LIMIT（日本語指示）
        ("30歳を超える利用者の一覧が欲しいです。idとnameだけ、最大3件でお願いします。", 3),
        # 2) OR/AND と括弧（日本語指示）
        ("居住地が東京または京都、かつ年齢が33歳以上の人のidとnameをください（上限10件）。", 2),
        # 3) NOT を含む（日本語指示）
        ("東京在住は除外し、30歳未満のユーザーを探してください。全てのカラムで、10件まで。", 2),
        # 4) JOIN + 数値条件（日本語指示）
        ("注文データと結合して、金額が100より大きい注文について、ユーザー名と金額を5件ほど見たいです。", 5),
        # 5) JOIN + 複合条件（日本語指示）
        ("支払い状態が paid で、金額が150以上の注文に限って、ユーザー名と金額を10件まで取得してください。", 4),
    ]
```

ケースは experiments/cfg_sql.py の `default_sql_cases()` に実装しています。いずれも自然文 →SQL への変換耐性をみるため、SQL そのものを書かない日本語の指示にしています。

### 結果ハイライト

対象レポート: docs/experiments/cfg-sql/run-20250811-073901.md

- 3 モデル（gpt-5 / gpt-5-mini / gpt-5-nano）× 5 ケース、計 15 行の結果を記録
- 全件で Parsed/Executed = yes、期待行数とも一致（Check=pass）
- おおよその所要時間（環境依存）
  - gpt-5: 10–22 秒
  - gpt-5-mini: 9–13 秒
  - gpt-5-nano: 9–11 秒

どのモデルも、文法制約に従い、正しい SQL を生成し、SQLite で実行できることを確認しました。

# 所感と学び

- 文法制約（CFG）により、未定義トークンや不完全な構文がほぼ排除され、SQL の構造が安定
- DDL を明示した指示により、列名・結合キーの整合性が向上し、`table.column` 参照が一貫
- 日本語の曖昧表現でも JOIN と複合 WHERE（括弧/優先順位含む）を堅実に構築
- 文法制約上不可能なケース（INSERT/集計関数）では、エラーを返すパターンと、
  代替の SQL を提案するパターンがある

# 次の一手

- SQL: ORDER BY / GROUP BY / 集約関数の段階的導入、落とし穴（否定の結合や境界条件）の収集
- KQL / OData / 独自 DSL（Mini Flow DSL）への横展開とスイート化
- 正規表現ツール（日本の住所 / アクセスログ）での抽出精度検証とエラーカタログ作り
