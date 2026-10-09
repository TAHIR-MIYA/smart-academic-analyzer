# PROJECT REPORT

> **Before submitting:** (1) fill every `[...]` placeholder; (2) run `python -m app.ml.train` on your own computer and replace
> the numbers in Sections 14 and 15 with yours if they differ (the values below are from a reference run, described there);
> (3) insert the screenshots listed in Section 16; (4) check each reference in Section 21 against its original source.
> Delete this note.

---

## 1. Title

**Smart Academic Document Analyzer using Natural Language Processing**

An individual NLP mini project

| | |
|---|---|
| Student | [Name] |
| Roll number / Enrolment number | [Number] |
| Programme and semester | [Programme, semester] |
| Guide | [Name of guide] |
| Department and institution | [Department, institution] |
| Academic year | [Year] |

---

## 2. Abstract

Students and staff handle large numbers of academic documents (assignments, notices, question papers, project reports and
study material) and must read each one to learn what it is and what it says. This project is a locally running web
application that accepts PDF, DOCX and TXT files and analyses them with classical natural language processing. The pipeline
extracts and cleans the text, splits it into sentences and words, lemmatises with part-of-speech information, removes stop
words, ranks keywords with TF-IDF, counts unigrams, bigrams and trigrams, recognises named entities, classifies the document
type with a TF-IDF and logistic-regression model, produces an extractive summary, measures similarity to subject profiles and
to other documents, and reports readability and vocabulary diversity. Results are shown in an interactive dashboard and can
be exported as a PDF report or JSON. Every stage exposes its intermediate results so that each technique can be explained.
The classifier was trained on 240 synthetic documents. On a held-out split of the same data it scored 100% accuracy, which
the project treats as optimistic because the documents share templates (average similarity to the nearest training document
0.62). On an independent set of 25 hand-written documents it scored 88% accuracy (macro F1 0.88). No evaluation on real
documents has been performed yet, and the application supports adding them. The system runs on an ordinary laptop with no GPU
and no external service.

**Keywords:** natural language processing, document classification, TF-IDF, named entity recognition, extractive
summarisation, cosine similarity, readability.

---

## 3. Introduction

Academic institutions produce documents of many kinds, in several file formats, with inconsistent layout. Finding out what a
document is, what it is about and how it relates to others normally requires a person to read it. Natural language processing
(NLP) offers methods to automate parts of this: breaking text into units, normalising words, measuring how informative a
word is, recognising names, classifying whole documents, and selecting key sentences.

Modern large language models can perform many of these tasks, but they require substantial computing resources or an external
service, send the document elsewhere, and are difficult to explain technique by technique. For a mini project that must be
defended in a viva, and that should run on a student laptop, classical NLP and machine learning are the better fit: each step
is a well-known algorithm, results can be inspected, and training takes seconds.

This report describes the design, implementation and evaluation of such a system, the **Smart Academic Document Analyzer**.

---

## 4. Problem Statement

To design and build a web application that accepts academic documents in PDF, DOCX and TXT format and automatically extracts,
analyses, classifies, summarises and compares their textual content using NLP, such that:

* the application runs locally without a GPU or paid service;
* every NLP technique is genuinely implemented and its intermediate results are visible;
* classification quality is **measured and reported honestly**, distinguishing training and test results from single
  predictions;
* invalid input and missing resources are handled gracefully.

---

## 5. Objectives

1. Accept PDF, DOCX and TXT files, validate them (type, content signature, size, emptiness) and extract text robustly.
2. Implement the pipeline: cleaning, tokenisation, stop-word removal, lemmatisation, TF-IDF, n-grams, keyword extraction,
   named entity recognition, classification, extractive summarisation, similarity analysis and visualisation.
3. Show a before/after view of preprocessing and compare stemming with lemmatisation.
4. Classify documents as Assignment, Notice, Question Paper, Project Report or Study Material using an explainable classical
   model, and report accuracy, precision, recall, F1, a confusion matrix and prediction confidence.
5. Provide word, sentence and character statistics, readability analysis and vocabulary diversity analysis.
6. Provide an interactive dashboard and export of results as PDF and JSON.
7. Use a clean layered architecture with SQLite storage that can be migrated to MySQL, with logging, configuration through
   environment variables, and automated tests.

---

## 6. Existing System

Without such a tool, document handling in an academic setting is largely manual. A person opens each file, decides what kind
of document it is, skims it for the important points, and compares it with others by memory or by searching for words. This
has several shortcomings:

* it is slow and inconsistent between people;
* simple word search finds exact words but does not rank them by importance or show which words characterise a document;
* general text-analysis services exist, but they typically require uploading documents to a third party, are not designed
  around academic document types, and do not explain how a result was obtained;
* a prediction from a statistical model is often shown without any indication of how reliable the model is, which can
  mislead the user.

---

## 7. Proposed System

The proposed system is a local web application with these properties.

* **Complete, visible pipeline.** Each stage reports its output (counts at each stage, samples, formulas).
* **Explainable models.** TF-IDF, logistic regression, cosine similarity and rule-based summarisation can all be explained
  and inspected; the classifier shows the terms behind each prediction.
* **Honest evaluation.** The classifier's measured results (on a held-out split, an independent challenge set and optionally
  real documents) are kept separate from the prediction for any one document, in the interface and in exports.
* **Local and private.** No document leaves the computer; only the extracted text is stored.
* **Graceful failure.** Scanned PDFs, corrupt files, missing language data, a missing model, or a spaCy that cannot load are
  reported with a clear message and do not stop the rest of the application.

---

## 8. System Architecture

### 8.1 Layers

```text
Browser: React + Vite + Tailwind CSS + Recharts            frontend/
            | REST / JSON  (Vite proxies /api to the backend in development)
            v
FastAPI application                                         backend/app/
   api/        HTTP routers: documents, analysis, model, export, dashboard, health
   services/   orchestration: document, analysis, analysis store, export, model results
   nlp/        cleaning, tokenisation, preprocessing, pipeline, TF-IDF, n-grams, NER, summariser,
               similarity, readability, vocabulary, statistics, resource checks
   ml/         dataset loading, features, models, training, evaluation, prediction
   db/         SQLAlchemy engine and models        schemas/  Pydantic models        utils/  errors, validation
            |
            v
SQLite (documents, analysis_results)      Files: trained model, metrics, reference IDF, topic profiles
```

Routers contain no NLP logic. They call services, which call plain functions in `nlp` and `ml`. This keeps each technique
small, testable and explainable.

### 8.2 Data flow

1. The user uploads a file. The server validates it, extracts text with PyMuPDF, python-docx or a text decoder, and stores
   the text with metadata.
2. When an analysis is requested the stored text is cleaned and processed by the pipeline once; its result feeds keywords,
   n-grams, entities, classification, summary, similarity, readability and vocabulary.
3. The complete analysis is saved as one JSON record per document, and the frontend reads it to fill the tabs.
4. Export builds a JSON file or a PDF (ReportLab with Matplotlib charts) from the saved analysis and the training results.

### 8.3 Database

| Table | Columns |
|---|---|
| `documents` | id, original filename, file type, size, page count, character count, word count, extraction method, extracted text (LONGTEXT on MySQL), warnings (JSON), created at |
| `analysis_results` | id, document id (unique, foreign key with cascade delete), schema version, result (JSON), created at, updated at |

Changing `DATABASE_URL` is enough to move to MySQL.

### 8.4 Interface

Pages: Dashboard, Upload, Documents, and a tabbed document workspace (Overview, Preprocessing, Keywords, Entities,
Classification, Summary, Similarity, Statistics, Export).

---

## 9. Methodology

### 9.1 Development

The project was built incrementally in nine modules, each runnable and tested before the next: (1) backend foundation,
validation and extraction; (2) preprocessing and statistics; (3) keywords, n-grams and entities; (4) dataset and
classifier; (5) summarisation, similarity, readability and vocabulary; (6) persistence and export; (7) frontend shell,
dashboard and upload; (8) analysis tabs; (9) documentation.

### 9.2 Evaluation methodology

1. A synthetic dataset of 300 documents (60 per class) is split 80/20, stratified by class, with a fixed random seed.
2. Candidate models (3 classifiers x 2 feature variants) are compared by 5-fold stratified cross-validation on the
   **training part only**, using mean macro F1.
3. The selected model is fitted on the training part and scored **once** on the held-out test part, on an independent
   hand-written challenge set, and (if present) on real documents.
4. Training accuracy is stored but labelled as not a performance figure. The average similarity of each evaluation set to
   its nearest training document is reported to show how optimistic a score is.

### 9.3 Testing

Automated tests cover each NLP function (many with hand-computed expected values), the API, training end to end, and every
interface tab. Several tests were validated by deliberately breaking the code and confirming that they fail.

---

## 10. NLP Techniques

| Technique | What it does | Tool | Where |
|---|---|---|---|
| Text extraction | Reads PDF, DOCX and TXT | PyMuPDF, python-docx | `services/extraction.py` |
| Cleaning | Fixes ligatures, hyphenated line breaks, removes page numbers, headers, URLs | own rules | `nlp/cleaning.py` |
| Sentence tokenisation | Finds sentence boundaries (Punkt), including headings | NLTK | `nlp/tokenization.py` |
| Word tokenisation | Splits sentences into words | NLTK | `nlp/tokenization.py` |
| Case folding and word filtering | Lower-case; keep alphabetic words of two or more letters | own code | `nlp/pipeline.py` |
| Stop-word removal | Removes frequent function words | NLTK list plus extras | `nlp/resources.py` |
| Lemmatisation | Dictionary form using part of speech | spaCy | `nlp/preprocessing.py` |
| Stemming (comparison) | Rule-based suffix stripping | NLTK Porter | `nlp/preprocessing.py` |
| TF-IDF keywords | Ranks words by importance | own formula, checked against scikit-learn | `nlp/tfidf.py` |
| N-grams | Unigram, bigram, trigram frequencies | NLTK `ngrams` | `nlp/ngrams.py` |
| Named entity recognition | People, organisations, places, dates | spaCy | `nlp/ner.py` |
| Text classification | Predicts the document type | scikit-learn | `ml/` |
| Extractive summarisation | Selects key sentences | own algorithm | `nlp/summarizer.py` |
| Similarity | Cosine similarity to topic profiles and between documents | scikit-learn vectors | `nlp/similarity.py` |
| Readability | Flesch, Flesch-Kincaid, Gunning Fog, ARI | own formulas | `nlp/readability.py` |
| Vocabulary diversity | TTR, Root TTR, Corrected TTR, MATTR, hapax ratio, lexical density, Zipf data | own code | `nlp/vocabulary.py` |

---

## 11. Algorithms

**TF-IDF keyword score.** For a term t in document d: `tf = count(t) / total terms`; `idf = ln((1 + N) / (1 + df)) + 1`;
`score = tf x idf`. N and df come from, in order of preference, a reference table built from the training documents, the
sentences of the document (each treated as a document, at least five needed), or none (frequency only). Only nouns, proper
nouns and adjectives are scored.

**Classifier features.** scikit-learn `TfidfVectorizer`: word unigrams and bigrams, minimum document frequency 2,
sublinear term frequency `1 + ln(tf)`, L2 normalisation.

**Logistic regression (chosen).** One linear score per class, converted to probabilities with softmax; regularisation
parameter C = 10; at most 2000 iterations. The prediction is the class of highest probability; that probability is the
reported confidence, and below 0.5 the prediction is flagged uncertain. The explanation of a prediction lists the terms with
the largest positive value of (learned weight x TF-IDF value in the document).

**Linear SVM and Naive Bayes (compared).** `LinearSVC` (C = 1) wrapped in sigmoid calibration (3 folds) to obtain
probabilities; multinomial Naive Bayes with additive smoothing 0.1.

**Model selection.** Mean macro F1 over 5 stratified folds of the training part. Candidates within 0.005 of the best are
treated as tied; the first in a fixed order (logistic regression, linear SVM, naive Bayes; cleaned text before lemmas) is
chosen.

**Cosine similarity.** `cos(a, b) = a . b / (|a| |b|)` on TF-IDF vectors with IDF computed over the topic profiles plus the
document(s). A best topic score below 0.10 is reported as "no strong match" (a rule-of-thumb threshold). Sentence pairs with
cosine of at least 0.5 are reported as near copies.

**Extractive summary.** Sentence score = (sum of the TF-IDF weights of its distinct content words) / sqrt(number of those
words); the first usable sentence receives a 25% bonus; a sentence whose content words overlap an already chosen sentence by
more than 0.6 (Jaccard) is skipped; sentences shorter than 5 or longer than 60 words are ignored; the chosen sentences are
output in original order. The default length is about a quarter of the sentences, up to 8.

**Readability.** Flesch Reading Ease = 206.835 - 1.015 (words / sentences) - 84.6 (syllables / words). Flesch-Kincaid grade =
0.39 (words / sentences) + 11.8 (syllables / words) - 15.59. Gunning Fog = 0.4 [(words / sentences) + 100 (words of three or
more syllables / words)]. ARI = 4.71 (letters / words) + 0.5 (words / sentences) - 21.43. Syllables are estimated by counting
vowel groups with rules for silent endings.

**Vocabulary diversity.** TTR = types / tokens; Root TTR = types / sqrt(tokens); Corrected TTR = types / sqrt(2 tokens);
MATTR = mean TTR over every window of 50 consecutive words.

---

## 12. Dataset

| Set | Size | Source | Purpose |
|---|---|---|---|
| Training data (`datasets/raw`) | 300 documents, 60 per class | **Synthetic**, generated from templates by `generate_dataset.py` (seed 42) | Training, cross-validation and the held-out test split |
| Challenge set (`datasets/challenge`) | 25 documents, 5 per class | Written by hand in layouts different from the generator | Independent evaluation |
| Real set (`datasets/real`) | none supplied | Student's own documents | The only real-world estimate; evaluation only |
| Topic profiles (`datasets/topics`) | 10 files | Concept definitions plus key terms for ten subjects | Document-to-topic similarity |

**Classes:** assignment, notice, question paper, project report, study material.

**Generator design.** Ten subjects with seven concepts each are combined with templates that vary section order, header
style, marks formats, dates, optional sections, shouting headers, a missing first line and hard-wrapped lines. Vocabulary is
shared between classes, so the classifier must use genre cues rather than topic words. Duplicates are rejected.

**Limitations of the data.** Documents are template-generated, so evaluation on a split of them is optimistic and some
learned features are template phrases. The challenge set was written by the assistant that helped build the project after the
generator existed and has only 25 documents. Neither is real-world data. See `backend/datasets/DATASET.md`.

---

## 13. Implementation

### 13.1 Technology

| Layer | Technology (version used in development) |
|---|---|
| Language | Python 3.12 |
| API | FastAPI 0.142, Uvicorn 0.54, Pydantic 2.13 |
| NLP | NLTK 3.10, spaCy 3.8 (model `en_core_web_sm`) |
| Machine learning | scikit-learn 1.8, NumPy 2.4, joblib 1.5 |
| Documents | PyMuPDF 1.28, python-docx 1.2 |
| Database | SQLAlchemy 2.1 with SQLite |
| Reports | ReportLab 4.4, Matplotlib 3.10 |
| Frontend | React 18, Vite 5, Tailwind CSS 3, Recharts 3, React Router 6, axios |
| Tests | pytest, Vitest, Testing Library |

### 13.2 Notable implementation decisions

* **Validation by content.** Extension, size, emptiness and file signature are all checked; file names are sanitised.
* **Tokenise once.** NLTK tokenises; spaCy tags and lemmatises those same tokens, so both agree on word boundaries.
* **Heading-aware sentence splitting.** Short title-like lines between sentences are terminated so they are not glued to the
  next sentence.
* **Reference IDF.** Training writes a document-frequency table, which keyword extraction uses automatically.
* **Soft failure.** Classification, summary and topic similarity are optional sections; a failure leaves that section empty
  with its reason. spaCy is imported only when needed, so a spaCy that cannot load (for example blocked by an operating-system
  policy) does not stop the application.
* **Saved analyses** are versioned; an outdated record returns an explicit message and is recomputed on request.
* **Two-section classification page and PDF.** The prediction for a document and the classifier's measured results are shown
  separately.

### 13.3 Size and tests

About 3,800 lines of backend application code, 2,300 lines of backend tests, 450 lines for the dataset generator, and 4,200
lines of frontend source and tests. At the time of writing the backend suite has 293 passing tests and the
frontend suite 186 (development environment).

---

## 14. Experimental Results

> **Provenance.** The values in this section are the output of `python -m app.ml.train` in a reference run (Python 3.12.3,
> scikit-learn 1.8.0, random seed 42, 300 synthetic documents). They are copied from `metrics.json`, not estimated. Replace
> them with your own run's values if they differ, and add your real-document result if you have one.

### 14.1 Model selection (5-fold cross-validation on the 240 training documents)

| Features | Classifier | Mean accuracy | Mean macro F1 | Std of macro F1 |
|---|---|---|---|---|
| Cleaned text (stop words kept) | Logistic regression | 1.000 | 1.000 | 0.000 |
| Cleaned text | Linear SVM (calibrated) | 1.000 | 1.000 | 0.000 |
| Cleaned text | Naive Bayes | 1.000 | 1.000 | 0.000 |
| Lemmas (stop words removed) | Logistic regression | 1.000 | 1.000 | 0.000 |
| Lemmas | Linear SVM (calibrated) | 1.000 | 1.000 | 0.000 |
| Lemmas | Naive Bayes | 1.000 | 1.000 | 0.000 |

All six candidates tied, so cross-validation could not discriminate between them. Logistic regression on cleaned text was
selected by the fixed tie rule (Section 11), not by superior performance. Accuracy on the training data itself was 1.0 and
is not a performance figure.

### 14.2 Held-out test split (60 documents, 12 per class)

Accuracy 1.00; macro precision 1.00; macro recall 1.00; macro F1 1.00; confusion matrix with all 60 documents on the
diagonal. Average cosine similarity of a test document to its nearest training document: **0.62**.

### 14.3 Independent challenge set (25 documents, 5 per class)

Accuracy **0.88**; macro precision 0.9029; macro recall 0.88; macro F1 0.8822. Average similarity to the nearest training
document: **0.28**.

| Class | Precision | Recall | F1 | Documents |
|---|---|---|---|---|
| Assignment | 1.00 | 0.80 | 0.89 | 5 |
| Notice | 1.00 | 1.00 | 1.00 | 5 |
| Project report | 1.00 | 0.80 | 0.89 | 5 |
| Question paper | 0.80 | 0.80 | 0.80 | 5 |
| Study material | 0.71 | 1.00 | 0.83 | 5 |

Confusion matrix (rows: true class; columns: predicted class; order as in the table above):

|  | Assignment | Notice | Project report | Question paper | Study material |
|---|---|---|---|---|---|
| **Assignment** | 4 | 0 | 0 | 1 | 0 |
| **Notice** | 0 | 5 | 0 | 0 | 0 |
| **Project report** | 0 | 0 | 4 | 0 | 1 |
| **Question paper** | 0 | 0 | 0 | 4 | 1 |
| **Study material** | 0 | 0 | 0 | 0 | 5 |

The three misclassified documents were an assignment predicted as a question paper, a question paper predicted as study
material, and a project-report chapter predicted as study material.

### 14.4 Real-world set

Not evaluated: no real documents were supplied. [If you add documents to `datasets/real/`, report the result here with the
number of documents per class and list the misclassified files.]

### 14.5 Strongest terms learned (logistic regression weights)

| Class | Highest-weight terms |
|---|---|
| Assignment | assignment, marks, attach, prepare, suitable example |
| Notice | informed, hereby, hereby informed, students |
| Project report | system, the system, results, project, implementation |
| Question paper | marks, any, time, maximum marks |
| Study material | where, step, in practice, remember, unit |

Terms such as "hereby informed" and "maximum marks" are plausible genre cues. Several study-material terms ("in practice",
"step") come from phrases in the data generator and would not be expected in real study notes.

### 14.6 Other measured observations

| Observation | Value (development machine, indicative) |
|---|---|
| Training, including preprocessing 300 documents and all cross-validation | about 10 to 25 seconds |
| Preprocessing a 270,000-character text | about 3 seconds |
| Entity recognition on a 250,000-character text | about 2.6 seconds |
| Reference-corpus keyword IDF built from | 300 documents |

### 14.7 Interpretation

The 100% test-split score reflects an easy, template-based test and not general performance; the lower challenge-set score
(0.88) with much lower similarity to the training data (0.28) is the more informative figure, though 25 documents give a wide
uncertainty (one error changes accuracy by four percentage points). The summariser, entity recogniser, readability formulas
and similarity measures were not scored against reference data; their behaviour was checked by unit tests with
hand-computed values and by inspecting outputs.

---

## 15. Evaluation Metrics

For a class c, with TP true positives, FP false positives and FN false negatives:

* **Accuracy** = correct predictions / all predictions.
* **Precision** = TP / (TP + FP): of the documents predicted as c, the share that really are c.
* **Recall** = TP / (TP + FN): of the documents that really are c, the share found.
* **F1** = 2 x precision x recall / (precision + recall), the harmonic mean.
* **Macro average**: the unweighted mean over classes (each class counts equally); **weighted average** weights by class size.
* **Confusion matrix**: counts of true class (rows) against predicted class (columns).
* **Prediction confidence**: the highest class probability for one document; not an accuracy.
* **Cross-validation score**: mean macro F1 over stratified folds of the training data, used only for choosing a model.
* **Similarity to nearest training document**: for each evaluation document, the cosine similarity to the closest training
  document, averaged; a value near 1 means the evaluation set resembles the training data and scores will be optimistic.

Metrics are computed with scikit-learn and unit-tested against hand-computed examples. The summariser has no automatic score
because ROUGE needs human reference summaries.

---

## 16. Screenshots

Insert the figures below (see `docs/SCREENSHOTS.md` for how to capture each).

| Figure | Content | Page |
|---|---|---|
| 1 | Dashboard with figures, class distribution and classifier results | `/` |
| 2 | Upload page with a file in progress | `/upload` |
| 3 | Documents list | `/documents` |
| 4 | Document overview | `/documents/{id}` |
| 5 | Preprocessing tab: cleaning steps, stage chart, stemming vs lemmatisation | `/documents/{id}/preprocessing` |
| 6 | Keywords tab: TF-IDF chart and word groups | `/documents/{id}/keywords` |
| 7 | Entities tab | `/documents/{id}/entities` |
| 8 | Classification tab: this document's prediction | `/documents/{id}/classification` |
| 9 | Classification tab: evaluation, per-class table and confusion matrix | same page, lower section |
| 10 | Summary tab | `/documents/{id}/summary` |
| 11 | Similarity tab: topic similarity and a document comparison | `/documents/{id}/similarity` |
| 12 | Statistics tab: readability, vocabulary, Zipf plot | `/documents/{id}/statistics` |
| 13 | First page of an exported PDF report | Export tab |
| 14 | Terminal showing the training summary | `python -m app.ml.train` |
| 15 | Terminal showing the passing test suites | `pytest` and `npm test` |

`[Figure 1: Dashboard]` `[Figure 2: Upload]` ... (replace with the images).

---

## 17. Advantages

* Runs locally on an ordinary laptop with no GPU, no paid API and no data leaving the computer.
* Every technique is classical, implemented or configured in the project, and can be explained and inspected.
* Intermediate results are visible (cleaning counts, stage counts, formulas, scores).
* Measured results are reported honestly and separated from single predictions, with a quantity that shows how optimistic a
  score is.
* Robust input handling and graceful failure; clear error messages that say what to do.
* Layered, tested code with a documented API, a MySQL-ready database layer and PDF/JSON export.

---

## 18. Limitations

* The classifier was trained on synthetic data; the evaluation sets are small; no real-world accuracy is claimed.
* Cross-validation could not distinguish the candidate models, so the choice was made by a rule.
* Entity recognition uses a model trained on news and web text and mislabels some academic terms (for example exam
  markings).
* Scanned documents are not supported (no OCR); only English is supported.
* Readability uses an estimated syllable count and assumes continuous prose.
* Document-to-document similarity measures shared wording, not meaning.
* The summary is extractive and its quality was not scored automatically; headings can appear as short sentences.
* Header and footer removal is a heuristic and may remove a legitimately repeated line.
* Only five document types exist; a document of another kind is assigned to the nearest and only the confidence warns.

---

## 19. Future Scope

* Collect and label real documents, evaluate on them, and retrain.
* Add OCR for scanned documents and support for more languages.
* Use pretrained sentence embeddings for similarity and classification.
* Fine-tune entity recognition on academic text; add domain labels such as course and department.
* Add an "Other" class, calibrated probabilities and active learning from user corrections.
* Evaluate summaries with ROUGE using human reference summaries; try graph-based (TextRank) methods.
* Add user accounts, a background job queue for large files, and deployment with MySQL.

---

## 20. Conclusion

The project delivers a working, locally run application that applies classical NLP to academic documents end to end: it
extracts and cleans text, normalises words, finds keywords, phrases and entities, classifies the document type, summarises,
compares and measures documents, and presents everything in an interactive interface with PDF and JSON export. Each
technique is genuine and explainable, and intermediate results are visible. The classifier reaches 100% on a held-out split
of synthetic data and 88% on an independent challenge set; because the training data is synthetic and the evaluation sets are
small, these figures are not claimed as real-world accuracy, and the system is built to measure real performance as soon as
real documents are supplied. The main lesson is that a high score is meaningless without knowing how similar the test data is
to the training data, which is why the project reports that similarity directly.

---

## 21. References

> Check each reference against the original source before submission and add any further sources you used.

1. Bird, S., Klein, E. and Loper, E. (2009). *Natural Language Processing with Python*. O'Reilly Media.
2. Carroll, J. B. (1964). *Language and Thought*. Prentice-Hall. (type-token ratio variants)
3. Covington, M. A. and McFall, J. D. (2010). Cutting the Gordian knot: the moving-average type-token ratio (MATTR). *Journal of
   Quantitative Linguistics*, 17(2).
4. Flesch, R. (1948). A new readability yardstick. *Journal of Applied Psychology*, 32(3).
5. Gunning, R. (1952). *The Technique of Clear Writing*. McGraw-Hill.
6. Guiraud, P. (1960). *Problemes et methodes de la statistique linguistique*. Presses Universitaires de France.
7. Honnibal, M. and Montani, I. spaCy: industrial-strength natural language processing in Python. https://spacy.io
8. Jurafsky, D. and Martin, J. H. *Speech and Language Processing* (3rd edition draft). https://web.stanford.edu/~jurafsky/slp3/
9. Kincaid, J. P., Fishburne, R. P., Rogers, R. L. and Chissom, B. S. (1975). *Derivation of New Readability Formulas for Navy
   Enlisted Personnel*. Naval Technical Training Command, Research Branch Report 8-75.
10. Kiss, T. and Strunk, J. (2006). Unsupervised multilingual sentence boundary detection. *Computational Linguistics*, 32(4).
11. Luhn, H. P. (1958). The automatic creation of literature abstracts. *IBM Journal of Research and Development*, 2(2).
12. Manning, C. D., Raghavan, P. and Schutze, H. (2008). *Introduction to Information Retrieval*. Cambridge University Press.
13. Pedregosa, F. et al. (2011). Scikit-learn: machine learning in Python. *Journal of Machine Learning Research*, 12.
14. Porter, M. F. (1980). An algorithm for suffix stripping. *Program*, 14(3).
15. Salton, G. and Buckley, C. (1988). Term-weighting approaches in automatic text retrieval. *Information Processing and
    Management*, 24(5).
16. Smith, E. A. and Senter, R. J. (1967). *Automated Readability Index*. Aerospace Medical Research Laboratories, AMRL-TR-66-220.
17. Weischedel, R. et al. (2013). *OntoNotes Release 5.0*. Linguistic Data Consortium, LDC2013T19.
18. Zipf, G. K. (1949). *Human Behavior and the Principle of Least Effort*. Addison-Wesley.
19. Documentation of FastAPI, NLTK, PyMuPDF, python-docx, SQLAlchemy, ReportLab, React, Vite, Tailwind CSS and Recharts.

---

## Appendix A. Reproducing the results

```powershell
cd backend
python -m scripts.setup_nlp
python -m datasets.generate_dataset --per-class 60 --seed 42     # optional: the dataset is included
python -m app.ml.train                                           # prints the summary; writes app/ml/artifacts/metrics.json
python -m pytest -q
cd ..\frontend ; npm test
```
