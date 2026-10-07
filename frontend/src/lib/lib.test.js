import { describe, expect, it } from "vitest";
import { classMeta } from "./classes.js";
import { fileTypeLabel, formatBytes, formatDate, formatNumber, formatPercent } from "./format.js";
import { validateFile } from "./validate.js";

const file = (name, size) => ({ name, size });

describe("validateFile", () => {
  it("accepts supported types in any letter case", () => {
    for (const name of ["a.pdf", "b.DOCX", "c.Txt"]) expect(validateFile(file(name, 100), 10)).toBeNull();
  });
  it("rejects other types and files without an extension", () => {
    expect(validateFile(file("photo.png", 100), 10)).toMatch(/not a supported file type/);
    expect(validateFile(file("README", 100), 10)).toMatch(/not a supported file type/);
    expect(validateFile(file("archive.tar.gz", 100), 10)).toMatch(/not a supported file type/);
  });
  it("rejects empty files", () => {
    expect(validateFile(file("a.txt", 0), 10)).toBe("a.txt is empty.");
  });
  it("rejects files over the limit and names both sizes", () => {
    expect(validateFile(file("a.txt", 3 * 1024 * 1024), 2)).toBe("a.txt is 3.0 MB. The limit is 2 MB.");
  });
  it("allows any size when the limit is not known yet", () => {
    expect(validateFile(file("a.txt", 500 * 1024 * 1024), undefined)).toBeNull();
  });
  it("accepts a file exactly at the limit", () => {
    expect(validateFile(file("a.txt", 2 * 1024 * 1024), 2)).toBeNull();
  });
});

describe("format helpers", () => {
  it("formats bytes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(5 * 1024 * 1024)).toBe("5.0 MB");
    expect(formatBytes(null)).toBe("");
  });
  it("groups digits the Indian way", () => {
    expect(formatNumber(14231)).toBe("14,231");
    expect(formatNumber(1234567)).toBe("12,34,567");
    expect(formatNumber(null)).toBe("");
  });
  it("formats percentages", () => {
    expect(formatPercent(0.88)).toBe("88%");
    expect(formatPercent(0.9567, 1)).toBe("95.7%");
  });
  it("treats zone-less API timestamps as UTC", () => {
    expect(formatDate("2026-10-05T23:30:00")).toBe(formatDate("2026-10-05T23:30:00Z"));
    expect(formatDate("not a date")).toBe("not a date");
    expect(formatDate(null)).toBe("");
  });
  it("labels file types", () => {
    expect(fileTypeLabel("pdf")).toBe("PDF");
  });
});

describe("classMeta", () => {
  it("returns a fixed colour per class and a safe default", () => {
    expect(classMeta("notice").name).toBe("Notice");
    expect(classMeta("notice").color).toMatch(/^#/);
    expect(classMeta("mystery").name).toBe("mystery");
  });
});
