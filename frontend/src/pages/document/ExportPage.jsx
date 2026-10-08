import { Download } from "lucide-react";
import { useState } from "react";
import { api, saveBlob } from "../../api/api.js";
import { Notice, Section, buttonClass } from "../../components/ui.jsx";
import { useDocument } from "../../hooks/useDocument.js";

export default function ExportPage() {
  const { doc } = useDocument();
  const [downloading, setDownloading] = useState(null);
  const [error, setError] = useState(null);

  async function download(format) {
    setDownloading(format);
    setError(null);
    try {
      const { blob, filename } = await api.exportAnalysis(doc.id, format);
      saveBlob(blob, filename);
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloading(null);
    }
  }

  return (
    <Section title="Download the analysis" hint="Downloading runs the analysis first if it has not been run.">
      {error && (
        <div className="mb-4">
          <Notice kind="error" title="The report was not downloaded">
            {error}
          </Notice>
        </div>
      )}
      <div className="grid gap-x-12 gap-y-6 md:grid-cols-2">
        <div>
          <h3 className="mb-1 text-lg font-semibold">PDF report</h3>
          <p className="mb-3 text-ink-muted">
            A readable report with charts: the predicted type, summary, statistics, readability, vocabulary, keywords, word groups,
            entities, topic similarity and the preprocessing steps. The classifier's measured results are in their own section.
          </p>
          <button type="button" className={buttonClass.primary} onClick={() => download("pdf")} disabled={downloading !== null}>
            <Download className="h-4 w-4" aria-hidden="true" />
            {downloading === "pdf" ? "Preparing PDF" : "Download PDF report"}
          </button>
        </div>
        <div>
          <h3 className="mb-1 text-lg font-semibold">JSON data</h3>
          <p className="mb-3 text-ink-muted">
            Every number from the analysis in a machine-readable file, plus the classifier's held-out evaluation, kept apart from
            this document's prediction.
          </p>
          <button type="button" className={buttonClass.secondary} onClick={() => download("json")} disabled={downloading !== null}>
            <Download className="h-4 w-4" aria-hidden="true" />
            {downloading === "json" ? "Preparing JSON" : "Download JSON"}
          </button>
        </div>
      </div>
    </Section>
  );
}
