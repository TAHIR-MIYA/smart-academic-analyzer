import axios from "axios";

export const http = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || "", timeout: 120_000 });

export class ApiError extends Error {
  constructor(message, { status = null, code = "error", details = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function readBlobText(blob) {
  if (typeof blob.text === "function") return blob.text();
  return new Promise((resolve, reject) => {  // very old browsers and jsdom
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(blob);
  });
}

/** Turn any axios failure into an ApiError with a message that tells the user what to do. */
export async function toApiError(err) {
  if (err instanceof ApiError) return err;
  if (err.response) {
    const { status } = err.response;
    let body = err.response.data;
    if (typeof Blob !== "undefined" && body instanceof Blob) {
      try {
        body = JSON.parse(await readBlobText(body));
      } catch {
        body = null;
      }
    }
    if (body?.error) {
      return new ApiError(body.error.message, { status, code: body.error.code, details: body.error.details });
    }
    if (Array.isArray(body?.detail)) {
      const first = body.detail[0];
      const where = Array.isArray(first?.loc) ? first.loc.filter((p) => p !== "body").join(".") : "";
      return new ApiError(`${where ? `${where}: ` : ""}${first?.msg ?? "The request was not valid."}`, {
        status,
        code: "validation_error",
      });
    }
    return new ApiError(`The server returned an error (${status}).`, { status });
  }
  if (err.code === "ECONNABORTED") {
    return new ApiError("The request took too long. Try again, or upload a smaller document.", { code: "timeout" });
  }
  if (err.request) {
    return new ApiError(
      "Cannot reach the API. Start the backend with: uvicorn app.main:app --reload",
      { code: "network_error" },
    );
  }
  return new ApiError(err.message || "Something went wrong.");
}

http.interceptors.response.use((r) => r, async (err) => Promise.reject(await toApiError(err)));

const data = (response) => response.data;

export const api = {
  health: () => http.get("/api/health").then(data),
  dashboard: () => http.get("/api/dashboard/summary").then(data),
  modelMetrics: () => http.get("/api/model/metrics").then(data),

  listDocuments: () => http.get("/api/documents").then(data),
  getDocument: (id) => http.get(`/api/documents/${id}`).then(data),
  deleteDocument: (id) => http.delete(`/api/documents/${id}`).then(data),
  uploadDocument: (file, onProgress) => {
    const form = new FormData();
    form.append("file", file);
    return http
      .post("/api/documents/upload", form, {
        onUploadProgress: (e) => e.total && onProgress?.(Math.round((e.loaded / e.total) * 100)),
      })
      .then(data);
  },

  getSummary: (id, sentences) =>
    http.get(`/api/analysis/${id}/summary`, { params: sentences ? { sentences } : {} }).then(data),
  compareDocuments: (a, b) => http.post("/api/analysis/compare", { document_a: a, document_b: b }).then(data),
  runAnalysis: (id) => http.post(`/api/analysis/${id}`).then(data),
  /** Resolves to the saved analysis, or null if none has been run (or it is out of date). */
  getAnalysis: async (id) => {
    try {
      return await http.get(`/api/analysis/${id}`).then(data);
    } catch (err) {
      if (err.status === 404 || err.code === "analysis_outdated") return null;
      throw err;
    }
  },

  /** Download the report; returns { blob, filename }. */
  exportAnalysis: async (id, format) => {
    const response = await http.get(`/api/export/${id}`, { params: { format }, responseType: "blob" });
    const disposition = response.headers["content-disposition"] || "";
    const match = /filename="?([^";]+)"?/.exec(disposition);
    return { blob: response.data, filename: match ? match[1] : `analysis_${id}.${format}` };
  },
};

/** Save a blob through a temporary link (works without any server-side redirect). */
export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
