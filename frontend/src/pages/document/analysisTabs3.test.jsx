import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../../api/api.js";
import { analysis, comparison, metrics } from "../../test/fixtures.js";
import { defaultApi, renderRoute } from "../../test/harness.jsx";
import { deferred } from "../../test/utils.jsx";

vi.mock("../../api/api.js", async (orig) => (await import("../../test/apiMock.js")).mockApiModule(orig));
beforeEach(() => defaultApi());

describe("similarity tab: subject profiles", () => {
  it("names the closest subject and the words behind the match", async () => {
    renderRoute("/documents/3/similarity");
    expect(await screen.findByText("Database Management Systems", { selector: "strong" })).toHaveTextContent("Database Management Systems");
    expect(screen.getByText(/cosine 0\.23/)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Shared words" })).toHaveTextContent("redundancy");
    const table = screen.getByRole("table", { name: "Cosine similarity to each topic profile" });
    expect(within(table).getByText("Data Structures").closest("tr")).toHaveTextContent("0.07");
  });

  it("says so honestly when nothing matches", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ topic_similarity: { ...analysis().topic_similarity, best_topic: null, best_similarity: 0.02, is_weak_match: true, note: "Weak match: no topic profile resembles this document." } }));
    renderRoute("/documents/3/similarity");
    expect(await screen.findByText(/No strong match\. The closest profile scores only 0\.02/)).toBeInTheDocument();
    expect(screen.getByText(/Weak match: no topic profile resembles/)).toBeInTheDocument();
  });

  it("explains when topic profiles are unavailable", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ topic_similarity: null, topic_similarity_error: "No topic profile files (.txt) found." }));
    renderRoute("/documents/3/similarity");
    expect(await screen.findByText("Topic similarity is not available")).toBeInTheDocument();
  });
});

describe("similarity tab: compare with another document", () => {
  const choose = async (user) => {
    await user.selectOptions(await screen.findByLabelText("Compare with"), "other.txt");
  };

  it("lists the other documents but not this one", async () => {
    renderRoute("/documents/3/similarity");
    const select = await screen.findByLabelText("Compare with");
    expect(within(select).getAllByRole("option").map((o) => o.textContent)).toEqual(["Choose a document", "other.txt"]);
  });

  it("only allows comparing once a document is chosen", async () => {
    const user = userEvent.setup();
    renderRoute("/documents/3/similarity");
    expect(await screen.findByRole("button", { name: "Compare documents" })).toBeDisabled();
    await choose(user);
    expect(screen.getByRole("button", { name: "Compare documents" })).toBeEnabled();
  });

  it("shows the scores, shared words and the near-copied sentences side by side", async () => {
    const user = userEvent.setup();
    api.compareDocuments.mockResolvedValue(comparison());
    renderRoute("/documents/3/similarity");
    await choose(user);
    await user.click(screen.getByRole("button", { name: "Compare documents" }));
    expect(api.compareDocuments).toHaveBeenCalledWith(3, 4);
    expect(await screen.findByText("0.62")).toBeInTheDocument();
    expect(screen.getByText("31%")).toBeInTheDocument();
    expect(screen.getByText("Related content")).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Shared terms" })).toHaveTextContent("library");
    expect(screen.getByText("97% similar")).toBeInTheDocument();
    expect(screen.getByText("The library will remain closed on Friday for stock checks.")).toBeInTheDocument();
    expect(screen.getByText(/other\.txt, sentence 4/)).toBeInTheDocument();
    expect(screen.getByText(/measures shared wording, not shared subject/)).toBeInTheDocument();
  });

  it("explains when no sentences match", async () => {
    const user = userEvent.setup();
    api.compareDocuments.mockResolvedValue(comparison({ similar_sentence_pairs: [], shared_terms: [] }));
    renderRoute("/documents/3/similarity");
    await choose(user);
    await user.click(screen.getByRole("button", { name: "Compare documents" }));
    expect(await screen.findByText(/No sentence in one document is close enough/)).toBeInTheDocument();
  });

  it("shows a failed comparison", async () => {
    const user = userEvent.setup();
    api.compareDocuments.mockRejectedValue(new ApiError("Document 4 was not found.", { status: 404 }));
    renderRoute("/documents/3/similarity");
    await choose(user);
    await user.click(screen.getByRole("button", { name: "Compare documents" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Document 4 was not found.");
  });

  it("asks for a second document when there is only one", async () => {
    api.listDocuments.mockResolvedValue([{ id: 3, original_filename: "notes.txt" }]);
    renderRoute("/documents/3/similarity");
    expect(await screen.findByText(/Upload a second document/)).toBeInTheDocument();
  });

  it("shows a spinner while comparing", async () => {
    const user = userEvent.setup();
    const pending = deferred();
    api.compareDocuments.mockReturnValue(pending.promise);
    renderRoute("/documents/3/similarity");
    await choose(user);
    await user.click(screen.getByRole("button", { name: "Compare documents" }));
    expect(await screen.findByText("Comparing")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Compare documents" })).toBeDisabled();
  });
});

describe("statistics tab", () => {
  it("lists the text statistics", async () => {
    renderRoute("/documents/3/statistics");
    const fact = async (label) => (await screen.findByText(label, { selector: "dt" })).closest("div");
    expect(await fact("Characters")).toHaveTextContent("1,200");
    expect(await fact("Sentences")).toHaveTextContent("12");
    expect(await fact("Average sentence length")).toHaveTextContent("20.8 words");
    expect(await fact("Longest sentence")).toHaveTextContent("38 words");
    expect(await fact("Reading time")).toHaveTextContent("1.3 min");
  });

  it("charts sentence and word lengths with exact numbers available", async () => {
    renderRoute("/documents/3/statistics");
    const t = await screen.findByRole("table", { name: "Number of sentences by length in words" });
    expect(within(t).getByText("11-20").closest("tr")).toHaveTextContent("6");
    expect(screen.getByRole("table", { name: "Number of words by length in letters" })).toBeInTheDocument();
  });

  it("shows readability scores with their formulas", async () => {
    renderRoute("/documents/3/statistics");
    const row = (await screen.findByText("Flesch Reading Ease")).closest("tr");
    expect(row).toHaveTextContent("62.5");
    expect(row).toHaveTextContent("Plain English");
    expect(row).toHaveTextContent("206.835 - 1.015");
    expect(screen.getByText(/Based on 250 words, 12 sentences and 380 syllables \(20 words have three or more\)/)).toBeInTheDocument();
  });

  it("warns that readability and vocabulary scores for short texts are rough", async () => {
    api.getAnalysis.mockResolvedValue(analysis({
      readability: { ...analysis().readability, reliable: false, warning: "Only 40 words in 2 sentence(s): readability formulas need at least 100 words." },
      vocabulary: { ...analysis().vocabulary, reliable: false, warning: "Only 40 words: diversity measures depend strongly on length." },
    }));
    renderRoute("/documents/3/statistics");
    expect(await screen.findByText(/Only 40 words in 2 sentence/)).toBeInTheDocument();
    expect(screen.getByText(/diversity measures depend strongly on length/)).toBeInTheDocument();
    expect(screen.getAllByText("Treat these scores as rough").length).toBe(1);
    expect(screen.getAllByText("Treat these measures as rough").length).toBe(1);
  });

  it("describes each vocabulary measure in plain words", async () => {
    renderRoute("/documents/3/statistics");
    const row = (await screen.findByText("MATTR (window 50)")).closest("div");
    expect(row).toHaveTextContent("0.79");
    expect(row).toHaveTextContent("Average TTR over windows of 50 words.");
    expect(screen.getByText(/250 alphabetic words of two or more letters, 140 distinct, 120 distinct after lemmatisation/)).toBeInTheDocument();
  });

  it("shows the word-frequency data behind the rank chart", async () => {
    renderRoute("/documents/3/statistics");
    const t = await screen.findByRole("table", { name: "Most frequent words by rank" });
    expect(within(t).getByText("library").closest("tr")).toHaveTextContent("2");
    expect(screen.getByText(/most frequent words are far more frequent than the rest/)).toBeInTheDocument();
  });
});
