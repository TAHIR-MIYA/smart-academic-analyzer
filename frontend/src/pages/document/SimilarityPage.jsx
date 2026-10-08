import { useState } from "react";
import { api } from "../../api/api.js";
import AnalysisGate from "../../components/AnalysisGate.jsx";
import { BarsChart } from "../../components/charts.jsx";
import { Notice, Section, Spinner, StatRow, buttonClass } from "../../components/ui.jsx";
import { useApi } from "../../hooks/useApi.js";
import { useDocument } from "../../hooks/useDocument.js";
import { formatPercent } from "../../lib/format.js";

function Topics({ analysis }) {
  const t = analysis.topic_similarity;
  if (!t) {
    return (
      <Notice kind="info" title="Topic similarity is not available">
        {analysis.topic_similarity_error ?? "No topic profiles were found."}
      </Notice>
    );
  }
  return (
    <>
      <p className="mb-4 text-lg">
        {t.best_topic ? (
          <>Closest subject: <strong className="font-serif">{t.best_topic}</strong> (cosine {t.best_similarity.toFixed(2)}).</>
        ) : (
          <>No strong match. The closest profile scores only {t.best_similarity.toFixed(2)}, below {t.weak_match_threshold}.</>
        )}
      </p>
      {t.note && <div className="mb-4"><Notice kind="warning">{t.note}</Notice></div>}
      <BarsChart
        data={t.similarities.map((x, i) => ({ name: x.topic, similarity: x.similarity }))}
        series={[{ key: "similarity", name: "Cosine similarity", color: "#7a3b8f" }]}
        categoryWidth={190}
        tableCaption="Cosine similarity to each topic profile"
      />
      {t.matched_terms.length > 0 && (
        <div className="mt-5">
          <h3 className="mb-2 text-base font-semibold">Words the document shares with {t.best_topic ?? "the closest profile"}</h3>
          <ul className="flex flex-wrap gap-2" aria-label="Shared words">
            {t.matched_terms.map((m) => (
              <li key={m.term} className="bg-mark-tint px-2.5 py-1 text-sm font-medium">{m.term}</li>
            ))}
          </ul>
        </div>
      )}
      <p className="mt-4 text-sm text-ink-muted">{t.method}. Profiles are plain text files in datasets/topics, so subjects can be added or edited.</p>
    </>
  );
}

function Compare() {
  const { doc } = useDocument();
  const { data: docs, error: listError } = useApi(api.listDocuments, []);
  const [otherId, setOtherId] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const others = (docs ?? []).filter((d) => d.id !== doc.id);

  async function compare() {
    setBusy(true);
    setError(null);
    try {
      setResult(await api.compareDocuments(doc.id, Number(otherId)));
    } catch (err) {
      setError(err.message);
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {listError && <Notice kind="error" title="Your documents could not be listed">{listError.message}</Notice>}
      {docs && others.length === 0 && <p className="text-ink-muted">Upload a second document to compare it with this one.</p>}
      {others.length > 0 && (
        <div className="flex flex-wrap items-end gap-3">
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Compare with</span>
            <select value={otherId} onChange={(e) => setOtherId(e.target.value)} className="min-w-[16rem] border border-rule bg-paper-raised px-3 py-2">
              <option value="">Choose a document</option>
              {others.map((d) => (
                <option key={d.id} value={d.id}>{d.original_filename}</option>
              ))}
            </select>
          </label>
          <button type="button" className={buttonClass.primary} onClick={compare} disabled={!otherId || busy}>
            Compare documents
          </button>
          {busy && <Spinner label="Comparing" />}
        </div>
      )}
      {error && <div className="mt-4"><Notice kind="error" title="The comparison failed">{error}</Notice></div>}

      {result && (
        <div className="mt-8">
          <StatRow
            stats={[
              { label: "Cosine similarity", value: result.cosine_similarity.toFixed(2) },
              { label: "Shared vocabulary", value: formatPercent(result.vocabulary_overlap_jaccard) },
              { label: "Reading", value: result.interpretation },
              { label: "Compared with", value: result.document_b.filename },
            ]}
          />
          <p className="mb-5 text-sm text-ink-muted">{result.note} {result.interpretation_note}</p>

          {result.shared_terms.length > 0 && (
            <div className="mb-6">
              <h3 className="mb-2 text-base font-semibold">Most important shared words</h3>
              <ul className="flex flex-wrap gap-2" aria-label="Shared terms">
                {result.shared_terms.map((t) => (
                  <li key={t.term} className="bg-mark-tint px-2.5 py-1 text-sm font-medium">{t.term}</li>
                ))}
              </ul>
            </div>
          )}

          <h3 className="mb-2 text-base font-semibold">Similar sentences</h3>
          {result.similar_sentence_pairs.length === 0 ? (
            <p className="text-ink-muted">No sentence in one document is close enough to a sentence in the other (cosine of at least {result.pair_threshold}).</p>
          ) : (
            <ul className="divide-y divide-rule border-y border-rule">
              {result.similar_sentence_pairs.map((p) => (
                <li key={`${p.index_a}-${p.index_b}`} className="py-4">
                  <p className="mb-2 text-sm font-semibold text-brand-dark">{formatPercent(p.similarity)} similar</p>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="mb-0.5 text-xs text-ink-muted">This document, sentence {p.index_a + 1}</p>
                      <p className="border-l-2 border-rule pl-3 font-serif">{p.sentence_a}</p>
                    </div>
                    <div>
                      <p className="mb-0.5 text-xs text-ink-muted">{result.document_b.filename}, sentence {p.index_b + 1}</p>
                      <p className="border-l-2 border-rule pl-3 font-serif">{p.sentence_b}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </>
  );
}

export default function SimilarityPage() {
  return (
    <>
      <Section title="Similarity to subject profiles" hint="Which known subject does the wording resemble most?">
        <AnalysisGate>{(analysis) => <Topics analysis={analysis} />}</AnalysisGate>
      </Section>
      <Section title="Compare with another document" hint="Finds shared wording and near-copied sentences.">
        <Compare />
      </Section>
    </>
  );
}
