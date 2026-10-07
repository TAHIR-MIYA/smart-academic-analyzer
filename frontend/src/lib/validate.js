export const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"];

/** Client-side pre-check so obvious mistakes are explained before any upload starts.
 *  The server repeats every check (and also inspects file content), so this is a convenience, not security. */
export function validateFile(file, maxMb) {
  const name = file.name;
  const dot = name.lastIndexOf(".");
  const ext = dot >= 0 ? name.slice(dot).toLowerCase() : "";
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `${name} is not a supported file type. Use a PDF, DOCX or TXT file.`;
  }
  if (file.size === 0) return `${name} is empty.`;
  if (maxMb && file.size > maxMb * 1024 * 1024) {
    return `${name} is ${(file.size / (1024 * 1024)).toFixed(1)} MB. The limit is ${maxMb} MB.`;
  }
  return null;
}
