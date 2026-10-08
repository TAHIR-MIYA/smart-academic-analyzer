import { useEffect, useState } from "react";
import { api } from "../../api/api.js";
import AnalysisGate from "../../components/AnalysisGate.jsx";
import { BarsChart } from "../../components/charts.jsx";
import { Notice, Section, Spinner, buttonClass } from "../../components/ui.jsx";
import { useDocument } from "../../hooks/useDocument.js";
import { formatPercent } from "../../lib/format.js";

const MAX_SENTENCES = 20;

function Summary({ analysis, docId }) {
  const base = analysis.summary;
  const [n, setN] = useState(base.sentences_selected);
  const [custom, setCustom] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (n === base.sentences_selected) {
      setCustom(null);
      setError(null);
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    api
      .getSummary(docId, n)
      .then((data) => {
        if (!cancelled) {
          setCustom(data);
          setError(null);
        }
      })
      .catch((err) => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [n, docId, base.sentences_selected]);

  const s = custom ?? base;
  const max = Math.min(base.sentences_eligible, MAX_SENTENCES);
  return (
    <>
      <Section
        title="Summary"
        hint={`${s.sentences_selected} of ${s.sentences_in_document} sentences, ${formatPercent(s.compression_ratio)} of the document's words.`}
      >
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <button type="button" className={buttonClass.secondary} onClick={() => setN((v) => v - 1)} disabled={n <= 1 || loading}>
            Fewer sentences
          </button>
          <span className="min-w-[6rem] text-center tabular-nums" aria-live="polite">{n} {n === 1 ? "sentence" : "sentences"}</span>
          <button type="button" className={buttonClass.secondary} onClick={() => setN((v) => v + 1)} disabled={n >= max || loading}>
            More sentences
          </button>
          {loading && <Spinner label="Updating" />}
        </div>
        {error && (
          <div className="mb-4"><Notice kind="error" title="The summary could not be updated">{error}</Notice></div>
        )}
        {s.note && <div className="mb-4"><Notice kind="info">{s.note}</Notice></div>}
        <ol className="space-y-4 border-l-2 border-brand pl-5 font-serif text-[18px] leading-relaxed">
          {s.summary.map((x) => (
            <li key={x.index}>
              {x.text}
              <span className="ml-2 font-sans text-xs text-ink-muted">sentence {x.index + 1}, score {Math.round(x.relative_score * 100)}</span>
            </li>
          ))}
        </ol>
        <p className="mt-4 text-sm text-ink-muted">
          The summary is made only of sentences copied from the document, in their original order. Nothing is rewritten.
        </p>
      </Section>

      <Section title="How the sentences were chosen" hint="Each bar is one sentence, in document order.">
        <BarsChart
          horizontal={false}
          data={s.sentence_scores.map((x) => ({ name: String(x.index + 1), score: x.score, color: x.selected ? "#1f6f5c" : "#c3c9d6" }))}
          series={[{ key: "score", name: "Sentence score", color: "#c3c9d6" }]}
          tickInterval="preserveStartEnd"
          tableCaption="Score of each sentence"
          caption="Green bars are in the summary."
        />
        <ul className="mt-4 list-disc space-y-1 pl-5 text-ink-soft">
          <li>A sentence scores the sum of the TF-IDF weights of its distinct content words, divided by the square root of how many there are.</li>
          <li>The first usable sentence gets a {formatPercent(s.parameters.position_bonus)} bonus, because introductions state the topic.</li>
          <li>A sentence that mostly repeats one already chosen (more than {formatPercent(s.parameters.redundancy_threshold)} shared words) is skipped.</li>
          <li>Sentences shorter than {s.parameters.min_words} or longer than {s.parameters.max_words} words are ignored. {s.sentences_eligible} of {s.sentences_in_document} were eligible.</li>
        </ul>
        <p className="mt-3 text-sm text-ink-muted">
          The quality of the summary has not been scored automatically, because that needs human-written reference summaries.
        </p>
      </Section>
    </>
  );
}

function Content({ analysis }) {
  const { doc } = useDocument();
  if (!analysis.summary) {
    return (
      <Notice kind="info" title="No summary is available">
        {analysis.summary_error ?? "The document has no sentences suitable for summarisation."}
      </Notice>
    );
  }
  return <Summary analysis={analysis} docId={doc.id} />;
}

export default function SummaryPage() {
  return <AnalysisGate>{(analysis) => <Content analysis={analysis} />}</AnalysisGate>;
}
