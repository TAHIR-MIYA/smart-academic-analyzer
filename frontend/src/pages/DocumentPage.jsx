import { Download } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, saveBlob } from "../api/api.js";
import { ClassMark, EmptyState, Notice, PageHeader, Section, Spinner, buttonClass } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { fileTypeLabel, formatBytes, formatDate, formatNumber } from "../lib/format.js";

const TEXT_PREVIEW_CHARS = 3000;

function useElapsedSeconds(running) {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!running) return undefined;
    setSeconds(0);
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [running]);
  return seconds;
}

function AnalysisOverview({ analysis }) {
  const c = analysis.classification;
  const keywords = analysis.keywords.keywords.slice(0, 8);
  const sentences = analysis.summary?.summary.slice(0, 2) ?? [];
  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-2 text-base font-semibold">Document type</h3>
        {c ? (
          <>
            <ClassMark label={c.label} confidence={c.confidence} uncertain={!c.is_confident} />
            {!c.is_confident && (
              <div className="mt-3">
                <Notice kind="warning" title="The classifier is not sure about this one">
                  Its best guess has a probability below {Math.round(c.confidence_threshold * 100)}%, so treat it as a suggestion.
                </Notice>
              </div>
            )}
          </>
        ) : (
          <Notice kind="info" title="No document type was predicted">
            {analysis.classification_error ?? "No trained classifier is available."}
          </Notice>
        )}
      </div>

      <div>
        <h3 className="mb-2 text-base font-semibold">Top keywords</h3>
        <ul className="flex flex-wrap gap-2" aria-label="Top keywords">
          {keywords.map((k) => (
            <li key={k.term} className="bg-mark-tint px-2.5 py-1 text-sm">
              <span className="font-medium">{k.term}</span>
              <span className="ml-1.5 text-xs text-ink-muted">{k.count}</span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-base font-semibold">Summary</h3>
        {sentences.length > 0 ? (
          <div className="space-y-2 border-l-2 border-rule pl-4 font-serif text-[17px] leading-relaxed">
            {sentences.map((s) => (
              <p key={s.index}>{s.text}</p>
            ))}
          </div>
        ) : (
          <p className="text-ink-muted">{analysis.summary_error ?? "No summary is available."}</p>
        )}
      </div>

      <p className="text-sm text-ink-muted">
        Reading level: {analysis.readability.reading_level}.
        {!analysis.readability.reliable && " This document is short, so the estimate is rough."}
      </p>
    </div>
  );
}

export default function DocumentPage() {
  const { id } = useParams();
  const docId = Number(id);
  const doc = useApi(() => api.getDocument(docId), [docId]);
  const saved = useApi(() => api.getAnalysis(docId), [docId]);

  const [fresh, setFresh] = useState(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(null);
  const [downloading, setDownloading] = useState(null);
  const [downloadError, setDownloadError] = useState(null);
  const [showFullText, setShowFullText] = useState(false);
  const elapsed = useElapsedSeconds(running);

  async function run() {
    setRunning(true);
    setRunError(null);
    try {
      setFresh(await api.runAnalysis(docId));
    } catch (err) {
      setRunError(err.message);
    } finally {
      setRunning(false);
    }
  }

  async function download(format) {
    setDownloading(format);
    setDownloadError(null);
    try {
      const { blob, filename } = await api.exportAnalysis(docId, format);
      saveBlob(blob, filename);
    } catch (err) {
      setDownloadError(err.message);
    } finally {
      setDownloading(null);
    }
  }

  if (doc.loading && !doc.data) return <Spinner label="Loading the document" />;
  if (doc.error && !doc.data) {
    const missing = doc.error.status === 404;
    return (
      <EmptyState
        title={missing ? "Document not found" : "The document could not be loaded"}
        action={
          <Link to="/documents" className={buttonClass.primary}>
            Back to documents
          </Link>
        }
      >
        {missing ? "It may have been deleted." : doc.error.message}
      </EmptyState>
    );
  }

  const d = doc.data;
  const analysis = fresh ?? saved.data;
  const text = d.extracted_text;
  const truncated = !showFullText && text.length > TEXT_PREVIEW_CHARS;

  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-3 text-sm">
        <Link to="/documents" className="text-brand-dark hover:underline">
          Documents
        </Link>
      </nav>
      <PageHeader title={d.original_filename}>
        {fileTypeLabel(d.file_type)} file, {formatBytes(d.size_bytes)}
        {d.page_count ? `, ${d.page_count} pages` : ""}, {formatNumber(d.word_count)} words. Added {formatDate(d.created_at)}.
      </PageHeader>

      {d.warnings.length > 0 && (
        <div className="mb-6 space-y-2">
          {d.warnings.map((w) => (
            <Notice key={w} kind="warning" title="Extraction warning">
              {w}
            </Notice>
          ))}
        </div>
      )}

      <Section
        title="Analysis"
        hint={analysis ? `Run on ${formatDate(analysis.generated_at)}.` : "Not analysed yet."}
      >
        {saved.error && !analysis && (
          <div className="mb-4">
            <Notice kind="error" title="The saved analysis could not be loaded">
              {saved.error.message}
            </Notice>
          </div>
        )}
        {runError && (
          <div className="mb-4">
            <Notice kind="error" title="The analysis failed">
              {runError}
            </Notice>
          </div>
        )}

        {analysis && <AnalysisOverview analysis={analysis} />}

        <div className="mt-6 flex flex-wrap items-center gap-4">
          <button type="button" className={buttonClass.primary} onClick={run} disabled={running}>
            {analysis ? "Run analysis again" : "Run analysis"}
          </button>
          {running && <Spinner label={`Analysing, ${elapsed}s. Long documents can take a few seconds.`} />}
        </div>
      </Section>

      <Section title="Download report" hint="Downloading runs the analysis first if it has not been run.">
        {downloadError && (
          <div className="mb-4">
            <Notice kind="error" title="The report was not downloaded">
              {downloadError}
            </Notice>
          </div>
        )}
        <div className="flex flex-wrap gap-3">
          <button type="button" className={buttonClass.secondary} onClick={() => download("pdf")} disabled={downloading !== null}>
            <Download className="h-4 w-4" aria-hidden="true" />
            {downloading === "pdf" ? "Preparing PDF" : "Download PDF report"}
          </button>
          <button type="button" className={buttonClass.secondary} onClick={() => download("json")} disabled={downloading !== null}>
            <Download className="h-4 w-4" aria-hidden="true" />
            {downloading === "json" ? "Preparing JSON" : "Download JSON"}
          </button>
        </div>
      </Section>

      <Section title="Extracted text" hint={`${formatNumber(d.char_count)} characters, extracted with ${d.extraction_method}.`}>
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words border border-rule bg-paper-raised p-4 font-sans text-sm leading-relaxed">
          {truncated ? `${text.slice(0, TEXT_PREVIEW_CHARS)}…` : text}
        </pre>
        {text.length > TEXT_PREVIEW_CHARS && (
          <button type="button" className={`${buttonClass.secondary} mt-3`} onClick={() => setShowFullText((s) => !s)}>
            {showFullText ? "Show less" : "Show the full text"}
          </button>
        )}
      </Section>
    </>
  );
}
