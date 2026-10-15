import os

from anthropic import Anthropic

MODEL_ID = "claude-haiku-4-5-20251001"

_client: Anthropic | None = None


def _get_client() -> Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        _client = Anthropic(api_key=api_key)
    return _client


def _extract_text(content) -> str:
    text_chunks: list[str] = []
    for block in content:
        block_text = getattr(block, "text", None)
        if block_text:
            text_chunks.append(str(block_text))
    return "".join(text_chunks).strip()


def _run_messages(messages: list[dict], max_tokens: int, **kwargs) -> str:
    response = _get_client().messages.create(
        model=MODEL_ID,
        max_tokens=max_tokens,
        messages=messages,
        **kwargs,
    )
    text = _extract_text(response.content)
    if not text:
        raise ValueError("Anthropic returned empty response")
    return text


def run_ai_ping(prompt: str) -> str:
    return _run_messages([{"role": "user", "content": prompt}], max_tokens=128)


def run_ai_chat(system: str, messages: list[dict]) -> str:
    return _run_messages(messages, max_tokens=2048, system=system)
