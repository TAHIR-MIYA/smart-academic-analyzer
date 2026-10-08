import { useDocument } from "../hooks/useDocument.js";
import { EmptyState, Spinner, buttonClass } from "./ui.jsx";

/** Shows its content only once the document has been analysed; otherwise offers to run the analysis. */
export default function AnalysisGate({ children }) {
  const { analysis, running, run } = useDocument();
  if (analysis) return children(analysis);
  return (
    <EmptyState
      title="This document has not been analysed yet"
      action={
        <button type="button" className={buttonClass.primary} onClick={run} disabled={running}>
          Run analysis
        </button>
      }
    >
      {running ? <Spinner label="Analysing" /> : "Run the analysis to fill this page. It usually takes a few seconds."}
    </EmptyState>
  );
}
