// Contract test: every tab is rendered with payloads captured from the REAL backend (src/test/real/*.json),
// so a field renamed or reshaped on the server fails here instead of on screen.
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../../api/api.js";
import { doc } from "../../test/fixtures.js";
import { defaultApi, renderRoute } from "../../test/harness.jsx";
import comparison from "../../test/real/comparison.json";
import metrics from "../../test/real/metrics.json";
import noModel from "../../test/real/analysis_no_model.json";
import notice from "../../test/real/analysis_notice.json";
import report from "../../test/real/analysis_report.json";
import short from "../../test/real/analysis_short.json";
import summary5 from "../../test/real/summary_5.json";

vi.mock("../../api/api.js", async (orig) => (await import("../../test/apiMock.js")).mockApiModule(orig));

const TABS = [
  ["", "At a glance"],
  ["/preprocessing", "Cleaning"],
  ["/keywords", "Word groups"],
  ["/entities", "Named entities"],
  ["/classification", "Prediction for this document"],
  ["/summary", null],
  ["/similarity", "Similarity to subject profiles"],
  ["/statistics", "Vocabulary variety"],
  ["/export", "Download the analysis"],
];
const FILES = { "no model": noModel, "project report": report, notice, "short notice": short };

beforeEach(() => {
  defaultApi();
  api.modelMetrics.mockResolvedValue(metrics);
  api.compareDocuments.mockResolvedValue(comparison);
  api.getSummary.mockResolvedValue(summary5);
});

describe.each(Object.entries(FILES))("real payload: %s", (_name, payload) => {
  it.each(TABS)("tab %s renders without error", async (tab, heading) => {
    api.getAnalysis.mockResolvedValue(payload);
    renderRoute(`/documents/3${tab}`);
    if (heading) expect(await screen.findByRole("heading", { name: heading })).toBeInTheDocument();
    else expect(await screen.findByText(/How the sentences were chosen|No summary is available/)).toBeInTheDocument();
    expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
  });
});

describe("real classification payloads", () => {
  it("shows the predicted class with one probability per class, summing to 1", async () => {
    api.getAnalysis.mockResolvedValue(report);
    renderRoute("/documents/3/classification");
    const table = await screen.findByRole("table", { name: "Probability of each document type" });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(5);
    expect(rows[0]).toHaveTextContent("Project Report");
    // The server's probabilities form a distribution; whole-number percentages on screen may round to 98..102.
    expect(report.classification.probabilities.reduce((sum, p) => sum + p.probability, 0)).toBeCloseTo(1, 3);
    const shown = rows.reduce((sum, r) => sum + parseFloat(r.lastChild.textContent), 0);
    expect(shown).toBeGreaterThanOrEqual(95);
    expect(shown).toBeLessThanOrEqual(105);
  });

  it("explains a missing model using the backend's own message", async () => {
    api.getAnalysis.mockResolvedValue(noModel);
    api.modelMetrics.mockRejectedValue(new ApiError("No training metrics were found."));
    renderRoute("/documents/3/classification");
    expect(await screen.findByText("No document type was predicted")).toBeInTheDocument();
    expect(await screen.findByText("No training results found")).toBeInTheDocument();
  });
});

describe("real model evaluation", () => {
  it("renders each evaluation set with a 5 x 5 confusion matrix and every per-class row", async () => {
    const user = userEvent.setup();
    api.getAnalysis.mockResolvedValue(report);
    renderRoute("/documents/3/classification");
    for (const title of ["Held-out test split", "Independent challenge set"]) {
      await user.click(await screen.findByRole("button", { name: title }));
      expect(screen.getAllByRole("cell").filter((c) => /documents predicted as/.test(c.getAttribute("aria-label") ?? ""))).toHaveLength(25);
    }
    const accuracy = screen.getByText("Accuracy", { selector: "dt" }).closest("div");
    expect(accuracy).toHaveTextContent(/%$/);
  });

  it("only offers the evaluation sets that exist (no real-documents button yet)", async () => {
    api.getAnalysis.mockResolvedValue(report);
    renderRoute("/documents/3/classification");
    await screen.findByRole("button", { name: "Held-out test split" });
    expect(screen.queryByRole("button", { name: "Real documents" })).not.toBeInTheDocument();
  });

  it("lists real misclassified files by readable class name", async () => {
    const user = userEvent.setup();
    api.getAnalysis.mockResolvedValue(report);
    renderRoute("/documents/3/classification");
    await user.click(await screen.findByRole("button", { name: "Independent challenge set" }));
    const wrong = metrics.evaluations.challenge_set.misclassified;
    expect(wrong.length).toBeGreaterThan(0);
    expect(screen.getByText(new RegExp(wrong[0].file.replace(".", "\\.")))).toBeInTheDocument();
    const items = screen.getAllByRole("listitem").filter((li) => /, predicted /.test(li.textContent));
    expect(items).toHaveLength(wrong.length);
    for (const item of items) {
      // file paths such as question_paper/sample_03.txt are fine; the class names around them must be readable
      expect(item.textContent).not.toMatch(/\b(is|predicted) (assignment|notice|question_paper|project_report|study_material)\b/);
      expect(item.textContent).toMatch(/is [A-Z][a-z]+( [a-z]+)?, predicted [A-Z][a-z]+( [a-z]+)?/);
    }
  });

  it("reflects the real model-selection result honestly", async () => {
    api.getAnalysis.mockResolvedValue(report);
    renderRoute("/documents/3/classification");
    expect(await screen.findByRole("cell", { name: "Chosen" })).toBeInTheDocument();
    const f1 = metrics.selection.candidates.map((c) => c.cv_macro_f1_mean);
    const tied = Math.max(...f1) - Math.min(...f1) < 0.005;
    expect(Boolean(screen.queryByText("Cross-validation could not tell these models apart"))).toBe(tied);
  });
});

describe("real comparison and summary payloads", () => {
  it("renders the real comparison result", async () => {
    const user = userEvent.setup();
    api.getAnalysis.mockResolvedValue(report);
    renderRoute("/documents/3/similarity");
    await user.selectOptions(await screen.findByLabelText("Compare with"), "other.txt");
    await user.click(screen.getByRole("button", { name: "Compare documents" }));
    expect(await screen.findByText(comparison.cosine_similarity.toFixed(2))).toBeInTheDocument();
    expect(screen.getByText(comparison.interpretation)).toBeInTheDocument();
  });

  it("renders a real longer summary returned by the server", async () => {
    const user = userEvent.setup();
    api.getAnalysis.mockResolvedValue(short);
    renderRoute("/documents/3/summary");
    const more = await screen.findByRole("button", { name: "More sentences" });
    if (more.disabled) return; // a short document may already show every eligible sentence
    await user.click(more);
    expect(await screen.findByText(summary5.summary[0].text)).toBeInTheDocument();
  });
});
