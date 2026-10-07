import { AxiosError } from "axios";
import { afterEach, describe, expect, it } from "vitest";
import { ApiError, api, http, toApiError } from "./api.js";

const original = http.defaults.adapter;
afterEach(() => {
  http.defaults.adapter = original;
});

/** Replace the network with a function that returns or throws what a real server would. */
function respondWith(status, data, headers = {}) {
  http.defaults.adapter = async (config) => {
    const response = { data, status, statusText: "", headers, config };
    if (status >= 400) throw new AxiosError("failed", "ERR_BAD_REQUEST", config, {}, response);
    return response;
  };
}

describe("error translation", () => {
  it("uses the API's own message, code and details", async () => {
    respondWith(413, { error: { code: "file_too_large", message: "File exceeds the maximum allowed size.", details: null } });
    const err = await api.getDocument(1).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ message: "File exceeds the maximum allowed size.", code: "file_too_large", status: 413 });
  });

  it("turns FastAPI validation errors into one readable sentence", async () => {
    respondWith(422, { detail: [{ loc: ["query", "sentences"], msg: "Input should be greater than or equal to 1" }] });
    const err = await api.getDocument(1).catch((e) => e);
    expect(err.message).toBe("query.sentences: Input should be greater than or equal to 1");
    expect(err.code).toBe("validation_error");
  });

  it("explains how to start the backend when it cannot be reached", async () => {
    http.defaults.adapter = async (config) => {
      throw new AxiosError("Network Error", "ERR_NETWORK", config, {});
    };
    const err = await api.health().catch((e) => e);
    expect(err.code).toBe("network_error");
    expect(err.message).toContain("uvicorn app.main:app --reload");
  });

  it("explains timeouts", async () => {
    http.defaults.adapter = async (config) => {
      throw new AxiosError("timeout", "ECONNABORTED", config, {});
    };
    expect((await api.health().catch((e) => e)).code).toBe("timeout");
  });

  it("falls back to the status code for unexpected bodies", async () => {
    respondWith(500, "<html>boom</html>");
    expect((await api.health().catch((e) => e)).message).toBe("The server returned an error (500).");
  });

  it("reads JSON error bodies that arrive as a Blob (failed downloads)", async () => {
    const body = new Blob([JSON.stringify({ error: { code: "not_found", message: "Document 9 was not found." } })]);
    const err = await toApiError(new AxiosError("x", "ERR", {}, {}, { status: 404, data: body, headers: {} }));
    expect(err).toMatchObject({ message: "Document 9 was not found.", code: "not_found" });
  });
});

describe("getAnalysis", () => {
  it("returns the saved analysis", async () => {
    respondWith(200, { schema_version: 1 });
    expect(await api.getAnalysis(1)).toEqual({ schema_version: 1 });
  });
  it("returns null when nothing was saved yet or it is outdated", async () => {
    respondWith(404, { error: { code: "not_found", message: "not analysed" } });
    expect(await api.getAnalysis(1)).toBeNull();
    respondWith(409, { error: { code: "analysis_outdated", message: "old" } });
    expect(await api.getAnalysis(1)).toBeNull();
  });
  it("still throws real failures", async () => {
    respondWith(500, { error: { code: "internal_error", message: "boom" } });
    await expect(api.getAnalysis(1)).rejects.toMatchObject({ code: "internal_error" });
  });
});

describe("exportAnalysis", () => {
  it("returns the blob and the file name chosen by the server", async () => {
    respondWith(200, new Blob(["pdf"]), { "content-disposition": 'attachment; filename="analysis_3_notes.pdf"' });
    const { blob, filename } = await api.exportAnalysis(3, "pdf");
    expect(filename).toBe("analysis_3_notes.pdf");
    expect(blob).toBeInstanceOf(Blob);
  });
  it("invents a sensible name if the header is missing", async () => {
    respondWith(200, new Blob(["{}"]));
    expect((await api.exportAnalysis(3, "json")).filename).toBe("analysis_3.json");
  });
  it("sends the format as a query parameter", async () => {
    let seen;
    http.defaults.adapter = async (config) => {
      seen = config;
      return { data: new Blob([]), status: 200, headers: {}, config };
    };
    await api.exportAnalysis(5, "json");
    expect(seen.url).toBe("/api/export/5");
    expect(seen.params).toEqual({ format: "json" });
  });
});

describe("uploadDocument", () => {
  it("posts multipart form data and reports progress", async () => {
    const progress = [];
    http.defaults.adapter = async (config) => {
      config.onUploadProgress({ loaded: 50, total: 200 });
      config.onUploadProgress({ loaded: 200, total: 200 });
      return { data: { id: 8 }, status: 201, headers: {}, config };
    };
    const doc = await api.uploadDocument(new File(["hello world text"], "a.txt"), (p) => progress.push(p));
    expect(doc.id).toBe(8);
    expect(progress).toEqual([25, 100]);
  });
});
