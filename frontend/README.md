# Frontend

React 18 + Vite + Tailwind CSS + Recharts. It talks to the FastAPI backend through `/api`.

## Run

```powershell
cd frontend
npm install
npm run dev          # http://localhost:5173  (backend must be running on port 8000)
```

In development Vite forwards every `/api` request to `http://127.0.0.1:8000`, so no CORS setup is needed.
If the backend runs elsewhere, set `VITE_BACKEND_URL` before `npm run dev`.

## Other commands

| Command | What it does |
|---|---|
| `npm test` | Runs the component and API-client tests (Vitest + Testing Library, no browser needed) |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serves the production build locally |

## Structure

```
src/
  api/          axios client; turns every failure into an ApiError with a readable message
  components/   Layout (sidebar, status), ui.jsx (shared pieces: notices, class mark, progress ...)
  hooks/        useApi: loads data, keeps the old data on screen while reloading
  lib/          validation, number/date formatting, the colour of each document class
  pages/        Dashboard, Upload, Documents, Document
  test/         shared fixtures and helpers
```
