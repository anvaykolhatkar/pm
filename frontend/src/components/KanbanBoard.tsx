"use client";

import { useEffect, useMemo, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import type { BoardData } from "@/lib/kanban";
import {
  addCard,
  chatWithAi,
  deleteCard,
  fetchBoard,
  moveCard,
  renameColumn,
  type ChatMessage,
} from "@/lib/api";

export const KanbanBoard = () => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board?.cards]);

  const loadBoard = async () => {
    try {
      setError(null);
      const nextBoard = await fetchBoard();
      setBoard(nextBoard);
    } catch {
      setError("Could not load board data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadBoard();
  }, []);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const findColumnId = (cardOrColumnId: string) => {
    if (!board) {
      return null;
    }
    const direct = board.columns.find((column) => column.id === cardOrColumnId);
    if (direct) {
      return direct.id;
    }
    const byCard = board.columns.find((column) =>
      column.cardIds.includes(cardOrColumnId)
    );
    return byCard?.id ?? null;
  };

  const handleDragEnd = async (event: DragEndEvent) => {
    if (!board) {
      return;
    }
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    const activeCardId = active.id as string;
    const overId = over.id as string;
    const targetColumnId = findColumnId(overId);

    if (!targetColumnId) {
      return;
    }

    const overCardId = overId.startsWith("card-") ? overId : null;

    try {
      await moveCard(activeCardId, targetColumnId, overCardId);
      await loadBoard();
    } catch {
      setError("Could not move card.");
    }
  };

  const handleRenameColumn = async (columnId: string, title: string) => {
    if (!board) {
      return;
    }
    const previous = board;
    setBoard({
      ...board,
      columns: board.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    });

    try {
      await renameColumn(columnId, title);
      await loadBoard();
    } catch {
      setBoard(previous);
      setError("Could not rename column.");
    }
  };

  const handleAddCard = async (columnId: string, title: string, details: string) => {
    try {
      await addCard(columnId, title, details);
      await loadBoard();
    } catch {
      setError("Could not add card.");
    }
  };

  const handleDeleteCard = async (_columnId: string, cardId: string) => {
    try {
      await deleteCard(cardId);
      await loadBoard();
    } catch {
      setError("Could not delete card.");
    }
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  const handleLogout = async () => {
    await fetch("/api/logout", { method: "POST" });
    window.location.href = "/login";
  };

  const handleSendChat = async () => {
    const question = chatInput.trim();
    if (!question || chatLoading) {
      return;
    }

    const nextMessages: ChatMessage[] = [
      ...chatMessages,
      { role: "user", content: question },
    ];
    setChatMessages(nextMessages);
    setChatInput("");
    setChatLoading(true);

    try {
      const result = await chatWithAi(question, chatMessages);
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.response },
      ]);
      setBoard(result.board);
      setError(null);
    } catch {
      setError("Could not send AI chat message.");
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I could not process that request right now. Please try again.",
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  if (loading || !board) {
    return (
      <main className="mx-auto flex min-h-screen max-w-[1500px] items-center justify-center px-6">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading board...
        </p>
      </main>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
              <button
                type="button"
                onClick={handleLogout}
                className="mt-4 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
              >
                Log out
              </button>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
          {error ? (
            <p className="text-sm font-semibold text-red-600" role="alert">
              {error}
            </p>
          ) : null}
        </header>

        <section className="grid gap-6 xl:grid-cols-[minmax(0,4fr)_360px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <aside className="flex min-h-[520px] flex-col rounded-3xl border border-[var(--stroke)] bg-white/85 p-5 shadow-[var(--shadow)] backdrop-blur">
            <div className="border-b border-[var(--stroke)] pb-3">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                AI Assistant
              </p>
              <h2 className="mt-2 font-display text-xl font-semibold text-[var(--navy-dark)]">
                Board Copilot
              </h2>
            </div>

            <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-1">
              {chatMessages.length === 0 ? (
                <p className="rounded-2xl border border-dashed border-[var(--stroke)] px-3 py-4 text-sm text-[var(--gray-text)]">
                  Ask me to update your board. Example: &quot;Move card-1 to
                  Discovery&quot;.
                </p>
              ) : (
                chatMessages.map((message, index) => (
                  <div
                    key={`${message.role}-${index}`}
                    className={`rounded-2xl px-3 py-3 text-sm leading-6 ${
                      message.role === "user"
                        ? "bg-[var(--primary-blue)]/10 text-[var(--navy-dark)]"
                        : "bg-[var(--surface)] text-[var(--gray-text)]"
                    }`}
                  >
                    <p className="mb-1 text-xs font-semibold uppercase tracking-[0.18em]">
                      {message.role}
                    </p>
                    <p>{message.content}</p>
                  </div>
                ))
              )}
            </div>

            <div className="mt-4 space-y-3 border-t border-[var(--stroke)] pt-4">
              <textarea
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                rows={3}
                placeholder="Ask AI to review or update cards..."
                className="w-full resize-none rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
              />
              <button
                type="button"
                onClick={() => void handleSendChat()}
                disabled={chatLoading || !chatInput.trim()}
                className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {chatLoading ? "Sending..." : "Send to AI"}
              </button>
            </div>
          </aside>
        </section>
      </main>
    </div>
  );
};
