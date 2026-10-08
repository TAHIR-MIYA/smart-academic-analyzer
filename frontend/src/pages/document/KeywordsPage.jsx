import { useState } from "react";
import AnalysisGate from "../../components/AnalysisGate.jsx";
import { BarsChart } from "../../components/charts.jsx";
import { Notice, Section, Segmented } from "../../components/ui.jsx";

const COUNTS = [10, 15, 20, 30].map((n) => ({ value: n, label: String(n) }));

function Keywords({ analysis }) {
  const k = analysis.keywords;
  const [top, setTop] = useState(15);
  const [level, setLevel] = useState(2);
  const shown = k.keywords.slice(0, top);
  const ng = analysis.ngrams.levels.find((l) => l.n === level);
  const modeNote =
    k.idf_mode === "term_frequency" ? (
      <Notice kind="warning" title="Ranked by frequency only">{k.idf_description}</Notice>
    ) : (
      <Notice kind="info">{k.idf_description}</Notice>
    );
  return (
    <>
      <Section
        title="Keywords"
        hint="TF-IDF scores a word higher when it is frequent in this document but not spread evenly across the comparison documents."
      >
        <div className="mb-4">{modeNote}</div>
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <span className="text-sm text-ink-muted">Show the top</span>
          <Segmented label="Number of keywords" options={COUNTS} value={top} onChange={setTop} />
        </div>
        <BarsChart
          data={shown.map((x) => ({ name: x.term, score: x.score }))}
          series={[{ key: "score", name: "TF-IDF score", color: "#c99a1c" }]}
          tableCaption="Keyword TF-IDF scores"
          categoryWidth={130}
        />
        <table className="mt-4 w-full text-left text-sm">
          <thead className="border-b border-rule text-ink-muted">
            <tr>
              <th className="py-2 pr-3 font-medium">Keyword</th>
              <th className="py-2 pr-3 text-right font-medium">Count</th>
              <th className="py-2 pr-3 text-right font-medium">TF</th>
              <th className="py-2 pr-3 text-right font-medium">IDF</th>
              <th className="py-2 text-right font-medium">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {shown.map((x) => (
              <tr key={x.term}>
                <td className="py-2 pr-3"><span className="bg-mark-tint px-1.5 font-medium">{x.term}</span></td>
                <td className="py-2 pr-3 text-right tabular-nums">{x.count}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{x.tf}</td>
                <td className="py-2 pr-3 text-right tabular-nums">{x.idf}</td>
                <td className="py-2 text-right tabular-nums">{x.score}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-4 text-sm text-ink-muted">
          How the score is calculated: {k.formula}. {k.total_terms} candidate words from a vocabulary of {k.vocabulary_size}.
          {k.pos_filter.length > 0 && ` Only ${k.pos_filter.join(", ").toLowerCase()} words are considered, because verbs are rarely topical.`}
        </p>
      </Section>

      <Section title="Word groups" hint="Sequences of neighbouring content words within a sentence.">
        <div className="mb-4">
          <Segmented
            label="Word group length"
            options={analysis.ngrams.levels.map((l) => ({ value: l.n, label: l.label }))}
            value={level}
            onChange={setLevel}
          />
        </div>
        {ng.top.length === 0 ? (
          <p className="text-ink-muted">This document is too short to contain {ng.label.toLowerCase()}.</p>
        ) : (
          <BarsChart
            data={ng.top.slice(0, 10).map((x) => ({ name: x.ngram, count: x.count }))}
            series={[{ key: "count", name: "Occurrences", color: "#2c3a56" }]}
            categoryWidth={190}
            tableCaption={`${ng.label} by frequency`}
            caption={`${ng.total} ${ng.label.toLowerCase()} in total, ${ng.distinct} distinct.`}
          />
        )}
        <p className="mt-3 text-sm text-ink-muted">{analysis.ngrams.note}</p>
      </Section>
    </>
  );
}

export default function KeywordsPage() {
  return <AnalysisGate>{(analysis) => <Keywords analysis={analysis} />}</AnalysisGate>;
}
