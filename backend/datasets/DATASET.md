# Dataset documentation

## 1. Purpose
Train and evaluate a classifier that assigns an academic document to one of five classes:
`assignment`, `notice`, `question_paper`, `project_report`, `study_material`.

## 2. Folder structure
```
datasets/
  generate_dataset.py     deterministic generator (seed 42 by default)
  raw/<class>/doc_NNN.txt 300 synthetic training documents (60 per class)  + labels.csv manifest
  challenge/<class>/*.txt 25 hand-written documents (5 per class), written in different styles
  real/<class>/           EMPTY - put your own real documents here (.txt, .pdf or .docx)
```

## 3. Provenance (read this before quoting any number)
| Folder | Source | How it should be described |
|---|---|---|
| `raw/` | **Synthetic.** Produced by `generate_dataset.py` from templates with random subjects, wording, section order, dates, marks formats and line wrapping. Documents are unique but share templates. | "Template-generated training data" |
| `challenge/` | **Hand-written by the AI assistant that helped build the project**, deliberately in different layouts from the generator (informal e-mail style assignments, single-paragraph notices, report excerpts, lecture notes). Written after the generator, so it is not free of the author's expectations. | "Independent hand-written challenge set" - not real-world data |
| `real/` | **Your own documents** (anonymise names, roll numbers, e-mails). Not included. | "Real-world test set" - the only honest estimate of real performance |

None of the shipped data are real college documents.

## 4. Generation design
* 10 subjects (Machine Learning, DBMS, Networks, OS, Data Structures, Software Engineering, NLP, Digital Electronics, Thermodynamics, Cloud Computing) x 7 concepts each, with a definition for every concept.
* **Vocabulary is shared across classes** - every class talks about the same concepts - so the classifier has to rely on *genre* cues (instructions, structure, phrasing), not topic words.
* Per class: optional sections, random ordering, several header styles, mark formats (`[5 marks]`, `(5M)`, ...), 15 % shouting headers, 8 % missing first line, 35 % hard-wrapped lines (imitates PDF extraction).
* Duplicates are rejected, so no two documents in a class are identical.

Regenerate: `python -m datasets.generate_dataset --per-class 60 --seed 42`

## 5. Known limitations
1. **Template similarity.** Test documents share templates with training documents, so the hold-out test split is *easy*. `metrics.json` reports `mean_max_similarity_to_train` (how close each evaluation document is to its nearest training document) so this is measurable, not just claimed.
2. **Learned template phrases.** The strongest features for some classes are phrases from the generator (e.g. "common mistake" for study material). They will not occur in real study notes.
3. **Small evaluation sets.** With 25 challenge documents one error changes accuracy by 4 percentage points; confidence intervals are wide.
4. **English only; no scanned documents (OCR is not supported).**
5. **Five classes only** - a document of any other kind (a certificate, a letter) is still forced into one of the five; low confidence is the only warning.

## 6. How to add real documents (recommended: 15-20 per class)
1. Copy files into `datasets/real/<class>/` (the file name does not matter).
2. Run `python -m app.ml.train`.
3. `metrics.json -> evaluations -> real_set` now holds the real-world result, with every misclassified file listed by name.
4. Real documents are **never used for training** by this script; they are evaluation-only. If you later want to train on them too, move them into `raw/` and re-evaluate on new real documents.

## 7. Evaluation protocol (implemented in `app/ml/train.py`)
1. Stratified 80/20 split of `raw/`, fixed seed.
2. Model selection by 5-fold stratified cross-validation on the 80 % training part **only**.
3. The selected model is fitted on the training part and scored once on the test split, the challenge set and (if present) the real set. Nothing is tuned on the challenge or real sets.
4. Training accuracy is stored separately and labelled as not a performance figure.
