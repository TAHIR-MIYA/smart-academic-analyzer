import { useState } from "react";
import AnalysisGate from "../../components/AnalysisGate.jsx";
import { BarsChart } from "../../components/charts.jsx";
import { Notice, Section } from "../../components/ui.jsx";

function Entities({ analysis }) {
  const e = analysis.entities;
  const [label, setLabel] = useState(null);
  const groups = label ? e.groups.filter((g) => g.label === label) : e.groups;

  if (e.groups.length === 0) {
    return (
      <Section title="Named entities">
        <p className="text-ink-muted">No people, organisations, places, dates or other named entities were found in this document.</p>
      </Section>
    );
  }
  return (
    <>
      <Section title="Named entities" hint={`${e.total_entities} mentions of ${e.unique_entities} distinct entities, found by ${e.model}.`}>
        <div className="mb-5">
          <Notice kind="warning" title="Labels can be wrong for academic text">
            The model was trained on news and web text. Technical terms, exam markings such as "Q.1" and course names are sometimes
            labelled as people, places or money. Check the examples before relying on a label.
          </Notice>
        </div>
        <BarsChart
          data={e.groups.map((g) => ({ name: g.label, mentions: g.total }))}
          series={[{ key: "mentions", name: "Mentions", color: "#1f6f5c" }]}
          categoryWidth={90}
          tableCaption="Entity mentions by label"
        />
      </Section>

      <Section title="Entities by type">
        <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter by entity type">
          <button type="button" aria-pressed={label === null} onClick={() => setLabel(null)} className={`border px-3 py-1 text-sm ${label === null ? "border-ink bg-ink text-white" : "border-rule bg-paper-raised"}`}>
            All types
          </button>
          {e.groups.map((g) => (
            <button key={g.label} type="button" aria-pressed={label === g.label} onClick={() => setLabel(g.label)} className={`border px-3 py-1 text-sm ${label === g.label ? "border-ink bg-ink text-white" : "border-rule bg-paper-raised"}`}>
              {g.label}
            </button>
          ))}
        </div>
        <ul className="divide-y divide-rule border-y border-rule">
          {groups.map((g) => (
            <li key={g.label} className="grid gap-2 py-4 md:grid-cols-[14rem_1fr]">
              <div>
                <h3 className="text-base font-semibold">{g.label}</h3>
                <p className="text-sm text-ink-muted">{g.description}</p>
                <p className="mt-1 text-sm">{g.total} mentions, {g.unique} distinct</p>
              </div>
              <ul className="flex flex-wrap content-start gap-2" aria-label={`${g.label} examples`}>
                {g.top.map((t) => (
                  <li key={t.text} className="border border-rule bg-paper-raised px-2.5 py-1 text-sm">
                    {t.text} <span className="text-xs text-ink-muted">{t.count}</span>
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </Section>
    </>
  );
}

export default function EntitiesPage() {
  return <AnalysisGate>{(analysis) => <Entities analysis={analysis} />}</AnalysisGate>;
}
