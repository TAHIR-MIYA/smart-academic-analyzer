import { Link } from "react-router-dom";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/api.js";
import { ClassMark, EmptyState, Notice, PageHeader, Section, Spinner, StatRow, StatusBadge, buttonClass } from "../components/ui.jsx";
import { useApi } from "../hooks/useApi.js";
import { classMeta } from "../lib/classes.js";
import { fileTypeLabel, formatDate, formatNumber, formatPercent } from "../lib/format.js";

const EVALUATION_TITLES = {
  test_split: "Held-out test split",
  challenge_set: "Independent challenge set",
  real_set: "Real documents",
};

function ClassDistribution({ items }) {
  if (items.length === 0) {
    return <p className="text-ink-muted">No predictions saved yet. Analyse a document to see its class here.</p>;
  }
  const data = items.map((c) => ({ ...c, name: classMeta(c.label).name }));
  return (
    <figure>
      <div aria-hidden="true">
        <ResponsiveContainer width="100%" height={Math.max(150, data.length * 46)}>
          <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 4, left: 4 }}>
            <XAxis type="number" allowDecimals={false} tick={{ fontSize: 12, fill: "#586175" }} />
            <YAxis type="category" dataKey="name" width={116} tickLine={false} axisLine={false} tick={{ fontSize: 13, fill: "#17233b" }} />
            <Tooltip cursor={{ fill: "#e9ecf1" }} />
            <Bar dataKey="count" name="Documents" barSize={22} radius={[0, 3, 3, 0]} isAnimationActive={false}>
              {data.map((d) => (
                <Cell key={d.label} fill={classMeta(d.label).color} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <caption>Documents per predicted class</caption>
        <thead>
          <tr><th>Class</th><th>Documents</th></tr>
        </thead>
        <tbody>
          {data.map((d) => (
            <tr key={d.label}><td>{d.name}</td><td>{d.count}</td></tr>
          ))}
        </tbody>
      </table>
      <figcaption className="mt-2 text-sm text-ink-muted">
        Counted from the predictions saved for your documents. These are predictions, not measurements of accuracy.
      </figcaption>
    </figure>
  );
}

function ModelResults({ model }) {
  if (!model.trained || model.evaluations.length === 0) {
    return (
      <Notice kind="warning" title="The classifier has not been trained">
        Run <code className="font-mono text-[13px]">python -m app.ml.train</code> in the backend folder to train it and record its results.
      </Notice>
    );
  }
  return (
    <div>
      <ul className="space-y-4">
        {model.evaluations.map((ev) => (
          <li key={ev.name}>
            <div className="flex items-baseline justify-between gap-3">
              <p className="font-medium">{EVALUATION_TITLES[ev.name] ?? ev.name}</p>
              <p className="font-serif text-lg font-semibold">{formatPercent(ev.accuracy)}</p>
            </div>
            <div
              role="meter"
              aria-label={`${EVALUATION_TITLES[ev.name] ?? ev.name} accuracy`}
              aria-valuemin={0}
              aria-valuemax={1}
              aria-valuenow={ev.accuracy}
              className="mt-1 h-2 bg-rule"
            >
              <div className="h-full bg-ink-soft" style={{ width: `${ev.accuracy * 100}%` }} />
            </div>
            <p className="mt-1 text-sm text-ink-muted">
              {ev.n} documents. {ev.description}.
            </p>
          </li>
        ))}
      </ul>
      <p className="mt-4 text-sm text-ink-muted">{model.note}</p>
    </div>
  );
}

export default function DashboardPage() {
  const { data, error, loading, reload } = useApi(api.dashboard, []);

  if (loading && !data) return <Spinner label="Loading the dashboard" />;
  if (error && !data) {
    return (
      <>
        <PageHeader title="Dashboard" />
        <Notice kind="error" title="The dashboard could not be loaded">
          {error.message}
        </Notice>
        <button type="button" onClick={reload} className={`${buttonClass.secondary} mt-4`}>
          Try again
        </button>
      </>
    );
  }

  const empty = data.total_documents === 0;
  return (
    <>
      <PageHeader
        title="Dashboard"
        actions={
          <Link to="/upload" className={buttonClass.primary}>
            Upload documents
          </Link>
        }
      >
        What you have uploaded and what the classifier made of it.
      </PageHeader>

      <StatRow
        stats={[
          { label: "Documents", value: formatNumber(data.total_documents) },
          { label: "Analysed", value: formatNumber(data.analyzed_documents), note: `of ${formatNumber(data.total_documents)}` },
          { label: "Words stored", value: formatNumber(data.total_words) },
          { label: "Uncertain predictions", value: formatNumber(data.uncertain_predictions), note: "classifier confidence below the threshold" },
        ]}
      />

      {empty ? (
        <EmptyState
          title="No documents yet"
          action={
            <Link to="/upload" className={buttonClass.primary}>
              Upload your first document
            </Link>
          }
        >
          Upload a PDF, DOCX or TXT file to see its keywords, entities, document type and summary.
        </EmptyState>
      ) : (
        <div className="grid gap-x-12 lg:grid-cols-2">
          <Section title="Document types">
            <ClassDistribution items={data.class_distribution} />
          </Section>
          <Section title="Classifier results" hint="Measured on separate evaluation sets, not on your documents.">
            <ModelResults model={data.model} />
          </Section>
        </div>
      )}

      {!empty && (
        <Section title="Recent documents">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-rule text-ink-muted">
              <tr>
                <th className="py-2 pr-3 font-medium">Document</th>
                <th className="py-2 pr-3 font-medium">Type</th>
                <th className="py-2 pr-3 text-right font-medium">Words</th>
                <th className="py-2 pr-3 font-medium">Added</th>
                <th className="py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {data.recent_documents.map((d) => (
                <tr key={d.id}>
                  <td className="max-w-[16rem] truncate py-2.5 pr-3">
                    <Link to={`/documents/${d.id}`} className="font-medium text-brand-dark underline-offset-2 hover:underline">
                      {d.filename}
                    </Link>
                  </td>
                  <td className="py-2.5 pr-3">{fileTypeLabel(d.file_type)}</td>
                  <td className="py-2.5 pr-3 text-right tabular-nums">{formatNumber(d.word_count)}</td>
                  <td className="py-2.5 pr-3">{formatDate(d.created_at)}</td>
                  <td className="py-2.5"><StatusBadge done={d.analyzed} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}
    </>
  );
}
