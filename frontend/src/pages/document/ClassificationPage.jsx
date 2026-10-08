import AnalysisGate from "../../components/AnalysisGate.jsx";
import ModelEvaluation from "../../components/ModelEvaluation.jsx";
import { BarsChart } from "../../components/charts.jsx";
import { ClassMark, Notice, Section } from "../../components/ui.jsx";
import { classMeta } from "../../lib/classes.js";
import { formatPercent } from "../../lib/format.js";

function Prediction({ analysis }) {
  const c = analysis.classification;
  if (!c) {
    return (
      <Notice kind="info" title="No document type was predicted">
        {analysis.classification_error ?? "No trained classifier is available."} Run{" "}
        <code className="font-mono text-[13px]">python -m app.ml.train</code>, then run the analysis again.
      </Notice>
    );
  }
  return (
    <>
      <div className="mb-5 flex flex-wrap items-center gap-4">
        <span className="text-2xl"><ClassMark label={c.label} confidence={c.confidence} uncertain={!c.is_confident} /></span>
      </div>
      {!c.is_confident && (
        <div className="mb-5">
          <Notice kind="warning" title="The classifier is not sure about this one">
            Its best guess has a probability of {formatPercent(c.confidence)}, below the {Math.round(c.confidence_threshold * 100)}% needed to call
            it confident. Treat the type as a suggestion and check the other probabilities.
          </Notice>
        </div>
      )}
      <BarsChart
        data={c.probabilities.map((p) => ({ name: p.display_name, probability: p.probability, color: classMeta(p.label).color }))}
        series={[{ key: "probability", name: "Probability", color: "#2c3a56" }]}
        format={(v) => (typeof v === "number" ? formatPercent(v) : v)}
        categoryWidth={120}
        tableCaption="Probability of each document type"
      />
      {c.explanation.length > 0 && (
        <div className="mt-6">
          <h3 className="mb-2 text-base font-semibold">Terms that pushed the prediction</h3>
          <ul className="flex flex-wrap gap-2" aria-label="Terms behind the prediction">
            {c.explanation.map((t) => (
              <li key={t.term} className="bg-mark-tint px-2.5 py-1 text-sm">
                <span className="font-medium">{t.term}</span>
                <span className="ml-1.5 text-xs text-ink-muted">{t.contribution}</span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-sm text-ink-muted">Terms from this document that point towards {c.display_name}. Larger numbers pushed harder.</p>
        </div>
      )}
      <p className="mt-6 text-sm text-ink-muted">
        {c.model.classifier.replace("_", " ")} on {c.model.feature_set.replace("_", " ")} features, trained on {c.model.n_training_documents} documents. {c.disclaimer}
      </p>
    </>
  );
}

export default function ClassificationPage() {
  return (
    <>
      <Section title="Prediction for this document" hint="One prediction, with the classifier's own confidence.">
        <AnalysisGate>{(analysis) => <Prediction analysis={analysis} />}</AnalysisGate>
      </Section>
      <Section title="How well does the classifier work?" hint="Measured on separate evaluation sets.">
        <ModelEvaluation />
      </Section>
    </>
  );
}
