import json
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class BoardUpdateOperation(BaseModel):
    action: Literal["rename_column", "add_card", "move_card", "delete_card"]
    column_id: str | None = None
    card_id: str | None = None
    target_column_id: str | None = None
    over_card_id: str | None = None
    title: str | None = None
    details: str | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.action == "rename_column":
            if not self.column_id or not self.title:
                raise ValueError("rename_column requires column_id and title")
        elif self.action == "add_card":
            if not self.column_id or not self.title:
                raise ValueError("add_card requires column_id and title")
        elif self.action == "move_card":
            if not self.card_id or not self.target_column_id:
                raise ValueError("move_card requires card_id and target_column_id")
        elif self.action == "delete_card":
            if not self.card_id:
                raise ValueError("delete_card requires card_id")
        return self


class StructuredAiResponse(BaseModel):
    response: str = Field(min_length=1)
    board_update: list[BoardUpdateOperation] | None = None


def build_structured_chat_prompt(
    board_data: dict,
    question: str,
    history: list[ChatHistoryMessage],
) -> str:
    history_payload = [message.model_dump() for message in history]
    schema_example = {
        "response": "Text shown to the user.",
        "board_update": [
            {
                "action": "rename_column",
                "column_id": "col-1",
                "title": "Ideas",
            }
        ],
    }
    return (
        "You are an assistant helping with a kanban board.\n"
        "Respond with ONLY valid JSON.\n"
        "Schema:\n"
        f"{json.dumps(schema_example, indent=2)}\n"
        "Rules:\n"
        "- Include key 'response' always.\n"
        "- 'board_update' is optional. If no changes needed, use null.\n"
        "- For operations, use only actions: rename_column, add_card, move_card, delete_card.\n"
        "- Use exact IDs from board data.\n"
        "- Do not include markdown fences.\n\n"
        f"Conversation history JSON:\n{json.dumps(history_payload, indent=2)}\n\n"
        f"Current board JSON:\n{json.dumps(board_data, indent=2)}\n\n"
        f"User question:\n{question}"
    )


def parse_structured_ai_response(raw_text: str) -> StructuredAiResponse:
    candidate = raw_text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3:
            candidate = "\n".join(lines[1:-1]).strip()

    if "{" in candidate and "}" in candidate:
        start = candidate.find("{")
        end = candidate.rfind("}")
        candidate = candidate[start : end + 1]

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("AI response was not valid JSON") from exc

    try:
        return StructuredAiResponse.model_validate(parsed)
    except ValidationError as exc:
        raise ValueError(f"AI response schema invalid: {exc}") from exc
