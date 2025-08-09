from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, List, Tuple

from lark import Lark

from lib.openai_client import responses_create, output_text


# Lark grammar: + - * / with parentheses and integers, ignoring inline spaces
ARITH_LARK = r"""
start: expr
?expr: term ( ("+"|"-") term )*
?term: factor ( ("*"|"/") factor )*
?factor: INT | "(" expr ")"
%import common.INT
%import common.WS_INLINE
%ignore WS_INLINE
"""


def safe_eval_arith(expr: str) -> Optional[float]:
    import ast

    try:
        node = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None

    def eval_node(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return eval_node(n.body)
        if isinstance(n, ast.BinOp) and isinstance(
            n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)
        ):
            left = eval_node(n.left)
            right = eval_node(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            if isinstance(n.op, ast.Sub):
                return left - right
            if isinstance(n.op, ast.Mult):
                return left * right
            return left / right
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            val = eval_node(n.operand)
            return val if isinstance(n.op, ast.UAdd) else -val
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        raise ValueError("Unsupported expression")

    try:
        return eval_node(node)
    except Exception:
        return None


parser = Lark(ARITH_LARK, start="start", parser="earley")


@dataclass
class MathRunResult:
    prompt: str
    expression: str
    parsed_ok: bool
    value: Optional[float]
    expected: Optional[float]


def run_cfg_math(
    prompt: str, expected: Optional[float] = None, model: Optional[str] = None
) -> MathRunResult:
    tools = [
        {
            "type": "custom",
            "name": "math_exp",
            "description": "Creates valid mathematical expressions",
            "format": {
                "type": "grammar",
                "syntax": "lark",
                "definition": ARITH_LARK,
            },
        }
    ]
    # Ask the model to use the tool to produce only an expression
    inp = f"Use the math_exp tool to produce only one expression for: {prompt}"
    resp = responses_create(input=inp, tools=tools, model=model)

    # Extract expression text from custom tool call if present; fallback to output_text
    expr: str = ""
    out = getattr(resp, "output", None)
    if isinstance(out, list):
        for item in out:
            typ = getattr(item, "type", None) or getattr(item, "object", None)
            if typ == "custom_tool_call" and getattr(item, "name", None) == "math_exp":
                candidate = getattr(item, "input", None)
                if isinstance(candidate, str):
                    expr = candidate
                    break
    if not expr:
        txt = output_text(resp)
        if isinstance(txt, str):
            expr = txt
    expr = expr.strip()

    parsed_ok = False
    value: Optional[float] = None
    try:
        parser.parse(expr)
        parsed_ok = True
        value = safe_eval_arith(expr)
    except Exception:
        parsed_ok = False

    return MathRunResult(
        prompt=prompt,
        expression=expr,
        parsed_ok=parsed_ok,
        value=value,
        expected=expected,
    )


def default_math_cases() -> List[Tuple[str, Optional[float]]]:
    return [
        ("add four plus four", 8),
        ("seven times three plus one", 22),
        ("open parenthesis ten minus six close parenthesis times five", 20),
        ("twenty divided by four plus two", 7),
    ]
