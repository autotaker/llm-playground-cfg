from __future__ import annotations

import argparse
import sys

from lib.openai_client import responses_create, output_text


def cmd_ping(args: argparse.Namespace) -> int:
    resp = responses_create(input="Say a short friendly hello.", model=args.model)
    print(output_text(resp))
    return 0


def cmd_cfg_math(args: argparse.Namespace) -> int:
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

    tools = [
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
    resp = responses_create(
        input="Use the math_exp tool to add four plus four.",
        tools=tools,
        model=args.model,
    )
    print(output_text(resp))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="llm-playground", description="LLM playground CLI")
    p.add_argument("--model", default=None, help="Override model (default from env or gpt-5)")
    sp = p.add_subparsers(dest="command", required=True)

    ping = sp.add_parser("ping", help="Basic Responses API sanity check")
    ping.set_defaults(func=cmd_ping)

    cfg_math = sp.add_parser("cfg-math", help="Grammar-constrained math expression sample")
    cfg_math.set_defaults(func=cmd_cfg_math)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

