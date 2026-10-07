// One colour per document class, used identically in charts, tables and headers (like a library classmark).
export const CLASS_META = {
  assignment: { name: "Assignment", color: "#2f5d9e" },
  notice: { name: "Notice", color: "#b86e0f" },
  question_paper: { name: "Question paper", color: "#7a3b8f" },
  project_report: { name: "Project report", color: "#1f6f5c" },
  study_material: { name: "Study material", color: "#56697d" },
};

export function classMeta(label) {
  return CLASS_META[label] ?? { name: label ?? "Unknown", color: "#586175" };
}
