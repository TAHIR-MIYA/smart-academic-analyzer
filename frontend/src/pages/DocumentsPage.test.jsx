import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../api/api.js";
import { doc } from "../test/fixtures.js";
import { renderAt } from "../test/utils.jsx";
import DocumentsPage from "./DocumentsPage.jsx";

vi.mock("../api/api.js", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, api: { listDocuments: vi.fn(), deleteDocument: vi.fn() } };
});

const two = () => [doc({ id: 1, original_filename: "a.txt", analyzed: true }), doc({ id: 2, original_filename: "b.pdf", file_type: "pdf", analyzed: false })];
beforeEach(() => vi.resetAllMocks());

it("lists documents with type, words and analysis status", async () => {
  api.listDocuments.mockResolvedValue(two());
  renderAt(<DocumentsPage />);
  const rowA = (await screen.findByRole("link", { name: "a.txt" })).closest("tr");
  expect(rowA).toHaveTextContent("TXT");
  expect(rowA).toHaveTextContent("Analysed");
  expect(within(screen.getByRole("link", { name: "b.pdf" }).closest("tr")).getByText("Not analysed")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "a.txt" })).toHaveAttribute("href", "/documents/1");
});

it("invites an upload when the list is empty", async () => {
  api.listDocuments.mockResolvedValue([]);
  renderAt(<DocumentsPage />);
  expect(await screen.findByText("No documents yet")).toBeInTheDocument();
});

describe("deleting", () => {
  it("asks for confirmation, then deletes and refreshes the list", async () => {
    const user = userEvent.setup();
    api.listDocuments.mockResolvedValueOnce(two()).mockResolvedValueOnce([two()[1]]);
    api.deleteDocument.mockResolvedValue(undefined);
    renderAt(<DocumentsPage />);
    await user.click(await screen.findByRole("button", { name: "Delete a.txt" }));
    expect(api.deleteDocument).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Delete a.txt" })); // now the confirming button
    expect(api.deleteDocument).toHaveBeenCalledWith(1);
    await screen.findByRole("link", { name: "b.pdf" });
    expect(screen.queryByRole("link", { name: "a.txt" })).not.toBeInTheDocument();
  });

  it("lets the user back out", async () => {
    const user = userEvent.setup();
    api.listDocuments.mockResolvedValue(two());
    renderAt(<DocumentsPage />);
    await user.click(await screen.findByRole("button", { name: "Delete a.txt" }));
    await user.click(screen.getByRole("button", { name: "Keep" }));
    expect(api.deleteDocument).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Delete a.txt" })).toBeInTheDocument();
  });

  it("reports a failed delete and keeps the document", async () => {
    const user = userEvent.setup();
    api.listDocuments.mockResolvedValue(two());
    api.deleteDocument.mockRejectedValue(new ApiError("Document 1 was not found.", { status: 404 }));
    renderAt(<DocumentsPage />);
    await user.click(await screen.findByRole("button", { name: "Delete a.txt" }));
    await user.click(screen.getByRole("button", { name: "Delete a.txt" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The document was not deleted");
    expect(screen.getByRole("link", { name: "a.txt" })).toBeInTheDocument();
  });
});

it("shows the error when the list cannot be loaded", async () => {
  api.listDocuments.mockRejectedValue(new ApiError("Cannot reach the API."));
  renderAt(<DocumentsPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach the API.");
});
