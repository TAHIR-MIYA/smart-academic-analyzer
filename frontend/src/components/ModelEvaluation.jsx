import { useState } from "react";
import { api } from "../api/api.js";
import { useApi } from "../hooks/useApi.js";
import { classMeta } from "../lib/classes.js";
import { formatDate, formatPercent } from "../lib/format.js";
import { ConfusionMatrix } from "./charts.jsx";
import { Notice, Section, Spinner, StatRow } from "./ui.jsx";

const SET_TITLES = { test_split: "Held-out test split", challenge_set: "Independent challenge set", real_set: "Real documents" };
const FEATURES = { cleaned_text: "Cleaned text, stop words kept", lemma_text: "Lemmas, stop words removed" };
const CLASSIFIERS = { logistic_regression: "Logistic regression", linear_svm: "Linear SVM", naive_bayes: "Naive Bayes" };
const two = (x) => x.toFixed(2);

/** Results of training: measured on evaluation sets, completely separate from any one document's prediction. */
export default function ModelEvaluation() {
  const { data: m, error, loading } = useApi(api.modelMetrics, []);
  const [picked, setPicked] = useState(null);

  if (loading && !m) return <Spinner label="Loading the training results" />;
  if (error && !m) {
    return (
      <Notice kind="warning" title="No training results found">
        {error.message} Run <code className="font-mono text-[13px]">python -m app.ml.train</code> in the backend folder to create them.
      </Notice>
    );
  }

  const sets = Object.entries(m.evaluations).filter(([, v]) => v);
  const current = picked && m.evaluations[picked] ? picked : sets[0][0];
  const ev = m.evaluations[current];
  const names = Object.fromEntries(ev.labels.map((l) => [l, classMeta(l).name]));
  const f1s = m.selection.candidates.map((c) => c.cv_macro_f1_mean);
  const tied = Math.max(...f1s) - Math.min(...f1s) < 0.005;

  return (
    <>
      <Notice kind="info" title="These results describe the classifier, not this document">
        They were measured on separate evaluation sets after training on {m.dataset.train_size} documents ({m.dataset.source}). Trained{" "}
        {formatDate(m.created_at)}.
      </Notice>

      <div className="mt-6">
        <div role="group" aria-label="Evaluation set" className="mb-3 flex flex-wrap gap-2">
          {sets.map(([key]) => (
            <button key={key} type="button" aria-pressed={key === current} onClick={() => setPicked(key)} className={`border px-3 py-1.5 text-sm font-medium ${key === current ? "border-ink bg-ink text-white" : "border-rule bg-paper-raised"}`}>
              {SET_TITLES[key] ?? key}
            </button>
          ))}
        </div>
        <p className="mb-4 text-ink-muted">
          {ev.description}. {ev.n} documents.
        </p>

        <StatRow
          stats={[
            { label: "Accuracy", value: formatPercent(ev.accuracy) },
            { label: "Macro precision", value: two(ev.macro_precision) },
            { label: "Macro recall", value: two(ev.macro_recall) },
            { label: "Macro F1", value: two(ev.macro_f1) },
          ]}
        />

        <dl className="mb-6 grid gap-x-8 gap-y-1 text-sm text-ink-muted md:grid-cols-3">
          <div><dt className="inline font-medium text-ink">Precision: </dt><dd className="inline">of the documents predicted as a class, the share that were right.</dd></div>
          <div><dt className="inline font-medium text-ink">Recall: </dt><dd className="inline">of the documents truly in a class, the share the classifier found.</dd></div>
          <div><dt className="inline font-medium text-ink">F1: </dt><dd className="inline">the balance of precision and recall. Macro averages treat every class equally.</dd></div>
        </dl>

        <p className="mb-6 text-sm">
          Average similarity to the nearest training document: <strong className="tabular-nums">{ev.mean_max_similarity_to_train}</strong>.{" "}
          <span className="text-ink-muted">
            The closer to 1, the more these documents resemble the training data, and the more optimistic the scores are.
          </span>
        </p>

        <h3 className="mb-2 text-base font-semibold">Results for each class</h3>
        <table className="mb-8 w-full max-w-2xl text-left text-sm">
          <thead className="border-b border-rule text-ink-muted">
            <tr>
              <th className="py-2 pr-3 font-medium">Class</th>
              <th className="py-2 pr-3 text-right font-medium">Precision</th>
              <th className="py-2 pr-3 text-right font-medium">Recall</th>
              <th className="py-2 pr-3 text-right font-medium">F1</th>
              <th className="py-2 text-right font-medium">Documents</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-rule">
            {ev.labels.map((l) => {
              const r = ev.per_class[l];
              return (
                <tr key={l}>
                  <td className="py-2 pr-3 font-medium" style={{ color: classMeta(l).color }}>{names[l]}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{two(r.precision)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{two(r.recall)}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{two(r.f1)}</td>
                  <td className="py-2 text-right tabular-nums">{r.support}</td>
                </tr>
              );
            })}
          </tbody>
        </table>

        <h3 className="mb-2 text-base font-semibold">Confusion matrix</h3>
        <ConfusionMatrix matrix={ev.confusion_matrix} labels={ev.labels} names={names} />

        <h3 className="mb-2 mt-8 text-base font-semibold">Documents the classifier got wrong</h3>
        {ev.misclassified.length === 0 ? (
          <p className="text-ink-muted">None in this set.</p>
        ) : (
          <ul className="divide-y divide-rule border-y border-rule text-sm">
            {ev.misclassified.map((x) => (
              <li key={x.file} className="py-2">
                <span className="font-medium">{x.file}</span>: is {classMeta(x.true).name}, predicted {classMeta(x.predicted).name}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-10">
        <Section title="How the model was chosen" hint={m.selection.method}>
          <table className="w-full text-left text-sm">
            <thead className="border-b border-rule text-ink-muted">
              <tr>
                <th className="py-2 pr-3 font-medium">Features</th>
                <th className="py-2 pr-3 font-medium">Classifier</th>
                <th className="py-2 pr-3 text-right font-medium">Cross-validated macro F1</th>
                <th className="py-2 font-medium"><span className="sr-only">Chosen</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-rule">
              {m.selection.candidates.map((c) => {
                const chosen = c.feature_set === m.selection.chosen.feature_set && c.classifier === m.selection.chosen.classifier;
                return (
                  <tr key={`${c.feature_set}-${c.classifier}`} className={chosen ? "bg-brand-tint font-medium" : ""}>
                    <td className="py-2 pr-3">{FEATURES[c.feature_set] ?? c.feature_set}</td>
                    <td className="py-2 pr-3">{CLASSIFIERS[c.classifier] ?? c.classifier}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">{two(c.cv_macro_f1_mean)} ± {two(c.cv_macro_f1_std)}</td>
                    <td className="py-2 pr-2 text-right text-brand-dark">{chosen ? "Chosen" : ""}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {tied && (
            <div className="mt-4">
              <Notice kind="warning" title="Cross-validation could not tell these models apart">
                Their scores are within 0.005 of each other, so the choice was made by a fixed rule, not by merit: {m.selection.tie_rule}.
              </Notice>
            </div>
          )}
          <p className="mt-4 text-sm text-ink-muted">
            Accuracy on the training data itself was {formatPercent(m.train_accuracy)}. That figure only shows the model fits what it
            was shown and is not a measure of performance.
          </p>
        </Section>

        {Object.keys(m.top_features).length > 0 && (
          <Section title="What the model looks for" hint="The terms with the largest positive weight for each class.">
            <dl className="space-y-3">
              {Object.entries(m.top_features).map(([label, terms]) => (
                <div key={label} className="grid gap-1 md:grid-cols-[10rem_1fr]">
                  <dt className="font-medium" style={{ color: classMeta(label).color }}>{classMeta(label).name}</dt>
                  <dd className="flex flex-wrap gap-2">
                    {terms.slice(0, 8).map((t) => (
                      <span key={t.term} className="border border-rule bg-paper-raised px-2 py-0.5 text-sm">{t.term}</span>
                    ))}
                  </dd>
                </div>
              ))}
            </dl>
          </Section>
        )}

        <Section title="Read these results with care">
          <ul className="list-disc space-y-1 pl-5 text-ink-soft">
            {m.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </Section>
      </div>
    </>
  );
}
