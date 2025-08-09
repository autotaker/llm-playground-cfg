from __future__ import annotations

from typing import Any, Iterable, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


console = Console()


def print_text(text: str) -> None:
    console.print(Panel.fit(text, title="Response", border_style="cyan"))


def _iter_output_items(resp: Any) -> Iterable[Any]:
    items = getattr(resp, "output", None)
    if isinstance(items, list):
        for it in items:
            yield it


def extract_custom_tool_calls(resp: Any) -> List[dict]:
    calls: List[dict] = []
    for it in _iter_output_items(resp):
        typ = getattr(it, "type", None) or getattr(it, "object", None)
        if typ == "custom_tool_call":
            calls.append(
                {
                    "name": getattr(it, "name", None),
                    "input": getattr(it, "input", None),
                    "status": getattr(it, "status", None),
                    "call_id": getattr(it, "call_id", None),
                }
            )
    return calls


def show_custom_tool_calls(resp: Any, title: str = "Custom Tool Calls") -> None:
    calls = extract_custom_tool_calls(resp)
    table = Table(title=title, show_lines=False, header_style="bold magenta")
    table.add_column("Name", style="bold")
    table.add_column("Input")
    table.add_column("Status", style="green")
    for c in calls:
        table.add_row(str(c.get("name")), str(c.get("input")), str(c.get("status")))
    console.print(table)


def safe_eval_add_mul(expr: str) -> Optional[int]:
    # Evaluate expressions with integers, + and * only.
    import ast

    try:
        node = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None

    def eval_node(n: ast.AST) -> int:
        if isinstance(n, ast.Expression):
            return eval_node(n.body)
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Mult)):
            left = eval_node(n.left)
            right = eval_node(n.right)
            if isinstance(n.op, ast.Add):
                return left + right
            else:
                return left * right
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.UAdd):
            return eval_node(n.operand)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            # Negative numbers not in grammar, but allow safely
            return -eval_node(n.operand)
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return int(n.value)
        raise ValueError("Unsupported expression")

    try:
        return eval_node(node)
    except Exception:
        return None


def show_math_result(expr: str) -> None:
    from rich.align import Align
    from rich.text import Text

    result = safe_eval_add_mul(expr)
    t = Table(box=None, show_header=False)
    t.add_column("Field", style="bold cyan")
    t.add_column("Value")
    t.add_row("Expression", expr)
    t.add_row("Result", str(result) if result is not None else "(n/a)")
    console.print(Panel.fit(t, title="Math Expression", border_style="cyan"))

