import { useState } from "react";
import AnalysisGate from "../../components/AnalysisGate.jsx";
import { ClassMark, Notice, Section, buttonClass } from "../../components/ui.jsx";
import { useDocument } from "../../hooks/useDocument.js";
import { formatNumber } from "../../lib/format.js";

const TEXT_PREVIEW_CHARS = 3000;

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

export default function OverviewPage() {
  const { doc } = useDocument();
  const [showFull, setShowFull] = useState(false);
  const text = doc.extracted_text;
  const truncated = !showFull && text.length > TEXT_PREVIEW_CHARS;
  return (
    <>
      <Section title="At a glance" hint="Each tab above explains one part of the analysis in detail.">
        <AnalysisGate>{(analysis) => <AnalysisOverview analysis={analysis} />}</AnalysisGate>
      </Section>

      <Section title="Extracted text" hint={`${formatNumber(doc.char_count)} characters, extracted with ${doc.extraction_method}.`}>
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words border border-rule bg-paper-raised p-4 font-sans text-sm leading-relaxed">
          {truncated ? `${text.slice(0, TEXT_PREVIEW_CHARS)}…` : text}
        </pre>
        {text.length > TEXT_PREVIEW_CHARS && (
          <button type="button" className={`${buttonClass.secondary} mt-3`} onClick={() => setShowFull((s) => !s)}>
            {showFull ? "Show less" : "Show the full text"}
          </button>
        )}
      </Section>
    </>
  );
}
