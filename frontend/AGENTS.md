# Frontend Demo Overview

## Purpose

This `frontend/` app is a standalone Next.js Kanban demo. It currently runs as a frontend-only experience with in-memory state and no backend persistence or authentication.

## Stack

- Next.js App Router (`next` 16)
- React 19 + TypeScript
- Tailwind CSS 4
- Drag and drop via `@dnd-kit`
- Unit tests with Vitest + Testing Library
- E2E tests with Playwright

## How it runs

- Entry page: `src/app/page.tsx`
- Main UI component: `src/components/KanbanBoard.tsx`
- Root route (`/`) renders a single Kanban board directly.

## Current behavior

- Loads one board from backend API after login.
- Columns can be renamed inline (persisted via backend).
- Cards can be created and deleted (persisted via backend).
- Cards can be reordered/moved via drag and drop (persisted via backend).
- Includes logout action that ends the session server-side.
- Includes AI sidebar chat ("Board Copilot") that sends question + history to backend.
- AI responses are shown in conversation history and board updates are applied from API response.

## Data model

Defined in `src/lib/kanban.ts`:

- `Card`: `id`, `title`, `details`
- `Column`: `id`, `title`, `cardIds`
- `BoardData`: `columns[]`, `cards` lookup map

Helper functions include:

- `moveCard(...)` for same-column reorder and cross-column moves
- `createId(...)` for client-side card IDs
- `initialData` seed board data

## Key files

- `src/app/page.tsx` - root page, renders board
- `src/components/KanbanBoard.tsx` - board-level state + DnD handlers
- `src/components/KanbanColumn.tsx` - column UI, rename input, card list, add-card form
- `src/components/KanbanCard.tsx` - sortable card item with remove action
- `src/components/NewCardForm.tsx` - add-card form toggle and submit logic
- `src/lib/kanban.ts` - types, seed data, board move logic
- `src/app/globals.css` - global styles and design tokens

## Tests today

- Unit/component:
  - `src/lib/kanban.test.ts` covers `moveCard` behavior
  - `src/components/KanbanBoard.test.tsx` covers render, rename, add/remove flows
- End-to-end:
  - `tests/kanban.spec.ts` covers board load, add card, drag between columns

## Current limitations (important for backend integration)

- Error handling is intentionally lightweight for MVP.
