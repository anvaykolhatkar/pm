import json

import pytest

from app.ai_structured import (
    ChatHistoryMessage,
    build_structured_chat_prompt,
    parse_structured_ai_response,
)


def test_parse_structured_response_valid() -> None:
    raw = """
    {
      "response": "Done",
      "board_update": [
        {"action": "rename_column", "column_id": "col-1", "title": "Ideas"}
      ]
    }
    """
    parsed = parse_structured_ai_response(raw)
    assert parsed.response == "Done"
    assert parsed.board_update is not None
    assert parsed.board_update[0].action == "rename_column"


def test_parse_structured_response_invalid_json() -> None:
    with pytest.raises(ValueError):
        parse_structured_ai_response("not-json")


def test_parse_structured_response_invalid_schema() -> None:
    with pytest.raises(ValueError):
        parse_structured_ai_response('{"response":"x","board_update":[{"action":"rename_column"}]}')


def test_build_prompt_sends_history_as_turns() -> None:
    history = [
        ChatHistoryMessage(role="user", content="Hi"),
        ChatHistoryMessage(role="assistant", content="Hello"),
    ]
    system, messages = build_structured_chat_prompt(
        {"columns": [], "cards": {}}, "Add a card", history
    )
    assert "Current board JSON" in system
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert json.loads(messages[1]["content"]) == {
        "response": "Hello",
        "board_update": None,
    }
    assert messages[-1]["content"] == "Add a card"
