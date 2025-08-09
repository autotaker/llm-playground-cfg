from __future__ import annotations

import argparse
import sys

from lib.openai_client import responses_create, output_text
from lib import render
from experiments.cfg_math import run_cfg_math, default_math_cases
from datetime import datetime
from pathlib import Path
import time


def cmd_ping(args: argparse.Namespace) -> int:
    resp = responses_create(input="Say a short friendly hello.", model=args.model)
    render.print_text(output_text(resp))
    return 0


def cmd_cfg_math(args: argparse.Namespace) -> int:
    prompt = args.prompt or "add four plus four"
    expected = args.expect
    res = run_cfg_math(prompt=prompt, expected=expected, model=args.model)
    render.show_arith_validation(res.prompt, res.expression, res.parsed_ok, res.value, res.expected)
    return 0


def cmd_cfg_math_suite(args: argparse.Namespace) -> int:
    cases = default_math_cases()
    # Determine models to run: prefer explicit --models if provided, else use args.model or defaults
    models_arg = getattr(args, "models", None)
    if models_arg:
        models = [m.strip() for m in str(models_arg).split(",") if m.strip()]
    else:
        models = [args.model] if args.model else ["gpt-5", "gpt-5-mini", "gpt-5-nano"]

    rows = []  # list of tuples (model, result, duration)
    for model in models:
        for prompt, expected in cases:
            t0 = time.perf_counter()
            res = run_cfg_math(prompt=prompt, expected=expected, model=model)
            dt = time.perf_counter() - t0
            rows.append((model, res, dt))

    # Prepare Markdown
    lines = []
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"# CFG Math Suite Report\n")
    lines.append(f"Generated: {ts}\n")
    lines.append("")
    lines.append("| # | Model | Prompt | Expression | Parsed | Value | Expected | Check | Time (s) |")
    lines.append("|---:|:---:|---|---|:---:|---:|---:|:---:|------:|")
    for i, (model, r, sec) in enumerate(rows, 1):
        parsed = "yes" if r.parsed_ok else "no"
        val = "" if r.value is None else (str(int(r.value)) if float(r.value).is_integer() else f"{r.value}")
        exp = "" if r.expected is None else (str(int(r.expected)) if float(r.expected).is_integer() else f"{r.expected}")
        check = "" if r.expected is None else ("pass" if (r.value is not None and abs(r.value - r.expected) < 1e-9) else "fail")
        expr = (r.expression or "").replace("|", "\\|")
        lines.append(f"| {i} | {model} | {r.prompt} | `{expr}` | {parsed} | {val} | {exp} | {check} | {sec:.2f} |")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    out_file.write_text("\n".join(lines), encoding="utf-8")
    render.print_text(f"Saved report to {out_file}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="llm-playground", description="LLM playground CLI")
    p.add_argument("--model", default=None, help="Override model (default from env or gpt-5)")
    sp = p.add_subparsers(dest="command", required=True)

    ping = sp.add_parser("ping", help="Basic Responses API sanity check")
    ping.set_defaults(func=cmd_ping)

    cfg_math = sp.add_parser("cfg-math", help="Grammar-constrained math expression with Lark validation")
    cfg_math.add_argument("--prompt", help="Natural language math task", default=None)
    cfg_math.add_argument("--expect", type=float, help="Expected numeric result (optional)", default=None)
    cfg_math.set_defaults(func=cmd_cfg_math)

    suite = sp.add_parser("cfg-math-suite", help="Run a batch of arithmetic cases and save a Markdown report")
    suite.add_argument("--out-dir", default="docs/experiments/cfg-math", help="Output directory for Markdown report")
    suite.add_argument(
        "--models",
        default="gpt-5,gpt-5-mini,gpt-5-nano",
        help="Comma-separated list of models to test (default: gpt-5,gpt-5-mini,gpt-5-nano)",
    )
    suite.set_defaults(func=cmd_cfg_math_suite)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
