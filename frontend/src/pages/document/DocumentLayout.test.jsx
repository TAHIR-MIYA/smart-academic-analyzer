import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, saveBlob } from "../../api/api.js";
import { analysis, doc } from "../../test/fixtures.js";
import { defaultApi, renderRoute } from "../../test/harness.jsx";
import { deferred } from "../../test/utils.jsx";

vi.mock("../../api/api.js", async (orig) => (await import("../../test/apiMock.js")).mockApiModule(orig));
beforeEach(() => defaultApi());

describe("document header and tabs", () => {
  it("describes the document in one plain sentence", async () => {
    api.getDocument.mockResolvedValue(doc({ file_type: "pdf", page_count: 3, size_bytes: 2048, word_count: 1234 }));
    renderRoute("/documents/3");
    expect(await screen.findByRole("heading", { name: "notes.txt" })).toBeInTheDocument();
    expect(screen.getByText(/PDF file, 2.0 KB, 3 pages, 1,234 words\. Added 5 Oct 2026\. Analysed 5 Oct 2026\./)).toBeInTheDocument();
  });

  it("offers every section as a tab and marks the current one", async () => {
    renderRoute("/documents/3/keywords");
    const nav = await screen.findByRole("navigation", { name: "Document sections" });
    const names = within(nav).getAllByRole("link").map((l) => l.textContent);
    expect(names).toEqual(["Overview", "Preprocessing", "Keywords", "Entities", "Classification", "Summary", "Similarity", "Statistics", "Export"]);
    expect(within(nav).getByRole("link", { name: "Keywords" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Overview" })).not.toHaveAttribute("aria-current");
    expect(within(nav).getByRole("link", { name: "Statistics" })).toHaveAttribute("href", "/documents/3/statistics");
  });

  it("moves between tabs without reloading the document", async () => {
    const user = userEvent.setup();
    renderRoute("/documents/3");
    await user.click(await screen.findByRole("link", { name: "Entities" }));
    expect(await screen.findByText(/mentions of 4 distinct entities/)).toBeInTheDocument();
    expect(api.getDocument).toHaveBeenCalledTimes(1);
    expect(api.getAnalysis).toHaveBeenCalledTimes(1);
  });

  it("shows extraction warnings above the tabs content", async () => {
    api.getDocument.mockResolvedValue(doc({ warnings: ["PDF has 400 pages; only the first 300 were processed."] }));
    renderRoute("/documents/3/keywords");
    expect(await screen.findByText(/only the first 300 were processed/)).toBeInTheDocument();
  });

  it("explains a missing document", async () => {
    api.getDocument.mockRejectedValue(new ApiError("Document 3 was not found.", { status: 404 }));
    renderRoute("/documents/3");
    expect(await screen.findByText("Document not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to documents" })).toHaveAttribute("href", "/documents");
  });

  it("shows other load errors", async () => {
    api.getDocument.mockRejectedValue(new ApiError("Cannot reach the API."));
    renderRoute("/documents/3");
    expect(await screen.findByText("The document could not be loaded")).toBeInTheDocument();
  });
});

describe("a document that has not been analysed", () => {
  beforeEach(() => api.getAnalysis.mockResolvedValue(null));

  it.each(["", "/preprocessing", "/keywords", "/entities", "/classification", "/summary", "/similarity", "/statistics"])(
    "the %s tab asks the user to run the analysis instead of showing empty charts",
    async (tab) => {
      renderRoute(`/documents/3${tab}`);
      expect(await screen.findByText("This document has not been analysed yet")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Run analysis" })).toBeEnabled();
    },
  );

  it("runs the analysis from any tab and then fills that tab, with elapsed time while waiting", async () => {
    const user = userEvent.setup();
    const run = deferred();
    api.runAnalysis.mockReturnValue(run.promise);
    renderRoute("/documents/3/keywords");
    await user.click(await screen.findByRole("button", { name: "Run analysis" }));
    expect(screen.getByRole("button", { name: "Run analysis" })).toBeDisabled();
    expect(screen.getAllByRole("status").some((s) => /Analysing, 0s/.test(s.textContent))).toBe(true);
    run.resolve(analysis());
    expect(await screen.findByRole("table", { name: "Keyword TF-IDF scores" })).toBeInTheDocument();
    expect(api.runAnalysis).toHaveBeenCalledWith(3);
    expect(screen.queryByText("This document has not been analysed yet")).not.toBeInTheDocument();
  });

  it("shows why a run failed and lets the user try again", async () => {
    const user = userEvent.setup();
    api.runAnalysis.mockRejectedValueOnce(new ApiError("The document contains no analysable words after cleaning.")).mockResolvedValueOnce(analysis());
    renderRoute("/documents/3");
    await user.click(await screen.findByRole("button", { name: "Run analysis" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no analysable words");
    await user.click(screen.getByRole("button", { name: "Run analysis" }));
    expect(await screen.findByText("Document type")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

it("offers 'Run analysis again' in the header once analysed, on every tab", async () => {
  const user = userEvent.setup();
  api.runAnalysis.mockResolvedValue(analysis());
  renderRoute("/documents/3/statistics");
  await user.click(await screen.findByRole("button", { name: "Run analysis again" }));
  expect(api.runAnalysis).toHaveBeenCalledWith(3);
});

describe("overview", () => {
  it("shows type, keywords, summary and reading level", async () => {
    renderRoute("/documents/3");
    expect(await screen.findByText("Notice")).toBeInTheDocument();
    expect(screen.getByText(/95% sure/)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Top keywords" })).toHaveTextContent("library");
    expect(screen.getByText("The library will remain closed on Friday.")).toBeInTheDocument();
    expect(screen.getByText(/Reading level: Plain English/)).toBeInTheDocument();
  });

  it("warns when the prediction is uncertain", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ classification: { label: "assignment", confidence: 0.39, is_confident: false, confidence_threshold: 0.5 } }));
    renderRoute("/documents/3");
    expect(await screen.findByText("The classifier is not sure about this one")).toBeInTheDocument();
    expect(screen.getByText(/probability below 50%/)).toBeInTheDocument();
  });

  it("explains why there is no predicted type or summary", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ classification: null, classification_error: "No trained model was found.", summary: null, summary_error: "The document has no sentences suitable for summarisation." }));
    renderRoute("/documents/3");
    expect(await screen.findByText("No document type was predicted")).toBeInTheDocument();
    expect(screen.getByText("No trained model was found.")).toBeInTheDocument();
    expect(screen.getByText(/no sentences suitable for summarisation/)).toBeInTheDocument();
  });

  it("flags a rough reading-level estimate for short documents", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ readability: { reading_level: "Easy (6th grade)", reliable: false } }));
    renderRoute("/documents/3");
    expect(await screen.findByText(/the estimate is rough/)).toBeInTheDocument();
  });

  it("previews long text and expands it on request", async () => {
    const user = userEvent.setup();
    api.getDocument.mockResolvedValue(doc({ extracted_text: "word ".repeat(2000), char_count: 10000 }));
    renderRoute("/documents/3");
    const button = await screen.findByRole("button", { name: "Show the full text" });
    const pre = button.closest("section").querySelector("pre");
    expect(pre.textContent.length).toBeLessThan(3100);
    await user.click(button);
    expect(pre.textContent.length).toBeGreaterThan(9000);
    expect(screen.getByRole("button", { name: "Show less" })).toBeInTheDocument();
  });

  it("does not offer expansion for short text", async () => {
    renderRoute("/documents/3");
    await screen.findByText("Short extracted text.");
    expect(screen.queryByRole("button", { name: /full text/ })).not.toBeInTheDocument();
  });
});

describe("export tab", () => {
  it("saves the PDF under the name chosen by the server", async () => {
    const user = userEvent.setup();
    const blob = new Blob(["%PDF"]);
    api.exportAnalysis.mockResolvedValue({ blob, filename: "analysis_3_notes.pdf" });
    renderRoute("/documents/3/export");
    await user.click(await screen.findByRole("button", { name: "Download PDF report" }));
    expect(api.exportAnalysis).toHaveBeenCalledWith(3, "pdf");
    expect(saveBlob).toHaveBeenCalledWith(blob, "analysis_3_notes.pdf");
  });

  it("downloads JSON too", async () => {
    const user = userEvent.setup();
    api.exportAnalysis.mockResolvedValue({ blob: new Blob(["{}"]), filename: "analysis_3_notes.json" });
    renderRoute("/documents/3/export");
    await user.click(await screen.findByRole("button", { name: "Download JSON" }));
    expect(api.exportAnalysis).toHaveBeenCalledWith(3, "json");
  });

  it("works even when the document has not been analysed (the server analyses first)", async () => {
    api.getAnalysis.mockResolvedValue(null);
    renderRoute("/documents/3/export");
    expect(await screen.findByRole("button", { name: "Download PDF report" })).toBeEnabled();
  });

  it("disables both buttons while a report is being prepared", async () => {
    const user = userEvent.setup();
    const pending = deferred();
    api.exportAnalysis.mockReturnValue(pending.promise);
    renderRoute("/documents/3/export");
    await user.click(await screen.findByRole("button", { name: "Download PDF report" }));
    expect(screen.getByRole("button", { name: "Preparing PDF" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Download JSON" })).toBeDisabled();
    pending.resolve({ blob: new Blob([]), filename: "x.pdf" });
    expect(await screen.findByRole("button", { name: "Download PDF report" })).toBeEnabled();
  });

  it("reports a failed download", async () => {
    const user = userEvent.setup();
    api.exportAnalysis.mockRejectedValue(new ApiError("Document 3 was not found."));
    renderRoute("/documents/3/export");
    await user.click(await screen.findByRole("button", { name: "Download PDF report" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The report was not downloaded");
    expect(saveBlob).not.toHaveBeenCalled();
  });
});
