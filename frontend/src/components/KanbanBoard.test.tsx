import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

const cloneBoard = (): BoardData =>
  JSON.parse(JSON.stringify(initialData)) as BoardData;

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  beforeEach(() => {
    const board = cloneBoard();
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url === "/api/board" && method === "GET") {
        return new Response(JSON.stringify(board), { status: 200 });
      }

      if (url.startsWith("/api/columns/") && method === "PATCH") {
        const columnId = url.split("/").pop() ?? "";
        const payload = JSON.parse(String(init?.body ?? "{}")) as { title?: string };
        board.columns = board.columns.map((column) =>
          column.id === columnId && payload.title
            ? { ...column, title: payload.title }
            : column
        );
        return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
      }

      if (url.includes("/cards") && method === "POST") {
        const parts = url.split("/");
        const columnId = parts[3];
        const payload = JSON.parse(String(init?.body ?? "{}")) as {
          title?: string;
          details?: string;
        };
        const cardId = `card-test-${Object.keys(board.cards).length + 1}`;
        board.cards[cardId] = {
          id: cardId,
          title: payload.title ?? "Untitled",
          details: payload.details ?? "",
        };
        board.columns = board.columns.map((column) =>
          column.id === columnId
            ? { ...column, cardIds: [...column.cardIds, cardId] }
            : column
        );
        return new Response(JSON.stringify({ status: "ok", card_id: cardId }), {
          status: 200,
        });
      }

      if (url.startsWith("/api/cards/") && method === "DELETE") {
        const cardId = url.split("/").pop() ?? "";
        delete board.cards[cardId];
        board.columns = board.columns.map((column) => ({
          ...column,
          cardIds: column.cardIds.filter((id) => id !== cardId),
        }));
        return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
      }

      if (url === "/api/logout" && method === "POST") {
        return new Response(JSON.stringify({ status: "ok" }), { status: 200 });
      }

      if (url === "/api/ai/chat" && method === "POST") {
        board.columns = board.columns.map((column, index) =>
          index === 0 ? { ...column, title: "Planning" } : column
        );
        return new Response(
          JSON.stringify({
            status: "ok",
            model: "claude-haiku-4-5-20251001",
            response: "Updated the first column to Planning.",
            board_updated: true,
            board,
          }),
          { status: 200 }
        );
      }

      return new Response("Not Found", { status: 404 });
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders five columns", async () => {
    render(<KanbanBoard />);
    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    await userEvent.tab();
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("sends chat and refreshes board state", async () => {
    render(<KanbanBoard />);
    await waitFor(() => {
      expect(screen.getAllByTestId(/column-/i)).toHaveLength(5);
    });

    await userEvent.type(
      screen.getByPlaceholderText(/ask ai to review or update cards/i),
      "Rename first column"
    );
    await userEvent.click(screen.getByRole("button", { name: /send to ai/i }));

    await waitFor(() => {
      expect(screen.getByText("Updated the first column to Planning.")).toBeInTheDocument();
    });
    expect(screen.getByDisplayValue("Planning")).toBeInTheDocument();
  });
});
