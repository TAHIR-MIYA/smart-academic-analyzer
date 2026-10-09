# Smart Academic Document Analyzer using Natural Language Processing

A web application that accepts academic documents (PDF, DOCX, TXT) and analyses them with classical NLP:
text extraction, cleaning, tokenisation, stop-word removal, lemmatisation, TF-IDF keywords, n-grams, named entity
recognition, document-type classification, extractive summarisation, similarity analysis, readability and vocabulary
measures, with an interactive dashboard and PDF/JSON export.

It runs on an ordinary laptop: no GPU, no paid API, no document ever leaves your computer.

* Backend: Python, FastAPI, NLTK, spaCy, scikit-learn, PyMuPDF, python-docx, SQLAlchemy (SQLite, MySQL-ready), ReportLab
* Frontend: React, Vite, Tailwind CSS, Recharts
* Documents for the viva: [`VIVA.md`](VIVA.md) (questions and answers), [`PROJECT_REPORT.md`](PROJECT_REPORT.md),
  [`backend/datasets/DATASET.md`](backend/datasets/DATASET.md), [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)

## 1. Objectives

1. Extract text robustly from PDF, DOCX and TXT files and refuse bad input with clear messages.
2. Implement the complete NLP pipeline and make **every stage visible** (before/after, counts, formulas).
3. Classify documents into Assignment, Notice, Question Paper, Project Report or Study Material with a classical,
   explainable model, and report **honest, measured** results (precision, recall, F1, confusion matrix).
4. Summarise, compare and measure documents, and export the analysis.

## 2. Architecture

```text
React + Vite + Tailwind + Recharts          (frontend/)
        |  REST / JSON   (Vite proxies /api to the backend in development)
        v
FastAPI  --  routers (app/api)  ->  services (app/services)  ->  NLP and ML code
   |                                   |
   |                                   +-- app/nlp  : extraction output -> cleaning -> tokenisation -> stop words
   |                                   |             -> lemmatisation -> TF-IDF -> n-grams -> NER -> summary
   |                                   |             -> similarity -> readability -> vocabulary
   |                                   +-- app/ml   : dataset, features, training, evaluation, prediction
   |                                   +-- ReportLab/Matplotlib : PDF report
   +-- SQLAlchemy -> SQLite (documents, analysis_results)
```

Rule: routers never contain NLP logic. They call services, which call plain functions in `app/nlp` and `app/ml`.
That keeps every technique small, testable and explainable.

### Pipeline

`Upload -> validate -> extract -> clean -> sentence split -> tokenise -> lemmatise (spaCy, POS-aware) -> filter words ->
case-fold -> remove stop words -> TF-IDF keywords -> n-grams -> NER -> classify -> summarise -> similarity ->
readability and vocabulary -> store -> visualise / export`

## 3. Folder structure

```text
smart-academic-analyzer/
  README.md  VIVA.md  PROJECT_REPORT.md  TROUBLESHOOTING.md
  docs/                      SCREENSHOTS.md (what to capture for the report) and screenshots/
  backend/
    app/
      main.py  config.py  logging_config.py        application, environment settings, logging
      api/        routes_documents  routes_analysis  routes_model  routes_export  routes_dashboard  routes_health
      services/   document_service  analysis_service  analysis_store  extraction  export_service  model_service
      nlp/        cleaning  tokenization  preprocessing  pipeline  tfidf  ngrams  ner
                  summarizer  similarity  readability  vocabulary  text_stats  resources
      ml/         dataset  features  models  train  evaluate  predict   artifacts/ (model, metrics, charts)
      db/         database  models
      schemas/    Pydantic request and response models
      utils/      errors  file_validation
    datasets/     generate_dataset.py  build_topics.py  raw/  challenge/  real/  topics/  DATASET.md
    scripts/      setup_nlp.py
    tests/        pytest suite (unit, API and end-to-end tests)
    requirements.txt  .env.example
  frontend/
    src/  api/  components/  hooks/  lib/  pages/ (+ pages/document/ tabs)  test/
    package.json  vite.config.js  tailwind.config.js
```

## 4. Installation

Requirements: **Python 3.10 or newer**, **Node.js 18 or newer**, about 1 GB of disk space, an internet connection for the
first installation only.

### 4.1 Backend (Windows PowerShell; on macOS/Linux use `python3` and `source .venv/bin/activate`)

```powershell
cd smart-academic-analyzer
python -m venv .venv
.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process RemoteSigned
cd backend
pip install -r requirements.txt
copy .env.example .env              # optional; the defaults work
```

### 4.2 NLP models (one time)

```powershell
python -m scripts.setup_nlp         # downloads NLTK data (punkt_tab, stopwords) and the spaCy model en_core_web_sm
```

### 4.3 Dataset and model

The synthetic training set (300 documents), the hand-written challenge set (25) and the 10 topic profiles are included.
To regenerate them: `python -m datasets.generate_dataset` and `python -m datasets.build_topics`.

```powershell
python -m app.ml.train              # about 10 to 30 seconds; writes the model, metrics.json, confusion matrices, reference IDF
```

Read [`backend/datasets/DATASET.md`](backend/datasets/DATASET.md) before quoting any accuracy: the training data is synthetic.
To measure real-world performance, put your own documents in `backend/datasets/real/<class>/` and train again.

### 4.4 Frontend

```powershell
cd ..\frontend
npm install
```

## 5. Running

Two terminals.

```powershell
# terminal 1, in backend/ with the virtual environment active
uvicorn app.main:app --reload       # API on http://localhost:8000 , interactive docs on /docs

# terminal 2, in frontend/
npm run dev                         # application on http://localhost:5173
```

Open http://localhost:5173. The sidebar shows whether the API, the classifier and the language data are ready.

Tests: `python -m pytest -q` in `backend/` and `npm test` in `frontend/`.

## 6. Using the application

1. **Upload**: drop PDF, DOCX or TXT files. Each file shows real upload progress and, by default, is analysed straight away.
2. **Dashboard**: totals, the predicted-class distribution of your documents and the classifier's measured results,
   which are kept apart from your documents' predictions.
3. **Documents -> open a document**. Tabs: *Overview, Preprocessing, Keywords, Entities, Classification, Summary,
   Similarity, Statistics, Export*. Every tab explains what was computed and from what.
4. **Classification tab**: first this document's prediction with its confidence, then, under a separate heading, how well
   the classifier works (precision, recall, F1, confusion matrix, how the model was chosen).
5. **Similarity tab**: closest subject profile, and comparison with another document including near-copied sentences.
6. **Export**: a PDF report with charts, or a JSON file with every number.

## 7. API

Interactive documentation: http://localhost:8000/docs. Errors always have the form
`{"error": {"code": "...", "message": "...", "details": ...}}`.

| Method and path | Purpose |
|---|---|
| `GET /api/health` | API, database, language data and model status |
| `POST /api/documents/upload` | Upload a file (multipart field `file`); validates, extracts and stores the text |
| `GET /api/documents` | List documents (with an `analyzed` flag) |
| `GET /api/documents/{document_id}` | One document with its extracted text |
| `DELETE /api/documents/{document_id}` | Delete a document and its saved analysis |
| `POST /api/analysis/{document_id}` | Run every analysis and save the result |
| `GET /api/analysis/{document_id}` | The saved analysis (404 if not run, 409 if saved by an older version) |
| `GET /api/analysis/{document_id}/preprocessing` | Cleaning steps, stage counts, before/after, stemming vs lemmatisation |
| `GET /api/analysis/{document_id}/statistics` | Characters, words, sentences, distributions |
| `GET /api/analysis/{document_id}/keywords` | TF-IDF keywords (`top_k`) |
| `GET /api/analysis/{document_id}/ngrams` | Unigrams, bigrams, trigrams |
| `GET /api/analysis/{document_id}/entities` | Named entities grouped by type |
| `GET /api/analysis/{document_id}/classification` | Predicted class, confidence, probabilities, explanation |
| `GET /api/analysis/{document_id}/summary` | Extractive summary (`sentences`) |
| `GET /api/analysis/{document_id}/readability` | Flesch, Flesch-Kincaid, Gunning Fog, ARI |
| `GET /api/analysis/{document_id}/vocabulary` | TTR, MATTR, hapax ratio, lexical density, Zipf data |
| `GET /api/analysis/{document_id}/similarity` | Cosine similarity to the topic profiles |
| `POST /api/analysis/compare` | Compare two stored documents |
| `POST /api/analysis/preview` | Run the analyses on pasted text (nothing is stored); handy for demos |
| `GET /api/model/metrics` | The training and evaluation results (`metrics.json`) |
| `GET /api/export/{document_id}` | Download the analysis (`format=json` or `pdf`, `refresh=true` to re-run) |
| `GET /api/dashboard/summary` | Figures for the dashboard |

Status codes: `400 invalid_file`, `404 not_found`, `409 analysis_outdated`, `413 file_too_large`,
`415 unsupported_file_type`, `422 empty_document / malformed_document / validation_error`,
`503 nlp_resources_missing / model_not_trained`, `500 internal_error`.

```powershell
curl -F "file=@notes.pdf" http://localhost:8000/api/documents/upload
curl -X POST http://localhost:8000/api/analysis/1
curl -o report.pdf "http://localhost:8000/api/export/1?format=pdf"
```

## 8. Configuration

Settings are read from environment variables or `backend/.env` (see `.env.example`). Nothing secret is needed.

| Variable | Default | Meaning |
|---|---|---|
| `DATABASE_URL` | SQLite file in `backend/data/` | Change to `mysql+pymysql://user:password@host/db` to use MySQL (install `pymysql`) |
| `MAX_UPLOAD_MB` | 10 | Largest accepted upload |
| `MAX_PDF_PAGES` | 300 | Pages read from a PDF (a warning is shown if more) |
| `MIN_TEXT_CHARS` | 20 | Shorter extracted text is rejected as empty |
| `MAX_ANALYSIS_CHARS` | 500000 | Longer texts are truncated for analysis (with a warning) |
| `CLASSIFICATION_MIN_CONFIDENCE` | 0.5 | Below this probability a prediction is flagged as uncertain |
| `REFERENCE_IDF_PATH` | `app/ml/artifacts/reference_idf.json` | Document frequencies built during training |
| `MODEL_PATH` | `app/ml/artifacts/model.joblib` | The trained classifier |
| `METRICS_PATH` | `app/ml/artifacts/metrics.json` | Training and evaluation results |
| `TOPICS_DIR` | `datasets/topics` | Topic profile files for similarity |
| `LOG_LEVEL` | INFO | Logging level; logs go to the console and `backend/logs/app.log` |
| `LOG_DIR` | `backend/logs` | Log folder |
| `CORS_ORIGINS` | the two Vite addresses | JSON list of allowed browser origins |

## 9. Honest limitations

* The classifier is trained on **synthetic** documents. Its score on a split of that data is optimistic; the score on the
  independent challenge set is lower. Only documents you add under `datasets/real/` give a real-world estimate.
* Named entity recognition uses a model trained on news and web text and mislabels some academic terms.
* Scanned (image-only) PDFs are rejected: there is no OCR. Only English is supported.
* Readability formulas use an estimated syllable count and are designed for prose, not lists or notices.
* Document-to-document similarity measures shared wording, not shared meaning.

## 10. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'app'` | Run commands from the `backend/` folder |
| 503 `nlp_resources_missing` | `python -m scripts.setup_nlp`; if spaCy is blocked by Windows see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| 503 `model_not_trained` | `python -m app.ml.train` |
| Many tests are skipped | The language data is missing or spaCy cannot load; check `GET /api/health` |
| `422 empty_document` on a PDF | It is probably scanned images; OCR is not supported |
| Frontend shows "API not reachable" | Start the backend; confirm http://localhost:8000/api/health opens |
| `npm install` fails | Use Node.js 18 or newer (`node --version`) |
| Port 8000 or 5173 already in use | Stop the other program or pass `--port` to uvicorn / `npm run dev -- --port 5174` |
| PowerShell will not activate the environment | `Set-ExecutionPolicy -Scope Process RemoteSigned`, then activate again |

## 11. Tests

Backend: pytest (unit tests for every NLP function, API tests, end-to-end training). Frontend: Vitest and Testing
Library, including a contract test that renders every tab with real payloads captured from the backend. A backend test
(`tests/test_docs.py`) checks that the API table and configuration table above match the running application.
