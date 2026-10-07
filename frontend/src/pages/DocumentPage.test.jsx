import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, saveBlob } from "../api/api.js";
import { analysis, doc } from "../test/fixtures.js";
import { deferred, renderAt } from "../test/utils.jsx";
import DocumentPage from "./DocumentPage.jsx";

vi.mock("../api/api.js", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, saveBlob: vi.fn(), api: { getDocument: vi.fn(), getAnalysis: vi.fn(), runAnalysis: vi.fn(), exportAnalysis: vi.fn() } };
});

const open = () => renderAt(<DocumentPage />, { path: "/documents/:id", route: "/documents/3" });
beforeEach(() => {
  vi.resetAllMocks();
  api.getDocument.mockResolvedValue(doc());
  api.getAnalysis.mockResolvedValue(null);
});

describe("document details", () => {
  it("describes the document in one plain sentence", async () => {
    api.getDocument.mockResolvedValue(doc({ file_type: "pdf", page_count: 3, size_bytes: 2048, word_count: 1234 }));
    open();
    expect(await screen.findByRole("heading", { name: "notes.txt" })).toBeInTheDocument();
    expect(screen.getByText(/PDF file, 2.0 KB, 3 pages, 1,234 words\. Added 5 Oct 2026\./)).toBeInTheDocument();
  });

  it("shows extraction warnings", async () => {
    api.getDocument.mockResolvedValue(doc({ warnings: ["PDF has 400 pages; only the first 300 were processed."] }));
    open();
    expect(await screen.findByText(/only the first 300 were processed/)).toBeInTheDocument();
  });

  it("previews long text and expands it on request", async () => {
    const user = userEvent.setup();
    api.getDocument.mockResolvedValue(doc({ extracted_text: "word ".repeat(2000), char_count: 10000 }));
    open();
    const pre = (await screen.findByRole("button", { name: "Show the full text" })).closest("section").querySelector("pre");
    expect(pre.textContent.length).toBeLessThan(3100);
    await user.click(screen.getByRole("button", { name: "Show the full text" }));
    expect(pre.textContent.length).toBeGreaterThan(9000);
    expect(screen.getByRole("button", { name: "Show less" })).toBeInTheDocument();
  });

  it("does not offer expansion for short text", async () => {
    open();
    await screen.findByText("Short extracted text.");
    expect(screen.queryByRole("button", { name: /full text/ })).not.toBeInTheDocument();
  });

  it("explains a missing document", async () => {
    api.getDocument.mockRejectedValue(new ApiError("Document 3 was not found.", { status: 404 }));
    open();
    expect(await screen.findByText("Document not found")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to documents" })).toHaveAttribute("href", "/documents");
  });

  it("shows other load errors", async () => {
    api.getDocument.mockRejectedValue(new ApiError("Cannot reach the API."));
    open();
    expect(await screen.findByText("The document could not be loaded")).toBeInTheDocument();
  });
});

describe("analysis", () => {
  it("offers to run the analysis when none is saved", async () => {
    open();
    expect(await screen.findByText("Not analysed yet.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run analysis" })).toBeInTheDocument();
  });

  it("runs the analysis, shows elapsed time, then the result", async () => {
    const user = userEvent.setup();
    const run = deferred();
    api.runAnalysis.mockReturnValue(run.promise);
    open();
    await user.click(await screen.findByRole("button", { name: "Run analysis" }));
    expect(screen.getByRole("button", { name: "Run analysis" })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/Analysing, 0s/);
    run.resolve(analysis());
    expect(await screen.findByText("Notice")).toBeInTheDocument();
    expect(api.runAnalysis).toHaveBeenCalledWith(3);
    expect(screen.getByRole("button", { name: "Run analysis again" })).toBeEnabled();
  });

  it("shows a saved analysis straight away: type, keywords, summary, reading level", async () => {
    api.getAnalysis.mockResolvedValue(analysis());
    open();
    expect(await screen.findByText("Notice")).toBeInTheDocument();
    expect(screen.getByText(/95% sure/)).toBeInTheDocument();
    const keywords = screen.getByRole("list", { name: "Top keywords" });
    expect(keywords).toHaveTextContent("library");
    expect(keywords).toHaveTextContent("student");
    expect(screen.getByText("The library will remain closed on Friday.")).toBeInTheDocument();
    expect(screen.getByText(/Reading level: Plain English/)).toBeInTheDocument();
  });

  it("warns when the prediction is uncertain", async () => {
    api.getAnalysis.mockResolvedValue(
      analysis({ classification: { label: "assignment", confidence: 0.39, is_confident: false, confidence_threshold: 0.5 } }),
    );
    open();
    expect(await screen.findByText("The classifier is not sure about this one")).toBeInTheDocument();
    expect(screen.getByText(/probability below 50%/)).toBeInTheDocument();
  });

  it("explains why there is no predicted type or summary", async () => {
    api.getAnalysis.mockResolvedValue(
      analysis({ classification: null, classification_error: "No trained model was found.", summary: null, summary_error: "The document has no sentences suitable for summarisation." }),
    );
    open();
    expect(await screen.findByText("No document type was predicted")).toBeInTheDocument();
    expect(screen.getByText("No trained model was found.")).toBeInTheDocument();
    expect(screen.getByText(/no sentences suitable for summarisation/)).toBeInTheDocument();
  });

  it("flags a rough reading-level estimate for short documents", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ readability: { reading_level: "Easy (6th grade)", reliable: false } }));
    open();
    expect(await screen.findByText(/the estimate is rough/)).toBeInTheDocument();
  });

  it("shows why a run failed and lets the user try again", async () => {
    const user = userEvent.setup();
    api.runAnalysis.mockRejectedValueOnce(new ApiError("The document contains no analysable words after cleaning.")).mockResolvedValueOnce(analysis());
    open();
    await user.click(await screen.findByRole("button", { name: "Run analysis" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no analysable words");
    await user.click(screen.getByRole("button", { name: "Run analysis" }));
    expect(await screen.findByText("Notice")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("report download", () => {
  it("saves the PDF under the name chosen by the server", async () => {
    const user = userEvent.setup();
    const blob = new Blob(["%PDF"]);
    api.exportAnalysis.mockResolvedValue({ blob, filename: "analysis_3_notes.pdf" });
    open();
    await user.click(await screen.findByRole("button", { name: "Download PDF report" }));
    expect(api.exportAnalysis).toHaveBeenCalledWith(3, "pdf");
    expect(saveBlob).toHaveBeenCalledWith(blob, "analysis_3_notes.pdf");
  });

  it("downloads JSON too", async () => {
    const user = userEvent.setup();
    api.exportAnalysis.mockResolvedValue({ blob: new Blob(["{}"]), filename: "analysis_3_notes.json" });
    open();
    await user.click(await screen.findByRole("button", { name: "Download JSON" }));
    expect(api.exportAnalysis).toHaveBeenCalledWith(3, "json");
  });

  it("disables both buttons while a report is being prepared", async () => {
    const user = userEvent.setup();
    const pending = deferred();
    api.exportAnalysis.mockReturnValue(pending.promise);
    open();
    await user.click(await screen.findByRole("button", { name: "Download PDF report" }));
    expect(screen.getByRole("button", { name: "Preparing PDF" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Download JSON" })).toBeDisabled();
    pending.resolve({ blob: new Blob([]), filename: "x.pdf" });
    expect(await screen.findByRole("button", { name: "Download PDF report" })).toBeEnabled();
  });

  it("reports a failed download", async () => {
    const user = userEvent.setup();
    api.exportAnalysis.mockRejectedValue(new ApiError("Document 3 was not found."));
    open();
    await user.click(await screen.findByRole("button", { name: "Download PDF report" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The report was not downloaded");
    expect(saveBlob).not.toHaveBeenCalled();
  });
});
