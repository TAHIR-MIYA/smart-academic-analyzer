import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../../api/api.js";
import { analysis, comparison, metrics } from "../../test/fixtures.js";
import { defaultApi, renderRoute } from "../../test/harness.jsx";
import { deferred } from "../../test/utils.jsx";

vi.mock("../../api/api.js", async (orig) => (await import("../../test/apiMock.js")).mockApiModule(orig));
beforeEach(() => defaultApi());

const withPre = (over) => analysis({ preprocessing: { ...analysis().preprocessing, ...over } });

describe("preprocessing tab", () => {
  it("lists every cleaning step with how often it was applied", async () => {
    renderRoute("/documents/3/preprocessing");
    const row = (await screen.findByText("Hyphenated line breaks")).closest("tr");
    expect(row).toHaveTextContent("Rejoined words split across lines");
    expect(row).toHaveTextContent("2");
    expect(screen.getByText("URLs").closest("tr")).toHaveTextContent("0");
    expect(screen.getByText(/1,200 characters before, 1,100 after/)).toBeInTheDocument();
  });

  it("gives the word counts at each stage in an accessible table", async () => {
    renderRoute("/documents/3/preprocessing");
    const table = await screen.findByRole("table", { name: "Words and distinct words at each preprocessing stage" });
    expect(within(table).getByText("4. Stop-word removal").closest("tr")).toHaveTextContent("120");
    expect(within(table).getByText("1. Tokenisation").closest("tr")).toHaveTextContent("300");
    expect(screen.getAllByText("5. Lemmatisation").length).toBeGreaterThan(0);
  });

  it("shows the text before and after", async () => {
    renderRoute("/documents/3/preprocessing");
    expect(await screen.findByText("The library will remain closed on Friday.")).toBeInTheDocument();
    expect(screen.getByText("library remain close friday")).toBeInTheDocument();
  });

  it("shows stop words removed and their share", async () => {
    renderRoute("/documents/3/preprocessing");
    expect(await screen.findByText(/52% of the words were stop words/)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Most removed stop words" })).toHaveTextContent("the");
  });

  it("contrasts stemming with lemmatisation", async () => {
    renderRoute("/documents/3/preprocessing");
    const row = (await screen.findByText("studying")).closest("tr");
    expect(row).toHaveTextContent("studi");
    expect(row).toHaveTextContent("study");
    expect(row).toHaveTextContent("VERB");
  });

  it("says so when the two methods never disagree", async () => {
    api.getAnalysis.mockResolvedValue(withPre({ stem_vs_lemma: [] }));
    renderRoute("/documents/3/preprocessing");
    expect(await screen.findByText(/No frequent word in this document/)).toBeInTheDocument();
  });

  it("warns when a very long document was cut short", async () => {
    api.getAnalysis.mockResolvedValue(withPre({ warnings: ["The document was very long; only the first part was analysed."] }));
    renderRoute("/documents/3/preprocessing");
    expect(await screen.findByText(/only the first part was analysed/)).toBeInTheDocument();
  });
});

describe("keywords tab", () => {
  it("shows scores in a table and explains where IDF comes from", async () => {
    renderRoute("/documents/3/keywords");
    await screen.findByText(/IDF computed over the 12 sentences/);
    const row = screen.getAllByRole("row").find((r) => r.textContent.includes("0.0556")); // the visible table, not the chart's hidden one
    expect(row).toHaveTextContent("library");
    expect(row).toHaveTextContent("5");
    expect(row).toHaveTextContent("0.1167");
    expect(screen.getByText(/IDF computed over the 12 sentences of this document/)).toBeInTheDocument();
    expect(screen.getByText(/score = tf x idf/)).toBeInTheDocument();
    expect(screen.getByText(/Only noun, propn, adj words are considered/)).toBeInTheDocument();
  });

  it("lets the user choose how many keywords to show", async () => {
    const user = userEvent.setup();
    renderRoute("/documents/3/keywords");
    const group = await screen.findByRole("group", { name: "Number of keywords" });
    expect(within(group).getByRole("button", { name: "15" })).toHaveAttribute("aria-pressed", "true");
    await user.click(within(group).getByRole("button", { name: "10" }));
    expect(within(group).getByRole("button", { name: "10" })).toHaveAttribute("aria-pressed", "true");
  });

  it("warns when the ranking is by frequency only", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ keywords: { ...analysis().keywords, idf_mode: "term_frequency", idf_description: "Only 3 sentence(s) with content words; at least 5 are needed." } }));
    renderRoute("/documents/3/keywords");
    expect(await screen.findByText("Ranked by frequency only")).toBeInTheDocument();
  });

  it("switches between unigrams, bigrams and trigrams", async () => {
    const user = userEvent.setup();
    renderRoute("/documents/3/keywords");
    expect(await screen.findByRole("table", { name: "Bigrams by frequency" })).toHaveTextContent("library close");
    await user.click(screen.getByRole("button", { name: "Trigrams" }));
    expect(screen.getByRole("table", { name: "Trigrams by frequency" })).toHaveTextContent("library close friday");
    expect(screen.getByText(/100 trigrams in total, 95 distinct/)).toBeInTheDocument();
    expect(screen.getByText(/stop words removed first/)).toBeInTheDocument();
  });

  it("explains when there are no word groups", async () => {
    const levels = analysis().ngrams.levels.map((l) => (l.n === 3 ? { ...l, top: [], total: 0, distinct: 0 } : l));
    api.getAnalysis.mockResolvedValue(analysis({ ngrams: { ...analysis().ngrams, levels } }));
    const user = userEvent.setup();
    renderRoute("/documents/3/keywords");
    await user.click(await screen.findByRole("button", { name: "Trigrams" }));
    expect(screen.getByText(/too short to contain trigrams/)).toBeInTheDocument();
  });
});

describe("entities tab", () => {
  it("summarises the mentions and warns that labels can be wrong", async () => {
    renderRoute("/documents/3/entities");
    expect(await screen.findByText(/6 mentions of 4 distinct entities, found by en_core_web_sm/)).toBeInTheDocument();
    expect(screen.getByText("Labels can be wrong for academic text")).toBeInTheDocument();
  });

  it("lists each type with its examples and counts", async () => {
    renderRoute("/documents/3/entities");
    const org = await screen.findByRole("list", { name: "ORG examples" });
    expect(org).toHaveTextContent("Princeton University");
    expect(org).toHaveTextContent("3");
    expect(screen.getByText("Companies, agencies, institutions, etc.")).toBeInTheDocument();
  });

  it("filters by entity type", async () => {
    const user = userEvent.setup();
    renderRoute("/documents/3/entities");
    const filter = await screen.findByRole("group", { name: "Filter by entity type" });
    await user.click(within(filter).getByRole("button", { name: "DATE" }));
    expect(screen.getByRole("list", { name: "DATE examples" })).toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "ORG examples" })).not.toBeInTheDocument();
    await user.click(within(filter).getByRole("button", { name: "All types" }));
    expect(screen.getByRole("list", { name: "ORG examples" })).toBeInTheDocument();
  });

  it("says so when no entities were found", async () => {
    api.getAnalysis.mockResolvedValue(analysis({ entities: { model: "en_core_web_sm", total_entities: 0, unique_entities: 0, groups: [] } }));
    renderRoute("/documents/3/entities");
    expect(await screen.findByText(/No people, organisations, places, dates/)).toBeInTheDocument();
  });
});
