import type { BoardData } from "@/lib/kanban";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type AiChatResult = {
  status: string;
  model: string;
  response: string;
  board_updated: boolean;
  board: BoardData;
};

const readJsonOrThrow = async <T>(response: Response): Promise<T> => {
  if (response.ok) {
    return (await response.json()) as T;
  }

  if (response.status === 401) {
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  const errorText = await response.text();
  throw new Error(errorText || `Request failed with ${response.status}`);
};

export const fetchBoard = async (): Promise<BoardData> => {
  const response = await fetch("/api/board");
  return readJsonOrThrow<BoardData>(response);
};

export const renameColumn = async (
  columnId: string,
  title: string
): Promise<void> => {
  const response = await fetch(`/api/columns/${columnId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  await readJsonOrThrow<{ status: string }>(response);
};

export const addCard = async (
  columnId: string,
  title: string,
  details: string
): Promise<void> => {
  const response = await fetch(`/api/columns/${columnId}/cards`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, details }),
  });
  await readJsonOrThrow<{ status: string }>(response);
};

export const deleteCard = async (cardId: string): Promise<void> => {
  const response = await fetch(`/api/cards/${cardId}`, {
    method: "DELETE",
  });
  await readJsonOrThrow<{ status: string }>(response);
};

export const moveCard = async (
  cardId: string,
  targetColumnId: string,
  overCardId: string | null
): Promise<void> => {
  const response = await fetch(`/api/cards/${cardId}/move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      target_column_id: targetColumnId,
      over_card_id: overCardId,
    }),
  });
  await readJsonOrThrow<{ status: string }>(response);
};

export const chatWithAi = async (
  question: string,
  history: ChatMessage[]
): Promise<AiChatResult> => {
  const response = await fetch("/api/ai/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      history,
    }),
  });
  return readJsonOrThrow<AiChatResult>(response);
};
