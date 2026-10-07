import { CheckCircle2, FileText, UploadCloud, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api.js";
import { ClassMark, Notice, PageHeader, ProgressBar, Section, Spinner, buttonClass } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { formatBytes } from "../lib/format.js";
import { ALLOWED_EXTENSIONS, validateFile } from "../lib/validate.js";

const PIPELINE = [
  "The text is extracted from your file.",
  "It is cleaned: ligatures, hyphenated line breaks, page numbers and repeated headers are fixed or removed.",
  "It is split into sentences and words, reduced to base forms, and stop words are removed.",
  "Keywords, word groups and named entities are found.",
  "A trained classifier predicts the document type and says how sure it is.",
  "The most informative sentences are selected as a summary.",
  "Readability, vocabulary variety and similarity to subject profiles are measured.",
];

function ItemStatus({ item, onAnalyse }) {
  switch (item.status) {
    case "queued":
      return <span className="text-sm text-ink-muted">Waiting</span>;
    case "uploading":
      return (
        <div className="w-44">
          <ProgressBar value={item.progress} label={`Uploading ${item.file.name}`} />
          <span className="text-xs text-ink-muted">Uploading {item.progress}%</span>
        </div>
      );
    case "processing":
      return <Spinner label="Extracting text" />;
    case "analysing":
      return <Spinner label="Analysing" />;
    case "uploaded":
      return (
        <div className="flex flex-wrap items-center gap-3">
          <span className="inline-flex items-center gap-1 text-sm text-brand-dark">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Uploaded
          </span>
          <button type="button" className={buttonClass.secondary} onClick={() => onAnalyse(item)}>
            Analyse
          </button>
        </div>
      );
    case "done": {
      const c = item.analysis?.classification;
      return (
        <div className="flex flex-wrap items-center gap-3">
          {c ? (
            <ClassMark label={c.label} confidence={c.confidence} uncertain={!c.is_confident} />
          ) : (
            <span className="inline-flex items-center gap-1 text-sm text-brand-dark">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Analysed
            </span>
          )}
        </div>
      );
    }
    default:
      return (
        <span className="inline-flex items-start gap-1 text-sm text-alert">
          <XCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" /> Not uploaded
        </span>
      );
  }
}

export default function UploadPage() {
  const { data: health } = useApi(api.health, []);
  const maxMb = health?.max_upload_mb;
  const [items, setItems] = useState([]);
  const [autoAnalyse, setAutoAnalyse] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [activeId, setActiveId] = useState(null);
  const nextId = useRef(1);
  const inputRef = useRef(null);

  const patch = (id, changes) => setItems((list) => list.map((i) => (i.id === id ? { ...i, ...changes } : i)));

  async function analyse(id, docId) {
    patch(id, { status: "analysing", analysisError: null });
    try {
      const analysis = await api.runAnalysis(docId);
      patch(id, { status: "done", analysis });
    } catch (err) {
      patch(id, { status: "uploaded", analysisError: err.message });
    }
  }

  function addFiles(fileList) {
    const additions = Array.from(fileList).map((file) => {
      const error = validateFile(file, maxMb);
      return { id: nextId.current++, file, status: error ? "error" : "queued", progress: 0, error, docId: null, analysis: null, analysisError: null };
    });
    setItems((list) => [...list, ...additions]);
  }

  // Files are processed one at a time so a slow analysis never competes with the next upload.
  useEffect(() => {
    if (activeId !== null) return;
    const next = items.find((i) => i.status === "queued");
    if (!next) return;
    setActiveId(next.id);
    patch(next.id, { status: "uploading", progress: 0 });
    (async () => {
      try {
        const doc = await api.uploadDocument(next.file, (progress) =>
          patch(next.id, { progress, status: progress >= 100 ? "processing" : "uploading" }),
        );
        patch(next.id, { status: "uploaded", docId: doc.id, progress: 100 });
        if (autoAnalyse) await analyse(next.id, doc.id);
      } catch (err) {
        patch(next.id, { status: "error", error: err.message });
      } finally {
        setActiveId(null);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items, activeId]);

  const finished = items.filter((i) => ["done", "uploaded", "error"].includes(i.status));

  return (
    <>
      <PageHeader title="Upload documents">
        Add PDF, DOCX or TXT files{maxMb ? `, up to ${maxMb} MB each` : ""}. Scanned images are not supported.
      </PageHeader>

      <div className="grid gap-x-12 gap-y-8 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <div>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              addFiles(e.dataTransfer.files);
            }}
            className={`border-2 border-dashed px-6 py-10 text-center ${dragging ? "border-brand bg-brand-tint" : "border-rule bg-paper-raised"}`}
          >
            <UploadCloud className="mx-auto h-8 w-8 text-ink-muted" aria-hidden="true" />
            <p className="mt-3 font-medium">Drop files here</p>
            <p className="text-sm text-ink-muted">or</p>
            <button type="button" className={`${buttonClass.primary} mt-2`} onClick={() => inputRef.current?.click()}>
              Choose files
            </button>
            <input
              ref={inputRef}
              type="file"
              multiple
              accept={ALLOWED_EXTENSIONS.join(",")}
              aria-label="Files to upload"
              className="sr-only"
              onChange={(e) => {
                addFiles(e.target.files);
                e.target.value = "";
              }}
            />
          </div>

          <label className="mt-4 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={autoAnalyse} onChange={(e) => setAutoAnalyse(e.target.checked)} className="h-4 w-4 accent-[#1f6f5c]" />
            Analyse each file as soon as it is uploaded
          </label>

          {items.length > 0 && (
            <ul className="mt-6 divide-y divide-rule border-y border-rule" aria-label="Upload queue">
              {items.map((item) => (
                <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <div className="flex min-w-0 items-start gap-2">
                    <FileText className="mt-0.5 h-5 w-5 shrink-0 text-ink-muted" aria-hidden="true" />
                    <div className="min-w-0">
                      <p className="truncate font-medium">{item.file.name}</p>
                      <p className="text-xs text-ink-muted">{formatBytes(item.file.size)}</p>
                      {item.error && (
                        <p className="mt-1 text-sm text-alert" role="alert">
                          {item.error}
                        </p>
                      )}
                      {item.analysisError && (
                        <p className="mt-1 text-sm text-alert" role="alert">
                          Uploaded, but the analysis failed: {item.analysisError}
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <ItemStatus item={item} onAnalyse={(it) => analyse(it.id, it.docId)} />
                    {item.docId && (
                      <Link to={`/documents/${item.docId}`} className="text-sm font-medium text-brand-dark hover:underline">
                        Open
                      </Link>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          {finished.length > 0 && (
            <button type="button" className={`${buttonClass.secondary} mt-4`} onClick={() => setItems((l) => l.filter((i) => !finished.includes(i)))}>
              Clear finished files
            </button>
          )}
        </div>

        <Section title="What happens to your document">
          <ol className="space-y-3">
            {PIPELINE.map((step, i) => (
              <li key={step} className="flex gap-3">
                <span className="mt-0.5 font-serif text-lg font-semibold leading-tight text-brand-dark">{i + 1}</span>
                <span className="text-ink-soft">{step}</span>
              </li>
            ))}
          </ol>
          <div className="mt-6">
            <Notice kind="info">Files are stored as extracted text only. The original file is not kept.</Notice>
          </div>
        </Section>
      </div>
    </>
  );
}
