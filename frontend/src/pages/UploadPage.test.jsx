import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "../api/api.js";
import { analysis, health } from "../test/fixtures.js";
import { deferred, renderAt } from "../test/utils.jsx";
import UploadPage from "./UploadPage.jsx";

vi.mock("../api/api.js", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, api: { health: vi.fn(), uploadDocument: vi.fn(), runAnalysis: vi.fn() } };
});

// applyAccept:false lets the tests offer a disallowed file, as a drag-and-drop would.
const setup = () => userEvent.setup({ applyAccept: false });
const txt = (name = "notes.txt", body = "Some text for the document.") => new File([body], name, { type: "text/plain" });
const pick = async (user, ...files) => user.upload(screen.getByLabelText("Files to upload"), files);

beforeEach(() => {
  vi.resetAllMocks();
  api.health.mockResolvedValue(health({ max_upload_mb: 1 }));
});

describe("choosing files", () => {
  it("shows the limit once the API has answered", async () => {
    renderAt(<UploadPage />);
    expect(await screen.findByText(/up to 1 MB each/)).toBeInTheDocument();
  });

  it("explains an unsupported file type and never uploads it", async () => {
    const user = setup();
    renderAt(<UploadPage />);
    await screen.findByText(/up to 1 MB/);
    await pick(user, new File(["x"], "virus.exe"));
    expect(await screen.findByRole("alert")).toHaveTextContent("virus.exe is not a supported file type");
    expect(screen.getByText("Not uploaded")).toBeInTheDocument();
    expect(api.uploadDocument).not.toHaveBeenCalled();
  });

  it("explains an oversized file", async () => {
    const user = setup();
    renderAt(<UploadPage />);
    await screen.findByText(/up to 1 MB/);
    await pick(user, txt("big.txt", "x".repeat(1_200_000)));
    expect(await screen.findByRole("alert")).toHaveTextContent("The limit is 1 MB");
    expect(api.uploadDocument).not.toHaveBeenCalled();
  });

  it("rejects an empty file", async () => {
    const user = setup();
    renderAt(<UploadPage />);
    await pick(user, txt("empty.txt", ""));
    expect(await screen.findByRole("alert")).toHaveTextContent("empty.txt is empty.");
  });

  it("accepts files dropped onto the drop area", async () => {
    api.uploadDocument.mockResolvedValue({ id: 4 });
    api.runAnalysis.mockResolvedValue(analysis());
    renderAt(<UploadPage />);
    const zone = screen.getByText("Drop files here").closest("div");
    fireEvent.drop(zone, { dataTransfer: { files: [txt("dropped.txt")] } });
    expect(await screen.findByText("dropped.txt")).toBeInTheDocument();
    await waitFor(() => expect(api.uploadDocument).toHaveBeenCalledTimes(1));
  });
});

describe("uploading", () => {
  it("shows real progress, then the extraction step, then the predicted class", async () => {
    const user = setup();
    const upload = deferred();
    const analyse = deferred();
    let report;
    api.uploadDocument.mockImplementation((_file, onProgress) => {
      report = onProgress;
      return upload.promise;
    });
    api.runAnalysis.mockReturnValue(analyse.promise);
    renderAt(<UploadPage />);
    await pick(user, txt());

    await waitFor(() => expect(api.uploadDocument).toHaveBeenCalled());
    report(40);
    expect(await screen.findByRole("progressbar", { name: /Uploading notes.txt/ })).toHaveAttribute("aria-valuenow", "40");
    report(100);
    expect(await screen.findByText("Extracting text")).toBeInTheDocument();

    upload.resolve({ id: 7 });
    expect(await screen.findByText("Analysing")).toBeInTheDocument();
    analyse.resolve(analysis());
    expect(await screen.findByText("Notice")).toBeInTheDocument();
    expect(screen.getByText(/95% sure/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute("href", "/documents/7");
    expect(api.runAnalysis).toHaveBeenCalledWith(7);
  });

  it("marks a low-confidence prediction as uncertain", async () => {
    const user = setup();
    api.uploadDocument.mockResolvedValue({ id: 1 });
    api.runAnalysis.mockResolvedValue(
      analysis({ classification: { label: "assignment", confidence: 0.39, is_confident: false, confidence_threshold: 0.5 } }),
    );
    renderAt(<UploadPage />);
    await pick(user, txt());
    expect(await screen.findByText(/39% sure, uncertain/)).toBeInTheDocument();
  });

  it("shows the API's own message when the upload is refused", async () => {
    const user = setup();
    api.uploadDocument.mockRejectedValue(new ApiError("The PDF is password-protected and cannot be read.", { status: 422 }));
    renderAt(<UploadPage />);
    await pick(user, txt("locked.txt"));
    expect(await screen.findByRole("alert")).toHaveTextContent("The PDF is password-protected");
    expect(screen.getByText("Not uploaded")).toBeInTheDocument();
    expect(api.runAnalysis).not.toHaveBeenCalled();
  });

  it("keeps the upload when only the analysis fails, and lets the user retry", async () => {
    const user = setup();
    api.uploadDocument.mockResolvedValue({ id: 5 });
    api.runAnalysis.mockRejectedValueOnce(new ApiError("The spaCy model is not installed.")).mockResolvedValueOnce(analysis());
    renderAt(<UploadPage />);
    await pick(user, txt());
    expect(await screen.findByRole("alert")).toHaveTextContent("Uploaded, but the analysis failed: The spaCy model is not installed.");
    expect(screen.getByRole("link", { name: "Open" })).toHaveAttribute("href", "/documents/5");
    await user.click(screen.getByRole("button", { name: "Analyse" }));
    expect(await screen.findByText("Notice")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not analyse automatically when the option is switched off", async () => {
    const user = setup();
    api.uploadDocument.mockResolvedValue({ id: 2 });
    api.runAnalysis.mockResolvedValue(analysis());
    renderAt(<UploadPage />);
    await user.click(screen.getByLabelText(/Analyse each file as soon as it is uploaded/));
    await pick(user, txt());
    await screen.findByText("Uploaded");
    expect(api.runAnalysis).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Analyse" }));
    expect(await screen.findByText("Notice")).toBeInTheDocument();
  });

  it("processes several files one at a time", async () => {
    const user = setup();
    const first = deferred();
    api.uploadDocument.mockReturnValueOnce(first.promise).mockResolvedValueOnce({ id: 2 });
    api.runAnalysis.mockResolvedValue(analysis());
    renderAt(<UploadPage />);
    await pick(user, txt("one.txt"), txt("two.txt"));

    await waitFor(() => expect(api.uploadDocument).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Waiting")).toBeInTheDocument(); // second file is queued
    first.resolve({ id: 1 });
    await waitFor(() => expect(api.uploadDocument).toHaveBeenCalledTimes(2));
    expect(api.uploadDocument.mock.calls.map((c) => c[0].name)).toEqual(["one.txt", "two.txt"]);
  });

  it("clears finished files from the list", async () => {
    const user = setup();
    api.uploadDocument.mockResolvedValue({ id: 1 });
    api.runAnalysis.mockResolvedValue(analysis());
    renderAt(<UploadPage />);
    await pick(user, txt());
    await screen.findByText("Notice");
    await user.click(screen.getByRole("button", { name: "Clear finished files" }));
    expect(screen.queryByText("notes.txt")).not.toBeInTheDocument();
  });
});

it("lists what happens to a document, in order", () => {
  renderAt(<UploadPage />);
  const steps = screen.getAllByRole("listitem").filter((li) => li.closest("ol"));
  expect(steps).toHaveLength(7);
  expect(steps[0]).toHaveTextContent("The text is extracted from your file.");
});
