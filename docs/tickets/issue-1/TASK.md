## 概要

Responses API に新しく追加された CFG 機能を試す。

公式のサンプルコード

### Lark を使用した CFG の例

```python
from openai import OpenAI

client = OpenAI()

grammar = """
start: expr
expr: term (SP ADD SP term)* -> add
| term
term: factor (SP MUL SP factor)* -> mul
| factor
factor: INT
SP: " "
ADD: "+"
MUL: "*"
%import common.INT
"""

response = client.responses.create(
    model="gpt-5",
    input="Use the math_exp tool to add four plus four.",
    tools=[
        {
            "type": "custom",
            "name": "math_exp",
            "description": "Creates valid mathematical expressions",
            "format": {
                "type": "grammar",
                "syntax": "lark",
                "definition": grammar,
            },
        }
    ]
)
print(response.output)
```

詳細は <references/syntax.md> を参照してください。

### 正規表現を使用した例

```python
from openai import OpenAI

client = OpenAI()

grammar = r"^(?P<month>January|February|March|April|May|June|July|August|September|October|November|December)s+(?P<day>d{1,2})(?:st|nd|rd|th)?s+(?P<year>d{4})s+ats+(?P<hour>0?[1-9]|1[0-2])(?P<ampm>AM|PM)$"

response = client.responses.create(
    model="gpt-5",
    input="Use the timestamp tool to save a timestamp for August 7th 2025 at 10AM.",
    tools=[
        {
            "type": "custom",
            "name": "timestamp",
            "description": "Saves a timestamp in date + time in 24-hr format.",
            "format": {
                "type": "grammar",
                "syntax": "regex",
                "definition": grammar,
            },
        }
    ]
)
print(response.output)
```

## タスク

今回は LLM が以下の形式言語を生成できるかを試します。

CFG:

- 四則演算
- SQL
- KQL
- OData
- 独自 DSL(<references/custom_dsl.md>)

正規表現:

- 日本の住所
- アクセスログ
