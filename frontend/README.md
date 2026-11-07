# Brainy — frontend

Web app (Vite + React + TypeScript): keyboard shortcut, Siri-like voice overlay, microphone → Gladia.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # fill in GLADIA_API_KEY / HCOMPANY_API_KEY
npm run dev            # http://localhost:5173
```

## Scripts

- `npm run dev` — dev server
- `npm run build` — type-check + production build
- `npm run lint` — ESLint

API keys stay server-side: never expose them through `VITE_*` variables.
