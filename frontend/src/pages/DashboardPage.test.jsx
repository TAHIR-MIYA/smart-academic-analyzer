import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../api/api.js";
import { dashboard } from "../test/fixtures.js";
import { renderAt } from "../test/utils.jsx";
import DashboardPage from "./DashboardPage.jsx";

vi.mock("../api/api.js", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, api: { dashboard: vi.fn() } };
});

beforeEach(() => vi.resetAllMocks());

describe("with documents", () => {
  beforeEach(() => api.dashboard.mockResolvedValue(dashboard()));

  it("shows the headline figures", async () => {
    renderAt(<DashboardPage />);
    expect(await screen.findByText("14,231")).toBeInTheDocument();
    const stat = (label) => screen.getByText(label, { selector: "dt" }).closest("div");
    expect(stat("Documents")).toHaveTextContent("12");
    expect(stat("Analysed")).toHaveTextContent("9");
    expect(stat("Words stored")).toHaveTextContent("14,231");
    expect(stat("Uncertain predictions")).toHaveTextContent("2");
  });

  it("offers the class counts in an accessible table next to the chart", async () => {
    renderAt(<DashboardPage />);
    const table = await screen.findByRole("table", { name: "Documents per predicted class" });
    expect(within(table).getByText("Notice").closest("tr")).toHaveTextContent("5");
    expect(within(table).getByText("Assignment").closest("tr")).toHaveTextContent("3");
    expect(screen.getByText(/These are predictions, not measurements of accuracy/)).toBeInTheDocument();
  });

  it("keeps evaluation results separate from predictions and labels each set", async () => {
    renderAt(<DashboardPage />);
    expect(await screen.findByText("Held-out test split")).toBeInTheDocument();
    expect(screen.getByText("Independent challenge set")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Held-out test split accuracy" })).toHaveAttribute("aria-valuenow", "1");
    expect(screen.getByRole("meter", { name: "Independent challenge set accuracy" })).toHaveAttribute("aria-valuenow", "0.88");
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("88%")).toBeInTheDocument();
    expect(screen.getByText(/not a measure of any single prediction/)).toBeInTheDocument();
    expect(screen.getByText(/Measured on separate evaluation sets, not on your documents/)).toBeInTheDocument();
  });

  it("links recent documents to their pages", async () => {
    renderAt(<DashboardPage />);
    expect(await screen.findByRole("link", { name: "notes.txt" })).toHaveAttribute("href", "/documents/3");
    expect(screen.getByText("Analysed", { selector: "span" })).toBeInTheDocument();
  });

  it("says so when no class has been predicted yet", async () => {
    api.dashboard.mockResolvedValue(dashboard({ class_distribution: [] }));
    renderAt(<DashboardPage />);
    expect(await screen.findByText(/No predictions saved yet/)).toBeInTheDocument();
  });
});

describe("other states", () => {
  it("invites the first upload when there are no documents", async () => {
    api.dashboard.mockResolvedValue(dashboard({ total_documents: 0, analyzed_documents: 0, total_words: 0, recent_documents: [], class_distribution: [] }));
    renderAt(<DashboardPage />);
    expect(await screen.findByText("No documents yet")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Upload your first document" })).toHaveAttribute("href", "/upload");
  });

  it("tells the user how to train the classifier", async () => {
    api.dashboard.mockResolvedValue(dashboard({ model: { trained: false, evaluations: [], note: "x", trained_at: null, classifier: null, feature_set: null } }));
    renderAt(<DashboardPage />);
    expect(await screen.findByText("The classifier has not been trained")).toBeInTheDocument();
    expect(screen.getByText("python -m app.ml.train")).toBeInTheDocument();
  });

  it("shows a readable error and retries on request", async () => {
    const user = userEvent.setup();
    api.dashboard.mockRejectedValueOnce(new ApiError("Cannot reach the API. Start the backend with: uvicorn app.main:app --reload"));
    api.dashboard.mockResolvedValueOnce(dashboard());
    renderAt(<DashboardPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the API");
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("14,231")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows a loading indicator first", () => {
    api.dashboard.mockReturnValue(new Promise(() => {}));
    renderAt(<DashboardPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading the dashboard");
  });
});
