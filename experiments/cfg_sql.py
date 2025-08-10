from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple

import sqlite3
from lark import Lark

from lib.openai_client import responses_create, output_text, extract_usage


"""
Minimal SQL subset grammar (uppercase keywords), two tables: users, orders.
Supports:
- SELECT item_list FROM table (JOIN table ON colref = colref)* [WHERE boolean_expr] [LIMIT INT]
- Boolean expr precedence: NOT > AND > OR, parentheses allowed.
- Predicate: colref op value; op in (=, !=, <, <=, >, >=)
- Columns limited to: users(id,name,age,city), orders(id,user_id,amount,status)
- Column refs may be qualified (table.column) or unqualified (column)
- String literal supports single quotes without escaping.
"""

SQL_LARK = r"""
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
"""


parser = Lark(SQL_LARK, start="start", parser="earley")


def _init_sample_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    cur = con.cursor()
    cur.execute(
        """
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            city TEXT NOT NULL
        )
        """
    )
    rows = [
        (1, "Alice", 30, "Tokyo"),
        (2, "Bob", 25, "Osaka"),
        (3, "Charlie", 35, "Tokyo"),
        (4, "Diana", 28, "Nagoya"),
        (5, "Evan", 42, "Kyoto"),
        (6, "Fiona", 33, "Sapporo"),
    ]
    cur.executemany("INSERT INTO users(id, name, age, city) VALUES(?, ?, ?, ?)", rows)
    cur.execute(
        """
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    orders = [
        (1, 1, 120, "paid"),
        (2, 1, 60, "pending"),
        (3, 2, 200, "paid"),
        (4, 3, 80, "cancelled"),
        (5, 3, 300, "paid"),
        (6, 4, 150, "paid"),
        (7, 5, 40, "pending"),
        (8, 6, 220, "paid"),
    ]
    cur.executemany(
        "INSERT INTO orders(id, user_id, amount, status) VALUES(?, ?, ?, ?)", orders
    )
    con.commit()
    return con


@dataclass
class SqlRunResult:
    prompt: str
    query: str
    parsed_ok: bool
    executed_ok: bool
    columns: Sequence[str]
    rows: Sequence[Tuple[Any, ...]]
    error: Optional[str]
    model: Optional[str] = None
    usage_input_tokens: Optional[int] = None
    usage_output_tokens: Optional[int] = None
    expected_rows: Optional[int] = None


def run_cfg_sql(
    prompt: str, model: Optional[str] = None, expected_rows: Optional[int] = None
) -> SqlRunResult:
    tools = [
        {
            "type": "custom",
            "name": "sql_query",
            "description": "Creates a minimal SQL SELECT query for the users table.",
            "format": {
                "type": "grammar",
                "syntax": "lark",
                "definition": SQL_LARK,
            },
        }
    ]
    instruction = (
        "Use the sql_query tool to output only one SQL statement. "
        "Use uppercase keywords. Available tables and schema are:\n"
        "CREATE TABLE users (\n"
        "  id INTEGER PRIMARY KEY,\n"
        "  name TEXT NOT NULL,\n"
        "  age INTEGER NOT NULL,\n"
        "  city TEXT NOT NULL\n"
        ");\n"
        "city: Tokyo, Osaka, Nagoya, Kyoto, Sapporo\n"
        "CREATE TABLE orders (\n"
        "  id INTEGER PRIMARY KEY,\n"
        "  user_id INTEGER NOT NULL,\n"
        "  amount INTEGER NOT NULL,\n"
        "  status TEXT NOT NULL,\n"
        "  FOREIGN KEY(user_id) REFERENCES users(id)\n"
        ");\n"
        "status: paid, pending, cancelled\n"
        "Boolean operators supported: AND, OR, NOT. Use parentheses to group conditions when needed. "
        "Prefer qualified column names (table.column)."
    )
    inp = f"{instruction} Task: {prompt}"
    resp = responses_create(input=inp, tools=tools, model=model)
    used_model = getattr(resp, "model", None) or model
    in_tok, out_tok = extract_usage(resp)

    # Extract query text from custom tool call when possible
    query: str = ""
    out = getattr(resp, "output", None)
    if isinstance(out, list):
        for item in out:
            typ = getattr(item, "type", None) or getattr(item, "object", None)
            if typ == "custom_tool_call" and getattr(item, "name", None) == "sql_query":
                candidate = getattr(item, "input", None)
                if isinstance(candidate, str):
                    query = candidate
                    break
    if not query:
        txt = output_text(resp)
        if isinstance(txt, str):
            query = txt
    query = query.strip()

    parsed_ok = False
    try:
        parser.parse(query)
        parsed_ok = True
    except Exception:
        parsed_ok = False

    executed_ok = False
    cols: List[str] = []
    rows: List[Tuple[Any, ...]] = []
    err: Optional[str] = None
    con = _init_sample_db()
    try:
        cur = con.execute(query)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
        executed_ok = True
    except Exception as e:  # noqa: BLE001
        err = str(e)
        executed_ok = False
    finally:
        con.close()

    return SqlRunResult(
        prompt=prompt,
        query=query,
        parsed_ok=parsed_ok,
        executed_ok=executed_ok,
        columns=cols,
        rows=rows,
        error=err,
        model=used_model,
        usage_input_tokens=in_tok,
        usage_output_tokens=out_tok,
        expected_rows=expected_rows,
    )


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
