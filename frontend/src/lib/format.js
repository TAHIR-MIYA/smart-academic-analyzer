export function formatBytes(bytes) {
  if (bytes == null || Number.isNaN(bytes)) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatNumber(n) {
  return n == null ? "" : new Intl.NumberFormat("en-IN").format(n);
}

export function formatDate(iso) {
  if (!iso) return "";
  // The API sends UTC timestamps without a zone marker; treat them as UTC.
  const date = new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function formatPercent(fraction, digits = 0) {
  return fraction == null ? "" : `${(fraction * 100).toFixed(digits)}%`;
}

export function fileTypeLabel(type) {
  return type ? type.toUpperCase() : "";
}
