from openai import OpenAI


def main() -> None:
    client = OpenAI()
    resp = client.responses.create(
        model="gpt-5",
        input="Say a short friendly hello.",
    )
    out = getattr(resp, "output_text", None) or getattr(resp, "output", None) or str(resp)
    print(out)


if __name__ == "__main__":
    main()
