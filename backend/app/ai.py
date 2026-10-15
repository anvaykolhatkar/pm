import os

from anthropic import Anthropic

MODEL_ID = "claude-haiku-4-5-20251001"


def _extract_text(content) -> str:
    text_chunks: list[str] = []
    for block in content:
        block_text = getattr(block, "text", None)
        if block_text:
            text_chunks.append(str(block_text))
    return "".join(text_chunks).strip()


def run_ai_ping(prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL_ID,
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}],
    )
    text = _extract_text(response.content)
    if not text:
        raise ValueError("Anthropic returned empty response")
    return text


def run_ai_chat_prompt(prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured")

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=MODEL_ID,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    text = _extract_text(response.content)
    if not text:
        raise ValueError("Anthropic returned empty response")
    return text
