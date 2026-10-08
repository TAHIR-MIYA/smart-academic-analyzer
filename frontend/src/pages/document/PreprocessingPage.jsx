import AnalysisGate from "../../components/AnalysisGate.jsx";
import { BarsChart } from "../../components/charts.jsx";
import { Notice, Section } from "../../components/ui.jsx";
import { formatNumber, formatPercent } from "../../lib/format.js";

function Content({ analysis }) {
  const p = analysis.preprocessing;
  const stages = p.stages.map((s) => ({ name: s.name, tokens: s.token_count, distinct: s.unique_count }));
  return (
    <>
      {p.warnings.map((w) => (
        <div key={w} className="mb-6">
          <Notice kind="warning">{w}</Notice>
        </div>
      ))}

      <Section title="Cleaning" hint={`${formatNumber(p.cleaning.original_characters)} characters before, ${formatNumber(p.cleaning.cleaned_characters)} after.`}>
        <table className="w-full text-left text-sm">
          <thead className="border-b border-rule text-ink-muted">
            <tr>
              <th className="py-2 pr-3 font-medium">Step</th>
              <th className="py-2 pr-3 font-medium">What it does</th>
              <th className="py-2 text-right font-medium">Times applied</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {p.cleaning.operations.map((o) => (
              <tr key={o.name} className={o.count === 0 ? "text-ink-muted" : ""}>
                <td className="py-2 pr-3 font-medium">{o.name}</td>
                <td className="py-2 pr-3">{o.description}</td>
                <td className="py-2 text-right tabular-nums">{o.count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Words at each stage" hint="Distinct words are different spellings or forms counted once.">
        <BarsChart
          data={stages}
          series={[{ key: "tokens", name: "Words", color: "#2c3a56" }, { key: "distinct", name: "Distinct words", color: "#1f6f5c" }]}
          categoryWidth={150}
          tableCaption="Words and distinct words at each preprocessing stage"
        />
        <table className="mt-4 w-full text-left text-sm">
          <thead className="border-b border-rule text-ink-muted">
            <tr>
              <th className="py-2 pr-3 font-medium">Stage</th>
              <th className="py-2 pr-3 font-medium">What happens</th>
              <th className="py-2 font-medium">First few words</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {p.stages.map((s) => (
              <tr key={s.name}>
                <td className="py-2 pr-3 font-medium">{s.name}</td>
                <td className="py-2 pr-3">{s.description}</td>
                <td className="py-2 text-ink-soft">{s.sample.slice(0, 8).join(" ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Before and after">
        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="mb-1 text-base font-semibold">Cleaned text</h3>
            <p className="border-l-2 border-rule pl-4 text-ink-soft">{p.original_sample}</p>
          </div>
          <div>
            <h3 className="mb-1 text-base font-semibold">After stop words and lemmatisation</h3>
            <p className="border-l-2 border-brand pl-4 text-ink-soft">{p.processed_sample}</p>
          </div>
        </div>
      </Section>

      <Section title="Stop words removed" hint={`${formatPercent(p.stopword_removal_rate)} of the words were stop words.`}>
        <p className="mb-3 text-ink-muted">Stop words are very common words such as "the" that say little about the topic.</p>
        <ul className="flex flex-wrap gap-2" aria-label="Most removed stop words">
          {p.removed_stopwords.map((w) => (
            <li key={w.term} className="border border-rule bg-paper-raised px-2.5 py-1 text-sm">
              {w.term} <span className="text-xs text-ink-muted">{w.count}</span>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Stemming compared with lemmatisation" hint="The analysis uses lemmas.">
        <p className="mb-3 max-w-2xl text-ink-muted">
          A stemmer cuts word endings by rule, so its result may not be a real word. A lemmatiser looks the word up and
          returns its dictionary form, using the word's part of speech.
        </p>
        {p.stem_vs_lemma.length === 0 ? (
          <p className="text-ink-muted">No frequent word in this document was changed differently by the two methods.</p>
        ) : (
          <table className="w-full max-w-xl text-left text-sm">
            <thead className="border-b border-rule text-ink-muted">
              <tr>
                <th className="py-2 pr-3 font-medium">Word</th>
                <th className="py-2 pr-3 font-medium">Stem</th>
                <th className="py-2 pr-3 font-medium">Lemma</th>
                <th className="py-2 font-medium">Part of speech</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {p.stem_vs_lemma.map((r) => (
                <tr key={r.word}>
                  <td className="py-2 pr-3 font-medium">{r.word}</td>
                  <td className="py-2 pr-3">{r.stem}</td>
                  <td className="py-2 pr-3 text-brand-dark">{r.lemma}</td>
                  <td className="py-2">{r.pos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>
    </>
  );
}

export default function PreprocessingPage() {
  return <AnalysisGate>{(analysis) => <Content analysis={analysis} />}</AnalysisGate>;
}
