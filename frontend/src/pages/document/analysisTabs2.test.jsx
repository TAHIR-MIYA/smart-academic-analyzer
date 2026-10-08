import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../../api/api.js";
import { analysis, comparison, metrics } from "../../test/fixtures.js";
import { defaultApi, renderRoute } from "../../test/harness.jsx";
import { deferred } from "../../test/utils.jsx";

vi.mock("../../api/api.js", async (orig) => (await import("../../test/apiMock.js")).mockApiModule(orig));
beforeEach(() => defaultApi());

describe("classification tab: this document's prediction", () => {
  it("shows the predicted type, probabilities and the terms behind it", async () => {
    renderRoute("/documents/3/classification");
    expect((await screen.findAllByText("Notice")).length).toBeGreaterThan(0);
    const table = screen.getByRole("table", { name: "Probability of each document type" });
    expect(within(table).getByText("Notice").closest("tr")).toHaveTextContent("95%");
    expect(within(table).getByText("Assignment").closest("tr")).toHaveTextContent("3%");
    expect(screen.getByRole("list", { name: "Terms behind the prediction" })).toHaveTextContent("hereby informed");
    expect(screen.getByText(/logistic regression on cleaned text features, trained on 240 documents/)).toBeInTheDocument();
  });

  it("warns about an uncertain prediction and names the probability", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ classification: { ...analysis().classification, label: "assignment", display_name: "Assignment", confidence: 0.39, is_confident: false } }));
    renderRoute("/documents/3/classification");
    expect(await screen.findByText("The classifier is not sure about this one")).toBeInTheDocument();
    expect(screen.getByText(/probability of 39%, below the 50%/)).toBeInTheDocument();
  });

  it("explains how to get a prediction when no model was trained", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ classification: null, classification_error: "No trained model was found." }));
    renderRoute("/documents/3/classification");
    expect(await screen.findByText("No document type was predicted")).toBeInTheDocument();
    expect(screen.getByText(/No trained model was found\./)).toHaveTextContent("python -m app.ml.train");
  });
});

describe("classification tab: how well the classifier works", () => {
  it("is a separate section that says it is not about this document", async () => {
    renderRoute("/documents/3/classification");
    expect(await screen.findByRole("heading", { name: "How well does the classifier work?" })).toBeInTheDocument();
    expect(await screen.findByText("These results describe the classifier, not this document")).toBeInTheDocument();
    expect(screen.getByText(/after training on 240 documents \(synthetic/)).toBeInTheDocument();
  });

  it("shows the headline figures and the meaning of precision, recall and F1", async () => {
    renderRoute("/documents/3/classification");
    const stat = async (label) => (await screen.findByText(label, { selector: "dt" })).closest("div");
    expect(await stat("Accuracy")).toHaveTextContent("100%");
    expect(await stat("Macro F1")).toHaveTextContent("1.00");
    expect(screen.getByText(/of the documents predicted as a class, the share that were right/)).toBeInTheDocument();
    expect(screen.getByText(/60 documents/)).toBeInTheDocument();
  });

  it("switches evaluation set and updates every figure", async () => {
    const user = userEvent.setup();
    renderRoute("/documents/3/classification");
    await user.click(await screen.findByRole("button", { name: "Independent challenge set" }));
    expect(screen.getByText("Accuracy", { selector: "dt" }).closest("div")).toHaveTextContent("88%");
    expect(screen.getByText(/25 documents/)).toBeInTheDocument();
    expect(screen.getByText(/0\.28/)).toBeInTheDocument();
  });

  it("lists the documents it got wrong with readable class names", async () => {
    const user = userEvent.setup();
    renderRoute("/documents/3/classification");
    await user.click(await screen.findByRole("button", { name: "Independent challenge set" }));
    expect(screen.getByText(/assignment\/sample_04.txt/).closest("li")).toHaveTextContent("is Assignment, predicted Question paper");
  });

  it("says when there were no errors", async () => {
    renderRoute("/documents/3/classification");
    expect(await screen.findByText("None in this set.")).toBeInTheDocument();
  });

  it("gives per-class precision, recall and F1", async () => {
    const user = userEvent.setup();
    renderRoute("/documents/3/classification");
    await user.click(await screen.findByRole("button", { name: "Independent challenge set" }));
    const row = screen.getAllByRole("row").find((r) => r.textContent.startsWith("Assignment") && r.textContent.includes("0.80"));
    expect(row).toHaveTextContent("1.00");
    expect(row).toHaveTextContent("0.80");
    expect(row).toHaveTextContent("0.89");
    expect(row).toHaveTextContent("5");
  });

  it("renders the confusion matrix as a labelled table", async () => {
    const user = userEvent.setup();
    renderRoute("/documents/3/classification");
    await user.click(await screen.findByRole("button", { name: "Independent challenge set" }));
    expect(screen.getByLabelText("4 Assignment documents predicted as Assignment")).toHaveTextContent("4");
    expect(screen.getByLabelText("1 Assignment documents predicted as Notice")).toHaveTextContent("1");
    expect(screen.getByText("Rows are the true class, columns the predicted class.")).toBeInTheDocument();
  });

  it("shows how the model was chosen and marks the winner", async () => {
    renderRoute("/documents/3/classification");
    const chosen = (await screen.findByRole("cell", { name: "Chosen" })).closest("tr");
    expect(chosen).toHaveTextContent("Logistic regression");
    expect(chosen).toHaveTextContent("Cleaned text, stop words kept");
    expect(screen.getByText(/Accuracy on the training data itself was 100%/)).toBeInTheDocument();
    expect(screen.queryByText("Cross-validation could not tell these models apart")).not.toBeInTheDocument();
  });

  it("states plainly when cross-validation could not separate the models", async () => {
    const m = metrics();
    m.selection.candidates = m.selection.candidates.map((c) => ({ ...c, cv_macro_f1_mean: 1 }));
    api.modelMetrics.mockResolvedValue(m);
    renderRoute("/documents/3/classification");
    expect(await screen.findByText("Cross-validation could not tell these models apart")).toBeInTheDocument();
    expect(screen.getByText(/the choice was made by a fixed rule, not by merit/)).toBeInTheDocument();
  });

  it("shows the strongest terms for each class and the cautions", async () => {
    renderRoute("/documents/3/classification");
    expect(await screen.findByText("hereby informed", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText(/optimistic estimate/)).toBeInTheDocument();
    expect(screen.getByText(/must not be quoted as performance/)).toBeInTheDocument();
  });

  it("explains how to create the results when training has not been run", async () => {
    api.modelMetrics.mockRejectedValue(new ApiError("No training metrics were found."));
    renderRoute("/documents/3/classification");
    expect(await screen.findByText("No training results found")).toBeInTheDocument();
    expect(screen.getByText(/No training metrics were found\./)).toHaveTextContent("python -m app.ml.train");
    expect(screen.getAllByText("Notice").length).toBeGreaterThan(0); // the document's own prediction still shows
  });
});

describe("summary tab", () => {
  it("shows the selected sentences in order with their scores", async () => {
    renderRoute("/documents/3/summary");
    await screen.findByText(/2 of 12 sentences/);
    const items = screen.getAllByRole("listitem");
    const sentences = items.filter((li) => li.closest("ol"));
    expect(sentences[0]).toHaveTextContent("The library will remain closed on Friday.");
    expect(sentences[0]).toHaveTextContent("sentence 1, score 100");
    expect(sentences[1]).toHaveTextContent("sentence 3, score 75");
    expect(screen.getByText(/2 of 12 sentences, 18% of the document's words/)).toBeInTheDocument();
  });

  it("explains how sentences were chosen and that quality was not scored", async () => {
    renderRoute("/documents/3/summary");
    expect(await screen.findByText(/square root of how many there are/)).toBeInTheDocument();
    expect(screen.getByText(/25% bonus/)).toBeInTheDocument();
    expect(screen.getByText(/60% shared words/)).toBeInTheDocument();
    expect(screen.getByText(/has not been scored automatically/)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Score of each sentence" })).toBeInTheDocument();
  });

  it("asks the server for a longer summary and shows it", async () => {
    const user = userEvent.setup();
    const longer = analysis().summary;
    api.getSummary.mockResolvedValue({ ...longer, sentences_selected: 3, summary: [...longer.summary, { index: 5, text: "A third sentence appears.", score: 0.2, relative_score: 0.5, words: 4 }] });
    renderRoute("/documents/3/summary");
    await user.click(await screen.findByRole("button", { name: "More sentences" }));
    expect(api.getSummary).toHaveBeenCalledWith(3, 3);
    expect(await screen.findByText("A third sentence appears.")).toBeInTheDocument();
    expect(screen.getByText("3 sentences")).toBeInTheDocument();
  });

  it("returns to the saved summary without another request when going back", async () => {
    const user = userEvent.setup();
    api.getSummary.mockResolvedValue({ ...analysis().summary, sentences_selected: 3 });
    renderRoute("/documents/3/summary");
    await user.click(await screen.findByRole("button", { name: "More sentences" }));
    await screen.findByText("3 sentences");
    await user.click(screen.getByRole("button", { name: "Fewer sentences" }));
    expect(await screen.findByText("2 sentences")).toBeInTheDocument();
    expect(api.getSummary).toHaveBeenCalledTimes(1);
  });

  it("cannot go below one sentence or above the eligible count", async () => {
    const base = analysis();
    api.getAnalysis.mockResolvedValue(analysis({ summary: { ...base.summary, sentences_selected: 2, sentences_eligible: 2 } }));
    renderRoute("/documents/3/summary");
    expect(await screen.findByRole("button", { name: "More sentences" })).toBeDisabled();
  });

  it("reports a failure to update", async () => {
    const user = userEvent.setup();
    api.getSummary.mockRejectedValue(new ApiError("Cannot reach the API."));
    renderRoute("/documents/3/summary");
    await user.click(await screen.findByRole("button", { name: "More sentences" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the API.");
  });

  it("explains why there is no summary", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ summary: null, summary_error: "The document has no sentences suitable for summarisation." }));
    renderRoute("/documents/3/summary");
    expect(await screen.findByText("No summary is available")).toBeInTheDocument();
  });
});
