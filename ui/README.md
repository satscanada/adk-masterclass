# React Agent Chat UI

This folder contains the React + Vite + Tailwind chat UI for the learning project.

## Commands

```bash
npm install
npm run dev
```

## API settings

Create a local `.env` file from `.env.example` if you want to point the UI at a different backend.

- `VITE_AGENT_API_BASE_URL`: full browser-facing API base, defaults to `/api`
- `VITE_DEV_API_PROXY_TARGET`: Vite dev proxy target, defaults to `http://127.0.0.1:8512`
- `VITE_DEV_PORT`: Vite dev server port, defaults to **8513**

## Streaming agents with audit (Module 07)

For **`multi_agent_banking`**, the chat consumes NDJSON from `POST /api/chat/stream`. Besides `{"type":"delta","text":...}` lines, the API may send **`{"type":"audit",...}`** events. `App.jsx` accumulates them on the in-flight assistant message and renders **Pipeline Audit Trail** above the bubble (tool JSON input/output, grouped by agent). Agent metadata can include **`suggestions`** from `GET /api/agents` for empty-state quick-start buttons.
