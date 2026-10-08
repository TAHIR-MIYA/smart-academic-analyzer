import { useOutletContext } from "react-router-dom";

/** What the document layout shares with every tab: { doc, analysis, running, run, runError, elapsed }. */
export function useDocument() {
  return useOutletContext();
}
