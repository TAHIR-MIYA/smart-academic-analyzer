export const health = (over = {}) => ({
  status: "ok", version: "0.1.0", max_upload_mb: 1,
  model: { trained: true }, nlp_resources: { ready: true }, ...over,
});

export const doc = (over = {}) => ({
  id: 3, original_filename: "notes.txt", file_type: "txt", size_bytes: 2048, page_count: null, char_count: 120,
  word_count: 20, extraction_method: "text:utf-8", warnings: [], created_at: "2026-10-05T10:00:00",
  extracted_text: "Short extracted text.", analyzed: false, ...over,
});

export const analysis = (over = {}) => ({
  schema_version: 1, generated_at: "2026-10-05T11:00:00+00:00", app_version: "0.1.0",
  classification: { label: "notice", display_name: "Notice", confidence: 0.95, is_confident: true, confidence_threshold: 0.5 },
  classification_error: null,
  keywords: { keywords: [{ term: "library", count: 3 }, { term: "student", count: 2 }] },
  summary: { summary: [{ index: 0, text: "The library will remain closed on Friday." }, { index: 2, text: "Students should note this." }] },
  summary_error: null,
  readability: { reading_level: "Plain English (8th-9th grade)", reliable: true },
  ...over,
});

export const dashboard = (over = {}) => ({
  total_documents: 12, analyzed_documents: 9, total_words: 14231, by_file_type: { pdf: 5, txt: 7 },
  class_distribution: [{ label: "notice", display_name: "Notice", count: 5 }, { label: "assignment", display_name: "Assignment", count: 3 }],
  uncertain_predictions: 2,
  recent_documents: [{ id: 3, filename: "notes.txt", file_type: "txt", word_count: 20, analyzed: true, created_at: "2026-10-05T10:00:00" }],
  model: {
    trained: true, trained_at: "2026-10-05T09:00:00+00:00", classifier: "logistic_regression", feature_set: "cleaned_text",
    evaluations: [
      { name: "test_split", description: "Stratified hold-out split of the generated dataset", n: 60, accuracy: 1, macro_f1: 1 },
      { name: "challenge_set", description: "Independent hand-written documents", n: 25, accuracy: 0.88, macro_f1: 0.88 },
    ],
    note: "These figures describe the classifier in general and are not a measure of any single prediction.",
  },
  ...over,
});
