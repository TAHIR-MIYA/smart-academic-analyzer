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
  pages/        Dashboard, Upload, Documents
  pages/document/   the tabbed document workspace: Overview, Preprocessing, Keywords, Entities,
                    Classification, Summary, Similarity, Statistics, Export
  test/         fixtures, helpers, and real/ = payloads captured from the running backend
                (used by pages/document/contract.test.jsx so server changes break a test, not the screen)
```

## Refreshing the captured backend payloads

If you change what the API returns, regenerate `src/test/real/*.json` from a running backend
(upload a document, train the model, then save the responses of `POST /api/analysis/{id}`,
`GET /api/model/metrics`, `POST /api/analysis/compare` and `GET /api/analysis/{id}/summary?sentences=5`).
The contract test will then show exactly which screen no longer matches.
