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
  document: { id: 3, filename: "notes.txt" },
  preprocessing: {
    truncated: false, warnings: [],
    cleaning: {
      operations: [
        { name: "Hyphenated line breaks", description: "Rejoined words split across lines with a hyphen", count: 2 },
        { name: "URLs", description: "Removed web addresses", count: 0 },
      ],
      original_characters: 1200, cleaned_characters: 1100,
    },
    stages: [
      { name: "1. Tokenisation", description: "NLTK word_tokenize", token_count: 300, unique_count: 150, sample: ["The", "library", ","] },
      { name: "2. Word filtering", description: "Keep alphabetic tokens", token_count: 250, unique_count: 140, sample: ["The", "library"] },
      { name: "3. Case folding", description: "Lower-case", token_count: 250, unique_count: 130, sample: ["the", "library"] },
      { name: "4. Stop-word removal", description: "Remove function words", token_count: 120, unique_count: 90, sample: ["library", "closed"] },
      { name: "5. Lemmatisation", description: "Dictionary forms", token_count: 120, unique_count: 80, sample: ["library", "close"] },
    ],
    removed_stopwords: [{ term: "the", count: 30 }, { term: "and", count: 12 }],
    stopword_removal_rate: 0.52,
    top_terms: [{ term: "library", count: 5 }],
    stem_vs_lemma: [{ word: "studying", stem: "studi", lemma: "study", pos: "VERB" }],
    original_sample: "The library will remain closed on Friday.", processed_sample: "library remain close friday",
    sentences_sample: [],
  },
  statistics: {
    characters: 1200, characters_no_spaces: 1000, words: 250, unique_words: 140, sentences: 12, paragraphs: 3,
    avg_word_length: 5.1, avg_sentence_length: 20.8, longest_sentence_words: 38, reading_time_minutes: 1.3,
    sentence_length_distribution: [{ range: "1-10", count: 2 }, { range: "11-20", count: 6 }, { range: "21-30", count: 4 }],
    word_length_distribution: [{ length: "2", count: 20 }, { length: "3", count: 40 }],
  },
  keywords: {
    idf_mode: "document_sentences", idf_description: "IDF computed over the 12 sentences of this document (each sentence is treated as one document).",
    idf_n_documents: 12, pos_filter: ["NOUN", "PROPN", "ADJ"], formula: "score = tf x idf", total_terms: 90, vocabulary_size: 60,
    keywords: [
      { term: "library", count: 5, tf: 0.0556, idf: 2.1, score: 0.1167, relative_score: 1 },
      { term: "student", count: 3, tf: 0.0333, idf: 2.4, score: 0.08, relative_score: 0.69 },
      { term: "friday", count: 1, tf: 0.0111, idf: 3.5, score: 0.0389, relative_score: 0.33 },
    ],
  },
  ngrams: {
    note: "Built from lemmatised content words within sentences (stop words removed first).",
    levels: [
      { n: 1, label: "Unigrams", total: 120, distinct: 80, top: [{ ngram: "library", count: 5 }] },
      { n: 2, label: "Bigrams", total: 110, distinct: 90, top: [{ ngram: "library close", count: 2 }] },
      { n: 3, label: "Trigrams", total: 100, distinct: 95, top: [{ ngram: "library close friday", count: 1 }] },
    ],
  },
  entities: {
    model: "en_core_web_sm", total_entities: 6, unique_entities: 4,
    groups: [
      { label: "ORG", description: "Companies, agencies, institutions, etc.", total: 4, unique: 2, top: [{ text: "Princeton University", count: 3 }, { text: "Google", count: 1 }] },
      { label: "DATE", description: "Absolute or relative dates or periods", total: 2, unique: 2, top: [{ text: "Friday", count: 1 }, { text: "1933", count: 1 }] },
    ],
  },
  classification: {
    label: "notice", display_name: "Notice", confidence: 0.95, is_confident: true, confidence_threshold: 0.5,
    probabilities: [
      { label: "notice", display_name: "Notice", probability: 0.95 }, { label: "assignment", display_name: "Assignment", probability: 0.03 },
      { label: "study_material", display_name: "Study Material", probability: 0.02 },
    ],
    explanation: [{ term: "hereby informed", contribution: 0.31 }, { term: "all students", contribution: 0.22 }],
    model: { classifier: "logistic_regression", feature_set: "cleaned_text", trained_at: "2026-10-05T09:00:00+00:00", n_training_documents: 240 },
    disclaimer: "This is a single prediction for the uploaded document.",
  },
  classification_error: null,
  summary: {
    method: "TF-IDF sentence scoring with position bonus and redundancy filter", idf_mode: "document_sentences",
    sentences_in_document: 12, sentences_eligible: 10, sentences_selected: 2, compression_ratio: 0.18,
    summary: [
      { index: 0, text: "The library will remain closed on Friday.", score: 0.4, relative_score: 1, words: 8 },
      { index: 2, text: "Students should note this.", score: 0.3, relative_score: 0.75, words: 4 },
    ],
    summary_text: "The library will remain closed on Friday. Students should note this.",
    sentence_scores: [{ index: 0, score: 0.4, selected: true, words: 8 }, { index: 1, score: 0.1, selected: false, words: 6 }, { index: 2, score: 0.3, selected: true, words: 4 }],
    parameters: { position_bonus: 0.25, redundancy_threshold: 0.6, min_words: 5, max_words: 60 }, note: null,
  },
  summary_error: null,
  readability: {
    reliable: true, warning: null, reading_level: "Plain English (8th-9th grade)", note: "Syllables are estimated with a vowel-group heuristic, so scores are approximate.",
    counts: { words: 250, sentences: 12, syllables: 380, complex_words: 20, letters: 1100 }, averages: { words_per_sentence: 20.8, syllables_per_word: 1.52, letters_per_word: 4.4 },
    scores: [
      { name: "Flesch Reading Ease", value: 62.5, interpretation: "Plain English (8th-9th grade)", formula: "206.835 - 1.015 x (words/sentences) - 84.6 x (syllables/words)" },
      { name: "Flesch-Kincaid Grade Level", value: 8.9, interpretation: "About US school grade 8.9", formula: "0.39 x ..." },
    ],
  },
  vocabulary: {
    reliable: true, warning: null, tokens: 250, types: 140, lemma_types: 120, hapax_count: 90, dis_legomena_count: 20,
    measures: [
      { key: "ttr", name: "Type-Token Ratio (TTR)", value: 0.56, description: "Distinct words divided by total words." },
      { key: "mattr", name: "MATTR (window 50)", value: 0.79, description: "Average TTR over windows of 50 words." },
    ],
    frequency_spectrum: [{ occurrences: "1", count: 90 }, { occurrences: "2", count: 20 }],
    zipf: [{ rank: 1, word: "the", count: 20 }, { rank: 2, word: "library", count: 10 }, { rank: 3, word: "close", count: 6 }],
  },
  topic_similarity: {
    method: "Cosine similarity of TF-IDF vectors; IDF computed over 11 documents (10 topic profiles + this document)", topics_compared: 10,
    best_topic: "Database Management Systems", best_similarity: 0.23, is_weak_match: false, weak_match_threshold: 0.1, note: null,
    similarities: [{ topic: "Database Management Systems", similarity: 0.23 }, { topic: "Data Structures", similarity: 0.07 }],
    matched_terms: [{ term: "database", weight: 0.12 }, { term: "redundancy", weight: 0.08 }],
  },
  topic_similarity_error: null,
  ...over,
});

export const metrics = (over = {}) => ({
  created_at: "2026-10-05T09:00:00+00:00",
  dataset: { n_documents: 300, train_size: 240, test_size: 60, source: "synthetic (template-generated; see datasets/DATASET.md)" },
  selection: {
    method: "5-fold stratified cross-validation on the training split only", criterion: "mean macro-F1",
    tie_rule: "candidates within 0.005 of the best are tied; the first in canonical order wins",
    candidates: [
      { feature_set: "cleaned_text", classifier: "logistic_regression", cv_accuracy_mean: 1, cv_macro_f1_mean: 1, cv_macro_f1_std: 0 },
      { feature_set: "lemma_text", classifier: "naive_bayes", cv_accuracy_mean: 0.99, cv_macro_f1_mean: 0.99, cv_macro_f1_std: 0.01 },
    ],
    chosen: { feature_set: "cleaned_text", classifier: "logistic_regression" },
  },
  train_accuracy: 1,
  evaluations: {
    test_split: {
      description: "Stratified hold-out split of the generated dataset (same source as training)", n: 60, accuracy: 1, macro_precision: 1,
      macro_recall: 1, macro_f1: 1, weighted_f1: 1, mean_max_similarity_to_train: 0.62, misclassified: [],
      labels: ["assignment", "notice"], confusion_matrix: [[30, 0], [0, 30]],
      per_class: { assignment: { precision: 1, recall: 1, f1: 1, support: 30 }, notice: { precision: 1, recall: 1, f1: 1, support: 30 } },
    },
    challenge_set: {
      description: "Independent hand-written documents in different styles", n: 25, accuracy: 0.88, macro_precision: 0.9, macro_recall: 0.88,
      macro_f1: 0.88, weighted_f1: 0.88, mean_max_similarity_to_train: 0.28,
      misclassified: [{ file: "assignment/sample_04.txt", true: "assignment", predicted: "question_paper" }],
      labels: ["assignment", "notice"], confusion_matrix: [[4, 1], [0, 5]],
      per_class: { assignment: { precision: 1, recall: 0.8, f1: 0.89, support: 5 }, notice: { precision: 0.83, recall: 1, f1: 0.91, support: 5 } },
    },
    real_set: null,
  },
  top_features: { notice: [{ term: "hereby informed", weight: 2.4 }, { term: "notice", weight: 2.1 }], assignment: [{ term: "submission", weight: 1.9 }] },
  notes: ["train_accuracy is measured on data the model was fitted to and must not be quoted as performance.", "test_split comes from the same generator as the training data, so it is an optimistic estimate."],
  ...over,
});

export const comparison = (over = {}) => ({
  document_a: { id: 3, filename: "notes.txt" }, document_b: { id: 4, filename: "other.txt" },
  method: "Cosine similarity of TF-IDF vectors; IDF computed over 12 documents", cosine_similarity: 0.62, vocabulary_overlap_jaccard: 0.31,
  interpretation: "Related content", interpretation_note: "Interpretation bands are rule-of-thumb values, not calibrated thresholds.",
  shared_terms: [{ term: "library", weight: 0.2 }], pair_threshold: 0.5,
  similar_sentence_pairs: [{ similarity: 0.97, index_a: 0, sentence_a: "The library will remain closed on Friday.", index_b: 3, sentence_b: "The library will remain closed on Friday for stock checks." }],
  note: "Cosine similarity measures shared wording, not shared subject.",
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
