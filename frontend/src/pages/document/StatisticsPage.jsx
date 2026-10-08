import AnalysisGate from "../../components/AnalysisGate.jsx";
import { BarsChart, ZipfChart } from "../../components/charts.jsx";
import { Facts, Notice, Section } from "../../components/ui.jsx";
import { formatNumber } from "../../lib/format.js";

function Statistics({ analysis }) {
  const s = analysis.statistics;
  const r = analysis.readability;
  const v = analysis.vocabulary;
  return (
    <>
      <Section title="Text statistics">
        <Facts
          items={[
            ["Characters", formatNumber(s.characters)],
            ["Characters without spaces", formatNumber(s.characters_no_spaces)],
            ["Words, numbers included", formatNumber(s.words)],
            ["Distinct words", formatNumber(s.unique_words)],
            ["Sentences", formatNumber(s.sentences)],
            ["Paragraphs", formatNumber(s.paragraphs)],
            ["Average word length", `${s.avg_word_length} letters`],
            ["Average sentence length", `${s.avg_sentence_length} words`],
            ["Longest sentence", `${s.longest_sentence_words} words`],
            ["Reading time", `${s.reading_time_minutes} min`],
          ]}
        />
        <div className="mt-8 grid gap-x-10 gap-y-8 md:grid-cols-2">
          <div>
            <h3 className="mb-2 text-base font-semibold">Sentence lengths</h3>
            <BarsChart horizontal={false} data={s.sentence_length_distribution.map((b) => ({ name: b.range, sentences: b.count }))}
              series={[{ key: "sentences", name: "Sentences", color: "#2f5d9e" }]} tableCaption="Number of sentences by length in words" caption="Number of sentences by length in words." />
          </div>
          <div>
            <h3 className="mb-2 text-base font-semibold">Word lengths</h3>
            <BarsChart horizontal={false} data={s.word_length_distribution.map((b) => ({ name: b.length, words: b.count }))}
              series={[{ key: "words", name: "Words", color: "#56697d" }]} tableCaption="Number of words by length in letters" caption="Number of words by length in letters." />
          </div>
        </div>
      </Section>

      <Section title="Readability" hint={r.reading_level}>
        {r.warning && <div className="mb-4"><Notice kind="warning" title="Treat these scores as rough">{r.warning}</Notice></div>}
        <table className="w-full text-left text-sm">
          <thead className="border-b border-rule text-ink-muted">
            <tr>
              <th className="py-2 pr-3 font-medium">Index</th>
              <th className="py-2 pr-3 text-right font-medium">Score</th>
              <th className="py-2 pr-3 font-medium">Meaning</th>
              <th className="py-2 font-medium">Formula</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {r.scores.map((x) => (
              <tr key={x.name}>
                <td className="py-2 pr-3 font-medium">{x.name}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{x.value}</td>
                <td className="py-2 pr-3">{x.interpretation}</td>
                <td className="py-2 text-ink-muted">{x.formula}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-sm text-ink-muted">
          Based on {r.counts.words} words, {r.counts.sentences} sentences and {r.counts.syllables} syllables ({r.counts.complex_words} words have three or
          more). {r.note}
        </p>
      </Section>

      <Section title="Vocabulary variety">
        {v.warning && <div className="mb-4"><Notice kind="warning" title="Treat these measures as rough">{v.warning}</Notice></div>}
        <p className="mb-4 text-ink-muted">
          {formatNumber(v.tokens)} alphabetic words of two or more letters, {formatNumber(v.types)} distinct, {formatNumber(v.lemma_types)} distinct after
          lemmatisation. {formatNumber(v.hapax_count)} words appear only once.
        </p>
        <dl className="mb-8 divide-y divide-rule border-y border-rule">
          {v.measures.map((m) => (
            <div key={m.key} className="grid gap-1 py-2.5 md:grid-cols-[16rem_6rem_1fr]">
              <dt className="font-medium">{m.name}</dt>
              <dd className="tabular-nums">{m.value}</dd>
              <dd className="text-sm text-ink-muted">{m.description}</dd>
            </div>
          ))}
        </dl>
        <div className="grid gap-x-10 gap-y-8 md:grid-cols-2">
          <div>
            <h3 className="mb-2 text-base font-semibold">How often words repeat</h3>
            <BarsChart horizontal={false} data={v.frequency_spectrum.map((b) => ({ name: b.occurrences, words: b.count }))}
              series={[{ key: "words", name: "Distinct words", color: "#1f6f5c" }]} tableCaption="Distinct words by number of occurrences"
              caption="Distinct words, grouped by how many times each occurs." />
          </div>
          <div>
            <h3 className="mb-2 text-base font-semibold">Word frequency by rank</h3>
            <ZipfChart points={v.zipf} caption="In natural text the most frequent words are far more frequent than the rest (Zipf's law)." />
          </div>
        </div>
      </Section>
    </>
  );
}

export default function StatisticsPage() {
  return <AnalysisGate>{(analysis) => <Statistics analysis={analysis} />}</AnalysisGate>;
}
