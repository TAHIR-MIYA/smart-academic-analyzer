import { vi } from "vitest";

/** Shared factory for vi.mock("../api/api.js"): keeps the real ApiError, replaces the network functions. */
export async function mockApiModule(importOriginal) {
  const actual = await importOriginal();
  const names = ["health", "dashboard", "modelMetrics", "listDocuments", "getDocument", "deleteDocument", "uploadDocument",
    "getSummary", "compareDocuments", "runAnalysis", "getAnalysis", "exportAnalysis"];
  return { ...actual, saveBlob: vi.fn(), api: Object.fromEntries(names.map((n) => [n, vi.fn()])) };
}
