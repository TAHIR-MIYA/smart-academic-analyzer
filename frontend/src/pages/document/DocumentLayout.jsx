import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useParams } from "react-router-dom";
import { api } from "../../api/api.js";
import { EmptyState, Notice, PageHeader, Spinner, buttonClass } from "../../components/ui.jsx";
import { useApi } from "../../hooks/useApi.js";
import { fileTypeLabel, formatBytes, formatDate, formatNumber } from "../../lib/format.js";

const TABS = [
  ["", "Overview"],
  ["preprocessing", "Preprocessing"],
  ["keywords", "Keywords"],
  ["entities", "Entities"],
  ["classification", "Classification"],
  ["summary", "Summary"],
  ["similarity", "Similarity"],
  ["statistics", "Statistics"],
  ["export", "Export"],
];

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

/** Loads the document and its saved analysis once and shares them with every tab. */
export default function DocumentLayout() {
  const { id } = useParams();
  const docId = Number(id);
  const doc = useApi(() => api.getDocument(docId), [docId]);
  const saved = useApi(() => api.getAnalysis(docId), [docId]);
  const [fresh, setFresh] = useState(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState(null);
  const elapsed = useElapsedSeconds(running);

  useEffect(() => {
    setFresh(null);
  }, [docId]);

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
  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-3 text-sm">
        <Link to="/documents" className="text-brand-dark hover:underline">
          Documents
        </Link>
      </nav>
      <PageHeader
        title={d.original_filename}
        actions={
          analysis && (
            <button type="button" className={buttonClass.secondary} onClick={run} disabled={running}>
              Run analysis again
            </button>
          )
        }
      >
        {fileTypeLabel(d.file_type)} file, {formatBytes(d.size_bytes)}
        {d.page_count ? `, ${d.page_count} pages` : ""}, {formatNumber(d.word_count)} words. Added {formatDate(d.created_at)}.
        {analysis && ` Analysed ${formatDate(analysis.generated_at)}.`}
      </PageHeader>

      <nav aria-label="Document sections" className="-mt-4 mb-8 overflow-x-auto border-b border-rule">
        <ul className="flex min-w-max gap-1">
          {TABS.map(([path, label]) => (
            <li key={label}>
              <NavLink
                to={path ? `/documents/${docId}/${path}` : `/documents/${docId}`}
                end={path === ""}
                className={({ isActive }) =>
                  `-mb-px block border-b-2 px-3 py-2.5 text-sm font-medium ${
                    isActive ? "border-brand text-brand-dark" : "border-transparent text-ink-muted hover:text-ink"
                  }`
                }
              >
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {d.warnings.length > 0 && (
        <div className="mb-6 space-y-2">
          {d.warnings.map((w) => (
            <Notice key={w} kind="warning" title="Extraction warning">
              {w}
            </Notice>
          ))}
        </div>
      )}
      {saved.error && !analysis && (
        <div className="mb-6">
          <Notice kind="error" title="The saved analysis could not be loaded">
            {saved.error.message}
          </Notice>
        </div>
      )}
      {runError && (
        <div className="mb-6">
          <Notice kind="error" title="The analysis failed">
            {runError}
          </Notice>
        </div>
      )}
      {running && (
        <div className="mb-6">
          <Spinner label={`Analysing, ${elapsed}s. Long documents can take a few seconds.`} />
        </div>
      )}

      <Outlet context={{ doc: d, analysis, running, run, runError, elapsed }} />
    </>
  );
}
