import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api.js";
import { EmptyState, Notice, PageHeader, Spinner, StatusBadge, buttonClass } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { fileTypeLabel, formatBytes, formatDate, formatNumber } from "../lib/format.js";

export default function DocumentsPage() {
  const { data: documents, error, loading, reload } = useApi(api.listDocuments, []);
  const [confirmId, setConfirmId] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  async function remove(id) {
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteDocument(id);
      setConfirmId(null);
      await reload();
    } catch (err) {
      setDeleteError(err.message);
    } finally {
      setDeleting(false);
    }
  }

  if (loading && !documents) return <Spinner label="Loading documents" />;

  return (
    <>
      <PageHeader
        title="Documents"
        actions={
          <Link to="/upload" className={buttonClass.primary}>
            Upload documents
          </Link>
        }
      >
        Every document you have uploaded.
      </PageHeader>

      {error && !documents && (
        <Notice kind="error" title="The document list could not be loaded">
          {error.message}
        </Notice>
      )}
      {deleteError && (
        <div className="mb-4">
          <Notice kind="error" title="The document was not deleted">
            {deleteError}
          </Notice>
        </div>
      )}

      {documents && documents.length === 0 && (
        <EmptyState
          title="No documents yet"
          action={
            <Link to="/upload" className={buttonClass.primary}>
              Upload a document
            </Link>
          }
        >
          Documents you upload will be listed here with their analysis status.
        </EmptyState>
      )}

      {documents && documents.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead className="border-b border-rule text-ink-muted">
              <tr>
                <th className="py-2 pr-3 font-medium">Document</th>
                <th className="py-2 pr-3 font-medium">Type</th>
                <th className="py-2 pr-3 text-right font-medium">Words</th>
                <th className="py-2 pr-3 text-right font-medium">Size</th>
                <th className="py-2 pr-3 font-medium">Added</th>
                <th className="py-2 pr-3 font-medium">Status</th>
                <th className="py-2 text-right font-medium">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {documents.map((d) => (
                <tr key={d.id}>
                  <td className="max-w-[18rem] truncate py-3 pr-3">
                    <Link to={`/documents/${d.id}`} className="font-medium text-brand-dark underline-offset-2 hover:underline">
                      {d.original_filename}
                    </Link>
                  </td>
                  <td className="py-3 pr-3">{fileTypeLabel(d.file_type)}</td>
                  <td className="py-3 pr-3 text-right tabular-nums">{formatNumber(d.word_count)}</td>
                  <td className="py-3 pr-3 text-right tabular-nums">{formatBytes(d.size_bytes)}</td>
                  <td className="py-3 pr-3">{formatDate(d.created_at)}</td>
                  <td className="py-3 pr-3"><StatusBadge done={d.analyzed} /></td>
                  <td className="py-3 text-right">
                    {confirmId === d.id ? (
                      <span className="inline-flex items-center gap-2">
                        <button type="button" className={buttonClass.danger} disabled={deleting} onClick={() => remove(d.id)}>
                          Delete {d.original_filename}
                        </button>
                        <button type="button" className={buttonClass.secondary} onClick={() => setConfirmId(null)}>
                          Keep
                        </button>
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="rounded p-1.5 text-ink-muted hover:bg-alert-tint hover:text-alert"
                        aria-label={`Delete ${d.original_filename}`}
                        onClick={() => setConfirmId(d.id)}
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
