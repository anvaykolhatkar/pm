import pytest

from app.ai_structured import parse_structured_ai_response


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
