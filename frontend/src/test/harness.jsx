import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { api } from "../api/api.js";
import App from "../App.jsx";
import { analysis, doc, health, metrics } from "./fixtures.js";

/** Render the whole app at a route, with the API already mocked by the calling test file. */
export function renderRoute(route) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <App />
    </MemoryRouter>,
  );
}

/** Sensible defaults for every API call; tests override only what they care about. */
export function defaultApi(overrides = {}) {
  vi.resetAllMocks();
  api.health.mockResolvedValue(health());
  api.getDocument.mockResolvedValue(doc());
  api.getAnalysis.mockResolvedValue(analysis());
  api.modelMetrics.mockResolvedValue(metrics());
  api.listDocuments.mockResolvedValue([doc({ id: 3 }), doc({ id: 4, original_filename: "other.txt" })]);
  for (const [name, value] of Object.entries(overrides)) api[name].mockResolvedValue(value);
}

