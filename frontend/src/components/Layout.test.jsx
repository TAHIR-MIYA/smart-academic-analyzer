import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../api/api.js";
import App from "../App.jsx";
import { dashboard, health } from "../test/fixtures.js";

vi.mock("../api/api.js", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, api: { health: vi.fn(), dashboard: vi.fn(), listDocuments: vi.fn() } };
});

const at = (route) => render(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>);
beforeEach(() => {
  vi.resetAllMocks();
  api.health.mockResolvedValue(health());
  api.dashboard.mockResolvedValue(dashboard());
  api.listDocuments.mockResolvedValue([]);
});

describe("navigation", () => {
  it("offers the three main sections and highlights the current one", async () => {
    at("/documents");
    const nav = screen.getByRole("navigation", { name: "Main" });
    expect(nav).toHaveTextContent("Dashboard");
    expect(screen.getByRole("link", { name: "Documents" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveAttribute("aria-current");
    expect(await screen.findByText("No documents yet")).toBeInTheDocument();
  });

  it("moves between pages", async () => {
    const user = userEvent.setup();
    at("/");
    await user.click(screen.getByRole("link", { name: "Upload" }));
    expect(await screen.findByRole("heading", { name: "Upload documents" })).toBeInTheDocument();
  });

  it("has a skip link and a working mobile menu button", async () => {
    const user = userEvent.setup();
    at("/");
    expect(screen.getByRole("link", { name: "Skip to content" })).toHaveAttribute("href", "#main");
    const button = screen.getByRole("button", { name: "Open menu" });
    expect(button).toHaveAttribute("aria-expanded", "false");
    await user.click(button);
    expect(screen.getByRole("button", { name: "Close menu" })).toHaveAttribute("aria-expanded", "true");
  });

  it("shows a not-found page for unknown addresses", () => {
    at("/nothing-here");
    expect(screen.getByText("Page not found")).toBeInTheDocument();
  });
});

describe("system status in the sidebar", () => {
  it("reports a healthy system briefly", async () => {
    at("/");
    expect(await screen.findByText("API connected")).toBeInTheDocument();
    expect(screen.getByText("Classifier trained")).toBeInTheDocument();
    expect(screen.queryByText(/Language data missing/)).not.toBeInTheDocument();
  });

  it("tells the user how to start the API when it is down", async () => {
    api.health.mockRejectedValue(new ApiError("Cannot reach the API."));
    at("/upload");
    expect(await screen.findByText("API not reachable")).toBeInTheDocument();
    expect(screen.getAllByText(/uvicorn app.main:app --reload/).length).toBeGreaterThan(0);
  });

  it("tells the user how to fix a missing model or missing language data", async () => {
    api.health.mockResolvedValue(health({ model: { trained: false }, nlp_resources: { ready: false } }));
    at("/upload");
    expect(await screen.findByText(/Classifier not trained/)).toBeInTheDocument();
    expect(screen.getByText(/python -m app.ml.train/)).toBeInTheDocument();
    expect(screen.getByText(/python -m scripts.setup_nlp/)).toBeInTheDocument();
  });

  it("does not suggest the language-data fix when spaCy itself is blocked or broken", async () => {
    api.health.mockResolvedValue(health({ nlp_resources: { ready: false, spacy_problem: "spaCy is installed but cannot be loaded: DLL load failed" } }));
    at("/upload");
    expect(await screen.findByText(/spaCy cannot be used/)).toBeInTheDocument();
    expect(screen.queryByText(/python -m scripts.setup_nlp/)).not.toBeInTheDocument();
  });
});
