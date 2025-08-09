from openai import OpenAI


def main() -> None:
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

    # Minimal request using the Responses API with a grammar-constrained tool
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
        ],
    )

    # Prefer output_text if available, otherwise print the raw object
    out = getattr(response, "output_text", None) or getattr(response, "output", None) or str(response)
    print(out)


if __name__ == "__main__":
    main()
