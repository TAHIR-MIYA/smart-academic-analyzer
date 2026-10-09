# Screenshots for the report

Save each image in `docs/screenshots/` with the file name shown, then insert it at the matching figure in
`PROJECT_REPORT.md` Section 16. Use a browser window of about 1400 px width. Use a document you are happy to show (for
example a generated one from `backend/datasets/raw/`) so no personal data appears.

Preparation: start both servers, run `python -m app.ml.train` once, upload three to five documents of different types.

| File | How to capture |
|---|---|
| `fig01_dashboard.png` | Open `/` after analysing several documents. Include the figure row, the class chart and "Classifier results". |
| `fig02_upload.png` | Open `/upload`, drop a large PDF, and capture while the progress bar is moving. |
| `fig03_documents.png` | Open `/documents` showing the status column. |
| `fig04_overview.png` | Open a document, Overview tab. |
| `fig05_preprocessing.png` | Preprocessing tab; capture the cleaning table, stage chart and the stemming table (scroll, or take two shots). |
| `fig06_keywords.png` | Keywords tab, including the "Word groups" section. |
| `fig07_entities.png` | Entities tab. |
| `fig08_prediction.png` | Classification tab, top section (prediction and probabilities). |
| `fig09_evaluation.png` | Classification tab, lower section: choose "Independent challenge set" and include the confusion matrix. |
| `fig10_summary.png` | Summary tab. |
| `fig11_similarity.png` | Similarity tab after running a comparison with a second document. |
| `fig12_statistics.png` | Statistics tab (readability, vocabulary, Zipf chart). |
| `fig13_pdf.png` | Export tab, download the PDF, screenshot its first page. |
| `fig14_training.png` | Terminal output of `python -m app.ml.train` (the "TRAINING SUMMARY" block). |
| `fig15_tests.png` | Terminal showing `pytest` and `npm test` passing. |

Tips: Windows `Win + Shift + S` captures a region. Avoid showing your username or folder path if you do not want it in the
report.
